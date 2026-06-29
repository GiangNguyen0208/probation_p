"""Per-key rate limiting using Redis fixed-window counters.

Two windows are tracked per key:
- `ratelimit:{key_id}:minute` — 60s TTL
- `ratelimit:{key_id}:day` — 86400s TTL

On each request, both counters are incremented. If either exceeds the
key's tier limit, the request is rejected with the remaining TTL as
the `Retry-After` value.

Per-key tier limits match Section 6.3 of the architecture document:

| Tier                  | Per minute | Per day   |
| --------------------- | ---------- | --------- |
| external_default      | 60         | 10_000    |
| external_elevated     | 200        | 50_000    |
| internal              | 1_000      | 1_000_000 |

Burst allowances (per the architecture) are not implemented in Phase 2;
they require a token-bucket algorithm and are deferred to a later phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

import redis.asyncio as aioredis

from ..auth.models import APIKeyTier


@dataclass(frozen=True)
class RateLimits:
    """Per-tier rate limits."""

    requests_per_minute: int
    requests_per_day: int


TIER_LIMITS: dict[APIKeyTier, RateLimits] = {
    APIKeyTier.EXTERNAL_DEFAULT: RateLimits(requests_per_minute=60, requests_per_day=10_000),
    APIKeyTier.EXTERNAL_ELEVATED: RateLimits(requests_per_minute=200, requests_per_day=50_000),
    APIKeyTier.INTERNAL: RateLimits(requests_per_minute=1_000, requests_per_day=1_000_000),
}


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    count_minute: int
    count_day: int
    limit_minute: int
    limit_day: int
    retry_after_seconds: int | None = None


class RateLimitService:
    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def check(self, key_id: UUID, tier: APIKeyTier) -> RateLimitResult:
        """Atomically increment both counters and check the tier limits."""
        limits = TIER_LIMITS[tier]
        minute_key = f"ratelimit:{key_id}:minute"
        day_key = f"ratelimit:{key_id}:day"

        count_minute, ttl_minute = await self._increment(minute_key, 60)
        count_day, ttl_day = await self._increment(day_key, 86400)

        if count_minute > limits.requests_per_minute:
            return RateLimitResult(
                allowed=False,
                count_minute=count_minute,
                count_day=count_day,
                limit_minute=limits.requests_per_minute,
                limit_day=limits.requests_per_day,
                retry_after_seconds=max(1, ttl_minute),
            )
        if count_day > limits.requests_per_day:
            return RateLimitResult(
                allowed=False,
                count_minute=count_minute,
                count_day=count_day,
                limit_minute=limits.requests_per_minute,
                limit_day=limits.requests_per_day,
                retry_after_seconds=max(1, ttl_day),
            )
        return RateLimitResult(
            allowed=True,
            count_minute=count_minute,
            count_day=count_day,
            limit_minute=limits.requests_per_minute,
            limit_day=limits.requests_per_day,
        )

    async def _increment(self, key: str, window_seconds: int) -> tuple[int, int]:
        """INCR a key, set TTL on first increment. Returns (count, ttl_seconds)."""
        pipe = self._redis.pipeline()
        pipe.incr(key)
        # Set TTL only if not already set. Compatible with Redis 6+ and 7.
        pipe.expire(key, window_seconds, nx=True)
        pipe.ttl(key)
        results = await pipe.execute()
        count = int(results[0])
        ttl = int(results[2])
        if ttl < 0:
            ttl = window_seconds
        return count, ttl

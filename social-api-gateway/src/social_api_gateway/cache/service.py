"""Redis cache wrapper for gateway responses.

All operations are best-effort: Redis failures are logged and treated
as cache misses / no-ops, so a Redis outage degrades latency but does
not break request handling. The gateway reads from cache when
available and falls back to the database on miss.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

import redis.asyncio as aioredis

from ..logging_setup import get_logger

logger = get_logger("social_api_gateway.cache")


def hash_query_params(**params: Any) -> str:
    """Stable short hash of query parameters for cache key construction.

    None values are normalized to empty strings so missing params and
    empty strings produce the same hash.
    """
    parts = []
    for k in sorted(params.keys()):
        v = "" if params[k] is None else params[k]
        parts.append(f"{k}={v}")
    raw = "&".join(parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class CacheService:
    """JSON cache backed by Redis. Errors are swallowed."""

    def __init__(self, redis: aioredis.Redis):
        self._redis = redis

    async def get(self, key: str) -> Any | None:
        """Return the cached value for `key`, or None on miss / error / invalid JSON."""
        try:
            raw = await self._redis.get(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("cache.get.failed", key=key, error=str(exc))
            return None
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError) as exc:
            logger.warning("cache.get.invalid_json", key=key, error=str(exc))
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """Store `value` at `key` with the given TTL. Errors are swallowed."""
        try:
            await self._redis.set(
                key,
                json.dumps(value, default=str),
                ex=ttl_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("cache.set.failed", key=key, error=str(exc))

    async def delete(self, key: str) -> None:
        try:
            await self._redis.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("cache.delete.failed", key=key, error=str(exc))

    async def delete_prefix(self, prefix: str) -> None:
        """Delete all keys starting with `prefix`. Uses SCAN to avoid blocking."""
        try:
            async for key in self._redis.scan_iter(match=f"{prefix}*"):
                await self._redis.delete(key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("cache.delete_prefix.failed", prefix=prefix, error=str(exc))

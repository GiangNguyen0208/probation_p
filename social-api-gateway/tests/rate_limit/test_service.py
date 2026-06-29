"""Tests for the rate limit service."""

from __future__ import annotations

from uuid import uuid4

import fakeredis.aioredis
import pytest

from social_api_gateway.auth.models import APIKeyTier
from social_api_gateway.rate_limit.service import (
    TIER_LIMITS,
    RateLimitService,
)


@pytest.mark.asyncio
async def test_first_request_is_allowed():
    redis = fakeredis.aioredis.FakeRedis()
    service = RateLimitService(redis)
    result = await service.check(uuid4(), APIKeyTier.INTERNAL)
    assert result.allowed is True
    assert result.count_minute == 1
    assert result.count_day == 1
    await redis.aclose()


@pytest.mark.asyncio
async def test_per_minute_limit_exceeded():
    redis = fakeredis.aioredis.FakeRedis()
    service = RateLimitService(redis)
    key_id = uuid4()
    limits = TIER_LIMITS[APIKeyTier.EXTERNAL_DEFAULT]
    for _ in range(limits.requests_per_minute):
        result = await service.check(key_id, APIKeyTier.EXTERNAL_DEFAULT)
        assert result.allowed is True
    result = await service.check(key_id, APIKeyTier.EXTERNAL_DEFAULT)
    assert result.allowed is False
    assert result.retry_after_seconds is not None
    assert result.retry_after_seconds > 0
    await redis.aclose()


@pytest.mark.asyncio
async def test_per_day_limit_exceeded():
    redis = fakeredis.aioredis.FakeRedis()
    service = RateLimitService(redis)
    key_id = uuid4()
    # Pre-populate the day counter near the limit
    day_key = f"ratelimit:{key_id}:day"
    limits = TIER_LIMITS[APIKeyTier.EXTERNAL_DEFAULT]
    await redis.set(day_key, limits.requests_per_day, ex=86400)
    result = await service.check(key_id, APIKeyTier.EXTERNAL_DEFAULT)
    assert result.allowed is False
    assert result.retry_after_seconds is not None
    await redis.aclose()


@pytest.mark.asyncio
async def test_different_keys_have_independent_counters():
    redis = fakeredis.aioredis.FakeRedis()
    service = RateLimitService(redis)
    limits = TIER_LIMITS[APIKeyTier.EXTERNAL_DEFAULT]
    for _ in range(limits.requests_per_minute):
        result = await service.check(uuid4(), APIKeyTier.EXTERNAL_DEFAULT)
        assert result.allowed is True
    # A different key is still allowed
    result = await service.check(uuid4(), APIKeyTier.EXTERNAL_DEFAULT)
    assert result.allowed is True
    await redis.aclose()


@pytest.mark.asyncio
async def test_internal_tier_has_higher_limit():
    internal_limits = TIER_LIMITS[APIKeyTier.INTERNAL]
    external_limits = TIER_LIMITS[APIKeyTier.EXTERNAL_DEFAULT]
    assert internal_limits.requests_per_minute > external_limits.requests_per_minute
    assert internal_limits.requests_per_day > external_limits.requests_per_day

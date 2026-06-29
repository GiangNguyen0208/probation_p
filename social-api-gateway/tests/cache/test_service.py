"""Tests for the cache service."""

from __future__ import annotations

import fakeredis.aioredis
import pytest

from social_api_gateway.cache.service import CacheService, hash_query_params


@pytest.mark.asyncio
async def test_set_and_get_roundtrip():
    redis = fakeredis.aioredis.FakeRedis()
    cache = CacheService(redis)
    await cache.set("k1", {"a": 1}, ttl_seconds=60)
    assert await cache.get("k1") == {"a": 1}
    await redis.aclose()


@pytest.mark.asyncio
async def test_get_missing_returns_none():
    redis = fakeredis.aioredis.FakeRedis()
    cache = CacheService(redis)
    assert await cache.get("missing") is None
    await redis.aclose()


@pytest.mark.asyncio
async def test_get_invalid_json_returns_none():
    redis = fakeredis.aioredis.FakeRedis()
    await redis.set("bad", "not valid json")
    cache = CacheService(redis)
    assert await cache.get("bad") is None
    await redis.aclose()


@pytest.mark.asyncio
async def test_delete_removes_key():
    redis = fakeredis.aioredis.FakeRedis()
    cache = CacheService(redis)
    await cache.set("k1", {"a": 1}, ttl_seconds=60)
    await cache.delete("k1")
    assert await cache.get("k1") is None
    await redis.aclose()


@pytest.mark.asyncio
async def test_delete_prefix_removes_matching_keys():
    redis = fakeredis.aioredis.FakeRedis()
    cache = CacheService(redis)
    await cache.set("cache:subjects:list:abc", {"a": 1}, ttl_seconds=60)
    await cache.set("cache:subjects:list:def", {"b": 2}, ttl_seconds=60)
    await cache.set("cache:subject:uuid", {"c": 3}, ttl_seconds=60)
    await cache.delete_prefix("cache:subjects:list:")
    assert await cache.get("cache:subjects:list:abc") is None
    assert await cache.get("cache:subjects:list:def") is None
    assert await cache.get("cache:subject:uuid") == {"c": 3}
    await redis.aclose()


def test_hash_query_params_deterministic():
    h1 = hash_query_params(platform="facebook", status="active", page=1, limit=20)
    h2 = hash_query_params(platform="facebook", status="active", page=1, limit=20)
    assert h1 == h2


def test_hash_query_params_differs_on_value():
    h1 = hash_query_params(platform="facebook", page=1)
    h2 = hash_query_params(platform="youtube", page=1)
    assert h1 != h2


def test_hash_query_params_treats_none_as_empty():
    h1 = hash_query_params(platform="facebook", status=None)
    h2 = hash_query_params(platform="facebook", status="")
    assert h1 == h2

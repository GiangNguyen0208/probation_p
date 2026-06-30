"""FastAPI dependencies for the gateway.

API key dependencies:
1. `get_db_session` — async DB session per request.
2. `get_redis_client` — async Redis client per request.
3. `get_cache_service` — CacheService wrapping the Redis client.
4. `get_api_key` — extracts key from headers, looks it up, verifies hash.
5. `rate_limit` — depends on get_api_key; increments counters, returns 429 on excess.

JWT / Telegram auth dependencies:
6. `get_current_user` — extracts and verifies a Bearer JWT, returns user info.
7. `rate_limit_auth` — IP-based rate limiting (10 req/min per IP) for unauthenticated endpoints.

Route handlers compose these via `Depends(...)`. Tests override the
underlying dependencies in `app.dependency_overrides` to use SQLite +
fakeredis without spinning up external services.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

import jwt
from celery import Celery
from fastapi import Depends, Header, HTTPException, Request, Response, status
from jwt import PyJWTError
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from .auth.models import APIKeyModel
from .auth.security import key_prefix as key_prefix_extract
from .auth.security import verify_key
from .auth.service import APIKeyService
from .cache.service import CacheService
from .config import get_settings
from .db import get_engine, get_session_factory
from .logging_setup import get_logger
from .rate_limit.service import TIER_LIMITS, RateLimitService

logger = get_logger("social_api_gateway.deps")


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield a short-lived async DB session per request."""
    settings = get_settings()
    engine = get_engine(settings.database)
    session_factory = get_session_factory(engine)
    async with session_factory() as session:
        yield session


async def get_redis_client() -> AsyncIterator[Redis]:
    """Yield an async Redis client per request."""
    settings = get_settings()
    client = Redis.from_url(settings.redis.url, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


async def get_cache_service(
    redis: Redis = Depends(get_redis_client),
) -> CacheService:
    """Wrap the Redis client in a CacheService."""
    return CacheService(redis)


def get_celery_client() -> Celery:
    """Return a Celery client instance connected to the shared Redis broker."""
    settings = get_settings()
    return Celery(
        "social_data_collector",
        broker=settings.redis.url,
        backend=settings.redis.url,
    )


def _extract_key(authorization: str | None, x_api_key: str | None) -> str | None:
    """Extract the raw API key from request headers."""
    if x_api_key:
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


async def get_api_key(
    db: AsyncSession = Depends(get_db_session),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> APIKeyModel:
    """Authenticate the caller by API key. Raises 401 on failure."""
    raw_key = _extract_key(authorization, x_api_key)
    if not raw_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_api_key", "message": "API key is required."},
            headers={"WWW-Authenticate": "Bearer, X-API-Key"},
        )
    if len(raw_key) < 8:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_api_key", "message": "API key is invalid."},
        )

    settings = get_settings()
    service = APIKeyService(db)
    api_key = await service.lookup_by_prefix(key_prefix_extract(raw_key))

    pepper = settings.auth.pepper.get_secret_value()
    if api_key is None or not verify_key(raw_key, api_key.key_hash, pepper):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_api_key", "message": "API key is invalid or revoked."},
        )

    if not api_key.is_active or api_key.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "revoked_api_key", "message": "API key has been revoked."},
        )

    return api_key


async def rate_limit(
    response: Response,
    api_key: APIKeyModel = Depends(get_api_key),
    redis: Redis = Depends(get_redis_client),
) -> APIKeyModel:
    """Apply per-key rate limiting. Sets rate-limit headers on the response.

    Fails open if Redis is unreachable: the request is allowed and a
    warning is logged. The gateway prefers a transient rate-limit
    outage over a full service outage.
    """
    limits = TIER_LIMITS[api_key.tier]
    try:
        result = await RateLimitService(redis).check(api_key.id, api_key.tier)
    except Exception as exc:  # noqa: BLE001
        logger.warning("rate_limit.check_failed", error=str(exc), key_id=str(api_key.id))
        return api_key

    response.headers["X-RateLimit-Limit-Minute"] = str(limits.requests_per_minute)
    response.headers["X-RateLimit-Limit-Day"] = str(limits.requests_per_day)
    response.headers["X-RateLimit-Remaining-Minute"] = str(
        max(0, limits.requests_per_minute - result.count_minute)
    )
    response.headers["X-RateLimit-Remaining-Day"] = str(
        max(0, limits.requests_per_day - result.count_day)
    )

    if not result.allowed:
        logger.warning(
            "rate_limit.exceeded",
            key_id=str(api_key.id),
            tier=api_key.tier.value,
            retry_after=result.retry_after_seconds,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited", "message": "Rate limit exceeded."},
            headers={"Retry-After": str(result.retry_after_seconds or 60)},
        )

    return api_key


# ---------------------------------------------------------------------------
# JWT / Telegram auth
# ---------------------------------------------------------------------------


def _get_client_ip(request: Request) -> str:
    """Extract the client IP from the request, respecting proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "127.0.0.1"


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict[str, Any]:
    """Extract and verify a Bearer JWT from the Authorization header.

    Returns a dict with ``telegram_id``, ``name``, and ``username``
    on success. Raises ``401`` if the token is missing, expired, or
    tampered with.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_token", "message": "Authorization Bearer token is required."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization[7:].strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_token", "message": "Authorization Bearer token is required."},
            headers={"WWW-Authenticate": "Bearer"},
        )
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt.secret.get_secret_value(),
            algorithms=[settings.jwt.algorithm],
        )
    except PyJWTError as exc:
        logger.warning("auth.jwt_invalid", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Token is invalid or expired."},
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    telegram_id = payload.get("sub")
    if not telegram_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_token", "message": "Token payload is malformed."},
        )

    return {
        "telegram_id": int(telegram_id),
        "name": payload.get("name", ""),
        "username": payload.get("username", ""),
    }


async def rate_limit_auth(
    request: Request,
    redis: Redis = Depends(get_redis_client),
) -> None:
    """IP-based rate limiting for unauthenticated endpoints (e.g. login).

    10 requests per minute per IP. Use ``Depends(rate_limit_auth)``
    on public endpoints that need to be gated before authentication.
    """
    ip = _get_client_ip(request)
    key = f"ratelimit:auth:{ip}:minute"
    pipe = redis.pipeline()
    pipe.incr(key)
    pipe.expire(key, 60, nx=True)
    pipe.ttl(key)
    results = await pipe.execute()
    count = int(results[0])
    ttl = int(results[2])
    if ttl < 0:
        ttl = 60
    if count > 10:
        logger.warning("auth.rate_limit.exceeded", ip=ip, count=count)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limited", "message": "Too many requests. Try again later."},
            headers={"Retry-After": str(max(1, ttl))},
        )

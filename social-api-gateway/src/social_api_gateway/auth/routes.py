"""Authentication endpoints for the Telegram Mini App.

Two routes are provided:

1. ``POST /v1/auth/telegram-login`` — accepts initData signed by Telegram,
   verifies the signature, upserts the user in ``telegram_users``, and
   returns a short-lived JWT for subsequent API calls.
2. ``POST /v1/auth/refresh`` — (future) refresh an expiring JWT.
"""

from __future__ import annotations

import time
from typing import Any

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from redis.asyncio import Redis
from sqlalchemy import select as sa_select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..deps import get_db_session, get_redis_client
from ..logging_setup import get_logger
from ..telegram.initdata import verify_init_data
from .models import TelegramUserModel, UserRole

logger = get_logger("social_api_gateway.auth.routes")

router = APIRouter(prefix="/v1/auth", tags=["auth"])


# ---------------------------------------------------------------------------
# Helpers
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


async def _check_auth_rate_limit(redis: Redis, ip: str) -> None:
    """IP-based rate limit for the auth endpoint: 10 req/min."""
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
            detail={"code": "rate_limited", "message": "Too many login attempts. Try again later."},
            headers={"Retry-After": str(max(1, ttl))},
        )


async def _upsert_telegram_user(
    db: AsyncSession,
    telegram_id: int,
    first_name: str,
    last_name: str | None,
    username: str | None,
    language_code: str | None,
) -> TelegramUserModel:
    """Upsert a Telegram user — insert on first login, update on subsequent logins."""
    result = await db.execute(
        sa_select(TelegramUserModel).where(TelegramUserModel.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()
    if user is None:
        user = TelegramUserModel(
            telegram_id=telegram_id,
            first_name=first_name,
            last_name=last_name,
            username=username,
            language_code=language_code,
        )
        db.add(user)
    else:
        user.first_name = first_name
        user.last_name = last_name
        user.username = username
        user.language_code = language_code
    await db.flush()
    await db.commit()
    return user


def _mint_jwt(telegram_id: int, first_name: str, username: str | None, role: str = UserRole.USER) -> str:
    """Create a signed JWT for the authenticated Telegram user."""
    settings = get_settings()
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": str(telegram_id),
        "name": first_name,
        "username": username or "",
        "role": role,
        "iat": now,
        "exp": now + settings.jwt.expiry_hours * 3600,
    }
    return jwt.encode(payload, settings.jwt.secret.get_secret_value(), algorithm=settings.jwt.algorithm)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post(
    "/telegram-login",
    summary="Login via Telegram initData",
    description=(
        "Accept a Telegram WebApp initData string, verify its HMAC-SHA-256 "
        "signature using the bot token, and return a JWT session token. "
        "The user is upserted in the `telegram_users` table on each login."
    ),
    responses={
        200: {
            "description": "Login successful",
            "content": {
                "application/json": {
                    "example": {
                        "token": "eyJhbGciOiJIUzI1NiIs...",
                        "user": {"id": 123456789, "first_name": "John", "username": "johndoe", "role": "user"},
                    }
                }
            },
        },
        401: {"description": "Invalid or expired initData"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def telegram_login(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
) -> dict[str, Any]:
    """Verify the Telegram initData signature and return a JWT."""
    ip = _get_client_ip(request)
    await _check_auth_rate_limit(redis, ip)

    try:
        body: dict[str, Any] = await request.json()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_body", "message": "Request body must be valid JSON."},
        ) from None

    init_data: str | None = body.get("init_data")
    if not init_data or not isinstance(init_data, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "missing_init_data",
                "message": "The 'init_data' field is required in the request body.",
            },
        )

    settings = get_settings()
    bot_token = settings.telegram.bot_token.get_secret_value()
    if not bot_token:
        logger.error("auth.bot_token_not_configured")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "server_error", "message": "Authentication is not configured."},
        )

    user_data = verify_init_data(init_data, bot_token)
    if user_data is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_init_data", "message": "Invalid or expired initData."},
        )

    db_user = await _upsert_telegram_user(
        db,
        telegram_id=user_data.id,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        username=user_data.username,
        language_code=user_data.language_code,
    )

    token = _mint_jwt(
        user_data.id,
        user_data.first_name,
        user_data.username,
        role=db_user.role.value,
    )

    logger.info(
        "auth.login_success",
        telegram_id=user_data.id,
        username=user_data.username,
        role=db_user.role.value,
    )

    return {
        "token": token,
        "user": {
            "id": db_user.telegram_id,
            "first_name": db_user.first_name,
            "last_name": db_user.last_name,
            "username": db_user.username,
            "role": db_user.role.value,
        },
    }

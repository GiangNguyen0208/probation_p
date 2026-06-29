"""/v1/health endpoint."""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..deps import get_db_session, get_redis_client

router = APIRouter(prefix="/v1/health", tags=["health"])


@router.get(
    "",
    summary="Health check",
    description=(
        "Liveness and dependency check. Returns 200 with `status: ok` when "
        "the database is reachable, `degraded` otherwise. The Redis check "
        "is included but does not affect the overall status because the "
        "cache falls back gracefully to the database on Redis errors."
    ),
)
async def health(
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis_client),
) -> dict[str, Any]:
    started = time.perf_counter()
    db_status = "ok"
    db_error: str | None = None
    redis_status = "ok"
    redis_error: str | None = None

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_status = "down"
        db_error = str(exc)

    try:
        await redis.ping()
    except Exception as exc:  # noqa: BLE001
        redis_status = "down"
        redis_error = str(exc)

    overall = "ok" if db_status == "ok" else "degraded"
    return {
        "status": overall,
        "latency_ms": round((time.perf_counter() - started) * 1000, 2),
        "checks": {
            "database": {"status": db_status, "error": db_error},
            "redis": {"status": redis_status, "error": redis_error},
        },
    }

"""Health check for the collector service.

Verifies that Postgres and Redis are reachable. The scheduler status
is reported separately (it depends on a running beat process which is
external to this service in production).
"""

from __future__ import annotations

import time
from typing import Any

import redis
from sqlalchemy import text

from .config import get_settings
from .logging_setup import get_logger
from .persistence.db import get_engine

logger = get_logger("social_data_collector.health")


def _check_database() -> dict[str, Any]:
    settings = get_settings()
    engine = get_engine(settings.database)
    started = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as exc:  # noqa: BLE001 - we want to capture any failure
        logger.error("health.database.failed", error=str(exc))
        return {"status": "down", "error": str(exc)}


def _check_redis() -> dict[str, Any]:
    settings = get_settings()
    client = redis.Redis.from_url(settings.redis.url)
    started = time.perf_counter()
    try:
        client.ping()
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as exc:  # noqa: BLE001
        logger.error("health.redis.failed", error=str(exc))
        return {"status": "down", "error": str(exc)}


def run_health_check() -> dict[str, Any]:
    """Run all health checks and return a structured result.

    The top-level status is "ok" only if every check is "ok".
    """
    db = _check_database()
    rds = _check_redis()

    overall = "ok" if db["status"] == "ok" and rds["status"] == "ok" else "degraded"

    return {
        "status": overall,
        "checks": {
            "database": db,
            "redis": rds,
        },
    }

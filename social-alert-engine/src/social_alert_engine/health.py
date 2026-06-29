import time
from typing import Any

import redis
from sqlalchemy import create_engine, text

from .logging_setup import get_logger
from .settings import get_settings

logger = get_logger("social_alert_engine.health")


def _check_database() -> dict[str, Any]:
    settings = get_settings()
    engine = create_engine(settings.database.url)
    started = time.perf_counter()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as exc:
        logger.error("health.database.failed", error=str(exc))
        return {"status": "down", "error": str(exc)}
    finally:
        engine.dispose()


def _check_redis() -> dict[str, Any]:
    settings = get_settings()
    client = redis.Redis.from_url(settings.redis.url)
    started = time.perf_counter()
    try:
        client.ping()
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        return {"status": "ok", "latency_ms": latency_ms}
    except Exception as exc:
        logger.error("health.redis.failed", error=str(exc))
        return {"status": "down", "error": str(exc)}
    finally:
        client.close()


def run_health_check() -> dict[str, Any]:
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

"""Celery application and beat schedule for the alert engine.

Runs as a separate Celery app from the collector (ADR-00X Decision 1).
Shares the same Redis broker. Beat schedule periodically evaluates all
subjects with active alert rules.
"""

from __future__ import annotations

from celery import Celery  # type: ignore[import-untyped]
from celery.schedules import crontab  # type: ignore[import-untyped]
from social_common.constants import TASK_EVALUATE_ALL_ALERTS

from .logging_setup import configure_logging
from .settings import get_settings

_settings = get_settings()

celery_app = Celery(
    "social_alert_engine",
    broker=_settings.redis.url,
    backend=_settings.redis.url,
    include=["social_alert_engine.tasks"],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_max_tasks_per_child=200,
    worker_prefetch_multiplier=1,
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

_interval = _settings.alert.evaluation_interval_seconds
_beat_schedule: dict[str, dict[str, object]] = {
    "evaluate-all-alerts": {
        "task": TASK_EVALUATE_ALL_ALERTS,
        "schedule": crontab(minute=f"*/{max(1, _interval // 60)}"),
    },
}

celery_app.conf.beat_schedule = _beat_schedule

configure_logging(_settings.runtime.log_level)

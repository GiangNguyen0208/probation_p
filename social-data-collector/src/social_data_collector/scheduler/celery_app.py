"""Celery application and beat schedule.

Two periodic tasks: one for Facebook, one for YouTube. Each task
iterates over the configured platform IDs and dispatches a per-
subject sync task. The per-subject tasks are retryable so a single
bad subject does not stall the rest of the cycle.

The beat schedule fires at `SYNC_DEFAULT_INTERVAL_MINUTES` intervals.
Each platform can be independently disabled via `SYNC_FACEBOOK_ENABLED`
/ `SYNC_YOUTUBE_ENABLED`. For dev, run `worker --beat` in one process;
for prod, split into separate worker and beat containers.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from ..config import get_settings
from ..logging_setup import configure_logging

_settings = get_settings()

celery_app = Celery(
    "social_data_collector",
    broker=_settings.redis.url,
    backend=_settings.redis.url,
    include=["social_data_collector.scheduler.tasks"],
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

_interval = _settings.sync.default_interval_minutes

_beat_schedule: dict[str, dict[str, object]] = {}

if _settings.sync.facebook_enabled:
    _beat_schedule["sync-facebook-cycle"] = {
        "task": "social_data_collector.scheduler.tasks.sync_all_facebook_subjects",
        "schedule": crontab(minute=f"*/{_interval}"),
    }

if _settings.sync.youtube_enabled:
    _beat_schedule["sync-youtube-cycle"] = {
        "task": "social_data_collector.scheduler.tasks.sync_all_youtube_subjects",
        "schedule": crontab(minute=f"*/{_interval}"),
    }

celery_app.conf.beat_schedule = _beat_schedule


# Ensure logging is configured when the worker or beat process starts.
configure_logging(_settings.runtime.log_level)

"""Celery tasks for periodic and on-demand alert evaluation.

Task hierarchy:
- `evaluate_all_alerts`: periodic beat task — iterates over all subjects
  with active rules and dispatches per-subject evaluation.
- `evaluate_subject_alerts`: per-subject task, called both by the beat
  loop and by the collector after a successful sync (via send_task).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from celery import shared_task  # type: ignore[import-untyped]
from social_common.constants import TASK_EVALUATE_ALL_ALERTS, TASK_EVALUATE_SUBJECT_ALERTS
from sqlalchemy import select

from .db import get_session_factory
from .evaluator import evaluate_subject
from .logging_setup import get_logger
from .models import AlertRuleModel

logger = get_logger("social_alert_engine.tasks")


def _subjects_with_active_rules() -> list[UUID]:
    """Return distinct subject IDs that have at least one active rule."""
    factory = get_session_factory()
    with factory() as session:
        rows = (
            session.execute(
                select(AlertRuleModel.subject_id).where(AlertRuleModel.is_active).distinct()
            )
            .scalars()
            .all()
        )
    return list(rows)


@shared_task(  # type: ignore[untyped-decorator]
    name=TASK_EVALUATE_ALL_ALERTS,
    bind=True,
)
def evaluate_all_alerts(self: Any) -> int:
    """Evaluate all subjects with active alert rules.

    Triggered by the beat schedule. Returns the total number of
    delivered alerts across all subjects.
    """
    subject_ids = _subjects_with_active_rules()
    logger.info(
        "tasks.evaluate_all.start",
        subjects_with_rules=len(subject_ids),
    )

    total = 0
    for sid in subject_ids:
        try:
            total += evaluate_subject(sid)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "tasks.evaluate_all.subject_error",
                subject_id=str(sid),
                error=str(exc),
            )

    logger.info("tasks.evaluate_all.complete", total_delivered=total)
    return total


@shared_task(  # type: ignore[untyped-decorator]
    name=TASK_EVALUATE_SUBJECT_ALERTS,
    bind=True,
)
def evaluate_subject_alerts(self: Any, subject_id: str) -> int:
    """Evaluate alerts for a single subject.

    Called by the collector via send_task after a successful sync,
    or directly by the beat loop.
    """
    try:
        uid = UUID(subject_id)
    except ValueError:
        logger.error("tasks.invalid_subject_id", subject_id=subject_id)
        return 0

    logger.info("tasks.evaluate_subject.start", subject_id=subject_id)
    count = evaluate_subject(uid)
    logger.info(
        "tasks.evaluate_subject.complete",
        subject_id=subject_id,
        delivered=count,
    )
    return count

"""Baseline computation for alert rule evaluation."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from .db import get_session_factory
from .logging_setup import get_logger
from .models import ActivitySnapshotModel

logger = get_logger("social_alert_engine.baseline")


class BaselineResult:
    """Aggregate statistics derived from recent activity snapshots."""

    def __init__(self, followers: Sequence[int], frequencies: Sequence[float]) -> None:
        self.followers = list(followers)
        self.frequencies = list(frequencies)
        n = len(followers) or 1
        self.follower_mean: float = sum(followers) / n
        self.frequency_mean: float = sum(frequencies) / n
        self.follower_stdev: float = _stdev(followers)
        self.frequency_stdev: float = _stdev(frequencies)


def _stdev(values: Sequence[int | float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((float(v) - mean) ** 2 for v in values) / (n - 1)
    return float(variance**0.5)


def compute_baseline(
    subject_id: str,
    window_hours: int = 24,
    min_snapshots: int = 3,
) -> BaselineResult | None:
    """Compute a baseline from recent activity snapshots.

    Args:
        subject_id: UUID of the subject to compute baseline for.
        window_hours: How many hours of snapshots to consider (default 24).
        min_snapshots: Minimum number of snapshots required (default 3).

    Returns:
        BaselineResult if enough snapshots are found, None otherwise.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)

    factory = get_session_factory()
    with factory() as session:
        stmt = (
            select(ActivitySnapshotModel)
            .where(
                ActivitySnapshotModel.subject_id == subject_id,
                ActivitySnapshotModel.captured_at >= cutoff,
            )
            .order_by(ActivitySnapshotModel.captured_at.asc())
        )
        rows = list(session.execute(stmt).scalars().all())

    if len(rows) < min_snapshots:
        logger.info(
            "baseline.insufficient_data",
            subject_id=subject_id,
            found=len(rows),
            required=min_snapshots,
        )
        return None

    followers = [r.followers for r in rows]
    frequencies = [r.frequency for r in rows]

    logger.info(
        "baseline.computed",
        subject_id=subject_id,
        snapshots=len(rows),
        follower_mean=round(sum(followers) / len(followers), 2),
        frequency_mean=round(sum(frequencies) / len(frequencies), 4),
    )

    return BaselineResult(followers=followers, frequencies=frequencies)

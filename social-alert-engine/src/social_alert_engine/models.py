"""SQLAlchemy ORM models for the alert engine.

The alert engine owns the `alert_logs` table (created by its own
migration). Subject, snapshot, and alert-rule tables are mirrored as
read-only models so the evaluator can query them without importing the
collector or gateway packages.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from social_common.enums import AlertRuleType, Platform, SubjectStatus
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AlertLogModel(Base):
    """Record of a single alert firing event.

    Owned by the alert engine — written by evaluator.py, read by the
    gateway's read-only mirror for the mini-app alert history panel.
    """

    __tablename__ = "alert_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    rule_type: Mapped[AlertRuleType] = mapped_column(
        SAEnum(
            AlertRuleType,
            name="alert_rule_type_enum",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class SubjectModel(Base):
    """Read-only mirror of the collector's subjects table."""

    __tablename__ = "subjects"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    platform: Mapped[Platform] = mapped_column(
        SAEnum(Platform, name="platform_enum", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    platform_id: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    display_name: Mapped[str] = mapped_column(String(500), nullable=False)
    followers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    post_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activity_frequency: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[SubjectStatus] = mapped_column(
        SAEnum(
            SubjectStatus,
            name="subject_status_enum",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    extended_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    credential_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)


class ActivitySnapshotModel(Base):
    """Read-only mirror of the collector's activity_snapshots table."""

    __tablename__ = "activity_snapshots"

    subject_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    followers: Mapped[int] = mapped_column(Integer, nullable=False)
    post_count: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[float] = mapped_column(Float, nullable=False)


class AlertRuleModel(Base):
    """Read-only mirror of the collector's alert_rules table."""

    __tablename__ = "alert_rules"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    subject_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[AlertRuleType] = mapped_column(
        SAEnum(
            AlertRuleType,
            name="alert_rule_type_enum",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

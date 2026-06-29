"""SQLAlchemy model for alert rules (read/write mirror).

The `alert_rules` table is owned by the collector (created by its 0001
migration). The gateway mirrors the model so it can read and write rows
without a migration of its own.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from social_common.enums import AlertRuleType
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class AlertRuleModel(Base):
    __tablename__ = "alert_rules"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
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
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )


class AlertLogModel(Base):
    """Read-only mirror of the alert engine's alert_logs table."""

    __tablename__ = "alert_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    subject_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False
    )
    rule_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("alert_rules.id", ondelete="SET NULL"), nullable=True
    )
    rule_type: Mapped[AlertRuleType] = mapped_column(
        SAEnum(
            AlertRuleType,
            name="alert_rule_type_enum",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    delivered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

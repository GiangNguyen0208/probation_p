"""SQLAlchemy ORM models mirroring the social-common schemas.

These are the persistent representation. The Pydantic schemas in
social-common are the wire/contract representation. Repository
functions convert between them.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from social_common.enums import AlertRuleType, Platform, SubjectStatus
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class SubjectModel(Base):
    __tablename__ = "subjects"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    platform: Mapped[Platform] = mapped_column(
        SAEnum(Platform, name="platform_enum", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        index=True,
    )
    platform_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
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
        default=SubjectStatus.ACTIVE,
    )
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    extended_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    credential_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("platform_credentials.id", ondelete="SET NULL"),
        unique=True,
        nullable=True,
    )

    snapshots: Mapped[list[ActivitySnapshotModel]] = relationship(
        back_populates="subject", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("platform", "platform_id", name="uq_subjects_platform_platform_id"),
    )


class ActivitySnapshotModel(Base):
    __tablename__ = "activity_snapshots"

    # Composite primary key including the partitioning column. TimescaleDB
    # requires the partitioning column to participate in either the PK or a
    # unique constraint with an index.
    subject_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    followers: Mapped[int] = mapped_column(Integer, nullable=False)
    post_count: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[float] = mapped_column(Float, nullable=False)

    subject: Mapped[SubjectModel] = relationship(back_populates="snapshots")


class VideoModel(Base):
    __tablename__ = "videos"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    platform_video_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration: Mapped[str | None] = mapped_column(String(20), nullable=True)
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    like_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    __table_args__ = (
        UniqueConstraint(
            "subject_id", "platform_video_id", name="uq_videos_subject_platform_video"
        ),
    )


class AlertRuleModel(Base):
    """Alert rule table. Logic ships in Phase 4; the table is created now
    so the schema is stable and migration history is clean.
    """

    __tablename__ = "alert_rules"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    subject_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
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
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    channel_id: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class AlertLogModel(Base):
    """Read-only mirror of the alert engine's alert_logs table."""

    __tablename__ = "alert_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
    subject_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        nullable=False,
    )
    rule_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("alert_rules.id", ondelete="SET NULL"),
        nullable=True,
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


class PlatformModel(Base):
    """Registered platform definition.

    Seeded at deploy time, extended via admin API. The `config_schema`
    JSONB describes what credential fields are required for this platform
    (e.g. `{"access_token": {"type": "string", "sensitive": true}}`).
    """

    __tablename__ = "platforms"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    auth_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config_schema: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    icon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class PlatformCredentialModel(Base):
    """Stored credentials for one connected account on a platform.

    The `credentials` JSONB is encrypted at rest via `cryptography.fernet`.
    Each credential maps to exactly one subject (enforced by the UNIQUE
    constraint on `subjects.credential_id`).
    """

    __tablename__ = "platform_credentials"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    platform_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("platforms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    credentials: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="active")
    last_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

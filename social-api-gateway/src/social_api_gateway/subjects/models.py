"""SQLAlchemy models for subjects and activity snapshots (read-only).

These mirror the schema written by the data collector. The gateway
is read-only on these tables: the collector owns writes. The two
services share a database but maintain independent ORM models so they
can be deployed independently.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from social_common.enums import Platform, SubjectStatus
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


class SubjectModel(Base):
    __tablename__ = "subjects"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
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
        default=SubjectStatus.ACTIVE,
    )
    last_synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    extended_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"), nullable=True
    )
    credential_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("platform", "platform_id", name="uq_subjects_platform_platform_id"),
    )


class ActivitySnapshotModel(Base):
    __tablename__ = "activity_snapshots"

    subject_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("subjects.id", ondelete="CASCADE"),
        primary_key=True,
    )
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    followers: Mapped[int] = mapped_column(Integer, nullable=False)
    post_count: Mapped[int] = mapped_column(Integer, nullable=False)
    frequency: Mapped[float] = mapped_column(Float, nullable=False)


class VideoModel(Base):
    __tablename__ = "videos"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True)
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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "subject_id", "platform_video_id", name="uq_videos_subject_platform_video"
        ),
    )

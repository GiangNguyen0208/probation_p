"""Repository functions for the data collector.

These functions are the only ones that touch the database from the
collector. They:
- Upsert subjects by (platform, platform_id) — idempotent.
- Append activity snapshots — never updated, only inserted.
- Convert between Pydantic schemas (social-common) and SQLAlchemy
  ORM models.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar, cast
from uuid import UUID

from social_common.enums import Platform
from social_common.schemas import ActivitySnapshot, Subject, Video
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .db import get_session_factory
from .models import ActivitySnapshotModel, SubjectModel, VideoModel

_T = TypeVar("_T")


def upsert_subject(session: Session, subject: Subject) -> UUID:
    """Insert a subject or update it if (platform, platform_id) already exists.

    Returns the subject's id. The existing id is preserved on update
    so historical snapshots remain linked to the same UUID.
    """
    values = {
        "id": subject.id,
        "platform": subject.platform,
        "platform_id": subject.platform_id,
        "name": subject.name,
        "display_name": subject.display_name,
        "followers": subject.followers,
        "post_count": subject.post_count,
        "activity_frequency": subject.activity_frequency,
        "status": subject.status,
        "last_synced_at": subject.last_synced_at,
        "extended_data": subject.extended_data,
    }

    stmt = pg_insert(SubjectModel).values(values)
    # On conflict (platform, platform_id), update all mutable fields and
    # preserve the existing id. created_at is intentionally not in the
    # update set so the original creation time is kept.
    stmt = stmt.on_conflict_do_update(
        constraint="uq_subjects_platform_platform_id",
        set_={
            "name": stmt.excluded.name,
            "display_name": stmt.excluded.display_name,
            "followers": stmt.excluded.followers,
            "post_count": stmt.excluded.post_count,
            "activity_frequency": stmt.excluded.activity_frequency,
            "status": stmt.excluded.status,
            "last_synced_at": stmt.excluded.last_synced_at,
            "extended_data": stmt.excluded.extended_data,
        },
    )
    session.execute(stmt)
    session.flush()

    # Look up the id (preserved on update, returned by insert).
    result = session.execute(
        select(SubjectModel.id).where(
            SubjectModel.platform == subject.platform,
            SubjectModel.platform_id == subject.platform_id,
        )
    )
    row = result.one()
    return cast(UUID, row[0])


def append_snapshot(session: Session, snapshot: ActivitySnapshot) -> None:
    """Insert a new activity snapshot row.

    Snapshots are append-only. Re-syncing the same subject at the same
    timestamp would be a programming error; we let the unique constraint
    on (subject_id, captured_at) reject it.
    """
    session.add(
        ActivitySnapshotModel(
            subject_id=snapshot.subject_id,
            captured_at=snapshot.captured_at,
            followers=snapshot.followers,
            post_count=snapshot.post_count,
            frequency=snapshot.frequency,
        )
    )
    session.flush()


def get_subject_by_platform_id(
    session: Session, platform: Platform, platform_id: str
) -> SubjectModel | None:
    result = session.execute(
        select(SubjectModel).where(
            SubjectModel.platform == platform,
            SubjectModel.platform_id == platform_id,
        )
    )
    return result.scalar_one_or_none()


def list_subject_ids_for_platform(session: Session, platform: Platform) -> list[UUID]:
    result = session.execute(select(SubjectModel.id).where(SubjectModel.platform == platform))
    return [row[0] for row in result.all()]


def sync_subject(session: Session, subject: Subject) -> UUID:
    """Upsert the subject and append a snapshot in a single transaction.

    Returns the subject's id. On any error the transaction is rolled
    back so neither the current state nor the snapshot is partially
    written.
    """
    subject_id = upsert_subject(session, subject)
    snapshot = ActivitySnapshot(
        subject_id=subject_id,
        captured_at=subject.last_synced_at,
        followers=subject.followers,
        post_count=subject.post_count,
        frequency=subject.activity_frequency,
    )
    append_snapshot(session, snapshot)
    session.commit()
    return subject_id


def sync_videos(session: Session, subject_id: UUID, videos: list[Video]) -> None:
    """Upsert video records for a subject.

    Videos are upserted by (subject_id, platform_video_id). This keeps
    each video row updated with the latest metrics without creating
    duplicates. Videos no longer in the incoming list are NOT deleted
    — they remain in the database with their last known state.
    """
    for video in videos:
        values = {
            "id": video.id,
            "subject_id": subject_id,
            "platform_video_id": video.platform_video_id,
            "title": video.title,
            "description": video.description,
            "thumbnail_url": video.thumbnail_url,
            "published_at": video.published_at,
            "duration": video.duration,
            "view_count": video.view_count,
            "like_count": video.like_count,
            "comment_count": video.comment_count,
            "last_synced_at": video.last_synced_at,
        }
        stmt = pg_insert(VideoModel).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_videos_subject_platform_video",
            set_={
                "title": stmt.excluded.title,
                "description": stmt.excluded.description,
                "thumbnail_url": stmt.excluded.thumbnail_url,
                "duration": stmt.excluded.duration,
                "view_count": stmt.excluded.view_count,
                "like_count": stmt.excluded.like_count,
                "comment_count": stmt.excluded.comment_count,
                "last_synced_at": stmt.excluded.last_synced_at,
            },
        )
        session.execute(stmt)
    session.flush()


def run_in_transaction(work: Callable[[Session], _T]) -> _T:
    """Open a session, run `work(session)`, commit, and return the result."""
    session_factory = get_session_factory()
    with session_factory() as session:
        result = work(session)
        session.commit()
        return result

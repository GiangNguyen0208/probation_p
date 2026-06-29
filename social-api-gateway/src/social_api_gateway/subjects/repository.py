"""Read queries for subjects and activity snapshots."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from social_common.enums import Platform, SubjectStatus
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ActivitySnapshotModel, SubjectModel, VideoModel


class SubjectRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def list_subjects(
        self,
        platform: Platform | None = None,
        status: SubjectStatus | None = None,
        q: str | None = None,
        last_synced_from: datetime | None = None,
        last_synced_to: datetime | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[SubjectModel], int]:
        """List subjects with filters. Returns (rows, total_count)."""
        conditions = []
        if platform is not None:
            conditions.append(SubjectModel.platform == platform)
        if status is not None:
            conditions.append(SubjectModel.status == status)
        if q is not None and q.strip():
            like = f"%{q.strip()}%"
            conditions.append(
                or_(
                    SubjectModel.name.ilike(like),
                    SubjectModel.platform_id.ilike(like),
                )
            )
        if last_synced_from is not None:
            conditions.append(SubjectModel.last_synced_at >= last_synced_from)
        if last_synced_to is not None:
            conditions.append(SubjectModel.last_synced_at <= last_synced_to)

        where = and_(*conditions) if conditions else None

        count_stmt = select(func.count(SubjectModel.id))
        if where is not None:
            count_stmt = count_stmt.where(where)
        total = (await self._db.execute(count_stmt)).scalar_one()

        stmt = select(SubjectModel)
        if where is not None:
            stmt = stmt.where(where)
        stmt = stmt.order_by(SubjectModel.last_synced_at.desc()).limit(limit).offset(offset)
        rows = (await self._db.execute(stmt)).scalars().all()
        return rows, int(total)

    async def get_subject(self, subject_id: UUID) -> SubjectModel | None:
        result = await self._db.execute(select(SubjectModel).where(SubjectModel.id == subject_id))
        return result.scalar_one_or_none()

    async def get_activity(
        self,
        subject_id: UUID,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        limit: int = 1000,
    ) -> Sequence[ActivitySnapshotModel]:
        conditions = [ActivitySnapshotModel.subject_id == subject_id]
        if from_dt is not None:
            conditions.append(ActivitySnapshotModel.captured_at >= from_dt)
        if to_dt is not None:
            conditions.append(ActivitySnapshotModel.captured_at <= to_dt)

        stmt = (
            select(ActivitySnapshotModel)
            .where(and_(*conditions))
            .order_by(ActivitySnapshotModel.captured_at.desc())
            .limit(limit)
        )
        return (await self._db.execute(stmt)).scalars().all()

    async def list_videos(
        self,
        subject_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[VideoModel], int]:
        conditions = [VideoModel.subject_id == subject_id]

        count_stmt = select(func.count(VideoModel.id)).where(and_(*conditions))
        total = (await self._db.execute(count_stmt)).scalar_one()

        stmt = (
            select(VideoModel)
            .where(and_(*conditions))
            .order_by(VideoModel.published_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return rows, int(total)

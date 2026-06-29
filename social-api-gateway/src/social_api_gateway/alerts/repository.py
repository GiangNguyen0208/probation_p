"""CRUD operations for the alert_rules table."""

from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import and_, delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AlertLogModel, AlertRuleModel


class AlertRepository:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def list_rules(
        self,
        subject_id: UUID,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[AlertRuleModel], int]:
        conditions = [AlertRuleModel.subject_id == subject_id]
        if active_only:
            conditions.append(AlertRuleModel.is_active == True)  # noqa: E712

        where = and_(*conditions)

        count_stmt = select(func.count(AlertRuleModel.id)).where(where)
        total = (await self._db.execute(count_stmt)).scalar_one()

        stmt = (
            select(AlertRuleModel)
            .where(where)
            .order_by(AlertRuleModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return rows, int(total)

    async def get_rule(self, rule_id: UUID) -> AlertRuleModel | None:
        result = await self._db.execute(select(AlertRuleModel).where(AlertRuleModel.id == rule_id))
        return result.scalar_one_or_none()

    async def create_rule(self, rule: AlertRuleModel) -> AlertRuleModel:
        self._db.add(rule)
        await self._db.flush()
        await self._db.refresh(rule)
        return rule

    async def update_rule(self, rule_id: UUID, values: dict[str, object]) -> AlertRuleModel | None:
        from datetime import UTC, datetime

        values["updated_at"] = datetime.now(UTC)
        stmt = (
            update(AlertRuleModel)
            .where(AlertRuleModel.id == rule_id)
            .values(**values)
            .returning(AlertRuleModel)
        )
        result = await self._db.execute(stmt)
        return result.scalar_one_or_none()

    async def delete_rule(self, rule_id: UUID) -> bool:
        stmt = delete(AlertRuleModel).where(AlertRuleModel.id == rule_id)
        result = await self._db.execute(stmt)
        return bool(result.rowcount)  # type: ignore[attr-defined]

    async def list_alert_logs(
        self,
        subject_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[Sequence[AlertLogModel], int]:
        where = AlertLogModel.subject_id == subject_id

        count_stmt = select(func.count(AlertLogModel.id)).where(where)
        total = (await self._db.execute(count_stmt)).scalar_one()

        stmt = (
            select(AlertLogModel)
            .where(where)
            .order_by(AlertLogModel.triggered_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return rows, int(total)

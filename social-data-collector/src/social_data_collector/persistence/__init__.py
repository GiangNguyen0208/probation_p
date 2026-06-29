"""Persistence layer: SQLAlchemy engine, models, and repository functions."""

from .db import get_engine, get_session_factory
from .models import ActivitySnapshotModel, AlertRuleModel, Base, SubjectModel
from .repository import (
    append_snapshot,
    get_subject_by_platform_id,
    list_subject_ids_for_platform,
    upsert_subject,
)

__all__ = [
    "ActivitySnapshotModel",
    "AlertRuleModel",
    "Base",
    "SubjectModel",
    "append_snapshot",
    "get_engine",
    "get_session_factory",
    "get_subject_by_platform_id",
    "list_subject_ids_for_platform",
    "upsert_subject",
]

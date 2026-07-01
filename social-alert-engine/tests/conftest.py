"""Shared fixtures for alert-engine tests."""

from __future__ import annotations

from uuid import uuid4

from social_common.enums import AlertRuleType, Platform, SubjectStatus

from social_alert_engine.baseline import BaselineResult
from social_alert_engine.models import AlertRuleModel, SubjectModel


def make_subject(
    *,
    status: SubjectStatus = SubjectStatus.ACTIVE,
    followers: int = 1000,
    activity_frequency: float = 5.0,
) -> SubjectModel:
    return SubjectModel(
        id=uuid4(),
        platform=Platform.FACEBOOK,
        platform_id="fb_1",
        name="Test Subject",
        display_name="Test Subject",
        followers=followers,
        post_count=50,
        activity_frequency=activity_frequency,
        status=status,
        last_synced_at=None,
        created_at=None,
    )


def make_rule(
    rule_type: AlertRuleType,
    *,
    threshold: float = 2.0,
    cooldown_seconds: int = 3600,
    channel_id: str = "@default",
    is_active: bool = True,
) -> AlertRuleModel:
    return AlertRuleModel(
        id=uuid4(),
        subject_id=uuid4(),
        rule_type=rule_type,
        threshold=threshold,
        cooldown_seconds=cooldown_seconds,
        channel_id=channel_id,
        is_active=is_active,
        created_at=None,
        updated_at=None,
    )


def make_baseline(
    followers: list[int] | None = None,
    frequencies: list[float] | None = None,
) -> BaselineResult:
    return BaselineResult(
        followers=followers or [100, 110, 120],
        frequencies=frequencies or [1.0, 1.1, 1.2],
    )

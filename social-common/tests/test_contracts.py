from datetime import UTC, datetime
from uuid import uuid4

from social_common import (
    ActivitySnapshot,
    AlertRule,
    AlertRuleType,
    Platform,
    Subject,
    SubjectStatus,
)


def test_subject_contract_accepts_required_fields() -> None:
    subject = Subject(
        id=uuid4(),
        platform=Platform.YOUTUBE,
        platform_id="UC_x5XG1OV2P6uZZ5FSM9Ttw",
        name="Google Developers",
        display_name="Google Developers",
        followers=100,
        post_count=10,
        activity_frequency=0.5,
        status=SubjectStatus.ACTIVE,
        last_synced_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
    )

    assert subject.platform == Platform.YOUTUBE


def test_activity_snapshot_contract_accepts_metrics() -> None:
    snapshot = ActivitySnapshot(
        subject_id=uuid4(),
        captured_at=datetime.now(UTC),
        followers=100,
        post_count=10,
        frequency=0.5,
    )

    assert snapshot.frequency == 0.5


def test_alert_rule_contract_accepts_rule_type() -> None:
    rule = AlertRule(
        subject_id=uuid4(),
        rule_type=AlertRuleType.FOLLOWER_SPIKE,
        threshold=10,
        cooldown_seconds=3600,
        channel_id="-100123456789",
    )

    assert rule.rule_type == AlertRuleType.FOLLOWER_SPIKE

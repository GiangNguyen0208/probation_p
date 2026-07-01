"""Tests for the alert evaluator logic.

Tests the pure computation helpers (follower/activity/status evaluators)
that do not require a live database session.  DB-bound functions such as
``_check_cooldown`` and ``_persist_and_notify`` are covered indirectly
through the evaluator's integration contract.
"""

from __future__ import annotations

from unittest.mock import patch

from conftest import make_baseline, make_rule, make_subject
from social_common.enums import AlertRuleType, SubjectStatus

from social_alert_engine.evaluator import (
    _evaluate_activity_rules,
    _evaluate_follower_rules,
    _evaluate_status_change,
    _extract_previous_status,
)


class TestExtractPreviousStatus:
    def test_extracts_new_status_line(self) -> None:
        msg = "<b>Status Change</b>\nSubject: X\nNew status: inactive\nPrevious status: active"
        assert _extract_previous_status(msg, "active") == "inactive"

    def test_fallback_on_unexpected_format(self) -> None:
        msg = "Some unrelated message without status lines"
        assert _extract_previous_status(msg, "active") == "active"

    def test_handles_multiple_new_status_lines(self) -> None:
        msg = (
            "<b>Status Change</b>\nSubject: X\n"
            "New status: suspended\nNew status: active\n"
            "Previous status: inactive"
        )
        assert _extract_previous_status(msg, "active") == "suspended"


class TestEvaluateFollowerRules:
    def test_follower_spike_triggers(self) -> None:
        rule = make_rule(AlertRuleType.FOLLOWER_SPIKE, threshold=2.0)
        subject = make_subject(followers=500)
        baseline = make_baseline(followers=[100, 110, 120])
        fired = _evaluate_follower_rules([rule], subject, baseline, "Test")
        assert len(fired) == 1
        assert fired[0].rule.rule_type == AlertRuleType.FOLLOWER_SPIKE

    def test_follower_drop_triggers(self) -> None:
        rule = make_rule(AlertRuleType.FOLLOWER_DROP, threshold=2.0)
        subject = make_subject(followers=50)
        baseline = make_baseline(followers=[100, 110, 120])
        fired = _evaluate_follower_rules([rule], subject, baseline, "Test")
        assert len(fired) == 1
        assert fired[0].rule.rule_type == AlertRuleType.FOLLOWER_DROP

    def test_no_trigger_when_below_threshold(self) -> None:
        rule_spike = make_rule(AlertRuleType.FOLLOWER_SPIKE, threshold=3.0)
        rule_drop = make_rule(AlertRuleType.FOLLOWER_DROP, threshold=3.0)
        subject = make_subject(followers=115)
        baseline = make_baseline(followers=[100, 110, 120])
        fired = _evaluate_follower_rules([rule_spike, rule_drop], subject, baseline, "Test")
        assert len(fired) == 0

    def test_skipped_when_stdev_zero(self) -> None:
        rule = make_rule(AlertRuleType.FOLLOWER_SPIKE, threshold=1.0)
        subject = make_subject(followers=999)
        baseline = make_baseline(followers=[100, 100, 100])
        fired = _evaluate_follower_rules([rule], subject, baseline, "Test")
        assert len(fired) == 0


class TestEvaluateActivityRules:
    def test_activity_silence_triggers(self) -> None:
        rule = make_rule(AlertRuleType.ACTIVITY_SILENCE, threshold=2.0)
        subject = make_subject(activity_frequency=0.5)
        baseline = make_baseline(frequencies=[5.0, 6.0, 7.0])
        fired = _evaluate_activity_rules([rule], subject, baseline, "Test")
        assert len(fired) == 1
        assert fired[0].rule.rule_type == AlertRuleType.ACTIVITY_SILENCE

    def test_activity_silence_not_triggered_above_threshold(self) -> None:
        rule = make_rule(AlertRuleType.ACTIVITY_SILENCE, threshold=2.0)
        subject = make_subject(activity_frequency=5.0)
        baseline = make_baseline(frequencies=[5.0, 6.0, 7.0])
        fired = _evaluate_activity_rules([rule], subject, baseline, "Test")
        assert len(fired) == 0


class TestEvaluateStatusChange:
    @patch("social_alert_engine.evaluator.get_session_factory")
    def test_no_false_positive_on_first_evaluation(
        self, mock_get_session_factory
    ) -> None:
        mock_get_session_factory.return_value = _FakeSessionFactory(None)
        rule = make_rule(AlertRuleType.STATUS_CHANGE)
        subject = make_subject(status=SubjectStatus.INACTIVE)
        fired = _evaluate_status_change([rule], subject, "Test")
        assert len(fired) == 0

    @patch("social_alert_engine.evaluator.get_session_factory")
    def test_fires_on_actual_transition(self, mock_get_session_factory) -> None:
        mock_get_session_factory.return_value = _FakeSessionFactory(
            _STATUS_CHANGE_LOG_ACTIVE_TO_INACTIVE
        )
        rule = make_rule(AlertRuleType.STATUS_CHANGE)
        subject = make_subject(status=SubjectStatus.ACTIVE)
        fired = _evaluate_status_change([rule], subject, "Test")
        assert len(fired) == 1
        assert "active" in fired[0].message and "inactive" in fired[0].message

    @patch("social_alert_engine.evaluator.get_session_factory")
    def test_does_not_fire_when_status_unchanged(
        self, mock_get_session_factory
    ) -> None:
        mock_get_session_factory.return_value = _FakeSessionFactory(
            _STATUS_CHANGE_LOG_ACTIVE_TO_INACTIVE
        )
        rule = make_rule(AlertRuleType.STATUS_CHANGE)
        subject = make_subject(status=SubjectStatus.INACTIVE)
        fired = _evaluate_status_change([rule], subject, "Test")
        assert len(fired) == 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STATUS_CHANGE_LOG_ACTIVE_TO_INACTIVE = (
    "<b>Status Change</b>\n"
    "Subject: Test\n"
    "New status: inactive\n"
    "Previous status: active"
)


class _FakeSessionFactory:
    """Mimics ``get_session_factory`` returning a session that yields
    ``scalar_one_or_none() -> last_status_log``."""

    def __init__(self, scalar_value: str | None) -> None:
        self._scalar_value = scalar_value

    def __call__(self):
        return _FakeSession(self._scalar_value)


class _FakeSession:
    def __init__(self, scalar_value: str | None) -> None:
        self._scalar_value = scalar_value

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def execute(self, *_, **__):
        return _FakeResult(self._scalar_value)


class _FakeResult:
    def __init__(self, scalar_value: str | None) -> None:
        self._scalar_value = scalar_value

    def scalar_one_or_none(self):
        return self._scalar_value

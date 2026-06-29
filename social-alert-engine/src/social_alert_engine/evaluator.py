"""Alert rule evaluation logic.

Evaluates all active rules for a subject by comparing current metrics
against a time-windowed baseline. Writes AlertLog entries for any
triggered rules and attempts Telegram delivery.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from social_common.enums import AlertRuleType
from sqlalchemy import select

from .baseline import BaselineResult, compute_baseline
from .db import get_session_factory
from .logging_setup import get_logger
from .models import AlertLogModel, AlertRuleModel, SubjectModel
from .notifier import send_alert_notification

logger = get_logger("social_alert_engine.evaluator")


_FOLLOWER_SPIKE_MSG = (
    "<b>Follower Spike</b>\n"
    "Subject: {subject_name}\n"
    "Current: {current:,} followers\n"
    "Baseline: {baseline:.0f} followers\n"
    "Threshold: {threshold}x stdev"
)

_FOLLOWER_DROP_MSG = (
    "<b>Follower Drop</b>\n"
    "Subject: {subject_name}\n"
    "Current: {current:,} followers\n"
    "Baseline: {baseline:.0f} followers\n"
    "Threshold: {threshold}x stdev"
)

_ACTIVITY_SPIKE_MSG = (
    "<b>Activity Spike</b>\n"
    "Subject: {subject_name}\n"
    "Current frequency: {current}\n"
    "Baseline: {baseline:.2f}\n"
    "Threshold: {threshold}x stdev"
)

_ACTIVITY_SILENCE_MSG = (
    "<b>Activity Silence</b>\n"
    "Subject: {subject_name}\n"
    "Current frequency: {current}\n"
    "Threshold: below {threshold}"
)

_STATUS_CHANGE_MSG = (
    "<b>Status Change</b>\n"
    "Subject: {subject_name}\n"
    "New status: {current}\n"
    "Previous status: {baseline}"
)


class FiredAlert:
    """Represents a single alert that has been triggered."""

    def __init__(
        self,
        rule: AlertRuleModel,
        message: str,
        metric_value: float | None,
    ) -> None:
        self.rule = rule
        self.message = message
        self.metric_value = metric_value


def _load_subject_and_rules(subject_id: UUID) -> tuple[SubjectModel | None, list[AlertRuleModel]]:
    factory = get_session_factory()
    with factory() as session:
        subject = session.execute(
            select(SubjectModel).where(SubjectModel.id == subject_id)
        ).scalar_one_or_none()

        rules = list(
            session.execute(
                select(AlertRuleModel).where(
                    AlertRuleModel.subject_id == subject_id,
                    AlertRuleModel.is_active,
                )
            )
            .scalars()
            .all()
        )
    return subject, rules


def _check_cooldown(rule_id: UUID) -> bool:
    factory = get_session_factory()
    with factory() as session:
        latest = session.execute(
            select(AlertLogModel.triggered_at)
            .where(AlertLogModel.rule_id == rule_id)
            .order_by(AlertLogModel.triggered_at.desc())
            .limit(1)
        ).scalar_one_or_none()
    if latest is None:
        return False
    now = datetime.now(UTC)
    return (now - latest).total_seconds() < 3600


def _evaluate_follower_rules(
    rules: list[AlertRuleModel],
    subject: SubjectModel,
    baseline: BaselineResult,
    subject_name: str,
) -> list[FiredAlert]:
    fired: list[FiredAlert] = []
    current = subject.followers

    for rule in rules:
        if rule.rule_type == AlertRuleType.FOLLOWER_SPIKE:
            if baseline.follower_stdev <= 0:
                continue
            threshold_val = baseline.follower_mean + rule.threshold * baseline.follower_stdev
            if current >= threshold_val:
                msg = _FOLLOWER_SPIKE_MSG.format(
                    subject_name=subject_name,
                    current=current,
                    baseline=baseline.follower_mean,
                    threshold=rule.threshold,
                )
                fired.append(FiredAlert(rule, msg, float(current)))

        elif rule.rule_type == AlertRuleType.FOLLOWER_DROP:
            if baseline.follower_stdev <= 0:
                continue
            threshold_val = baseline.follower_mean - rule.threshold * baseline.follower_stdev
            if current <= threshold_val:
                msg = _FOLLOWER_DROP_MSG.format(
                    subject_name=subject_name,
                    current=current,
                    baseline=baseline.follower_mean,
                    threshold=rule.threshold,
                )
                fired.append(FiredAlert(rule, msg, float(current)))

    return fired


def _evaluate_activity_rules(
    rules: list[AlertRuleModel],
    subject: SubjectModel,
    baseline: BaselineResult,
    subject_name: str,
) -> list[FiredAlert]:
    fired: list[FiredAlert] = []
    current = subject.activity_frequency

    for rule in rules:
        if rule.rule_type == AlertRuleType.ACTIVITY_SPIKE:
            if baseline.frequency_stdev <= 0:
                continue
            threshold_val = baseline.frequency_mean + rule.threshold * baseline.frequency_stdev
            if current >= threshold_val:
                msg = _ACTIVITY_SPIKE_MSG.format(
                    subject_name=subject_name,
                    current=round(current, 4),
                    baseline=baseline.frequency_mean,
                    threshold=rule.threshold,
                )
                fired.append(FiredAlert(rule, msg, float(current)))

        elif rule.rule_type == AlertRuleType.ACTIVITY_SILENCE:
            if current < rule.threshold:
                msg = _ACTIVITY_SILENCE_MSG.format(
                    subject_name=subject_name,
                    current=round(current, 4),
                    threshold=rule.threshold,
                )
                fired.append(FiredAlert(rule, msg, float(current)))

    return fired


def _evaluate_status_change(
    rules: list[AlertRuleModel],
    subject: SubjectModel,
    subject_name: str,
) -> list[FiredAlert]:
    fired: list[FiredAlert] = []
    current_status = str(subject.status)

    factory = get_session_factory()
    with factory() as session:
        last_status_log = session.execute(
            select(AlertLogModel.message)
            .where(
                AlertLogModel.subject_id == subject.id,
                AlertLogModel.rule_type == AlertRuleType.STATUS_CHANGE,
            )
            .order_by(AlertLogModel.triggered_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    for rule in rules:
        if rule.rule_type != AlertRuleType.STATUS_CHANGE:
            continue

        if last_status_log:
            previous_status = _extract_previous_status(last_status_log, current_status)
        else:
            previous_status = "active"

        if current_status != previous_status:
            msg = _STATUS_CHANGE_MSG.format(
                subject_name=subject_name,
                current=current_status,
                baseline=previous_status,
            )
            fired.append(FiredAlert(rule, msg, float(subject.followers)))

    return fired


def _extract_previous_status(log_message: str, fallback: str) -> str:
    """Extract the 'New status' value from a previous STATUS_CHANGE alert log."""
    for line in log_message.split("\n"):
        if line.startswith("New status:"):
            return line.split(":", 1)[1].strip()
    return fallback


def _persist_and_notify(fired: list[FiredAlert], subject_id: UUID) -> int:
    """Write AlertLog rows and send Telegram notifications.

    Returns the number of alerts that were delivered.
    """
    count = 0
    factory = get_session_factory()

    for alert in fired:
        if _check_cooldown(alert.rule.id):
            logger.info(
                "evaluate.cooldown_active",
                rule_id=str(alert.rule.id),
                subject_id=str(subject_id),
            )
            continue

        delivered = send_alert_notification(alert.rule.channel_id, alert.message)

        log_entry = AlertLogModel(
            id=uuid4(),
            subject_id=subject_id,
            rule_id=alert.rule.id,
            rule_type=alert.rule.rule_type,
            triggered_at=datetime.now(UTC),
            metric_value=alert.metric_value,
            threshold=alert.rule.threshold,
            message=alert.message,
            delivered=delivered,
        )

        with factory() as session:
            session.add(log_entry)
            session.commit()

        if delivered:
            count += 1
            logger.info(
                "evaluate.alert_fired",
                rule_id=str(alert.rule.id),
                subject_id=str(subject_id),
                rule_type=str(alert.rule.rule_type),
                delivered=True,
            )
        else:
            logger.warning(
                "evaluate.alert_fired",
                rule_id=str(alert.rule.id),
                subject_id=str(subject_id),
                rule_type=str(alert.rule.rule_type),
                delivered=False,
            )

    return count


def evaluate_subject(subject_id: UUID) -> int:
    """Evaluate all alert rules for a subject and write AlertLog entries.

    Returns the number of alerts delivered (notifications sent).
    """
    subject, rules = _load_subject_and_rules(subject_id)
    if subject is None:
        logger.warning("evaluate.subject_not_found", subject_id=str(subject_id))
        return 0

    subject_name = subject.display_name

    fired: list[FiredAlert] = []

    baseline = compute_baseline(str(subject_id))
    if baseline is not None:
        fired.extend(_evaluate_follower_rules(rules, subject, baseline, subject_name))
        fired.extend(_evaluate_activity_rules(rules, subject, baseline, subject_name))
    else:
        logger.info(
            "evaluate.skipped_insufficient_data",
            subject_id=str(subject_id),
            subject=subject_name,
        )

    fired.extend(_evaluate_status_change(rules, subject, subject_name))

    if not fired:
        logger.info("evaluate.no_alerts", subject_id=str(subject_id), subject=subject_name)
        return 0

    return _persist_and_notify(fired, subject_id)

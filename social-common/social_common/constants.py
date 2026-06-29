"""Shared constants used across multiple services.

Task names live here so cross-service `send_task()` calls use a single
source of truth rather than duplicated string literals. See ADR-00X
for the reasoning behind the separate-Celery-app pattern.
"""

TASK_EVALUATE_SUBJECT_ALERTS = "social-alert-engine.tasks.evaluate_subject_alerts"
TASK_EVALUATE_ALL_ALERTS = "social-alert-engine.tasks.evaluate_all_alerts"

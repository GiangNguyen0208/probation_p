# Phase 4 - Alert Engine

Window: Weeks 6-7  
Sprint: Sprint 7  
Goal: analysts receive automatic notifications when subjects behave unusually.

## Scope

Build the background alert service that evaluates subject metrics against configured rules, deduplicates sustained events, logs alert history, and sends Telegram Bot notifications.

Implement this service in Python. Reuse Celery and Redis for asynchronous evaluation and retries, Pydantic models from `social-common` for rule and alert payload validation, and `aiogram` or `python-telegram-bot` for Telegram Bot delivery.

## Repositories

- `social-alert-engine`
- `social-api-gateway`
- `social-mini-app`
- `social-infra`

## Deliverables

- Alert Engine service skeleton with configuration and health check.
- Rolling baseline calculation for subject metrics.
- Rule evaluator for follower spike, follower drop, activity spike, activity silence, and status change.
- Alert deduplication using subject, rule type, event identity, and cooldown window.
- Telegram Bot integration using `aiogram` or `python-telegram-bot`.
- Alert log persistence.
- Mini App alert history view or integration point if the view already exists.
- Celery worker task for event-triggered alert evaluation after manual syncs.

## Acceptance Criteria

- Active rules are evaluated after subject manual sync cycles.
- Triggered alerts include subject name, platform, alert type, current metric, baseline, timestamp, and Mini App deep link where supported.
- Sustained anomalies do not create notification floods.
- Alert history is queryable through the API and visible or prepared for visibility in the Mini App.
- Bot token and target chat IDs are read from secure environment configuration.
- Alert Engine tasks can be retried safely without duplicate notifications.

## Dependencies

- Alert rule endpoints from Phase 2.
- Alert config UI from Phase 3.
- Telegram Bot token and configured chat/channel IDs.
- Subject activity history from Phase 1.
- Redis and worker infrastructure from the Python collector setup.

## Risks

- Alert thresholds that are too sensitive can create analyst fatigue.
- Missing cooldown logic can flood Telegram channels.
- Baseline windows must handle sparse or newly created subjects.
- Worker retries must be idempotent so failed notification attempts do not produce duplicate alert logs.

## Sprint Exit

The phase exits when configured rules can produce accurate, deduplicated Telegram notifications and every sent alert is stored for audit and Mini App visibility.

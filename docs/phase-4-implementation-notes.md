# Phase 4 — Implementation Notes

These were open questions raised while wiring up the already-live Telegram/webhook
infrastructure (ngrok-exposed mini-app, gateway webhook at `/api/telegram-webhook`,
bot `@socialTracking_bot`). They're recorded here for traceability but are
operational/config choices rather than ADR-level architecture decisions.

## CORS origin for the mini-app's ngrok URL

Hardcoding the ngrok URL in the gateway's CORS config was rejected — free-tier
ngrok URLs change on every restart, which would require a code change and
redeploy just to keep the mini-app working. Resolved by adding a
`CORS_ALLOW_ORIGINS` env var (comma-separated) to the gateway's settings, so
the URL can be updated via `.env` alone. Note this still requires a gateway
restart when the ngrok URL rotates; a reserved ngrok domain (paid plan) would
remove this friction entirely if dev-loop speed becomes a problem.

## Notification target: per-rule `channel_id`, not a global fallback

Each `AlertRule` carries its own `channel_id`, and `notifier.py` sends to that
value rather than a `TELEGRAM_DEFAULT_CHAT_ID` fallback. Reasoning: different
subjects/rules may need to notify different chats, and silently substituting a
global default on a missing `channel_id` risks delivering one subject's alert
into an unrelated chat — a worse failure mode than simply not sending. If
`rule.channel_id` is missing, the evaluator logs a warning and skips delivery
(still writing an `AlertLog` row with `delivered=False`), rather than guessing
a destination. A dev-only fallback, if ever needed for local testing, should be
a distinctly-named variable gated on `environment == "development"`, kept out
of the production code path entirely.

## Celery task name constants, not hardcoded strings

Task names used in cross-service `send_task()` calls
(`evaluate_subject_alerts`, `evaluate_all_alerts`) are defined once in
`social_common/constants.py` and imported by both the collector (caller) and
the alert engine (task registration via `@celery_app.task(name=...)`). This
doesn't replace the integration test from ADR-00X Decision 1 — the constant
only prevents the *string* from drifting between services; the test still
catches a mismatch between the registered task name and the actual task
behavior (e.g. a rename of the decorated function without updating `name=`).

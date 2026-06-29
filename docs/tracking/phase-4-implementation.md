# Phase 4 Implementation Tracking

> Read this file to know exactly where implementation left off.
> Update status + checklist items as work progresses.
> Master plan: `docs/sprints/phase-4-alert-engine.md`
> ADR: `docs/ADR-00X-phase-4-alert-engine.md`
> Implementation notes: `docs/phase-4-implementation-notes.md`

## Status overview

| Step | Status |
|---|---|
| Step 0 — Fix alert-engine deps + env | [x] completed |
| Step 1 — AlertLog schema + constants | [x] completed |
| Step 2 — Alert-engine DB + models + migration | [x] completed |
| Step 3 — Alert-engine Celery + logic | [x] completed |
| Step 4 — Collector post-sync trigger | [x] completed |
| Step 5 — Gateway alert-log endpoint + CORS | [x] completed |
| Step 6 — Mini-app AlertHistoryPanel | [x] completed |
| Step 7 — Documentation | [x] completed |
| Final verification | [x] completed |

**Last worked on:** 2026-06-25
**Current task:** All 7 steps + final verification complete. Migration applied to live DB.

---

## Key ADR Decisions

| Decision | Summary | Reference |
|---|---|---|
| Separate Celery app | `social-alert-engine` runs its own Celery app + Beat, same Redis broker | ADR-00X §1 |
| Raw HTTP for Telegram | `httpx` POST to Bot API (no aiogram), mirroring gateway's `bot.py` | ADR-00X §2 |
| `alert_logs` owner | alert-engine owns its own Alembic migration (`alembic_version_alert_engine`) | ADR-00X §3 |
| Baseline window | Time-based: 24h window, min 3 snapshots | ADR-00X §4 |

## Implementation Notes (answered questions)

| Question | Answer | Source |
|---|---|---|
| CORS for ngrok URL | `CORS_ALLOW_ORIGINS` env var (comma-separated), not hardcoded | `phase-4-implementation-notes.md` §1 |
| Notification target | Per-rule `channel_id`, no global fallback; missing → log + `delivered=False` | `phase-4-implementation-notes.md` §2 |
| Task name strings | Shared constants in `social_common/constants.py` + integration test | `phase-4-implementation-notes.md` §3 |

## Existing Telegram/webhook state

- **Bot:** `@socialTracking_bot` — already active
- **Mini-app URL:** `https://2a6b-167-179-66-125.ngrok-free.app` (ngrok, changes on restart)
- **Gateway webhook:** `POST /api/telegram-webhook` (handles `/start`, `/help`)
- **Gateway CORS:** currently allows `localhost:5173`, `127.0.0.1:5173` only — ngrok URL added via `CORS_ALLOW_ORIGINS`
- **Alert-engine `.env`:** exists but has empty `TELEGRAM_BOT_TOKEN` and wrong `DATABASE_URL`

## File Manifest

### Step 0 — Fix alert-engine deps + env
- [ ] `social-alert-engine/pyproject.toml` — swap `aiogram` for `httpx`
- [ ] `social-alert-engine/src/social_alert_engine/settings.py` — load root `.env` (like collector/gateway)
- [ ] `social-alert-engine/.env` — populate `TELEGRAM_BOT_TOKEN`, fix `DATABASE_URL`

### Step 1 — social-common: AlertLog schema + constants
- [ ] `social-common/social_common/constants.py` — `TASK_NAMES` dict
- [ ] `social-common/social_common/schemas.py` — add `AlertLog` model

### Step 2 — social-alert-engine: DB + models + migrations
- [ ] `social-alert-engine/src/social_alert_engine/db.py` — async engine + session + `Base`
- [ ] `social-alert-engine/src/social_alert_engine/models.py` — `AlertLogModel` (read-write) + read-only mirrors (`SubjectModel`, `ActivitySnapshotModel`, `AlertRuleModel`)
- [ ] `social-alert-engine/migrations/` + `alembic.ini` + `env.py` with `version_table="alembic_version_alert_engine"`
- [ ] `social-alert-engine/migrations/versions/0001_add_alert_logs.py`

### Step 3 — social-alert-engine: Celery + core logic
- [ ] `social-alert-engine/src/social_alert_engine/celery_app.py` — separate Celery app
- [ ] `social-alert-engine/src/social_alert_engine/baseline.py` — `compute_baseline(subject_id, window_hours=24, min_snapshots=3)`
- [ ] `social-alert-engine/src/social_alert_engine/evaluator.py` — rule evaluation logic
- [ ] `social-alert-engine/src/social_alert_engine/notifier.py` — `httpx` POST to Telegram API
- [ ] `social-alert-engine/src/social_alert_engine/tasks.py` — beat + subject tasks
- [ ] `social-alert-engine/src/social_alert_engine/__main__.py` — CLI entrypoints
- [ ] `social-alert-engine/pyproject.toml` — console_scripts entry

### Step 4 — social-data-collector: Post-sync trigger
- [ ] `social-data-collector/src/social_data_collector/persistence/models.py` — read-only `AlertLogModel` mirror
- [ ] `social-data-collector/src/social_data_collector/scheduler/tasks.py` — `send_task(...)` after sync success

### Step 5 — social-api-gateway: AlertLog endpoint + CORS
- [ ] `social-api-gateway/src/social_api_gateway/main.py` — add `CORS_ALLOW_ORIGINS` env var support
- [ ] `social-api-gateway/src/social_api_gateway/config.py` — add `CORS_ALLOW_ORIGINS` setting
- [ ] `social-api-gateway/src/social_api_gateway/alerts/models.py` — read-only `AlertLogModel`
- [ ] `social-api-gateway/src/social_api_gateway/alerts/repository.py` — `list_alert_logs()`
- [ ] `social-api-gateway/src/social_api_gateway/alerts/schemas.py` — `AlertLogResponse` + paginated wrapper
- [ ] `social-api-gateway/src/social_api_gateway/alerts/routes.py` — `GET /v1/subjects/{id}/alerts/logs`

### Step 6 — social-mini-app: Alert history UI
- [ ] Regenerate OpenAPI types (or manual `AlertLog` type)
- [ ] `social-mini-app/src/api/hooks.ts` — `useAlertLogs(subjectId)` hook
- [ ] `social-mini-app/src/components/panels/AlertHistoryPanel.tsx` — new component
- [ ] `social-mini-app/src/pages/SubjectDetailPage.tsx` — integrate AlertHistoryPanel

### Step 7 — Documentation
- [ ] `AGENTS.md` — update alert-engine run commands
- [ ] `social-alert-engine/README.md` — update with commands + architecture

## Per-Step Verification

```bash
# Step 1
cd social-common && ruff check . && mypy social_common

# Step 2-3 (alert-engine)
cd social-alert-engine && pip install -e ".[dev]" && ruff check . && mypy src && pytest

# Step 4 (collector)
cd social-data-collector && ruff check . && pytest

# Step 5 (gateway)
cd social-api-gateway && ruff check . && pytest

# Step 6 (mini-app)
cd social-mini-app && npm run build

# Final end-to-end smoke:
# 1. alembic upgrade head from social-alert-engine/
# 2. Start worker: python -m social_alert_engine run-worker
# 3. Trigger sync: POST /v1/subjects/{id}/sync
# 4. Check logs: GET /v1/subjects/{id}/alerts/logs
```

## Known Gotchas

- `alert_logs` migration lives in **alert-engine's** history (`alembic_version_alert_engine`), not collector's
- Task name constants (`social_common/constants.py`) must be kept in sync between collector's `send_task()` call and alert-engine's `@celery_app.task(name=...)` — integration test catches drift
- `notifier.py` sends to `rule.channel_id` (per-rule chat ID), not a global default — if missing, log warning + `delivered=False`
- Status change rule on tie (equal baseline distribution): prefer most recent status (ADR-00X follow-up)
- Gateway CORS needs ngrok URL added via `CORS_ALLOW_ORIGINS` env var whenever ngrok URL changes
- `social-common` uses flat layout (`social-common/social_common/`) — no `src/` directory

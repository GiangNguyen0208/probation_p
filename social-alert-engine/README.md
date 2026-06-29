# social-alert-engine

Alert evaluation and Telegram notification worker. Evaluates active alert
rules for each monitored subject against a time-windowed baseline, writes
`AlertLog` entries for triggered rules, and delivers notifications via the
Telegram Bot API.

## Architecture

- **Separate Celery app** (not shared with the collector) with its own Beat schedule
- **Time-windowed baseline** (24h, min 3 snapshots) per ADR-00X Decision 4
- **Raw HTTP** to Telegram Bot API (no aiogram), matching the gateway's `bot.py`
- **Per-rule `channel_id`** — no global fallback; missing chat ID logs and writes
  `delivered=False`

## Setup

```bash
pip install -e ".[dev]"
```

## Commands

```bash
ruff check .
ruff format --check .
pytest
mypy src

# CLI
social-alert-engine evaluate-all               # all subjects with active rules
social-alert-engine evaluate-one <subject_id>   # single subject
social-alert-engine run-worker                  # Celery worker + beat

# Migrations (from this directory)
alembic upgrade head
```

## Tables owned

| Table | Owner |
|---|---|
| `alert_logs` | alert-engine (migration in `migrations/versions/`) |

## Key ADR decisions

See `docs/ADR-00X-phase-4-alert-engine.md` and `docs/phase-4-implementation-notes.md`
for the full rationale.

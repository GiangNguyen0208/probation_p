# social-data-collector

Phase 1 service for the Social Intelligence Platform. Pulls public data on Facebook pages and YouTube channels on demand, normalizes responses into the unified `Subject` schema from `social-common`, and persists both current state (Postgres) and historical snapshots (TimescaleDB hypertable).

## Responsibilities

- Facebook Graph API client for page profile, follower count, and recent posts.
- YouTube Data API v3 client for channel metadata, statistics, and uploads playlist activity.
- Normalizers that map both platform responses to the unified `Subject` schema.
- Persistence layer: idempotent upsert into `subjects`, append-only inserts into `activity_snapshots`.
- Celery-based worker for background on-demand tasks, exponential back-off, and graceful recovery from transient platform errors.
- Structured JSON logs for sync lifecycle events.

## Layout

```
src/social_data_collector/
├── clients/          # HTTP clients for Facebook and YouTube
├── normalizers/      # Map platform responses to Subject schema
├── persistence/      # SQLAlchemy models, engine, repository
├── scheduler/        # Celery app and tasks
├── config.py         # pydantic-settings configuration
├── logging_setup.py  # structlog configuration
├── health.py         # Health check for DB and Redis
└── main.py           # CLI entrypoint
scripts/
└── crawl_facebook.py # Live Facebook crawl utility (no DB required)
tests/
├── clients/          # Mocked HTTP client tests
├── normalizers/      # Normalizer tests with fixtures
└── integration/      # Live API integration tests (opt-in)
```

## Local Commands

```bash
# Apply migrations
cd social-data-collector
alembic upgrade head

# One-time: seed subjects from env-var lists into the DB
python -m social_data_collector.main seed-subjects

# Manual sync (runs in foreground, useful for debugging)
python -m social_data_collector.main sync-facebook
python -m social_data_collector.main sync-youtube
python -m social_data_collector.main sync-all

# Health check
python -m social_data_collector.main health

# Worker + beat (automatic periodic sync)
# Dev: gộp worker + beat trong 1 process. Prod: tách thành 2 process riêng.
celery -A social_data_collector.scheduler.celery_app worker --beat -l info

# Tests
pytest                                            # unit tests only
RUN_INTEGRATION=1 pytest -m integration -v        # live API tests (needs credentials)
```

## Live API Testing

The `scripts/crawl_facebook.py` script runs the full Facebook crawl pipeline against the live Graph API. It is the quickest way to verify credentials and inspect the raw platform response without bringing up the database or the scheduler.

```bash
# Use FACEBOOK_TEST_PAGE_ID from .env
python social-data-collector/scripts/crawl_facebook.py --pretty

# Specify a Page ID explicitly
python social-data-collector/scripts/crawl_facebook.py --page-id 1234567890 --pretty

# Persist the result to the database (requires DATABASE_URL + migrations applied)
python social-data-collector/scripts/crawl_facebook.py --page-id 1234567890 --persist
```

For automated end-to-end checks against the live API, integration tests are provided in `tests/integration/`. They are skipped by default:

```bash
cd social-data-collector
RUN_INTEGRATION=1 pytest -m integration -v
```

## Configuration

All configuration is read from environment variables (and a `.env` file at the project root). See `.env.example` at the repository root for the full list. The most relevant variables:

| Variable | Purpose |
| --- | --- |
| `DATABASE_URL` | SQLAlchemy connection string for Postgres+TimescaleDB |
| `REDIS_URL` | Celery broker and result backend |
| `FACEBOOK_*` | Graph API credentials and target Page IDs |
| `YOUTUBE_*` | YouTube Data API v3 key and target Channel IDs |
| `SYNC_FACEBOOK_ENABLED` | Enable/disable Facebook periodic sync |
| `SYNC_YOUTUBE_ENABLED` | Enable/disable YouTube periodic sync |
| `SYNC_DEFAULT_INTERVAL_MINUTES` | Beat schedule interval (default 60) |
| `SYNC_MAX_RETRIES` | Max retry attempts per platform call |
| `SYNC_BACKOFF_INITIAL_SECONDS` | Initial back-off delay |
| `SYNC_BACKOFF_MAX_SECONDS` | Cap for exponential back-off |

## Acceptance Criteria Mapping

| Criterion | Where it lives |
| --- | --- |
| Syncs configured Facebook and YouTube subjects into storage | `scheduler/tasks.py` |
| Failed platform calls do not crash the service | `clients/base.py`, `scheduler/tasks.py` |
| Duplicate syncs update current state and append snapshots | `persistence/repository.py` |
| Platform enablement and retry settings are configurable | `config.py` |
| Collector health check reports status | `health.py` |
| Unit tests cover normalizers with fixtures | `tests/normalizers/` |
| Live API smoke tests against real Facebook | `tests/integration/`, `scripts/crawl_facebook.py` |

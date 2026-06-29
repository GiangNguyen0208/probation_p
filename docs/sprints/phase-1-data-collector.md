# Phase 1 - Data Collector

Window: Weeks 1-2  
Sprints: Sprints 1-2  
Goal: data is flowing into storage from Facebook and YouTube on demand.

## Scope

Build the ingestion service responsible for platform API clients, normalization, persistence, on-demand execution, retries, and platform-aware error handling.

Implement this service in Python. Use `httpx` for external API calls, Pydantic models from `social-common` for validation, SQLAlchemy for persistence, Alembic for schema changes, and Celery with Redis for background on-demand tasks, retries, and back-off.

## Repositories

- `social-data-collector`
- `social-common`
- `social-infra`

## Sprint 1 Focus

- Implement collector service skeleton and configuration loading.
- Add Python project baseline with `pyproject.toml`, typed settings, Ruff, pytest, and worker entrypoints.
- Add Facebook Graph API client for page/profile data, followers, post count, and activity frequency.
- Add YouTube Data API v3 client for channel stats, subscriber count, video count, and upload frequency.
- Add normalizer interfaces using `social-common` schemas.
- Create initial persistence layer for current subject state.

## Sprint 2 Focus

- Complete normalizers for Facebook and YouTube responses.
- Persist time-series activity snapshots.
- Add endpoint or task listener to trigger on-demand syncs.
- Add retry, exponential back-off, quota handling, partial data handling, and network failure recovery through worker task policies.
- Add integration or smoke tests for one Facebook subject and one YouTube channel using controlled fixtures or sandbox credentials.

## Deliverables

- Platform clients for Facebook and YouTube.
- Unified normalizer output validated against `social-common`.
- Primary DB upsert for current subject state.
- Time-series snapshot append flow.
- On-demand worker with retry and back-off policies.
- Python worker process and listener process documented in local development commands.
- Structured logs for sync start, success, partial failure, quota exhaustion, and recovery.

## Acceptance Criteria

- Running the collector locally syncs configured Facebook and YouTube subjects into storage when manually triggered.
- Failed platform calls do not crash the service and are visible in logs.
- Duplicate syncs update current state and append historical snapshots correctly.
- Platform enablement and retry settings are configurable.
- Collector health check reports worker and dependency status.
- Unit tests cover normalizers with recorded or fixture-based platform responses.

## Dependencies

- Phase 0 schema and migration baseline.
- Valid Facebook and YouTube API credentials.
- Local PostgreSQL and time-series storage from `social-infra`.
- Redis available for Celery broker/result backend or chosen worker equivalent.

## Risks

- API quota exhaustion during testing.
- Platform response shape mismatch with the unified schema.
- Time-series volume growth if retention policy is ignored.

## Sprint Exit

The phase exits when both platforms can be synced on demand, normalized data is stored in current and historical tables, and the collector recovers predictably from common external API failures.

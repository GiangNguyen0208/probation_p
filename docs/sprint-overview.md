# Social Intelligence Platform Sprint Overview

Source: `SocialIntelligencePlatform_ArchitectureDocument_v2.md`

This plan converts the 8-week architecture roadmap into execution-ready sprint overviews. The sprint order follows the highest-risk and highest-evaluation-weight work first: schema and infrastructure foundation, data collection, API access, Mini App monitoring, alerting, then hardening and handover.

## Python Implementation Direction

The backend services can be implemented in Python while preserving the architecture from the source document. Use Python for `social-data-collector`, `social-api-gateway`, `social-alert-engine`, and `social-common`; keep `social-mini-app` as a TypeScript/React Telegram WebApp because Telegram Mini Apps run in a browser WebView.

Recommended Python stack:

| Repository | Recommended Stack | Notes |
| --- | --- | --- |
| `social-data-collector` | Python, `httpx`, Celery, Redis, SQLAlchemy, Alembic | Celery handles queueing, retries, and back-off for on-demand syncs. |
| `social-api-gateway` | Python, FastAPI, Pydantic, SQLAlchemy, Redis | FastAPI provides OpenAPI docs, validation, dependency-based auth, and clean async support. |
| `social-alert-engine` | Python, Celery, Redis, `aiogram` or `python-telegram-bot` | Reuses the same queue pattern as the collector and sends Telegram notifications. |
| `social-common` | Python package, Pydantic models, JSON Schema export | Pydantic models become the backend source of truth; generated JSON Schema can be consumed by frontend code. |
| `social-mini-app` | TypeScript, React, Vite, Telegram WebApp SDK | Python is not a good fit for the client UI itself; the app consumes the Python API. |
| `social-infra` | Docker, Docker Compose, GitHub Actions | Add Python toolchain setup, Redis, PostgreSQL, and worker containers. |

## Delivery Timeline

| Phase | Sprint | Window | Primary Repos | Main Outcome |
| --- | --- | --- | --- | --- |
| Phase 0 | Sprint 0 | Week 0 | `social-common`, `social-infra`, all repos | Build foundation is ready before feature work starts. |
| Phase 1 | Sprints 1-2 | Weeks 1-2 | `social-data-collector`, `social-common`, `social-infra` | Facebook and YouTube data flows into storage on-demand. |
| Phase 2 | Sprints 3-4 | Weeks 3-4 | `social-api-gateway`, `social-common`, `social-infra` | Consumers can read subject data through a secured documented API. |
| Phase 3 | Sprints 5-6 | Weeks 4-6 | `social-mini-app`, `social-api-gateway` | Analysts can monitor subjects and configure alerts inside Telegram. |
| Phase 4 | Sprint 7 | Weeks 6-7 | `social-alert-engine`, `social-api-gateway`, `social-mini-app` | Analysts receive deduplicated Telegram alerts from configured rules. |
| Phase 5 | Sprint 8 | Week 8 | All repos | System is tested, observable, documented, and ready for handover. |

## Sprint Cadence

- Sprint length: 1 week for foundation and hardening, 2 weeks for major build phases.
- Status reporting: daily progress report covering completed, in progress, blocked.
- Blocker rule: escalate any task blocked for more than 2 hours.
- Definition of done: code merged through PR, lint clean, tests or smoke checks documented, README or API docs updated where relevant.

## Evaluation Weight Focus

| Evaluation Area | Weight | Sprint Focus |
| --- | ---: | --- |
| Data collection from Facebook and YouTube | 30% | Sprints 0-2 |
| Telegram Mini App monitoring and alerts | 25% | Sprints 5-7 |
| Independent data store and public API endpoint | 25% | Sprints 0, 3-4 |
| Code quality | 10% | All sprints |
| Independent problem-solving | 10% | All sprints |

## Cross-Sprint Quality Gates

- `social-common` schema changes require versioning and coordinated service updates.
- Python backend repos use `pyproject.toml`, Ruff, mypy or pyright, pytest, and typed Pydantic models.
- Each service exposes a health check before it is considered runnable.
- API behavior must include auth, structured errors, pagination, and documented response envelopes.
- External API failures must be logged and recoverable without crashing services.
- Phase 0 must produce a verified platform API research note before Phase 1 collector implementation starts.
- Telegram Mini App functionality must be tested in Telegram WebView, not only in a desktop browser.
- Alerting must include deduplication before any production notification flow is enabled.

## Phase 0 API Research Gate

Before `social-data-collector` implementation begins, the team must validate Facebook and YouTube API behavior with real sandbox credentials and record the results in [Platform API Research](research/platform-api-phase-0.md).

Required findings:

- Facebook Graph API public-only field test for candidate Page fields, including `id`, `name`, follower/fan count field availability, public post access, token type used, and exact permission errors.
- YouTube Data API quota plan proving on-demand sync avoids expensive discovery calls and primarily uses `channels.list` plus `playlistItems.list`.
- API field-to-schema mapping for every value required by the unified Subject schema.
- Initial `.env.example` variable list for platform credentials, test subject IDs, and sync defaults.
- Go/no-go decision for Phase 1, including unresolved API access blockers.

## Phase Documents

- [Phase 0 - Foundation](sprints/phase-0-foundation.md)
- [Phase 1 - Data Collector](sprints/phase-1-data-collector.md)
- [Phase 2 - Public API Gateway](sprints/phase-2-public-api-gateway.md)
- [Phase 3 - Telegram Mini App](sprints/phase-3-telegram-mini-app.md)
- [Phase 4 - Alert Engine](sprints/phase-4-alert-engine.md)
- [Phase 5 - Hardening and Handover](sprints/phase-5-hardening-handover.md)

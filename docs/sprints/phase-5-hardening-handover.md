# Phase 5 - Hardening and Handover

Window: Week 8  
Sprint: Sprint 8  
Goal: the system is production-ready, observable, and documented.

## Scope

Stabilize the full platform, verify end-to-end behavior, fill documentation gaps, clean up CI quality gates, and prepare handover materials.

For the Python backend, this phase should verify service runtime behavior across FastAPI, Celery workers, Redis, PostgreSQL, and the TypeScript Mini App frontend.

## Repositories

- `social-data-collector`
- `social-api-gateway`
- `social-alert-engine`
- `social-mini-app`
- `social-common`
- `social-infra`

## Deliverables

- End-to-end smoke test covering ingest, store, API, Mini App, alert configuration, alert evaluation, and Telegram notification.
- Structured logging across all runtime services.
- Health check endpoints verified for collector, gateway, alert engine, and Mini App hosting.
- README completed per repository with local setup, environment variables, run commands, test commands, and troubleshooting.
- CI checks enforced for Ruff, type checking, pytest, frontend lint/build, container build, and deployment readiness.
- API Gateway load test at expected peak traffic.
- Handover checklist covering credentials, deployment, operations, monitoring, and known limitations.

## Acceptance Criteria

- A new developer can follow repository READMEs and run the system locally.
- Full smoke test passes from platform ingestion through analyst notification.
- No known lint failures remain.
- Python backend services pass tests, type checks, migrations, and worker startup checks.
- API Gateway meets expected peak traffic target or has documented bottlenecks and next actions.
- Operational runbook explains how to rotate secrets, inspect logs, recover failed jobs, and verify service health.

## Dependencies

- All feature phases are functionally complete.
- Test credentials or fixtures are available for repeatable smoke tests.
- Deployment target and secrets management approach are confirmed.
- Worker concurrency and retry settings have been tested with representative data volume.

## Risks

- End-to-end defects may reveal cross-service contract drift late.
- Missing observability can make production failures hard to diagnose.
- Documentation can lag behind implementation unless updated as part of each fix.

## Sprint Exit

The phase exits when the system has passed end-to-end verification, all repositories are documented, operational procedures are clear, and remaining issues are explicitly tracked for post-handover work.

# Phase 0 - Foundation

Window: Week 0  
Sprint: Sprint 0  
Goal: everything is ready to build on Day 1.

## Scope

Set up the project baseline across all repositories, lock the shared schema, validate the highest-risk Facebook and YouTube API access paths, and prepare local development and CI conventions.

This sprint should confirm the Python backend decision explicitly. The recommended split is Python for backend services and shared contracts, with the Telegram Mini App remaining a TypeScript/React frontend.

Phase 0 must also produce a platform API research note before collector coding starts. The goal is to avoid designing `social-data-collector` around fields, permissions, or quota assumptions that fail in real API calls.

## Repositories

- `social-common`
- `social-infra`
- `social-data-collector`
- `social-api-gateway`
- `social-alert-engine`
- `social-mini-app`

## Deliverables

- Six repositories created with branch protection and PR conventions.
- `social-common` v1.0 published as a Python package with Pydantic models for the unified Subject schema, activity snapshot DTO, alert rule DTO, shared error codes, and response envelope.
- JSON Schema export added from `social-common` so the Mini App can consume stable contracts without duplicating backend model definitions manually.
- `social-infra` scaffolded with local Docker Compose, PostgreSQL, Redis, Alembic migration structure, environment templates, and basic CI.
- Python backend standards added: `pyproject.toml`, Ruff, formatter configuration, mypy or pyright, pytest, dependency management, and pre-commit hooks.
- Lint, formatting, test, and PR description standards documented.
- Facebook Graph API access validated with sandbox token, public Page sample calls, field availability, token type, and exact permission/scope errors.
- YouTube Data API v3 quota research completed for `channels.list`, `playlistItems.list`, and `search.list`; on-demand sync strategy documented to avoid unnecessary search calls.
- API field mapping documented from Facebook and YouTube responses into the unified Subject schema.
- Initial API research file created at `docs/research/platform-api-phase-0.md`.
- Initial `.env.example` variable list drafted for platform tokens, API keys, test subject IDs, and manual sync configs.
- Initial README in each repository explaining local setup and expected commands.

## Platform API Research Tasks

### Facebook Graph API

- Read the official Facebook Graph API and Page API documentation before implementation.
- Use Graph API Explorer or sandbox calls to test candidate public Page endpoints.
- Record the token type used for each test: App Access Token, Page Access Token, or User Access Token.
- Validate candidate fields for public-only monitoring: `id`, `name`, current follower/fan count field, public post list, post timestamps, and any activity count that can be fetched without Page admin access.
- Explicitly record denied fields and required permissions, especially private insights or fields that require Page admin permissions.
- Capture sample successful response payloads with sensitive tokens removed.
- Decide whether the Phase 1 collector can support Facebook public Page monitoring without admin access or whether this is a blocker.

### YouTube Data API v3

- Read official quota and endpoint docs before implementation.
- Validate `channels.list` for channel metadata and statistics.
- Validate `playlistItems.list` against the channel uploads playlist for latest video activity.
- Avoid `search.list` for on-demand sync unless there is a one-time discovery use case with a quota budget.
- Build a small quota worksheet covering subject count, manual sync frequency, endpoint cost, and daily projected usage.
- Record the default daily quota assumption and the exact Google Cloud quota page used for the project.
- Define back-off behavior for quota/rate-limit failures before Phase 1 worker implementation.

## Required Research Output

The file `docs/research/platform-api-phase-0.md` must include:

- Source links and access date.
- Tested account/app/project IDs or safe aliases.
- Endpoint, parameters, token type, result status, and response field notes.
- Field mapping table from platform response to unified Subject schema.
- YouTube quota worksheet with at least 10, 50, 100, and 500 subject scenarios.
- Phase 1 collector recommendations and blockers.

## Acceptance Criteria

- A developer can clone the repos, install dependencies, and start the local baseline environment.
- `social-common` exports typed Pydantic schema and DTOs expected by collector, gateway, alert engine, and Mini App contract generation.
- CI runs lint and test placeholders for every repository.
- Facebook API access is either confirmed with required scopes or raised as a blocking risk with exact missing permissions.
- YouTube sync strategy has a documented quota budget and avoids `search.list` usage during on-demand syncs.
- API response fields are mapped to the unified Subject schema with missing fields explicitly marked.
- `docs/research/platform-api-phase-0.md` exists and contains the required research output.
- Database migration scaffold can create the initial schema locally.

## Dependencies

- Access to Git hosting and branch protection settings.
- Facebook developer app and token with target public data permissions.
- Google Cloud project with YouTube Data API v3 enabled and API key or OAuth credentials.
- Test Facebook Page IDs and YouTube Channel IDs approved for sandbox validation.
- Initial infrastructure decisions for PostgreSQL, Redis, Celery workers, and time-series storage.

## Risks

- Facebook API scopes may be incomplete or return empty data silently.
- Facebook public Page fields may differ by Graph API version, token type, Page category, or app review state.
- YouTube `search.list` can consume the wrong quota bucket quickly and should not be part of on-demand sync.
- Quota usage can be underestimated if pagination or invalid requests are ignored.
- Schema instability can create downstream rework.
- Python and frontend schema sharing needs a clear JSON Schema generation path.
- Overbuilding infrastructure in Week 0 can delay core platform tasks.

## Sprint Exit

The phase exits when all teams can start feature work against a stable schema, local services can boot, and Facebook plus YouTube API risks have clear confirmed paths or documented escalations.

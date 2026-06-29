# AGENTS.md

Compact guidance for OpenCode agents working in this monorepo. Read this
before running commands or editing code; the traps below are not obvious from
filenames.

## Repo shape

Social Intelligence Platform monorepo. Python 3.11+ backend services plus one
TypeScript frontend. All Python packages use `pyproject.toml`, Ruff
(line-length 100, py311), strict mypy, and pytest.

| Package | Language | Layout | Role |
| --- | --- | --- | --- |
| `social-common` | Python | **flat** (no `src/`) | Shared Pydantic schemas/enums/errors. Pure lib, no runtime deps. |
| `social-data-collector` | Python | `src/` | Phase 1. Facebook + YouTube sync, Celery worker. Owns `subjects`, `activity_snapshots`. |
| `social-api-gateway` | Python | `src/` | Phase 2. FastAPI public API. Owns `api_keys`. |
| `social-alert-engine` | Python | `src/` | Phase 4. Alert evaluation + Telegram notification Celery worker. Owns `alert_logs`. |
| `social-mini-app` | TS/React | Vite | Telegram WebView frontend. Only Node package. |
| `social-infra` | — (not a package) | — | Docker compose + Alembic scaffold + CI notes. Phase 0 template only. |

There is **no monorepo-wide README**. The root `README.md` is the *gateway*
README (tracked, newer). `social-api-gateway/README.md` is a stale skeleton
(untracked) — trust the root one when they differ.

## Critical gotchas

- **`social-common` ships a single flat package.** The canonical layout is
  `social-common/social_common/` (`enums.py`, `schemas.py`, `envelope.py`,
  `errors.py`, `py.typed`) — this is what `pyproject.toml` ships (`packages =
  ["social_common"]`), what the root `conftest.py` puts on `sys.path`, and what
  the README's public API lists. There is no `social-common/src/` layout; do not
  recreate one. The `py.typed` marker is required so downstream `mypy` can
  analyze the package (PEP 561).
- **Two conflicting `docker-compose.yml` files.** The **root** one is canonical:
  `timescale/timescaledb:latest-pg16`, db/user `social_intel`, matches root
  `.env.example` `DATABASE_URL`. `social-infra/docker-compose.yml` is a diverged
  Phase 0 template (plain `postgres:16-alpine`, db/user `social`) — do not use it
  for the real services. Collector requires TimescaleDB (hypertable).
- **Real migrations live per-package** under `social-{collector,gateway}/migrations/`.
  There is no root `alembic/` or root `alembic.ini`; do not run alembic from the
  repo root. Run it from the package directory.
- **`.venv` may be Python 3.13** even though packages target `>=3.11`. Fine, but
  do not use 3.13-only syntax (e.g. multi-line f-string replacement fields are
  3.12+ only and break on 3.11).
- **Gateway README is stale on admin endpoints.** It lists `POST /v1/admin/keys`
  as "Out of Scope (deferred to Sprint 2)" but it **is implemented** in
  `social-api-gateway/src/social_api_gateway/admin/routes.py`. Auth is a static
  `ADMIN_TOKEN` bearer (separate from `X-API-Key`). If `ADMIN_TOKEN` is empty,
  all admin endpoints reject every request.
- **API key prefix is 16 chars, not 8.** `key_prefix()` returns the first 16
  chars of the raw key (the `ghn_live_`/`ghn_test_` literal plus 7 random base62
  chars). The `api_keys.key_prefix` column is `String(16)` with a UNIQUE
  constraint — the prefix must be unique per key so the lookup-then-verify
  pattern finds a single candidate. Do not shorten it back to 8 chars or every
  live key will collide on `ghn_live`.

## Mobile UI/UX rules (`social-mini-app`)

`social-mini-app` is a Telegram WebView mini-app, not a scaled-down web
dashboard. It is read on a phone, in short sessions, often one-handed. Do not
port desktop dashboard layouts (full chart grids, multi-column tables) directly
into this package — they fail review even if functionally correct.

- **Progressive disclosure.** Home screen shows at most 1-2 headline metrics
  per subject (e.g. weekly views, % change), not the full chart set. Full
  charts/breakdowns live one tap deeper (detail screen), never inline on the
  list/home screen.
- **One primary action per screen.** Each screen should answer one question
  ("what should I do today?"), not aggregate everything like a web dashboard.
  If a screen needs more than one clear CTA, split it.
- **Cards, not tables.** Never render multi-column data tables. Each
  subject/post is a card: 2-3 key metrics + one mini chart (sparkline) max.
  No raw grids ported from API responses.
- **Lightweight charts only.** Use sparkline / gauge / progress-ring
  components for in-list display. Full line/bar charts with axes, legends,
  tooltips are detail-screen only, opened via tap — never default-rendered on
  list screens.
- **Bottom navigation, thumb-reachable.** Primary nav is a bottom tab bar
  (Home / Inbox / Calendar / Analytics / Profile), not a sidebar or hamburger
  menu. Frequent actions (quick post, view new comments) get a visible
  affordance, not a buried menu item.
- **Push/Telegram notifications over polling.** Any "new state" the user
  needs to know about (milestone hit, new comment, alert fired) should be
  delivered via notification, not require the user to open the app to find
  out. Don't build features that only surface state on manual refresh if a
  push-capable alternative exists (see `social-alert-engine`).
- **Cache-first rendering.** Show last-known cached data immediately on open;
  fetch/refresh in the background. Never block initial render on a network
  call — this is a WebView inside Telegram, not a browser tab the user keeps
  open.
- **Gestures over click-equivalents.** Swipe to dismiss/approve a pending
  post, pull-to-refresh, long-press for quick actions. Don't reuse desktop
  patterns (right-click menus, hover states) — they don't exist in a
  touch/WebView context.

When in doubt: if a component or layout was designed by mentally shrinking a
web dashboard screen, it's wrong for `social-mini-app`. Design the mobile
screen as its own artifact first.

## Install order (matters)

`social-common` is a dependency of the gateway and collector. Install common
first, then the service, from the **repo root**:

```bash
pip install -e "./social-common[dev]" -e "./social-api-gateway[dev]"
# or
pip install -e "./social-common[dev]" -e "./social-data-collector[dev]"
```

`social-alert-engine` uses setuptools (not hatchling) and installs standalone:
`pip install -e "./social-alert-engine[dev]"`.

## Per-package commands

Run lint/typecheck/test **from inside each package directory** (config is
per-package in its `pyproject.toml`). There is no root-level runner.

Python packages (canonical checks, also the de-facto CI spec in
`social-infra/ci-template.md` — there are **no** `.github/workflows` yet):

```bash
ruff check .
ruff format --check .
pytest
mypy src        # alert-engine README uses `mypy src`; common has no src layout
```

Order when verifying a Python change: `ruff check -> mypy -> pytest`.

`social-mini-app` (Node, from `social-mini-app/`):

```bash
npm ci
npm run lint
npm run typecheck   # tsc --noEmit
npm run build       # tsc --noEmit && vite build  (no test script)
```

## Running the services

```bash
# Gateway (from social-api-gateway/)
uvicorn social_api_gateway.main:app --reload --host 0.0.0.0 --port 8000
# Swagger at /docs, /redoc; health at /v1/health

# Collector (from social-data-collector/)
python -m social_data_collector.main seed-subjects   # one-time: seed subjects into DB
python -m social_data_collector.main sync-facebook   # or sync-youtube | sync-all | health
celery -A social_data_collector.scheduler.celery_app worker --beat -l info  # dev: gộp worker+beat

# Mini app (from social-mini-app/)
npm run dev

# Alert engine (from social-alert-engine/)
social-alert-engine evaluate-all              # CLI: evaluate all subjects once
social-alert-engine evaluate-one <subject_id>  # CLI: evaluate a single subject
celery -A social_alert_engine.celery_app worker --beat -l info  # dev: gộp worker+beat
```

## Alembic / migrations

Run alembic **from the package directory** (`social-api-gateway/`,
`social-data-collector/`, or `social-alert-engine/`). Each `migrations/env.py`
loads the **root** `.env`
via `load_dotenv` and overrides the empty `sqlalchemy.url` in `alembic.ini` from
`get_settings().database.url` — so you do not need to edit `alembic.ini`.

```bash
cd social-data-collector && alembic upgrade head
cd social-api-gateway    && alembic upgrade head
cd social-alert-engine   && alembic upgrade head
```

- **Shared DB, separate version tables.** The collector uses
  `version_table="alembic_version_collector"`; the gateway uses the default
  `alembic_version`; the alert engine uses `alembic_version_alert_engine`. All
  point at the same Postgres+TimescaleDB instance but track versions
  independently. Do not collapse them into one version table.
- **Split table ownership.** Collector manages `subjects` + `activity_snapshots`;
  gateway manages `api_keys`; alert engine manages `alert_logs`. Do not
  autogenerate a migration in one package that touches the other's tables.
- `social-infra/migrations/` + `social-infra/alembic.ini` is a Phase 0 scaffold
  with a hardcoded `social:social@.../social_intelligence` URL that does **not**
  match the real `.env`. Avoid it for runtime work.

## Testing quirks

- **Integration-test gating differs per package — read the right one:**
  - `social-data-collector`: integration tests are **opt-in**, skipped by
    default. Run with `RUN_INTEGRATION=1 pytest -m integration -v` (needs live
    FB/YouTube credentials).
  - `social-api-gateway`: `pytest` runs unit **and** integration by default; use
    `pytest -m "not integration"` for unit only. Gateway integration tests use
    `aiosqlite` + `fakeredis`, so they run without external services.
- Collector live-Facebook smoke tool (no DB needed):
  `python social-data-collector/scripts/crawl_facebook.py --pretty`.
- Root `conftest.py` puts each package's `src/` on `sys.path` for tests; some
  packages also set `pythonpath = ["src"]` in `pyproject.toml`.

## Configuration

- All Python services load config exclusively from the **root** `.env` via
  `load_dotenv(_PROJECT_ROOT / ".env")`. The per-package `.env` files are
  **placeholders** — they are never read at runtime. Only root `.env` matters.
- Exception: `social-mini-app` loads `VITE_*` vars from its own `.env` (Vite
  convention). Non-VITE_ values (tokens, URLs) must also be present in root
  `.env` for the Python services that read them.
- The root `.env.example` documents every variable used by any package.
  Each package's `.env.example` documents its own subset for reference.
- Required for a runnable gateway: `DATABASE_URL`, `REDIS_URL`,
  `API_KEY_PEPPER` (rotating it invalidates every issued key), `ADMIN_TOKEN`
  (static bearer for `/v1/admin/*`; if empty all admin endpoints reject every
  request), `TELEGRAM_BOT_TOKEN`.
- API keys can now be created via `POST /v1/admin/keys` (requires `ADMIN_TOKEN`).
  The Python seed snippet in the root README is a legacy alternative.
- Start local deps with the **root** `docker compose up -d` (TimescaleDB + Redis).

## Style & commits

- Ruff rule sets differ: gateway/collector/common use
  `E,F,I,N,W,UP,B,C4,RET,SIM` (ignore `E501`); alert-engine uses `E,F,I,UP,B`.
  Tests allow `B011` in gateway/collector.
- Single branch is `master`. Commit style is conventional commits
  (`feat:`, `fix:`, `refactor:`, `chore:`, `test:`). Definition of done per
  `docs/sprint-overview.md`: PR merge, lint clean, tests/smoke documented, README
  or API docs updated where relevant.
- Do not commit real secrets; `.env` and `.env.local` are gitignored —
  `.env.example` files are the only committed templates.

## Tracking checks before approving implementation

Verify against `docs/` before marking done:

### API / endpoint quality

- [ ] 1. Endpoint is stable, returns correct and complete data.
- [ ] 2. API Key authentication works — invalid requests are rejected.
- [ ] 3. Filtering & pagination work correctly with multiple combined parameters.
- [ ] 4. Rate limit works — blocks requests exceeding the threshold.
- [ ] 5. Swagger docs are complete, sufficient for external integration without further questions.

### PR / convention

- [ ] 1. No lint errors when submitting PR.
- [ ] 2. Reviewer does not need to remind about convention more than twice on the same issue.
- [ ] 3. PR description clearly describes changes and how to test.
- [ ] 4. Always use curly braces for `if` statements, even for single-line bodies.
  - ❌ `if (condition) return;`
  - ✅ `if (condition) { return; }`
  
## Where to look for more

- `docs/sprint-overview.md` and `docs/sprints/phase-*.md` — phase scope,
  acceptance criteria, and quality gates per package (read before implementing).
- `docs/tracking/phase-3-implementation.md` — Phase 3 implementation tracking:
  read this first when resuming mid-implementation to know what's done and
  what's pending. Update checklists + status as work progresses.
- `docs/tracking/phase-4-implementation.md` — Phase 4 alert-engine implementation
  tracking with file manifest, ADR decisions per-step verification commands, and
  known gotchas.
- `docs/research/platform-api-phase-0.md` — Facebook/YouTube API findings the
  collector design depends on.
- `social-infra/ci-template.md` — minimum required checks (the CI spec until
  workflows are added).
- Each package's own `README.md` for its layout, endpoints, and config tables
  (but see the gotcha about the stale gateway-local README above).

# Phase 3 Plan — Telegram Mini App

Status: planning (reviewed after user feedback + telegram-miniapp-quickstart reference)
Derived from: `docs/sprints/phase-3-telegram-mini-app.md`
Read alongside: `AGENTS.md`, `docs/sprints/phase-2-public-api-gateway.md`

This document is the detailed implementation plan for Phase 3. It fixes the
scope against the **actual** current state of the repo (after the Phase 1/2
cleanup), surfaces backend prerequisites that Phase 2 left unfinished, and
specifies the code shape before any file is written.

---

## 1. Goal

Analysts can open the Social Intelligence Mini App inside Telegram and, without
leaving Telegram:

1. Browse and filter all monitored subjects.
2. Open a subject and inspect its follower/post-activity history as charts.
3. See a summary dashboard (totals, most active platform, last sync).
4. Create and update alert rules for a subject.

All data access goes through the API Gateway (`social-api-gateway`). The Mini
App never touches the database, Redis, or platform APIs directly.

## 2. Non-goals

- **No alert evaluation engine.** Rule *configuration* UI is in scope; the
  engine that *fires* notifications ships in Phase 4 (`social-alert-engine`).
  The Mini App only reads/writes rule rows.
- **No new platform connectors.** Facebook + YouTube remain the only platforms.
  The UI must not hard-code assumptions that break when a third platform lands.
- **No public/internet deployment automation.** We build a runnable Vite app
  testable in Telegram's WebView via `@BotFather` Web App URL. CI/CD, CDN, and
  TLS provisioning are Phase 5.
- **No reimplementation of backend contracts in TS by hand.** Types must come
  from the gateway's OpenAPI schema (generated), not be retyped.
- **No replacement of the Python backend.** Per the phase doc, the Mini App
  stays TypeScript/React because it runs in Telegram's WebView.

## 3. Current state (verified before planning)

### `social-mini-app` (target package)

- Bare placeholder: `src/main.tsx` renders a single `<h1>`. No routing, no API
  client, no Telegram SDK usage, no tests.
- `package.json` already depends on `@telegram-apps/sdk@^2.11`, `react@18`,
  `react-dom@18`, `vite@5`. Missing: router, data-fetching, charts, eslint
  config (script exists, no config file).
- `.env.example`: `VITE_API_BASE_URL`, `VITE_INTERNAL_API_KEY`,
  `VITE_TELEGRAM_BOT_USERNAME`.

### `social-api-gateway` (dependency)

Mounted routers (`main.py`): `health`, `subjects`, `admin`. **No `alerts`
router exists** — this is a Phase 2 Sprint 4 deliverable that was not built.
Available endpoints the Mini App can consume today:

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/v1/subjects` | List + filter (platform, status, q, dates) + paginate |
| `GET` | `/v1/subjects/{id}` | Single subject |
| `GET` | `/v1/subjects/{id}/activity` | Activity time-series (charts) |
| `POST` | `/v1/subjects/{id}/sync` | Trigger on-demand sync (internal) |
| `GET` | `/v1/health` | Health (not analyst-facing) |
| `POST` | `/v1/admin/keys` | Create API key (admin only, not for the UI) |

Auth: `X-API-Key` header. The Mini App uses a single **internal-tier** key baked
into the Vite build (`VITE_INTERNAL_API_KEY`).

### `social-common` (contracts)

`Subject`, `ActivitySnapshot`, `AlertRule` (Pydantic v2). Enums: `Platform`
(facebook, youtube), `SubjectStatus` (active, inactive, suspended),
`AlertRuleType` (follower_spike, follower_drop, activity_spike,
activity_silence, status_change). `py.typed` is present (PEP 561).

### `alert_rules` table

Created by `social-data-collector/migrations/versions/0001_initial_schema.py`
and modeled by `social-data-collector/.../persistence/models.py:AlertRuleModel`.
**The table exists in the shared DB** but no service exposes it over HTTP yet.

---

## 4. Backend prerequisites (must land before/with Sprint 6)

These are Phase 2 leftovers. They are listed here because Phase 3 cannot meet
its acceptance criteria without them. They are **not** Mini App code; they are
gateway work tracked here so Sprint 6 is unblocked.

### 4.1 Alert endpoints in the gateway (blocking Sprint 6)

**Why:** Phase 3 Sprint 6 requires "Connect alert config panel to internal API
endpoints." The endpoints do not exist. Without them the alert UI can only be a
mock, and the phase acceptance criterion "Analysts can create or update alert
thresholds for a subject" cannot pass.

**What to add (gateway):**

```
social-api-gateway/src/social_api_gateway/alerts/
  __init__.py
  models.py        # AlertRuleModel — mirrors the collector-owned table (read+write ORM), NO new migration
  repository.py    # list/get/create/update for alert_rules
  schemas.py       # AlertRuleResponse, AlertRuleListResponse, AlertRuleCreate, AlertRuleUpdate
  routes.py        # GET /v1/subjects/{id}/alerts, POST /v1/subjects/{id}/alerts,
                   # PUT /v1/alerts/{rule_id}, DELETE /v1/alerts/{rule_id}
```

**Interface preview — routes:**

```python
router = APIRouter(prefix="/v1", tags=["alerts"])

@router.get("/subjects/{subject_id}/alerts", response_model=AlertRuleListResponse)
async def list_alerts(subject_id: UUID, api_key=Depends(rate_limit), db=Depends(get_db_session)): ...

@router.post("/subjects/{subject_id}/alerts", status_code=201, response_model=AlertRuleResponse)
async def create_alert(subject_id: UUID, body: AlertRuleCreate, api_key=Depends(rate_limit), db=Depends(get_db_session)): ...

@router.put("/alerts/{rule_id}", response_model=AlertRuleResponse)
async def update_alert(rule_id: UUID, body: AlertRuleUpdate, api_key=Depends(rate_limit), db=Depends(get_db_session)): ...

@router.delete("/alerts/{rule_id}", status_code=204)
async def delete_alert(rule_id: UUID, api_key=Depends(rate_limit), db=Depends(get_db_session)): ...
```

**Model preview (gateway mirror, no migration):**

```python
class AlertRuleModel(Base):
    __tablename__ = "alert_rules"   # table created by collector's 0001 migration
    # fields mirror social_common.schemas.AlertRule + collector's AlertRuleModel
```

**Ownership note (AGENTS.md "Split table ownership"):** The collector created
`alert_rules`; the gateway adding a read/write ORM model pointing at an existing
table follows the **same pattern** the gateway already uses for `subjects` and
`activity_snapshots` (collector-owned tables, gateway mirror models, no gateway
migration). The rule "do not autogenerate a migration that touches the other's
tables" is respected: **no gateway migration is added.** If the schema ever
needs to change, the migration goes in the collector.

**Auth boundary:** All alert endpoints require an **internal** API key (write +
read). External keys are read-only and must be rejected with 403, not just
omitted from OpenAPI. Reuse the `rate_limit` dependency for per-key limits.

### 4.2 OpenAPI contract export (blocking typed frontend client)

**Why:** The phase doc explicitly says "Import or reference JSON Schema/OpenAPI
contracts generated by the Python API." The gateway serves `/openapi.json` live,
but there is no committed contract file. Hand-typed TS types will drift from the
Pydantic models (the phase doc lists this as a risk). A committed
`social-mini-app/src/api/openapi.json` regenerated from the gateway is the
single source of truth for `openapi-typescript` codegen.

**What to add:**

```
social-api-gateway/scripts/export_openapi.py   # writes openapi.json from create_app()
social-mini-app/src/api/openapi.json           # generated, committed
social-mini-app/src/api/types.ts               # generated via openapi-typescript
```

`export_openapi.py` preview:

```python
from social_api_gateway.main import create_app
from social_api_gateway.main import _custom_openapi
import json, pathlib

app = create_app()
schema = _custom_openapi(app)
pathlib.Path("social-mini-app/src/api/openapi.json").write_text(
    json.dumps(schema, indent=2, default=str)
)
```

Run it from the gateway dir after endpoints change; commit the regenerated
`openapi.json` + `types.ts`. CI (Phase 5) will diff-check this.

### 4.3 `priority` field decision (blocking Sprint 5 filter UI)

**Why:** Phase 3 Sprint 5 says "search and filter UI for platform, **priority**,
and status." `social_common.schemas.Subject` has no `priority` field. Either we
add it to the contract + collector + a migration, or we drop it from the UI.

**Decision (recommended): drop `priority` from Phase 3.** Rationale: adding a
field touches `social-common`, the collector model, the collector normalizers,
the gateway read model, a collector migration, and the OpenAPI contract — all
for a filter no analyst has asked for yet. Keep the filter bar extensible (the
component already supports a placeholder) and revisit `priority` as a Phase 4/5
enhancement with full backend support. This keeps Phase 3 focused on the
WebView surface.

If the team wants `priority` now, it becomes a tracked prerequisite: add
`priority: int = Field(ge=0, default=0)` to `Subject`, `SubjectModel`, a
collector migration `add_priority_to_subjects`, regenerate OpenAPI. Called out
here so it is a conscious choice, not a silent contract drift.

### 4.4 Telegram webhook endpoint (blocks bot → Mini App flow)

**Why:** The Mini App is a Vite static build — it has no server to receive
Telegram webhook calls. Without a webhook, the bot cannot respond to `/start`
or route users to the Mini App. The webhook must live in the **API Gateway**
(FastAPI), which already has HTTP infrastructure, rate limiting, auth, and
logging.

**Pattern reference:** The `telegram-miniapp-quickstart` reference project
uses a single Next.js server for webhook + UI + API. Since our UI is a
separate static Vite app, the gateway fills the "server" role — this is a
cleaner separation because the gateway already handles auth and rate limits.

**What to add (gateway):**

```
social-api-gateway/src/social_api_gateway/telegram/
  __init__.py
  routes.py        # POST /api/telegram-webhook — single entry point for Telegram updates
  bot.py           # helper: send_message, answer_pre_checkout_query

social-api-gateway/scripts/
  setup_webhook.py    # register webhook URL with Telegram
  webhook_info.py     # check webhook status
  delete_webhook.py   # remove webhook
```

**Route preview:**

```python
router = APIRouter(prefix="/api", tags=["telegram"])

@router.post("/telegram-webhook")
async def telegram_webhook(update: dict[str, Any]) -> dict[str, bool]:
    # Handle /start → reply with Mini App inline button
    # Handle /help → instructions
    # Handle pre_checkout_query → approve (Phase 4)
    # Everything else → ignore
    ...
```

**Minimal handler scope (Phase 3):** Only `text == "/start"` is handled —
reply with a welcome message and an inline button that opens the Mini App.
All other updates are acknowledged with `{"ok": true}` and ignored. The
alert engine (Phase 4) will add `pre_checkout_query`, `successful_payment`,
and alert notification handlers.

**Bot command set (in BotFather):**
- `/start` — Welcome + Mini App button (handled by webhook)
- `/help` — Usage instructions (handled by webhook)

**Webhook scripts (mirror reference pattern):**

```python
# setup_webhook.py
BOT_TOKEN = ...
APP_URL = ...     # ngrok or deployed URL
WEBHOOK_URL = f"{APP_URL}/api/telegram-webhook"

# Calls setWebhook with allowed_updates=["message", "callback_query", "pre_checkout_query"]
# Then calls getWebhookInfo to verify
```

**Why in the gateway, not a separate service:** The gateway is the only
HTTP-facing service in the system. Adding a webhook to the collector (Celery)
would require running an HTTP server inside the worker process. Adding a
separate service adds operational complexity for a ~30-line handler. The
gateway already has `FastAPI`, rate limiting, logging, and error handling
that the webhook reuses.

**No auth required for the webhook itself.** The webhook URL is a secret by
obscurity (only known to Telegram and the team). The `BOT_TOKEN` is validated
by Telegram's signature on each request (add in Phase 5 with
`X-Telegram-Bot-Api-Secret-Token`). For Phase 3, the endpoint is unauthenticated
but internal-only (not exposed in OpenAPI docs, not behind a public DNS yet).

---

## 5. Frontend architecture (`social-mini-app`)

### 5.1 Dependency additions

| Package | Why |
| --- | --- |
| `react-router-dom@^6` | List → detail → dashboard navigation; WebView back button maps to router history. |
| `@tanstack/react-query@^5` | Server state: caching, pagination, loading/error states, refetch-on-focus. The phase doc lists "API latency or pagination issues" as a risk; react-query's stale-while-revalidate directly addresses it. |
| `recharts@^2` | Follower trend + post-frequency charts. Lightweight, SVG-based, renders correctly in Telegram WebView (no canvas quirks). |
| `openapi-typescript@^7` (dev) | Generate `types.ts` from `openapi.json` — typed API client without hand-written DTOs. |
| `eslint@^9` + `eslint.config.js` | `npm run lint` exists but has no config; Phase 3 must ship lint clean per AGENTS.md. |
| `vite` env types | `vite-env.d.ts` for `import.meta.env.VITE_*`. |

### 5.2 Proposed file tree

```
social-mini-app/
  eslint.config.js             # new — flat config, eslint:recommended + react-hooks + type-aware
  vite.config.ts               # new — path alias @ -> src, proxy /v1 -> gateway in dev
  src/
    main.tsx                   # rewrite — providers + router + telegram init
    vite-env.d.ts              # new — VITE_* env typing
    api/
      openapi.json             # generated from gateway (prereq 4.2)
      types.ts                 # generated by openapi-typescript
      client.ts                # thin fetch wrapper: base URL, X-API-Key, envelope unwrap, error normalize
      hooks.ts                 # useSubjects, useSubject, useActivity, useAlerts, useCreateAlert, useUpdateAlert
    telegram/
      useTelegram.ts           # WebApp SDK init, theme params, viewport, back button, safe-area insets
      theme.css                # CSS variables mapped from telegram themeParams
    routes.tsx                 # route definitions
    pages/
      DashboardPage.tsx        # summary metrics
      SubjectListPage.tsx      # list + filter + search + paginate
      SubjectDetailPage.tsx    # subject header + activity charts + alert panel + sync button
    components/
      Layout.tsx               # app shell, safe-area padding, theme vars
      SubjectCard.tsx          # platform badge, status, followers, freq, last sync
      FilterBar.tsx            # platform, status, search input (extensible for priority)
      Pagination.tsx
      FollowerChart.tsx        # recharts LineChart from ActivitySnapshot[]
      ActivityFrequencyChart.tsx
      AlertConfigPanel.tsx     # rule type, threshold, cooldown, channel; create/update
      StateViews.tsx           # Loading, Empty, ErrorBoundary
    utils/
      format.ts                # number/date formatting (compact followers, relative time)
    styles.css                 # base reset + layout
  .env.example                 # expand with all VITE_* used + APP_URL for webhook
  README.md                    # rewrite — setup, bot linkage (BotFather), env, WebView test steps, webhook setup
```

### 5.3 Key code previews (shape only, before implementation)

**`src/api/client.ts`** — single fetch layer so no component calls `fetch` directly:

```ts
const BASE = import.meta.env.VITE_API_BASE_URL;
const KEY  = import.meta.env.VITE_INTERNAL_API_KEY;

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string) { super(message); }
}

export async function apiGet<T>(path: string, params?: Record<string, unknown>): Promise<T> {
  const url = new URL(BASE + path);
  if (params) for (const [k, v] of Object.entries(params)) if (v != null) url.searchParams.set(k, String(v));
  const res = await fetch(url, { headers: { "X-API-Key": KEY } });
  const body = await res.json();
  if (!res.ok) throw new ApiError(res.status, body?.error?.code ?? "http_error", body?.error?.message ?? res.statusText);
  return body.data as T;   // unwrap ResponseEnvelope
}
```

**Why this shape:** Every endpoint returns `ResponseEnvelope<T>` (`{data, meta}`).
Unwrapping once in the client means hooks/components deal in plain domain
objects, and `meta` (pagination) is returned alongside via a tuple or a small
`Paginated<T>` type. Errors are normalized to `ApiError` so the UI has one
error shape to render (the phase doc calls out "API error states").

**`src/telegram/useTelegram.ts`** — the WebView integration the phase doc
requires ("Telegram WebApp SDK lifecycle, theme variables, safe areas, back
button"):

Uses `@telegram-apps/sdk@^2.11` (v2.x) which provides mountable signals
instead of a singleton `WebApp` object. Components subscribe to signals
for reactive theme/viewport updates.

```ts
import { useEffect } from "react";
import {
  backButton, viewport, themeParams, init, retrieveLaunchParams
} from "@telegram-apps/sdk";

export function useTelegram() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    init();                              // init the SDK
    viewport.expand();
    backButton.mount();
    themeParams.mount();
    setReady(true);

    return () => {
      backButton.unmount();
      themeParams.unmount();
    };
  }, []);

  return {
    ready,
    theme: themeParams.state(),
    back: {
      show: () => backButton.show(),
      hide: () => backButton.hide(),
      onClick: (cb: () => void) => backButton.onClick(cb),
      offClick: (cb: () => void) => backButton.offClick(cb),
    },
    launchParams: retrieveLaunchParams(),
  };
}
```

**Why:** Telegram WebView is not a normal browser — theme colors, safe-area
insets, and the back button are controlled by the SDK, not CSS/media queries
alone. Centralizing this is the difference between "works in Telegram" and
"acceptance criterion 4 passes." The `@telegram-apps/sdk@^2.11` API uses
mountable signals (components subscribe to reactive state); the v1.x
singleton `WebApp.*` methods no longer exist. Code preview above matches
the v2.x API.

**`src/api/hooks.ts`** — react-query hooks (one per endpoint):

```ts
export function useSubjects(filters: SubjectFilters) {
  return useQuery({
    queryKey: ["subjects", filters],
    queryFn: () => apiGet<Subject[]>("/v1/subjects", filters),
    placeholderData: keepPreviousData,   // smooth pagination
    staleTime: 60_000,                    // matches gateway CACHE_LIST_TTL_SECONDS
  });
}
export function useActivity(subjectId: string) {
  return useQuery({ queryKey: ["activity", subjectId], queryFn: () => apiGet<ActivitySnapshot[]>(`/v1/subjects/${subjectId}/activity`) });
}
export function useCreateAlert(subjectId: string) {
  return useMutation({ mutationFn: (body: AlertRuleCreate) => apiPost(`/v1/subjects/${subjectId}/alerts`, body) });
}
```

**Why react-query:** the phase doc lists "API latency or pagination issues can
make list views feel slow" as a risk. `keepPreviousData` + `staleTime` aligned
to the gateway cache TTL gives instant page switches and no double-fetching
against the cache. It also gives loading/error states for free, satisfying
"loading, empty, and API error states."

### 5.4 Screen-by-screen mapping to acceptance criteria

| Screen | AC satisfied | Data source |
| --- | --- | --- |
| `SubjectListPage` | "Analysts can view and filter subject lists inside Telegram" | `GET /v1/subjects` |
| `SubjectDetailPage` (charts) | "Analysts can open a subject and inspect historical activity" | `GET /v1/subjects/{id}/activity` |
| `SubjectDetailPage` (alert panel) | "Analysts can create or update alert thresholds for a subject" | `POST /v1/subjects/{id}/alerts`, `PUT /v1/alerts/{rule_id}` (prereq 4.1) |
| `DashboardPage` | summary dashboard deliverable | `GET /v1/subjects` aggregate + last sync |
| `Layout` + `useTelegram` | "Theme, safe area, viewport, and back button behavior work in actual Telegram" | SDK |

### 5.5 Dashboard "alerts today" metric

Sprint 6 wants "alerts today" on the dashboard. The alert **engine** (which
counts fired alerts) is Phase 4. For Phase 3, "alerts today" is interpreted as
**alert rules created/updated today** (available from `alert_rules.updated_at`
once 4.1 ships), clearly labeled as rule activity, not fired-alert count. This
avoids depending on Phase 4 while giving analysts a useful signal. Flagged as a
known scope interpretation.

---

## 6. Interface / model changes summary

### Backend (gateway) — prerequisite work

| Change | File | Migration? |
| --- | --- | --- |
| Add `alerts` router + model + repo + schemas | `social_api_gateway/alerts/*` | **No** (table exists in collector) |
| Mount `alerts_router` | `main.py` | — |
| Add Telegram webhook endpoint | `social_api_gateway/telegram/routes.py` | — |
| Add webhook scripts (setup/info/delete) | `scripts/setup_webhook.py` etc. | — |
| Add OpenAPI export script | `scripts/export_openapi.py` | — |
| Internal-only guard on alert writes | `alerts/routes.py` (check `api_key.tier == INTERNAL` else 403) | — |

### Backend (social-common) — only if 4.3 decision is "add priority"

| Change | File |
| --- | --- |
| `priority: int = Field(ge=0, default=0)` on `Subject` | `schemas.py` |
| Collector model + migration | `social-data-collector` (migration `add_priority_to_subjects`) |

(Recommended: do **not** do this in Phase 3.)

### Frontend (mini-app) — all new

No backend model changes. Frontend types are **generated** from OpenAPI
(prereq 4.2), never hand-written domain models. The only hand-written types are
UI-only (filter state, route params).

---

## 7. Scenario (analyst flow)

1. Analyst opens the bot and sends `/start`. The gateway webhook responds
   with a welcome message and an inline button to open the Mini App. The
   analyst taps the button. `index.html` loads, `useTelegram` calls `init()`
   + `viewport.expand()`, theme vars applied.
2. `SubjectListPage` mounts → `useSubjects({})` → `GET /v1/subjects?limit=20`.
   Shows 20 subject cards with platform badge, status, followers, freq, last
   sync. `keepPreviousData` makes page 2 instant.
3. Analyst selects platform=facebook, status=active → `useSubjects({platform:
   "facebook", status: "active"})` → filtered list. URL search params synced
   (shareable).
4. Analyst taps a subject → router navigates to `/subjects/:id`. Back button
   becomes visible via `back.show()`.
5. `SubjectDetailPage` loads subject + activity in parallel. `FollowerChart`
   renders the time-series; `ActivityFrequencyChart` renders post frequency.
6. Analyst opens `AlertConfigPanel`, picks rule_type=follower_spike,
   threshold=1000, cooldown=3600, channel=@ops → `useCreateAlert` →
   `POST /v1/subjects/:id/alerts`. On success, panel switches to "edit existing
   rule" mode (`PUT /v1/alerts/{rule_id}`).
7. Analyst taps "Sync now" → `POST /v1/subjects/:id/sync` → toast "sync
   scheduled"; react-query invalidates subject/activity after a short poll.
8. Back button → list (cached, no reload). Theme change in Telegram →
   `themeParams.onChange` → CSS vars update live.

## 8. Why implement this way (rationale)

- **Typed client from OpenAPI, not hand-written:** the phase doc's #1 risk is
  contract drift. Codegen makes drift a compile error, not a runtime bug.
- **react-query over raw fetch:** pagination + cache + loading/error states are
  ~60% of the list/detail UI value and the phase doc calls out latency/pagination
  as a risk. Solving it with ad-hoc `useEffect`+`useState` is more code and
  worse UX.
- **recharts over a heavier lib:** WebView rendering quirks are a listed risk;
  SVG charts render reliably where canvas libs sometimes do not. recharts is
  small and tree-shakeable.
- **Alert endpoints as a prerequisite, not deferred:** the phase *cannot exit*
  without "create or update alert thresholds." Mocking them in the UI would fail
  the exit gate and push the work to Phase 4, where it does not belong.
- **Drop `priority`:** keeps Phase 3 from ballooning into a cross-package schema
  change. The filter bar stays extensible.
- **Internal-key-in-bundle:** standard for Telegram Mini Apps (the Web App is
  served from a trusted HTTPS domain configured in BotFather; the key is
  internal-tier and rate-limited). Not a public secret. Rotating it is a
  redeploy. A stronger scheme (Telegram-initData validation in the gateway) is
  Phase 5 hardening and noted as a risk.
- **Webhook in gateway, not separate service:** The Vite app is statically
  served — it cannot host a webhook. Adding a FastAPI route to the existing
  gateway is ~30 lines vs. spinning up a new service or bolting an HTTP server
  onto the Celery worker. The `telegram-miniapp-quickstart` reference project
  confirms the common pattern: one HTTP server owns the webhook + API + Mini
  App serving; our gateway already covers API + will cover webhook.

## 9. Risks & mitigations

| Risk (from phase doc / observed) | Mitigation |
| --- | --- |
| Contract drift (hand-written TS types) | OpenAPI codegen (4.2); CI diff-check in Phase 5 |
| WebView rendering quirks | recharts (SVG); test on real Telegram iOS + Android before exit |
| API latency / pagination feel slow | react-query `keepPreviousData` + `staleTime` = gateway cache TTL |
| Alert config UX error-prone | client + server validation; `AlertRuleCreate` schema enforces threshold/cooldown ranges; inline errors before submit |
| Internal API key exposed in bundle | internal tier = rate-limited, read+write alerts only; no admin/secret scope. Phase 5 adds Telegram initData auth. |
| Backend alert endpoints missing | explicitly tracked as prereq 4.1, must merge before Sprint 6 starts |
| Bot webhook needed for Mini App launch | prereq 4.4: gateway webhook endpoint + setup scripts; `/start` handler inline; ignores non-command updates |
| SDK v1/v2 API confusion (`WebApp.*` vs signals) | code preview in plan matches `@telegram-apps/sdk@^2.11` mounted-signal API; verify against actual SDK types |

## 10. Verification / done criteria

Mapped to `AGENTS.md` "Tracking checks before approving implementation":

**API / endpoint quality** (applies to the new alert endpoints, prereq 4.1)
- [ ] Alert endpoints stable, return correct data, follow `ResponseEnvelope`.
- [ ] API Key auth works; **internal-only** writes reject external keys (403).
- [ ] `GET /v1/subjects/{id}/alerts` supports pagination + active filter.
- [ ] Alert writes rate-limited per key.
- [ ] Swagger docs cover all alert routes (auto via FastAPI response models).

**PR / convention**
- [ ] `npm run lint`, `npm run typecheck`, `npm run build` clean in
  `social-mini-app/`.
- [ ] `ruff check`, `mypy src`, `pytest` clean in `social-api-gateway/` after
  adding the alerts router and webhook endpoint.
- [ ] OpenAPI regenerated and committed; `types.ts` regenerated.
- [ ] README updated with WebView test steps + env vars + BotFather config.
- [ ] Webhook script works: `python scripts/setup_webhook.py` returns success
  and `getWebhookInfo` shows the correct URL.

**Phase acceptance (from `phase-3-telegram-mini-app.md`)**
- [ ] View + filter subject list inside Telegram.
- [ ] Open subject + inspect historical activity (charts).
- [ ] Create/update alert thresholds for a subject.
- [ ] Theme, safe area, viewport, back button work in actual Telegram.
- [ ] All data access via the API Gateway (no direct DB/Redis from the UI).

## 11. Implementation order (sprints)

**Sprint 5 — list + filter + SDK**
1. Add deps (router, react-query, recharts, eslint config, openapi-typescript).
2. Prereq 4.2: OpenAPI export script → generate `openapi.json` + `types.ts`.
3. `client.ts` + `useTelegram` + `Layout` + theme.
4. `SubjectListPage` + `FilterBar` + `SubjectCard` + `Pagination`.
5. Loading/empty/error states.
6. Test in real Telegram WebView.

**Sprint 6 — detail + dashboard + alerts**
1. Prereq 4.1: gateway `alerts` router + model + repo + schemas + internal guard.
2. Prereq 4.4: gateway `telegram` webhook endpoint + `bot.py` helper + setup
   scripts (setup/info/delete). Register with Telegram via BotFather + script.
3. Regenerate OpenAPI (alerts schema appears; webhook is not in OpenAPI).
4. `SubjectDetailPage` + `FollowerChart` + `ActivityFrequencyChart` + sync
   trigger.
5. `AlertConfigPanel` wired to alert endpoints.
6. `DashboardPage` summary metrics.
7. README rewrite with BotFather config steps + WebView test on iOS + Android.

---

## 12. Decisions (settled before Sprint 5 starts)

| # | Question | Decision | Rationale |
|---|---|---|---|
| 1 | **Priority field** — add to backend or drop from Phase 3? | **Drop from Phase 3.** | Touches social-common, collector model, collector migration, gateway read model, OpenAPI — all for a filter no analyst has asked for. Filter bar stays extensible; revisit in Phase 4/5. |
| 2 | **Alert endpoint shape** — `POST /v1/subjects/{id}/alerts` + `PUT /v1/alerts/{rule_id}` vs `PUT /v1/subjects/{id}/alerts` (single upsert)? | **POST per-subject + PUT global** (plan recommendation). | Model allows multiple rules per subject (e.g. both `follower_spike` and `activity_silence`). Single upsert would need extra logic to differentiate which rule to update — more complex for no benefit. |
| 3 | **Dashboard "alerts today"** — count fired alerts (needs Phase 4) or count rule activity today? | **Rule activity today** (alert rules created/updated today from `alert_rules.updated_at`). | Avoids depending on Phase 4 engine. Clearly labeled as "Rule activity" in the UI, not "Fired alerts." Defer fired-alert count to Phase 4. |
| 4 | **Internal API key in Vite bundle** — acceptable? | **Acceptable for Phase 3** with strict scope: internal tier, read+write alert only, no admin/secret scope. rate-limited. | Standard Telegram Mini App pattern (Web App served from trusted HTTPS domain configured in BotFather). Rotating key = redeploy. initData HMAC validation deferred to Phase 5. |
| 5 | **Telegram webhook location** — separate service or in gateway? | **In API Gateway** (new `telegram/routes.py`). | Vite app is static (no server). Separate service adds ops overhead for a ~30-line handler. Gateway already has FastAPI + rate limit + logging. No new migration needed. |
| 6 | **Bot command set** — which commands to support in Phase 3? | `/start` (welcome + Mini App button) and `/help` (usage). | Everything else (payments, alert notifications) is Phase 4 alert engine work. |

---

## 13. Template references (research findings)

Research was done to find existing open-source templates matching our
structure (monitoring dashboard + subject list + charts + alerts in a Telegram
Mini App). No single template matches exactly, but three are worth referencing
for patterns.

### 13.1 cocoon-pulse (closest match)

**GitHub:** `beepboop2025/cocoon-pulse`  
**Stack:** React 19, Vite 7, TypeScript, Tailwind 4, recharts, Zustand,
`@telegram-apps/sdk-react`, Framer Motion  
**Stars:** 0 (new project, 2026-02)  
**Relevance: ★★★★★**

A Telegram Mini App for real-time GPU node monitoring — the closest structural
match to our Social Intelligence dashboard. Key patterns to borrow:

| Pattern | How cocoon-pulse does it | What we adapt |
|---|---|---|
| **Realtime charts** | Recharts + sparklines for live metrics | Same lib already chosen; borrow sparkline pattern for dashboard KPI cards |
| **Alert system** | Telegram notifications when node goes offline | Our alert panel UI follows a similar mental model (rule → threshold → notify) |
| **Glassmorphism UI** | Frosted-glass panels for dark/light themes | Not needed — our app uses Telegram theme vars for native look |
| **SDK v2 integration** | `@telegram-apps/sdk-react` (v2.x) — mountable signals | Confirms our plan's SDK choice and code preview shape |
| **Structure** | `src/pages/` + `src/components/` + `src/hooks/` + `src/utils/` | Same layout already planned |

**Do not clone.** Borrow the alert-config and chart patterns only. The project
has no Python backend, no subject/activity data model, and no API Gateway
integration.

### 13.2 analytics-dashboard (Serkanbyx/analytics-dashboard)

**GitHub:** `Serkanbyx/analytics-dashboard`  
**Stack:** React 19, Vite, TypeScript, shadcn/ui, Recharts, Redux Toolkit,
Tailwind, React Router  
**Relevance: ★★★☆☆**

Modern analytics dashboard with KPI cards, interactive charts, data tables,
pagination, filtering. Not Telegram-specific, but the KPI/chart component
patterns are directly portable:

- **KPI stat cards** with percentage-change indicators — use for dashboard
  metrics (total subjects, most active platform, last sync).
- **Searchable/sortable data table** with column sorting — adapt for subject
  list table view.
- **Protected routes pattern** — adapt for future Telegram initData validation.

### 13.3 official reactjs-template (Telegram-Mini-Apps/reactjs-template)

**GitHub:** `Telegram-Mini-Apps/reactjs-template`  
**Stack:** React 18, Vite, TypeScript, `@telegram-apps/sdk` (v2.x), TON Connect  
**Stars:** 413  
**Relevance: ★★★☆☆**

The official template from Telegram Mini Apps team. Useful for:

- **`mockEnv.ts` pattern** — `mockTelegramEnv()` simulates Telegram environment
  during development outside Telegram. We should add this to our dev setup so
  the app is testable in a regular browser.
- **SDK init boilerplate** — confirms the `init()` + mountable signal pattern
  from our plan.
- **GitHub Pages deploy** — the template shows how to deploy to GitHub Pages
  (`gh-pages` tool); an alternative to Vercel for the static mini app.

### 13.4 Recommendation

Do not fork or clone any of these. Our `social-mini-app` structure (Section
5.2) is already the right shape. Use these references for:

1. **cocoon-pulse** — confirm our `@telegram-apps/sdk` v2.x + recharts +
   Tailwind choices are industry standard for this type of app.
2. **analytics-dashboard** — borrow KPI card and data table component patterns
   (see `src/components/`).
3. **reactjs-template** — add a `src/mockEnv.ts` for browser development;
   consider Cloudflare Pages or GitLab Pages as deployment alternative.

---

## 14. Development deployment guide

### 14.1 Phase 3: ngrok (immediate tunnel, no deploy)

For Phase 3 development, use **ngrok** to expose your local gateway to
Telegram. This is faster than deploying — no Cloudflare/Railway setup
needed until production.

**Requirements:**
- Node.js 18+, local gateway running on port 8000
- ngrok installed (`brew install ngrok` or [download](https://ngrok.com/download))
- Telegram bot token (provided: `TELEGRAM_BOT_TOKEN`)

**Setup steps:**

```bash
# Terminal 1: Start the gateway locally
cd social-api-gateway
uvicorn social_api_gateway.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start ngrok tunnel
ngrok http 8000
# → https://abc123.ngrok-free.app  (copy this URL)
```

Two URLs from ngrok:
- Gateway API: `https://abc123.ngrok-free.app` (used by Mini App and webhook)
- Telegram webhook: `https://abc123.ngrok-free.app/api/telegram-webhook`

**Mini App dev config:**

```bash
# social-mini-app/.env.local
VITE_API_BASE_URL=https://abc123.ngrok-free.app
VITE_INTERNAL_API_KEY=<generated internal key>
VITE_TELEGRAM_BOT_USERNAME=your_bot_username

# Run dev server
cd social-mini-app && npm run dev
# → http://localhost:5173
```

**Webhook registration:**

```bash
cd social-api-gateway
python scripts/setup_webhook.py \
  --token <TELEGRAM_BOT_TOKEN> \
  --url https://abc123.ngrok-free.app/api/telegram-webhook
```

**BotFather config (via Telegram):**

1. Open [@BotFather](https://t.me/botfather)
2. `/mybots` → select your bot
3. **Bot Settings → Menu Button**
   - Title: "Social Intelligence"
   - URL: `https://abc123.ngrok-free.app` (ngrok URL; Mini App Vite dev
     runs on localhost:5173, but Telegram needs HTTPS; proxy the Vite dev
     server through ngrok or use a separate ngrok tunnel on port 5173)
4. **Bot Settings → Domain**
   - Set domain: `abc123.ngrok-free.app`

> **Tip for Mini App + API on ngrok:** If both the Mini App dev server
> (port 5173) and gateway (port 8000) need HTTPS, run **two ngrok tunnels**:
> `ngrok http 8000` for API/webhook, `ngrok http 5173` for the Mini App.
> Or run the Mini App build locally (`npm run build && npx serve dist -l 5173`)
> behind the API's ngrok tunnel.

**When ngrok URL changes (every restart):**
1. Re-run `setup_webhook.py` with new URL
2. Update BotFather Menu Button URL
3. Update `VITE_API_BASE_URL` in `.env.local`
4. Restart Vite dev server

### 14.2 Phase 5: Production deploy (Cloudflare Pages + Railway)

Deferred to Phase 5. When ready, see the production deployment guide at
`docs/deployment/production.md` (to be written in Phase 5).

**Summary of the target stack for reference:**

| Component | Platform | Justification |
|---|---|---|
| Mini App (static) | Cloudflare Pages | GitLab native, free, unlimited bandwidth |
| Gateway (FastAPI) | Railway | Nixpacks, Postgres + Redis one-click, no cold start |
| DB + Redis | Railway add-ons | Auto-injected env vars, private networking |
| CI/CD | GitLab CI + Wrangler | Deploy Mini App via Wrangler, Gateway via Railway token |

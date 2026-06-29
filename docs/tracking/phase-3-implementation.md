# Phase 3 Implementation Tracking

> Read this file to know exactly where implementation left off.
> Update status + checklist items as work progresses.
> Master plan: `docs/sprints/phase-3-plan.md`

## Status overview

| Area | Sprint | Status |
|---|---|---|
| Sprint 5 — Deps + config | 5 | [x] completed |
| Sprint 5 — OpenAPI codegen | 5 | [x] completed |
| Sprint 5 — client + Telegram SDK + Layout | 5 | [x] completed |
| Sprint 5 — Subject list page | 5 | [x] completed |
| Sprint 5 — WebView test | 5 | [ ] pending (manual) |
| Sprint 6 — Alert endpoints (prereq 4.1) | 6 | [x] completed |
| Sprint 6 — Telegram webhook (prereq 4.4) | 6 | [x] completed |
| Sprint 6 — Regenerate OpenAPI | 6 | [x] completed |
| Sprint 6 — Subject detail + charts + sync | 6 | [x] completed |
| Sprint 6 — Alert config panel | 6 | [x] completed |
| Sprint 6 — Dashboard + README | 6 | [x] completed |

**Last worked on:** 2026-06-24
**Current task:** All Sprint 5 and 6 items completed. WebView test remaining (manual).

---

## Sprint 5 — List, filter, SDK

### 5.1 Add dependencies

**Files created/modified:**
- `social-mini-app/package.json` — added `react-router-dom`, `@tanstack/react-query`, `recharts`, `openapi-typescript` (dev), `tailwindcss` (dev), `@tailwindcss/vite` (dev), `@vitejs/plugin-react` (dev), eslint plugins
- `social-mini-app/eslint.config.js` — flat config with eslint:recommended + react-hooks + type-aware
- `social-mini-app/vite.config.ts` — path alias `@` → `src`, proxy `/v1` → gateway, Tailwind plugin
- `social-mini-app/vite-env.d.ts` — env typings for `VITE_*`
- `social-mini-app/tsconfig.json` — added `paths` alias, included `vite-env.d.ts`

**Verification:** `npm run lint`, `npm run typecheck`, `npm run build` clean.

**Checklist:**
- [x] `react-router-dom@^6` installed
- [x] `@tanstack/react-query@^5` installed
- [x] `recharts@^2` installed
- [x] `openapi-typescript@^7` (dev) installed
- [x] `tailwindcss@^4` + `postcss` (dev) installed
- [x] `eslint.config.js` created with flat config
- [x] `vite.config.ts` created with path alias + proxy
- [x] `vite-env.d.ts` created

---

### 5.2 Prereq 4.2 — OpenAPI export script

**Files created/modified:**
- `social-api-gateway/scripts/export_openapi.py` — new: writes `openapi.json` to mini-app
- `social-mini-app/src/api/openapi.json` — generated, committed
- `social-mini-app/src/api/types.ts` — generated via `openapi-typescript`

**Verification:** `python scripts/export_openapi.py` runs without error; `openapi.json` + `types.ts` are valid.

**Checklist:**
- [x] `export_openapi.py` script created
- [x] `openapi.json` generated and committed
- [x] `types.ts` generated from `openapi.json`

---

### 5.3 Client + Telegram SDK + Layout + theme

**Files created/modified:**
- `social-mini-app/src/api/client.ts` — fetch wrapper: `apiGet`, `apiPost`, `apiPut`, `apiDelete`, `ApiError`
- `social-mini-app/src/api/hooks.ts` — react-query hooks: `useSubjects`, `useSubject`, `useActivity`, `useAlerts`, `useCreateAlert`, `useUpdateAlert`, `useDeleteAlert`, `useTriggerSync`, `useDashboardStats`
- `social-mini-app/src/telegram/useTelegram.ts` — SDK init, back button, theme, viewport
- `social-mini-app/src/telegram/theme.css` — CSS vars from `themeParams`
- `social-mini-app/src/components/Layout.tsx` — app shell with safe-area + theme
- `social-mini-app/src/main.tsx` — rewrite: QueryClientProvider + RouterProvider
- `social-mini-app/src/routes.tsx` — route definitions (/, /subjects/:id, /dashboard)
- `social-mini-app/src/styles.css` — base reset + Tailwind import

**Verification:** App renders in browser dev (mock Telegram env), no TS errors.

**Checklist:**
- [x] `client.ts` handles `GET/POST/PUT/DELETE`, `ResponseEnvelope` unwrap, `ApiError`
- [x] `useTelegram` mounts `backButton` + `themeParams` + `viewport.expand`
- [x] `theme.css` maps Telegram CSS vars
- [x] `Layout` wraps children with safe-area padding
- [x] `main.tsx` wires providers (QueryClient, Router)
- [x] `routes.tsx` defines `/`, `/subjects/:id`, `/dashboard`
- [x] `styles.css` reset + Tailwind + Telegram-compatible base

---

### 5.4 Subject list page

**Files created:**
- `social-mini-app/src/pages/SubjectListPage.tsx` — list + filter + paginate
- `social-mini-app/src/components/SubjectCard.tsx` — platform badge, status, followers, freq, last sync
- `social-mini-app/src/components/FilterBar.tsx` — platform, status, search (extensible)
- `social-mini-app/src/components/Pagination.tsx`
- `social-mini-app/src/components/StateViews.tsx` — Loading, Empty, Error
- `social-mini-app/src/utils/format.ts` — number/date formatting

**Verification:** TypeScript and lint clean.

**Checklist:**
- [x] `SubjectListPage` calls `useSubjects(filters)`
- [x] `FilterBar` filters by platform + status + search query
- [x] `SubjectCard` shows platform badge, followers, freq, last sync
- [x] `Pagination` page controls with `keepPreviousData`
- [x] `StateViews` Loading spinner, Empty message, Error
- [x] `format.ts` compact followers (1.2K, 3.5M), relative time ("2h ago")

---

### 5.5 WebView test

**Manual test — no CI.**

- [ ] Open via Telegram (not browser), verify `useTelegram` init
- [ ] Subject list loads and paginates
- [ ] Filters work (platform, status, search)
- [ ] Loading/empty/error states visible
- [ ] Theme matches Telegram (light/dark)

---

## Sprint 6 — Detail, dashboard, alerts

### 6.1 Prereq 4.1 — Alert endpoints in gateway

**Files created/modified:**
- `social-api-gateway/src/social_api_gateway/alerts/__init__.py`
- `social-api-gateway/src/social_api_gateway/alerts/models.py` — `AlertRuleModel` (mirror collector)
- `social-api-gateway/src/social_api_gateway/alerts/repository.py` — CRUD for `alert_rules`
- `social-api-gateway/src/social_api_gateway/alerts/schemas.py` — `AlertRuleCreate`, `AlertRuleUpdate`, response types
- `social-api-gateway/src/social_api_gateway/alerts/routes.py` — `GET/POST /v1/subjects/{id}/alerts`, `PUT/DELETE /v1/alerts/{rule_id}`
- `social-api-gateway/src/social_api_gateway/main.py` — mounted `alerts_router`

**Auth:** Internal key required for write (POST/PUT/DELETE). External keys get 403.

**Verification:** `ruff check .` + `mypy src` + `pytest` clean (68 tests pass).

**Checklist:**
- [x] `AlertRuleModel` mirrors collector's table (no migration)
- [x] `repository.py` implements list/get/create/update/delete
- [x] `schemas.py` defines `AlertRuleCreate`, `AlertRuleUpdate`, response types
- [x] `routes.py` 4 endpoints with `ResponseEnvelope`
- [x] Internal-only guard: `api_key.tier == INTERNAL` else 403
- [x] `main.py` mounts `alerts_router`

---

### 6.2 Prereq 4.4 — Telegram webhook endpoint

**Files created/modified:**
- `social-api-gateway/src/social_api_gateway/telegram/__init__.py`
- `social-api-gateway/src/social_api_gateway/telegram/routes.py` — `POST /api/telegram-webhook`
- `social-api-gateway/src/social_api_gateway/telegram/bot.py` — helpers: `send_message`, `inline_keyboard_markup`
- `social-api-gateway/src/social_api_gateway/config.py` — added `TelegramSettings` (`bot_token`, `app_url`, `bot_username`)
- `social-api-gateway/scripts/setup_webhook.py`
- `social-api-gateway/scripts/webhook_info.py`
- `social-api-gateway/scripts/delete_webhook.py`
- `social-api-gateway/.env.example` — added `TELEGRAM_BOT_TOKEN`, `TELEGRAM_APP_URL`, `TELEGRAM_BOT_USERNAME`

**Handler scope (Phase 3):** `/start` → welcome + Mini App inline button. `/help` → usage. Everything else → `{"ok": true}`.

**Verification:** `ruff` + `mypy` + `pytest` clean (68 tests pass).

**Checklist:**
- [x] `TelegramSettings` in config with `bot_token` + `app_url` + `bot_username`
- [x] `bot.py` helpers: `send_message`, `inline_keyboard_markup`
- [x] `routes.py` webhook handler: `/start`, `/help`
- [x] Webhook not in OpenAPI (`include_in_schema=False`)
- [x] `setup_webhook.py` calls `setWebhook` + `getWebhookInfo`
- [x] `webhook_info.py` prints status
- [x] `delete_webhook.py` removes webhook
- [x] `.env.example` updated

---

### 6.3 Regenerate OpenAPI

- [x] Run `python scripts/export_openapi.py` from gateway dir
- [x] Re-run `openapi-typescript` to regenerate `types.ts`
- [x] Updated `openapi.json` + `types.ts` (now includes AlertRule schemas)

---

### 6.4 Subject detail + charts + sync

**Files created:**
- `social-mini-app/src/pages/SubjectDetailPage.tsx` — header + charts + sync button + metric cards
- `social-mini-app/src/components/FollowerChart.tsx` — recharts LineChart from activity data
- `social-mini-app/src/components/ActivityFrequencyChart.tsx` — bar chart of post frequency

**Verification:** Charts render from activity data; sync button triggers POST; back button navigates.

**Checklist:**
- [x] `SubjectDetailPage` loads subject + activity in parallel
- [x] `FollowerChart` renders followers over time
- [x] `ActivityFrequencyChart` renders post frequency over time
- [x] Sync button calls `POST /v1/subjects/{id}/sync` with feedback
- [x] Back button via `back.show()` / `back.hide()`

---

### 6.5 Alert config panel

**Files created:**
- `social-mini-app/src/components/AlertConfigPanel.tsx` — rule type, threshold, cooldown, channel, create/update/delete

**Verification:** Can create alert rule → appears in list → can update → can delete.

**Checklist:**
- [x] Panel shows existing rules for subject
- [x] Create form: rule_type dropdown, threshold input, cooldown input, channel input
- [x] Create/POST successful → panel switches to edit mode
- [x] Update/PUT changes rule
- [x] Delete/DELETE removes rule
- [x] Validation before submit (threshold range, cooldown >= 0)

---

### 6.6 Dashboard + README

**Files created/modified:**
- `social-mini-app/src/pages/DashboardPage.tsx` — summary metrics with KPI cards
- `social-mini-app/README.md` — rewrite with setup, BotFather config, env vars, WebView test steps

**Dashboard metrics (Phase 3 scope):**
- Total subjects tracked
- Subjects by platform (Facebook vs YouTube)
- Most active platform (highest total activity_frequency)
- Last sync timestamp

**Checklist:**
- [x] `DashboardPage` renders all metrics
- [x] KPI cards with number formatting
- [x] README covers: setup, env, BotFather config, ngrok, WebView test
- [x] `npm run build` passes (typecheck + Vite build)

---

## Pre-existing CI config (`.gitlab-ci.yml`)

Already exists in the repo, covers lint + test for collector. Do not modify
until Phase 5 (production deployment) adds deploy stages.

Current stages: `ruff`, `mypy`, `test:unit`, `test:integration`.
Mini App checks (`npm run lint` + `npm run typecheck` + `npm run build`)
are not in CI yet — added in Phase 5.

---

## Quick reference: how to resume

```bash
# 1. Check this file's Status overview table
# 2. Find the first [ ] pending item
# 3. Read that section for checklist + files
# 4. Read the master plan (docs/sprints/phase-3-plan.md) for full context
# 5. Implement, then mark [x] completed + update Status overview

# Before submitting: verify
cd social-api-gateway && source ../.venv/bin/activate && ruff check . && mypy src && pytest -q
cd social-mini-app && npm run lint && npm run typecheck && npm run build
```

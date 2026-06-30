# Telegram Mini App Login — Implementation Tracking

> Read this file to know exactly where implementation left off.
> Update status + checklist items as work progresses.

## Status Overview

| Phase | Status |
|-------|--------|
| Phase 1 — Backend Foundation | [x] complete |
| Phase 2 — Frontend Auth Integration | [x] complete |
| Phase 3 — Polish | [ ] pending |

**Last worked on:** 2026-06-30
**Current task:** — (all phases done)

---

## Phase 1 — Backend Foundation (social-api-gateway)

### Task 1: Add PyJWT dependency + JWT config

**Files created/modified:**
- [x] `social-api-gateway/pyproject.toml` — added `PyJWT>=2.8`
- [x] `social-api-gateway/src/social_api_gateway/config.py` — added `JwtSettings` + aggregate on `Settings`
- [x] `.env.example` — added `JWT_SECRET`

**Verification:**
- [x] `ruff check . && mypy src` passes (from `social-api-gateway/`)
- [x] `python -c "from social_api_gateway.config import get_settings; s=get_settings(); print(s.jwt.secret)"` works

---

### Task 2: Telegram initData verification utility

**Files created/modified:**
- [x] `social-api-gateway/src/social_api_gateway/telegram/initdata.py` — `verify_init_data()` function
- [x] `social-api-gateway/tests/telegram/test_initdata.py` — 11 unit tests

**Verification:**
- [x] `ruff check . && mypy src` passes
- [x] `pytest tests/telegram/` passes
- [x] Valid initData returns parsed user dict
- [x] Tampered initData returns `None`
- [x] Expired initData returns `None`

---

### Task 3: POST /v1/auth/telegram-login endpoint + telegram_users table

**Files created/modified:**
- [x] `social-api-gateway/src/social_api_gateway/auth/models.py` — added `TelegramUserModel` (telegram_users table)
- [x] `social-api-gateway/migrations/versions/da7dc61cab6e_add_telegram_users_table.py` — manual-slim Alembic migration (autogenerate stripped of other-service tables)
- [x] `social-api-gateway/migrations/env.py` — registered `TelegramUserModel` import
- [x] `social-api-gateway/src/social_api_gateway/auth/routes.py` — `POST /v1/auth/telegram-login`
- [x] `social-api-gateway/src/social_api_gateway/main.py` — register auth router + OpenAPI scheme
- [x] `social-api-gateway/tests/auth/test_login.py` — integration tests

**Verification:**
- [x] `ruff check . && mypy src` passes
- [x] `pytest` passes (33/33)
- [x] `POST /v1/auth/telegram-login` with valid initData returns `{ token, user }`
- [x] `POST /v1/auth/telegram-login` with invalid initData returns 401
- [x] Telegram user is stored in `telegram_users` table (upsert on re-login)
- [x] Swagger shows the endpoint
- [x] `alembic upgrade head` applies cleanly (verified against live DB)

---

### Task 4: JWT auth dependency + IP rate limiting

**Files created/modified:**
- [x] `social-api-gateway/src/social_api_gateway/deps.py` — added `get_current_user()` JWT dependency + `rate_limit_auth()` for IP-based rate limiting
- [x] `social-api-gateway/tests/auth/test_security.py` — tests for JWT + rate limit deps

**Known gotcha avoided:** The `rate_limit()` function body was accidentally corrupted during the edit (orphaned response-header code from a faulty oldString match). Fixed by reading the full file and rewriting the function body correctly.

**Verification:**
- [x] `ruff check . && mypy src` passes
- [x] `pytest` passes
- [x] Valid JWT returns user info from token
- [x] Expired/tampered JWT returns 401
- [x] Auth endpoint returns 429 after 10 req/min per IP

---

### Checkpoint 1: Backend Complete

- [x] `ruff check . && mypy src` passes clean (0 issues)
- [x] `pytest` passes (all tests, 33/33)
- [x] JWT issuable via `POST /v1/auth/telegram-login`
- [x] JWT verifiable via `get_current_user`
- [x] Existing API key auth still works (backward compat)
- [x] Rate limiting on auth endpoint works

---

## Phase 2 — Frontend Auth Integration (social-mini-app)

### Task 5: Create AuthProvider + auth hooks

**Files created/modified:**
- [x] `social-mini-app/src/auth/AuthContext.tsx` — React context + provider
- [x] `social-mini-app/src/auth/useAuth.ts` — hook exporting `{ user, token, isAuthenticated, isLoading, error, logout }`
- [x] `social-mini-app/src/main.tsx` — wrap with AuthProvider
- [ ] `social-mini-app/src/api/types.ts` — optional: not needed (response types inline)

**Verification:**
- [x] `npm run lint && npm run typecheck && npm run build` passes (1 react-refresh warning, harmless)
- [x] AuthProvider extracts initData on mount (via `retrieveLaunchParams()`)
- [x] Calls `POST /v1/auth/telegram-login` with initData
- [x] Stores JWT in context + localStorage
- [x] Falls back to static API key outside Telegram

---

### Task 6: Update API client to use JWT

**Files created/modified:**
- [x] `social-mini-app/src/api/client.ts` — add `setAuthToken()`/`getAuthToken()`, `buildHeaders()` for dynamic auth header

**Verification:**
- [x] `npm run lint && npm run typecheck && npm run build` passes
- [x] Before login: requests use `X-API-Key` (fallback key from env)
- [x] After login: requests use `Authorization: Bearer <jwt>`
- [ ] 401 triggers re-auth in AuthProvider (not yet implemented — minimal viable scope)

---

### Task 7: Route protection + loading/error UI

**Files created/modified:**
- [x] `social-mini-app/src/navigation/Layout.tsx` — add auth-aware loading state combined with Telegram ready check
- [x] `social-mini-app/src/pages/SettingsPage.tsx` — add Account section with user info + logout button
- [x] `social-mini-app/src/i18n/translations.ts` — add auth translation keys (en + vi)

**Verification:**
- [x] `npm run lint && npm run typecheck && npm run build` passes
- [x] App shows loading spinner during auth on Telegram (combined with Telegram init spinner)
- [x] Settings shows "Logout" when authenticated (with user name/handle)
- [x] Logout clears JWT and reverts to API key

---

### Task 8: Dev fallback (VITE_TELEGRAM_AUTH_REQUIRED)

**Files created/modified:**
- [x] `social-mini-app/.env.example` — add `VITE_TELEGRAM_AUTH_REQUIRED=false`
- [x] `social-mini-app/src/auth/AuthContext.tsx` — honor dev fallback flag

**Verification:**
- [x] Dev mode with `VITE_TELEGRAM_AUTH_REQUIRED=false` works with static API key
- [x] Production mode with `VITE_TELEGRAM_AUTH_REQUIRED=true` shows error "This app must be opened inside Telegram." if initData missing

---

### Task 9: Verify admin endpoints unchanged

**Files touched:** None (verification-only)

**Verification:**
- [x] Admin endpoints still use `VITE_ADMIN_TOKEN` via static `Authorization: Bearer` header in `admin-client.ts`
- [x] Credential management works before and after auth changes

---

### Checkpoint 2: Frontend Complete

- [x] `npm run lint && npm run typecheck && npm run build` passes clean
- [ ] Full end-to-end flow: Telegram → initData → JWT → API calls (needs real Telegram WebView + backend)
- [x] Dev fallback works without Telegram
- [x] Admin endpoints still functional
- [x] Logout works

---

## Notes / Blockers

- **Alembic autogenerate trap:** Because the gateway shares a database with other services, `--autogenerate` detects all foreign tables as "removed" and generates drop operations. The migration was manually slimmed to only create `telegram_users`. The `env.py` imports only the gateway's models so Base.metadata stays scoped to gateway-owned tables, but Alembic's `--autogenerate` still sees the full DB. This is normal — just always review autogenerated output before committing.
- **rate_limit() edit corruption:** The original edit to deps.py matched the wrong `return api_key` and dropped the function body. Fixed by reading the full file and rewriting. Next edit to this area: use more context in `oldString` to ensure unique matching.

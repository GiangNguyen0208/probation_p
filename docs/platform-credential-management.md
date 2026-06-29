# Platform Credential Management

## Problem

The current system stores all platform credentials (access tokens, API keys)
in environment variables (`FACEBOOK_PAGE_ACCESS_TOKEN`, `YOUTUBE_API_KEY`).
This design has several limitations:

- **Single credential per platform** — every subject on a platform uses the same token.
  Cannot add multiple pages/channels belonging to different owners.
- **No credential lifecycle** — tokens expire, get revoked, or need rotation,
  but there is no audit trail or status tracking.
- **Adding new platforms requires code changes** — the `Platform` enum, four
  mirror-model files across packages, and the collector's client code must all
  be edited to add a new platform like TikTok or Instagram.
- **No audit trail** — no record of which credential was used to sync which
  subject, or when a credential was last verified.

## Solution

Two new database tables (`platforms` and `platform_credentials`) plus a
nullable foreign key on the existing `subjects` table. Together they provide
a generic, extensible credential store that decouples auth from subject
monitoring.

### New Tables

#### `platforms` — Registry of supported platforms

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` PK | `gen_random_uuid()` |
| `name` | `VARCHAR(100)` NOT NULL | Human-readable: "Facebook", "YouTube" |
| `slug` | `VARCHAR(50)` UNIQUE NOT NULL | Machine name matching `Platform` enum: `"facebook"`, `"youtube"` |
| `description` | `TEXT` nullable | Optional explanation |
| `auth_type` | `VARCHAR(50)` NOT NULL | `"access_token"`, `"api_key"`, `"oauth2"` |
| `config_schema` | `JSONB` NOT NULL | Describes credential fields for this platform |
| `icon_url` | `VARCHAR(500)` nullable | For UI display |
| `is_active` | `BOOLEAN` DEFAULT `true` | Soft-disable a platform |
| `created_at` | `TIMESTAMPTZ` NOT NULL | |
| `updated_at` | `TIMESTAMPTZ` NOT NULL | |

#### `platform_credentials` — Stored authentication per connected account

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` PK | `gen_random_uuid()` |
| `platform_id` | `UUID` FK → platforms.id | NOT NULL |
| `label` | `VARCHAR(255)` NOT NULL | User-given name: "GHN Careers FB Page" |
| `credentials` | `JSONB` NOT NULL | **Encrypted at rest** via `cryptography.fernet` |
| `status` | `VARCHAR(50)` DEFAULT `'active'` | `active`, `expired`, `revoked` |
| `last_verified_at` | `TIMESTAMPTZ` nullable | Last successful API call with this credential |
| `is_active` | `BOOLEAN` DEFAULT `true` | Soft-delete / disable |
| `created_at` | `TIMESTAMPTZ` NOT NULL | |
| `updated_at` | `TIMESTAMPTZ` NOT NULL | |

#### Modified `subjects` table

```sql
ALTER TABLE subjects ADD COLUMN credential_id UUID
    UNIQUE REFERENCES platform_credentials(id);
```

The `UNIQUE` constraint enforces the **1 credential = 1 subject** contract.

### Entity Relationship

```
platforms (1) ── (N) platform_credentials (1) ── (1) subjects
```

### Encryption

Credentials are encrypted at the application layer before being stored in the
`credentials` JSONB column. The DB never sees plaintext tokens.

- **Algorithm:** Fernet (symmetric AES-128-CBC + HMAC-SHA256)
- **Key source:** `CREDENTIAL_ENCRYPTION_KEY` env var (generated once via
  `fernet.Fernet.generate_key()`)
- **Encrypt on:** write — gateway admin service
- **Decrypt on:** read — collector clients before calling platform APIs

### Platform Config Schema

Each platform's `config_schema` describes what fields are required when
creating credentials for that platform. The schema format is a JSON object
mapping field names to their metadata.

```jsonc
// Facebook
{
  "access_token": {
    "type": "string",
    "label": "Page Access Token",
    "required": true,
    "sensitive": true
  },
  "page_id": {
    "type": "string",
    "label": "Facebook Page ID",
    "required": true,
    "sensitive": false
  }
}

// YouTube
{
  "api_key": {
    "type": "string",
    "label": "YouTube API Key",
    "required": true,
    "sensitive": true
  },
  "channel_id": {
    "type": "string",
    "label": "YouTube Channel ID",
    "required": true,
    "sensitive": false
  }
}
```

Fields marked `"sensitive": true` are encrypted; non-sensitive fields are
stored as plaintext inside the encrypted payload (or could be extracted to
dedicated columns in a future iteration).

## API Endpoints

All under `POST /v1/admin/`, authenticated by `Authorization: Bearer <ADMIN_TOKEN>`:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/v1/admin/platforms` | Register a new platform |
| `GET` | `/v1/admin/platforms` | List platforms |
| `GET` | `/v1/admin/platforms/{id}` | Get platform details + config_schema |
| `PUT` | `/v1/admin/platforms/{id}` | Update platform metadata |
| `POST` | `/v1/admin/credentials` | Create credential (encrypts, creates subject) |
| `GET` | `/v1/admin/credentials` | List credentials (never returns encrypted payload) |
| `GET` | `/v1/admin/credentials/{id}` | Get credential details |
| `PUT` | `/v1/admin/credentials/{id}` | Update credential + re-encrypt |
| `DELETE` | `/v1/admin/credentials/{id}` | Soft-delete (set `is_active=false`) |
| `POST` | `/v1/admin/credentials/{id}/verify` | Test credential against platform API |

## Data Flow

### Adding a new page/channel

```
Frontend                       Gateway Admin API              Database
    │                               │                           │
    │  POST /v1/admin/credentials   │                           │
    │  { platform_slug, label,      │                           │
    │    credentials: { ... } }     │                           │
    ├──────────────────────────────►│                           │
    │                               │  Validate config_schema   │
    │                               │  Encrypt credentials      │
    │                               │  INSERT platform_creds    │
    │                               ├──────────────────────────►│
    │                               │  INSERT subject (pending)  │
    │                               ├──────────────────────────►│
    │  { id, label, subject_id,     │                           │
    │    created_at }               │                           │
    │◄──────────────────────────────┤                           │
```

### Syncing a subject (collector)

The collector checks if the subject has a `credential_id`. If so, it reads
the decrypted credentials from `platform_credentials` instead of env vars.
If not, it falls back to the legacy env-var path.

```
Collector Sync Task             Database                       Platform API
    │                               │                              │
    │  SELECT subject               │                              │
    ├──────────────────────────────►│                              │
    │  subject.credential_id != NULL│                              │
    │  SELECT platform_credentials  │                              │
    ├──────────────────────────────►│                              │
    │  Decrypt credentials          │                              │
    │  Extract access_token/api_key  │                              │
    │                               │                              │
    │  API call with credential     │                              │
    ├──────────────────────────────┼──────────────────────────────►│
    │                               │                              │
```

## Migration Plan

| Step | Description | Impact |
|---|---|---|
| 1 | Create `platforms` + `platform_credentials` tables | Non-breaking (new tables) |
| 2 | Add `credential_id` to `subjects` (nullable, UNIQUE) | Non-breaking (new column, nullable) |
| 3 | Seed `platforms` rows: Facebook + YouTube | Data-only |
| 4 | Add Pydantic schemas to `social-common` | Non-breaking (new exports) |
| 5 | Add gateway admin CRUD endpoints | New feature |
| 6 | Update collector clients to read from DB with env-var fallback | Backwards-compatible |
| 7 | Mirror models in gateway + alert-engine | Standard pattern |

## Startup Validation

On startup, the gateway and collector run a validation check:

1. Query all active platform slugs from the DB
2. Verify each slug exists in the `Platform` enum
3. Log a warning on mismatch

This keeps the enum (static type safety) and DB (runtime data) in sync
without being overly rigid.

## File Changes Summary

| Package | Files |
|---|---|
| **social-common** | `social_common/schemas.py` — add `PlatformConfig`, `PlatformCredential` |
| **social-data-collector** | `persistence/models.py` — add ORM models; `migrations/versions/0003_add_platforms_and_credentials.py` — migration; `main.py` — `seed-platforms` CLI |
| **social-api-gateway** | `admin/platforms/models.py` — mirror ORM models; `admin/platforms/schemas.py` — Pydantic request/response; `admin/platforms/service.py` — encryption + business logic; `admin/platforms/routes.py` — HTTP endpoints; `admin/__init__.py` — include router; `config.py` — add `CREDENTIAL_ENCRYPTION_KEY` setting |
| **social-alert-engine** | `models.py` — add mirror ORM models |
| **social-data-collector** | `clients/facebook.py`, `clients/youtube.py`, `scheduler/tasks.py` — optional credential lookup |

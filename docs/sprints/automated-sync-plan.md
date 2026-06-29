# Automated Periodic Sync Plan

Status: planning (pre-implementation)
Derived from: `docs/sprints/phase-1-data-collector.md`, `docs/research/platform-api-phase-0.md`
Goal: "Facebook và YouTube data synced correctly with all schema fields; periodic sync runs automatically — no manual trigger needed."

---

## 1. Problem statement

The collector can sync manually (`python -m social_data_collector.main sync-facebook`)
but **cannot run automatically**. Three blocking gaps were found in the codebase:

### Gap A — No Celery beat schedule (auto-sync impossible)

`celery_app.py:1` says "Two periodic tasks: one for Facebook, one for YouTube"
in the docstring, but **no `beat_schedule` is defined**. The worker processes
on-demand tasks only. There is no `celery beat` process documented in the
README, AGENTS.md, or docker-compose. Without beat, periodic sync does not
happen.

### Gap B — Sync config fields missing from `config.py`

`.env` contains `SYNC_FACEBOOK_ENABLED`, `SYNC_YOUTUBE_ENABLED`, and
`SYNC_DEFAULT_INTERVAL_MINUTES`, but `SyncSettings` in `config.py` does **not**
declare these fields. They are silently ignored. `.env.example` doesn't list
them either. There is no way to configure sync interval or enable/disable
platforms through config.

### Gap C — Sync targets come from env vars, not the database

`_facebook_targets()` in `tasks.py:40` reads `FACEBOOK_TEST_PAGE_IDS` from
config (a comma-separated string). This means:
- Adding a new subject requires editing `.env` and restarting the worker.
- The `subjects` table (which already exists and has
  `list_subject_ids_for_platform()` in `repository.py:111`) is never queried
  for sync targets.
- There is no CLI or API to register new subjects into the DB.

For periodic sync to be self-sustaining, the scheduler must read targets from
the `subjects` table, and there must be a way to seed subjects.

### Gap D (quality) — Schema field completeness & status inference

| Issue | Detail |
| --- | --- |
| Status hardcoded | Both normalizers set `SubjectStatus.ACTIVE` unconditionally. Research doc says "define fallback for unavailable/suspended." A deleted YouTube channel returns 200 with empty `items`; a restricted Facebook Page may return data with zero followers. |
| YouTube `viewCount` | Research doc maps `statistics.viewCount` but the client/normalizer don't capture it. `Subject.extended_data` is the place for it (Facebook already stores insights/photos/videos there). |
| `FACEBOOK_PAGE_ACCESS_TOKEN` | `.env` has this var but `FacebookSettings` doesn't read it. Only `app_access_token` is used. The user confirmed the token is now valid, so the config must read the right token. |

---

## 2. Goal & non-goals

### Goal

1. **Periodic sync runs automatically** via Celery beat — no manual `sync-facebook`
   command needed. A beat process triggers sync cycles at a configurable interval.
2. **All `Subject` schema fields populated correctly** from Facebook + YouTube
   responses, with proper status inference.
3. **Subjects are seeded into the DB** via a CLI command, and the scheduler
   picks them up from the DB on each cycle.

### Non-goals

- **No new platform connectors.** Facebook + YouTube only.
- **No alert evaluation.** That is Phase 4.
- **No API gateway changes.** The gateway already reads from the DB; this plan
  only changes the collector.
- **No schema migration.** All fields already exist in `subjects` and
  `activity_snapshots`. `extended_data` (JSONB) absorbs `viewCount` without a
  migration.
- **No Docker production deployment.** Docker compose entries for worker/beat
  are added so local dev matches production shape, but production TLS/CI is
  Phase 5.

---

## 3. Changes by file

### 3.1 `config.py` — add missing sync settings

**Why:** `.env` already has `SYNC_FACEBOOK_ENABLED`, `SYNC_YOUTUBE_ENABLED`,
`SYNC_DEFAULT_INTERVAL_MINUTES` but `SyncSettings` ignores them. Without these,
beat cannot read the interval and there is no platform enable/disable toggle.

```python
class SyncSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SYNC_", ...)

    facebook_enabled: bool = True
    youtube_enabled: bool = True
    default_interval_minutes: int = 60       # beat schedule interval
    max_retries: int = 5                     # existing
    backoff_initial_seconds: int = 60        # existing
    backoff_max_seconds: int = 3600          # existing
    activity_sample_size: int = 50           # existing
```

Also add `page_access_token` to `FacebookSettings` (the `.env` has
`FACEBOOK_PAGE_ACCESS_TOKEN` which is currently unread):

```python
class FacebookSettings(BaseSettings):
    # ... existing fields ...
    page_access_token: SecretStr = SecretStr("")

    @property
    def has_credentials(self) -> bool:
        return bool(self.app_access_token.get_secret_value() or
                    self.page_access_token.get_secret_value())
```

The client will prefer `page_access_token` (Page-level, broader field access)
and fall back to `app_access_token`.

### 3.2 `scheduler/celery_app.py` — add beat schedule

**Why:** This is THE missing piece. The docstring promises periodic tasks but
no schedule is registered. Without `celery beat`, no task ever fires
automatically.

```python
from celery.schedules import crontab

_settings = get_settings()
_interval_minutes = _settings.sync.default_interval_minutes

celery_app.conf.beat_schedule = {
    "sync-facebook-cycle": {
        "task": "social_data_collector.scheduler.tasks.sync_all_facebook_subjects",
        "schedule": crontab(minute=f"*/{_interval_minutes}"),
    },
    "sync-youtube-cycle": {
        "task": "social_data_collector.scheduler.tasks.sync_all_youtube_subjects",
        "schedule": crontab(minute=f"*/{_interval_minutes}"),
    },
}
```

The beat entries call the existing `sync_all_facebook_subjects` /
`sync_all_youtube_subjects` dispatcher functions (currently only used by the
CLI). Those dispatchers fan out to per-subject `sync_facebook_subject` /
`sync_youtube_subject` tasks, which are already retryable.

### 3.3 `scheduler/tasks.py` — read targets from DB, not env vars

**Why:** For auto-sync to be self-sustaining, targets must come from the
`subjects` table. The existing `list_subject_ids_for_platform()` in
`repository.py:111` is never called. Env-var lists (`FACEBOOK_TEST_PAGE_IDS`)
remain as a **seed source only** — used on first run when the DB is empty.

Change `_facebook_targets()` and `_youtube_targets()`:

```python
def _facebook_targets() -> list[str]:
    settings = get_settings()
    if not settings.sync.facebook_enabled or not settings.facebook.has_credentials:
        logger.warning("sync.facebook.disabled_or_no_credentials")
        return []

    # Prefer subjects already in the DB (auto-sync loop).
    db_targets = run_in_transaction(
        lambda s: [
            str(r) for r in
            s.execute(select(SubjectModel.platform_id).where(SubjectModel.platform == Platform.FACEBOOK))
            .scalars().all()
        ]
    )
    if db_targets:
        return db_targets

    # Fallback: env-var seed list (first run / empty DB).
    return settings.facebook.test_page_ids
```

Same pattern for YouTube. The dispatcher functions (`sync_all_*`) remain
unchanged — they iterate the target list and call `.run()` on each per-subject
task.

### 3.4 `main.py` — add `seed-subjects` CLI command

**Why:** There is no way to register subjects into the DB. Without subjects in
the DB, the scheduler has nothing to sync. The env-var list was the only entry
point, and it requires a restart.

```python
# New subparser:
subparsers.add_parser("seed-subjects", help="Seed subjects from env-var lists into the DB.")

# Handler:
def _handle_seed_subjects(logger) -> int:
    """Insert env-var subject IDs into the DB as initial subjects.

    Idempotent: upserts by (platform, platform_id). Subjects already
    in the DB are not duplicated. This is run once after migrations
    to populate the auto-sync target list.
    """
    settings = get_settings()
    seeded = 0
    for page_id in settings.facebook.test_page_ids:
        run_in_transaction(lambda s, pid=page_id: _seed_subject(s, Platform.FACEBOOK, pid))
        seeded += 1
    for channel_id in settings.youtube.test_channel_ids:
        run_in_transaction(lambda s, cid=channel_id: _seed_subject(s, Platform.YOUTUBE, cid))
        seeded += 1
    logger.info("seed.complete", seeded=seeded)
    return 0
```

`_seed_subject` does a lightweight upsert with placeholder name/display_name
(the first sync will fill in the real fields from the platform API):

```python
def _seed_subject(session, platform, platform_id):
    existing = session.execute(
        select(SubjectModel).where(
            SubjectModel.platform == platform,
            SubjectModel.platform_id == platform_id,
        )
    ).scalar_one_or_none()
    if existing:
        return  # already seeded
    session.add(SubjectModel(
        platform=platform,
        platform_id=platform_id,
        name=f"Pending sync: {platform_id}",
        display_name=f"Pending sync: {platform_id}",
        followers=0,
        post_count=0,
        activity_frequency=0.0,
        status=SubjectStatus.INACTIVE,   # becomes ACTIVE after first successful sync
        last_synced_at=datetime.now(UTC),
    ))
    session.commit()
```

### 3.5 `normalizers/facebook.py` — status inference

**Why:** Currently always returns `SubjectStatus.ACTIVE`. A Page that returns
data but has zero followers and zero posts is likely inactive. A 404 raises
`SubjectNotFoundError` upstream (correct), but a restricted Page may return
200 with minimal data.

```python
# In FacebookNormalizer.normalize():
if followers == 0 and post_count == 0:
    status = SubjectStatus.INACTIVE
else:
    status = SubjectStatus.ACTIVE
```

### 3.6 `normalizers/youtube.py` — status inference + viewCount

**Why:** Same status issue. Also, the research doc maps `statistics.viewCount`
but it's not captured. Store it in `extended_data` alongside the Facebook
insights/photos/videos pattern.

```python
# In YouTubeNormalizer.normalize():
view_count = int(statistics.get("viewCount", 0))

if followers == 0 and post_count == 0:
    status = SubjectStatus.INACTIVE
else:
    status = SubjectStatus.ACTIVE

return Subject(
    # ... existing fields ...
    status=status,
    extended_data={"view_count": view_count} if view_count else None,
)
```

### 3.7 `clients/facebook.py` — prefer page access token

**Why:** `.env` has `FACEBOOK_PAGE_ACCESS_TOKEN` but the client only reads
`app_access_token`. Page access tokens give broader field access for public
Page data. The user confirmed the token is valid.

```python
def __init__(self, settings: FacebookSettings, retry_policy: RetryPolicy) -> None:
    # ...
    token = settings.page_access_token.get_secret_value() or \
            settings.app_access_token.get_secret_value()
    self._access_token = token
```

### 3.8 `.env.example` — add missing sync vars

```dotenv
# --- Data collector sync configuration ---
SYNC_FACEBOOK_ENABLED=true
SYNC_YOUTUBE_ENABLED=true
SYNC_DEFAULT_INTERVAL_MINUTES=60
SYNC_MAX_RETRIES=5
SYNC_BACKOFF_INITIAL_SECONDS=60
SYNC_BACKOFF_MAX_SECONDS=3600
```

Also add `FACEBOOK_PAGE_ACCESS_TOKEN=` to the Facebook section.

### 3.9 `docker-compose.yml` — add worker --beat container

**Why:** Local dev must be able to run the auto-sync loop end-to-end. Without a
worker container, periodic sync never fires after `docker compose up`.

**Decision (accepted):** Gộp worker + beat vào một container dùng
`worker --beat` cho dev đơn giản. Khi scale lên, tách thành 2 container riêng
— chỉ cần sửa 1 dòng `command` trong docker-compose.

```yaml
  worker:
    build: ./social-data-collector
    command: celery -A social_data_collector.scheduler.celery_app worker --beat -l info
    depends_on: [postgres, redis]
    env_file: .env
```

### 3.10 `README.md` + `AGENTS.md` — document beat process

**Why:** AGENTS.md "Running the services" only documents the worker, not beat.
Without `celery beat`, periodic sync never fires.

Add to AGENTS.md:
```bash
# Collector worker + beat (from social-data-collector/)
# Dev: gộp worker + beat trong 1 process. Prod: tách thành 2 process riêng.
celery -A social_data_collector.scheduler.celery_app worker --beat -l info
```

Add to README:
```bash
# One-time: seed subjects from env-var lists into the DB
python -m social_data_collector.main seed-subjects

# Start worker + beat for automatic periodic sync (dev: gộp 1 process)
celery -A social_data_collector.scheduler.celery_app worker --beat -l info
```

---

## 4. Schema field completeness audit

Checked against `docs/research/platform-api-phase-0.md` field mapping tables.

| Schema field | Facebook source | YouTube source | Status |
| --- | --- | --- | --- |
| `platform_id` | `id` | `id` | ✓ |
| `name` / `display_name` | `name` | `snippet.title` | ✓ |
| `followers` | `followers_count` / `fan_count` | `statistics.subscriberCount` | ✓ |
| `post_count` | `len(posts)` | `max(statistics.videoCount, len(uploads))` | ✓ |
| `activity_frequency` | derived from posts `created_time` | derived from `videoPublishedAt` | ✓ |
| `status` | hardcoded ACTIVE → **fix: infer from data** | hardcoded ACTIVE → **fix: infer from data** | **fix** |
| `last_synced_at` | collector-generated | collector-generated | ✓ |
| `extended_data` | insights + photos + videos | empty → **fix: add `view_count`** | **fix** |

After the changes, all `Subject` schema fields are populated from real platform
data. No field is left empty or hardcoded.

---

## 5. Scenario (automated sync flow)

### First-time setup

1. `alembic upgrade head` — creates `subjects`, `activity_snapshots`, `alert_rules`.
2. `python -m social_data_collector.main seed-subjects` — reads
   `FACEBOOK_TEST_PAGE_IDS` + `YOUTUBE_TEST_CHANNEL_IDS` from `.env` and inserts
   placeholder rows into `subjects` (status=INACTIVE).
3. Start worker: `celery -A ... worker -l info`
4. Start beat: `celery -A ... beat -l info`

### Periodic cycle (every `SYNC_DEFAULT_INTERVAL_MINUTES` minutes)

1. Beat fires `sync_all_facebook_subjects` task (if `SYNC_FACEBOOK_ENABLED=true`).
2. Dispatcher reads targets from `subjects` table (where `platform=facebook`).
3. For each subject, dispatcher calls `sync_facebook_subject.run(platform_id)`.
4. Per-subject task:
   a. Fetches page profile + recent posts via `FacebookClient`.
   b. Normalizes to `Subject` (status inferred, extended_data populated).
   c. Upserts `subjects` row + appends `activity_snapshots` row.
   d. On success, subject status becomes ACTIVE. On permanent failure, logged
      and skipped. On transient failure, retried with back-off.
5. Same cycle for YouTube (if `SYNC_YOUTUBE_ENABLED=true`).
6. Next cycle reads from DB again — newly seeded subjects are automatically
   included.

### Adding a new subject later

- Option A: add to `FACEBOOK_TEST_PAGE_IDS` in `.env`, run `seed-subjects` again
  (idempotent — existing subjects are not duplicated).
- Option B (future, Phase 3): use the gateway's sync-trigger endpoint
  (`POST /v1/subjects/{id}/sync`) to sync a new subject on demand, which
  creates the `subjects` row on first sync.

---

## 6. Interface / model changes summary

| Change | File | Migration? |
| --- | --- | --- |
| Add `facebook_enabled`, `youtube_enabled`, `default_interval_minutes` to `SyncSettings` | `config.py` | No |
| Add `page_access_token` to `FacebookSettings` | `config.py` | No |
| Add `beat_schedule` with crontab | `scheduler/celery_app.py` | No |
| Read targets from `subjects` table, fall back to env vars | `scheduler/tasks.py` | No |
| Add `seed-subjects` CLI command | `main.py` | No |
| Infer status from data instead of hardcoding ACTIVE | `normalizers/facebook.py`, `normalizers/youtube.py` | No |
| Store `view_count` in `extended_data` | `normalizers/youtube.py` | No |
| Prefer `page_access_token`, fall back to `app_access_token` | `clients/facebook.py` | No |
| Add missing sync vars to `.env.example` | `.env.example` | No |
| Add worker + beat containers | `docker-compose.yml` | No |
| Document beat + seed-subjects | `README.md`, `AGENTS.md` | No |

**No migrations needed.** All changes use existing columns. `extended_data` is
JSONB and absorbs `view_count` without a schema change.

---

## 7. Why implement these changes

| Change | Why |
| --- | --- |
| Beat schedule | Without it, sync never runs automatically. This is the core ask. |
| DB-driven targets | Env-var lists require a restart to add subjects. DB-driven targets let `seed-subjects` + future API calls add subjects without restarting the worker. |
| `seed-subjects` CLI | There is no other way to get subjects into the DB. The env-var list was the only entry point, and it was never persisted. |
| Config fields | `.env` already has these vars but they're silently ignored. Fixing this makes platform enable/disable and interval actually configurable. |
| Status inference | Hardcoded ACTIVE is wrong for deleted/restricted pages. The research doc explicitly calls for fallback status logic. |
| `viewCount` in `extended_data` | Research doc maps it; it's useful for the Mini App dashboard ("most active platform" metric). JSONB absorbs it without a migration. |
| `page_access_token` | The user has a valid Page token. The client currently only reads `app_access_token`, which may have narrower field access. |
| Docker worker + beat | Local dev must match production shape so the auto-sync loop is testable end-to-end. |

---

## 8. Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Beat + worker in same process is not production-safe | Run them as separate containers (plan specifies this). For dev, `celery -A ... worker --beat -l info` works but is not recommended for prod. |
| DB-driven targets return empty on first run | Fallback to env-var seed list. `seed-subjects` CLI populates the DB before the first beat cycle. |
| YouTube quota exhaustion from hourly sync | `SYNC_DEFAULT_INTERVAL_MINUTES` defaults to 60. Research doc quota worksheet shows 100 subjects at hourly = 4,800 units/day (within 10,000 default). Configurable via env. |
| Facebook token expiry | User confirmed token is valid. Token rotation is a manual `.env` update + worker restart. Phase 5 can add token refresh logic. |
| Status inference false-positive (new page with 0 followers = INACTIVE) | Acceptable: a brand-new page with 0 followers and 0 posts IS inactive. First real activity flips it to ACTIVE on the next sync. |

---

## 9. Verification / done criteria

Mapped to the two goals:

**"Dữ liệu Facebook và YouTube được đồng bộ đúng, đủ các trường theo schema"**
- [ ] All `Subject` schema fields populated from real API data (section 4 audit).
- [ ] `status` inferred from data, not hardcoded.
- [ ] YouTube `view_count` stored in `extended_data`.
- [ ] Facebook uses `page_access_token` when available.
- [ ] Normalizer unit tests pass with updated fixtures.
- [ ] `ruff check`, `mypy src`, `pytest -m "not integration"` clean.

**"Đồng bộ định kỳ hoạt động tự động — không cần chạy thủ công"**
- [ ] `celery_app.conf.beat_schedule` defines periodic tasks at
      `SYNC_DEFAULT_INTERVAL_MINUTES` interval.
- [ ] `SYNC_FACEBOOK_ENABLED` / `SYNC_YOUTUBE_ENABLED` control whether each
      platform's beat entry fires.
- [ ] `seed-subjects` CLI inserts subjects into the DB from env vars.
- [ ] Scheduler reads targets from `subjects` table, falls back to env vars
      when DB is empty.
- [ ] `celery beat` + `celery worker` documented in README and AGENTS.md.
- [ ] docker-compose includes worker + beat containers.
- [ ] End-to-end smoke: `seed-subjects` → start worker + beat → verify
      `subjects` rows update and `activity_snapshots` rows appear within one
      interval cycle.

---

## 10. Implementation order

1. **Config** — add missing `SyncSettings` fields + `page_access_token` to
   `FacebookSettings`. Update `.env.example`.
2. **Beat schedule** — add `beat_schedule` to `celery_app.py`.
3. **DB-driven targets** — rewrite `_facebook_targets()` / `_youtube_targets()`
   in `tasks.py` to read from `subjects` table with env-var fallback.
4. **Seed CLI** — add `seed-subjects` command to `main.py`.
5. **Status inference** — update both normalizers.
6. **viewCount** — update YouTube normalizer to capture `view_count` in
   `extended_data`.
7. **Facebook token** — update `FacebookClient.__init__` to prefer
   `page_access_token`.
8. **Docker** — add worker + beat containers to `docker-compose.yml`.
9. **Docs** — update `README.md` + `AGENTS.md` with beat/seed commands.
10. **Verify** — `ruff check`, `mypy src`, `pytest`, then end-to-end smoke with
    live credentials.

---

## 11. Decisions (accepted)

1. **Sync interval** — 60 minutes default (`SYNC_DEFAULT_INTERVAL_MINUTES=60`).
   Research doc quota worksheet shows 60-min intervals are safe up to 100
   subjects (4,800 units/day within 10,000 default quota).
2. **Beat + worker** — gộp `worker --beat` trong 1 container cho dev. Khi scale
   lên, tách thành 2 container riêng — chỉ cần sửa 1 dòng `command` trong
   docker-compose.
3. **Subject seeding** — `seed-subjects` CLI là đủ cho Phase 1. Gateway endpoint
   (`POST /v1/admin/subjects`) là việc của Phase 3.

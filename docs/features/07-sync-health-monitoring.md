# Feature Spec: Sync Health Monitoring & Failure Alerts

## Overview

Add **observability into the data collection pipeline** by tracking every sync attempt and surfacing health status to users. Currently, users have no visibility into whether a subject's data is fresh, stale, or failing to sync. Operations teams cannot tell if the collector is healthy without checking logs manually. This feature introduces a `sync_logs` table that records every sync attempt (success or failure), exposes health indicators in the Mini App, and adds alert rules that fire when syncs fail repeatedly — transforming silent failures into actionable notifications.

## Goals

- [ ] New `sync_logs` table: `subject_id`, `platform`, `started_at`, `completed_at`, `status` ("success" | "failure" | "partial"), `error_message`, `records_synced`, `duration_ms`.
- [ ] Collector writes a `SyncLog` entry at the end of **every** sync task (success or failure), including Celery task ID for traceability.
- [ ] Gateway exposes:
  - `GET /v1/subjects/{id}/sync-logs` — paginated sync history
  - `GET /v1/health/sync` — aggregated sync health (subjects synced in last 24h, failure rate %, average sync duration)
- [ ] Alert Engine supports new rule type `SYNC_FAILURE`: fires when a subject has `N` consecutive failed syncs within `X` hours.
- [ ] Mini App shows:
  - **Sync status indicator** on Subject List cards (green dot = synced <24h, yellow = 24-48h, red = >48h or last sync failed)
  - **Sync history** section in Subject Detail (last 5 sync attempts with status + error message)
  - **Global health card** on Dashboard ("X of Y subjects healthy", "Last failure: Z minutes ago")

## Non-Goals

- **We do NOT build a full observability dashboard (Grafana/Prometheus).** Sync health is surfaced through the existing Mini App and Telegram alerts only. External monitoring tools are out of scope.
- **We do NOT implement automatic retry logic.** The collector already has retry logic (`SYNC_MAX_RETRIES`, exponential backoff). This feature only *observes* and *reports* on it; it does not change retry behaviour.
- **We do NOT store full stack traces.** Only `error_message` (truncated to 500 chars). Full exception logs stay in structured JSON logs.
- **We do NOT support real-time sync status push.** Sync status is fetched on-demand or refreshed with normal polling/React Query. WebSocket push is out of scope.
- **We do NOT alert on partial failures.** A "partial" sync (e.g. some posts fetched but not all) is logged but does not trigger `SYNC_FAILURE` alerts. Only "failure" status counts.

## Architecture

### Data Model Changes

#### New Table: `sync_logs`

Owned by `social-data-collector` (same migration table as `subjects`).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `subject_id` | `UUID` | FK → `subjects.id`, `ON DELETE CASCADE` | |
| `platform` | `Enum(Platform)` | NOT NULL | Denormalised for query convenience |
| `task_id` | `String(64)` | nullable | Celery task UUID for traceability |
| `started_at` | `TimestampTZ` | NOT NULL | When Celery task began |
| `completed_at` | `TimestampTZ` | nullable | When sync finished (null if task crashed unhandled) |
| `status` | `Enum('success', 'failure', 'partial')` | NOT NULL | |
| `error_message` | `String(500)` | nullable | Truncated error text |
| `records_synced` | `Integer` | NOT NULL, default 0 | Posts/videos synced in this run |
| `duration_ms` | `Integer` | nullable | `completed_at - started_at` in milliseconds |
| `created_at` | `TimestampTZ` | NOT NULL | |

**Indexes:**
- `CREATE INDEX idx_sync_logs_subject ON sync_logs(subject_id, started_at DESC);`
- `CREATE INDEX idx_sync_logs_status_time ON sync_logs(status, started_at DESC);`
- `CREATE INDEX idx_sync_logs_recent ON sync_logs(started_at DESC) WHERE status = 'failure';`

#### New Schema in `social-common`

```python
class SyncLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID
    platform: Platform
    task_id: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    status: str  # "success" | "failure" | "partial"
    error_message: str | None = None
    records_synced: int = Field(ge=0, default=0)
    duration_ms: int | None = Field(ge=0, default=None)
    created_at: datetime = Field(default_factory=_utcnow)
```

### Service Interactions

```
┌─────────────────────────────┐
│ Celery Beat / Manual Trigger │── Initiates sync task
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-data-collector       │
│  Celery Worker              │
│                             │
│  ┌───────────────────────┐  │
│  │ 1. Insert sync_log   │  │── INSERT INTO sync_logs (started_at, status='pending')
│  │    (started)          │  │    UPDATE at end
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 2. Run sync pipeline  │  │── fetch → normalise → upsert
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 3. Update sync_log    │  │── UPDATE sync_logs SET status='success', completed_at=NOW(),
│  │    (completed)        │  │    records_synced=?, duration_ms=?
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ (on exception)        │  │── UPDATE sync_logs SET status='failure', error_message=truncate(str(e), 500)
│  └───────────────────────┘  │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-api-gateway          │
│  /v1/subjects/{id}/sync-logs│── Paginated history
│  /v1/health/sync            │── Aggregated health
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-alert-engine         │
│  SYNC_FAILURE rule          │── Evaluate consecutive failures
│  → Telegram notify          │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-mini-app             │
│  Status indicator           │── Green/Yellow/Red dot
│  Sync history panel         │── Last 5 attempts
│  Dashboard health card      │── Global summary
└─────────────────────────────┘
```

### API Contract

#### `GET /v1/subjects/{subject_id}/sync-logs`

```yaml
parameters:
  page: int (default 1)
  limit: int (default 10, max 50)
  status: enum ["success", "failure", "partial"] | null

response: SyncLogListResponse
  data: SyncLog[]
  meta: { page, limit, total }
```

#### `GET /v1/health/sync`

```yaml
response: SyncHealthResponse
  data: {
    "total_subjects": 45,
    "healthy_subjects": 43,     // synced in last 24h
    "stale_subjects": 2,        // last sync >24h ago
    "failed_subjects": 1,       // last sync was failure
    "last_24h": {
      "total_syncs": 120,
      "successful": 115,
      "failed": 5,
      "failure_rate": 4.2,
      "avg_duration_ms": 3400
    },
    "last_failure_at": "2024-01-15T09:23:00Z",
    "last_failure_subject": "Subject Name"
  }
```

## Code Changes

### 1. `social-common` — Schema

**File:** `social_common/schemas.py`

```python
class SyncLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID
    platform: Platform
    task_id: str | None = None
    started_at: datetime
    completed_at: datetime | None = None
    status: str = Field(pattern=r"^(success|failure|partial)$")
    error_message: str | None = Field(None, max_length=500)
    records_synced: int = Field(ge=0, default=0)
    duration_ms: int | None = Field(None, ge=0)
    created_at: datetime = Field(default_factory=_utcnow)
```

### 2. `social-data-collector` — Sync Logging

**File:** `src/social_data_collector/persistence/models.py` (modify)

- Add `SyncLogModel` SQLAlchemy model.

**File:** `src/social_data_collector/persistence/repository.py` (modify)

```python
class SyncLogRepository:
    async def create(self, subject_id: UUID, platform: Platform, task_id: str | None) -> SyncLogModel:
        """Create a pending sync log at task start."""
        log = SyncLogModel(subject_id=subject_id, platform=platform, task_id=task_id, started_at=_utcnow(), status="success")
        # Actually we should not use 'success' as default; we insert with a 'pending' concept or just insert at end.
        # Better approach: INSERT at start with a dummy status, UPDATE at end.
        # But 'pending' is not in our enum. Let's add it.
        ...

    async def complete(self, log_id: UUID, status: str, records_synced: int, error_message: str | None = None):
        """Update log at task completion."""
        ...
```

**Decision:** Simpler approach — INSERT at the **end** of the task only, not at start. This avoids needing a "pending" status and the complexity of updating a row if the task crashes without a finally block. We lose `started_at` precision slightly, but `created_at` is sufficient. If we want `duration_ms`, we can store `started_at` in a local variable and compute at the end.

**Revised approach:**
```python
async def log_sync(
    subject_id: UUID,
    platform: Platform,
    task_id: str | None,
    started_at: datetime,
    status: str,
    records_synced: int,
    error_message: str | None,
) -> None:
    duration_ms = int((datetime.now(UTC) - started_at).total_seconds() * 1000)
    log = SyncLogModel(...)
    db.add(log)
    await db.commit()
```

**File:** `src/social_data_collector/scheduler/tasks.py` (modify)

Wrap each sync task in try/except/finally to guarantee a log entry:

```python
@celery_app.task(bind=True, max_retries=SYNC_MAX_RETRIES)
def sync_facebook_subject(self, page_id: str) -> None:
    started_at = datetime.now(UTC)
    subject = None
    status = "success"
    error_message = None
    records_synced = 0
    
    try:
        # ... existing sync logic ...
        records_synced = len(posts)  # or whatever metric makes sense
    except Exception as exc:
        status = "failure"
        error_message = str(exc)[:500]
        logger.exception("sync.failed", page_id=page_id)
        raise self.retry(exc=exc, countdown=...)
    finally:
        if subject:
            await sync_log_repo.log_sync(
                subject_id=subject.id,
                platform=Platform.FACEBOOK,
                task_id=self.request.id,
                started_at=started_at,
                status=status,
                records_synced=records_synced,
                error_message=error_message,
            )
```

**Note:** Celery tasks are synchronous functions that use `asyncio.run()` or `asyncio.to_thread()` for async DB calls. Ensure the `finally` block executes even on retry. In Celery, `retry` raises an exception, so `finally` will run. Good.

### 3. `social-api-gateway` — Health Endpoints

**File:** `src/social_api_gateway/health/routes.py` (modify)

- Add `GET /v1/health/sync` endpoint (or extend existing health check).

**File:** `src/social_api_gateway/health/service.py` (new or modify existing)

```python
class SyncHealthService:
    async def get_sync_health(self) -> SyncHealth:
        total = await self._count_subjects()
        healthy = await self._count_subjects_synced_within(hours=24)
        stale = await self._count_subjects_synced_within(hours=48) - healthy
        failed = await self._count_subjects_with_last_status("failure")
        
        last_24h = await self._aggregate_sync_stats(since=datetime.now(UTC) - timedelta(hours=24))
        last_failure = await self._get_last_failure()
        
        return SyncHealth(...)
```

**File:** `src/social_api_gateway/subjects/routes.py` (modify)

- Add `GET /{subject_id}/sync-logs` endpoint.

**File:** `src/social_api_gateway/subjects/repository.py` (modify)

- Add `list_sync_logs(subject_id, status, limit, offset)` method.

### 4. `social-alert-engine` — SYNC_FAILURE Rule

**File:** `src/social_alert_engine/evaluator.py` (modify — see Feature 3)

Add `SYNC_FAILURE` evaluation (if not already done in Feature 3):

```python
if rule.rule_type == AlertRuleType.SYNC_FAILURE:
    # threshold = number of consecutive failures
    # baseline_window_hours = lookback window
    max_failures = int(rule.threshold)
    recent_logs = await repo.get_recent_sync_logs(subject_id, since=datetime.now(UTC) - timedelta(hours=rule.baseline_window_hours))
    consecutive_failures = count_consecutive_failures_from_end(recent_logs)
    if consecutive_failures >= max_failures:
        return {
            "triggered": True,
            "metric_value": consecutive_failures,
            "threshold": max_failures,
            "message": f"Sync failed {consecutive_failures} times in a row (limit: {max_failures})",
        }
```

**Note:** SYNC_FAILURE is similar to STALL but checks `sync_logs` instead of `activity_snapshots`. Should we merge them? No — STALL checks "no new data", SYNC_FAILURE checks "sync task crashed". They are semantically different.

### 5. `social-mini-app` — Health UI

**File:** `src/api/hooks.ts`

```typescript
export function useSyncLogs(subjectId: string) {
  return useQuery({
    queryKey: ["sync-logs", subjectId],
    queryFn: () => apiGet<SyncLog[]>(`/v1/subjects/${subjectId}/sync-logs`, { limit: 5 }),
    enabled: !!subjectId,
  });
}

export function useSyncHealth() {
  return useQuery({
    queryKey: ["sync-health"],
    queryFn: () => apiGet<SyncHealth>("/v1/health/sync"),
    staleTime: 300_000,
  });
}
```

**File:** `src/components/subject/SyncStatusIndicator.tsx` (new)

```tsx
// Small colored dot + optional text
// Green (#22c55e): last_synced_at < 24h ago && last sync status == success
// Yellow (#eab308): 24h <= last_synced_at < 48h || last sync == partial
// Red (#ef4444): > 48h || last sync == failure
// Grey (#9ca3af): never synced
```

**File:** `src/components/panels/SyncHistoryPanel.tsx` (new)

```tsx
// Subject Detail section: "Sync History"
// List of last 5 sync attempts (vertical timeline style)
// Each row: timestamp | status badge (green/yellow/red) | duration | records synced
// If failure: expandable to show error message (truncated, copyable)
```

**File:** `src/components/panels/SyncHealthCard.tsx` (new)

```tsx
// Dashboard section: "System Health"
// Card showing:
//   - "43/45 subjects healthy" (progress ring)
//   - "1 failure in last 24h" (if any)
//   - "Avg sync time: 3.4s"
//   - Tap → navigate to failing subject detail
```

**File:** `src/pages/Subjects/SubjectListPage.tsx` (modify)

- Add `<SyncStatusIndicator subject={subject} />` to each `SubjectCard` (top-right corner or next to platform badge).

**File:** `src/pages/Subjects/SubjectDetail.tsx` (modify)

- Add `<SyncHistoryPanel subjectId={id!} />` below Alerts section.

**File:** `src/pages/DashboardPage.tsx` (modify)

- Add `<SyncHealthCard />` at top of Dashboard.

## Interface Changes (UI/UX)

### New Components

| Component | Description |
|---|---|
| `SyncStatusIndicator` | Colored dot (green/yellow/red/grey) for subject health |
| `SyncHistoryPanel` | Timeline of last 5 sync attempts with status + duration |
| `SyncHealthCard` | Dashboard card with global sync health metrics |

### Modified Screens

| Screen | Change |
|---|---|
| `SubjectListPage` | Add `SyncStatusIndicator` to each `SubjectCard` |
| `SubjectDetailPage` | Add `SyncHistoryPanel` section |
| `DashboardPage` | Add `SyncHealthCard` at top |

### Design Notes (Mobile-First)

- **Dot is enough.** On subject cards, a 8px colored dot next to the platform badge communicates health without words. Long-press shows tooltip "Last sync: 2h ago".
- **Timeline, not table.** Sync history uses a vertical timeline with small circles (success=green, failure=red) and connecting line. Each item is one line: "2h ago · 1.2s · 15 posts".
- **Failure detail is secondary.** Error messages are hidden behind a "Show error" toggle to avoid cluttering the UI.
- **Dashboard health card is prominent.** It's the first card on Dashboard because system health is the #1 concern for users.

## Files Relevant (Complete List)

| # | File | Action | Description |
|---|---|---|---|
| 1 | `social-common/social_common/schemas.py` | Modify | Add `SyncLog` schema |
| 2 | `social-data-collector/migrations/versions/` | Create | Migration: `sync_logs` table |
| 3 | `social-data-collector/src/social_data_collector/persistence/models.py` | Modify | Add `SyncLogModel` |
| 4 | `social-data-collector/src/social_data_collector/persistence/repository.py` | Modify | Add `SyncLogRepository` |
| 5 | `social-data-collector/src/social_data_collector/scheduler/tasks.py` | Modify | Log sync in finally block |
| 6 | `social-api-gateway/src/social_api_gateway/subjects/repository.py` | Modify | Add `list_sync_logs` |
| 7 | `social-api-gateway/src/social_api_gateway/subjects/routes.py` | Modify | Add `GET /{subject_id}/sync-logs` |
| 8 | `social-api-gateway/src/social_api_gateway/health/` | Modify/Create | Add sync health endpoint |
| 9 | `social-api-gateway/src/social_api_gateway/health/schemas.py` | Modify | Add `SyncHealth` response schema |
| 10 | `social-alert-engine/src/social_alert_engine/evaluator.py` | Modify | Add `SYNC_FAILURE` rule evaluation |
| 11 | `social-alert-engine/src/social_alert_engine/repository.py` | Modify | Add `get_recent_sync_logs` |
| 12 | `social-api-gateway/scripts/export_openapi.py` | Modify | Regenerate |
| 13 | `social-mini-app/src/api/types.ts` | Regenerate | From OpenAPI |
| 14 | `social-mini-app/src/api/hooks.ts` | Modify | Add `useSyncLogs`, `useSyncHealth` |
| 15 | `social-mini-app/src/components/subject/SyncStatusIndicator.tsx` | Create | Colored health dot |
| 16 | `social-mini-app/src/components/panels/SyncHistoryPanel.tsx` | Create | Sync timeline |
| 17 | `social-mini-app/src/components/panels/SyncHealthCard.tsx` | Create | Dashboard health card |
| 18 | `social-mini-app/src/pages/Subjects/SubjectListPage.tsx` | Modify | Add status indicator to cards |
| 19 | `social-mini-app/src/pages/Subjects/SubjectDetail.tsx` | Modify | Add SyncHistoryPanel |
| 20 | `social-mini-app/src/pages/DashboardPage.tsx` | Modify | Add SyncHealthCard |

## Failure Scenarios

| Scenario | Detection | Impact | Mitigation |
|---|---|---|---|
| **Sync task crashes before finally block** | Unhandled exception in Celery | No sync log written | Celery's `task_failure` signal can write a log if finally fails. Alternatively, wrap the entire task body in a mega-try/except.
| **Sync log table grows unbounded** | Millions of rows | DB bloat, slow queries | Add retention: delete sync logs older than 90 days via nightly Celery task. Add index on `started_at`. |
| **All syncs failing (platform outage)** | `failed_subjects` = total | Alert storm | Add alert deduplication: only send one "Multiple sync failures" alert per hour instead of one per subject. |
| **Sync failure alert on first failure** | User set threshold=1 | Noisy alerts | Default threshold should be 3 consecutive failures. UI recommends 3.
| **Sync took 0ms** | `duration_ms` computed as 0 | Misleadingly fast | If duration < 1000ms, show "<1s" in UI instead of "0ms".
| **Feature overlaps with STALL** | Both detect "no new data" | User confusion | Clear documentation: STALL = "no new content detected"; SYNC_FAILURE = "sync task crashed". Different triggers. |
| **Error message contains secrets** | Facebook API error includes token | Leaked in UI | Sanitise error_message: remove URLs, tokens, keys before storing. Use regex to scrub `access_token=...` patterns. |

## Testing Strategy

### Unit Tests (Collector)

- **Task logging:** Mock sync task that succeeds → verify sync_log row with status="success", duration_ms > 0, records_synced correct.
- **Task logging failure:** Mock task that raises Exception → verify sync_log row with status="failure", error_message non-empty.
- **Repository:** Test `SyncLogRepository` CRUD.

### Integration Tests (Gateway)

- Seed 5 sync logs (3 success, 2 failure).
- Verify `/v1/subjects/{id}/sync-logs` returns correct order and filtering.
- Verify `/v1/health/sync` computes failure rate correctly.

### Alert Engine Tests

- Create `SYNC_FAILURE` rule with threshold=2.
- Insert 2 consecutive failure logs for a subject.
- Run evaluator → verify alert fires.
- Insert 1 success log after failures → verify alert does NOT fire (consecutive count resets).

### Mini App Tests

- `npm run lint && npm run typecheck && npm run build`.
- Manual: Subject card shows green dot; tap subject → sync history shows timeline; dashboard shows health card.

## Rollout Plan

### Phase 1: Schema & Migration (Day 1)
1. Add `SyncLog` schema to `social-common`.
2. Create collector migration for `sync_logs`.
3. Add `SyncLogModel` and repository.

### Phase 2: Collector Logging (Day 2)
1. Modify Celery sync tasks to write sync logs in `finally` block.
2. Add error message sanitisation.
3. Write unit tests.

### Phase 3: Gateway API (Day 3)
1. Add `list_sync_logs` to subject repository + route.
2. Add `/v1/health/sync` endpoint.
3. Regenerate OpenAPI.

### Phase 4: Alert Engine (Day 4)
1. Add `SYNC_FAILURE` rule evaluation.
2. Add `get_recent_sync_logs` repository method.
3. Write tests.

### Phase 5: Mini App (Day 5-6)
1. Add hooks.
2. Build `SyncStatusIndicator`, `SyncHistoryPanel`, `SyncHealthCard`.
3. Integrate into list, detail, and dashboard pages.

### Phase 6: Verification (Day 7)
1. Run all test suites.
2. Manual: trigger a failing sync → verify red dot appears, sync history shows failure, alert fires.

## Open Questions

1. **Retention policy:** How long should `sync_logs` be retained? 90 days is reasonable for operational debugging. Should we add a nightly cleanup task? Yes, recommend adding a `cleanup_sync_logs` Celery beat task that runs daily and deletes logs older than 90 days.
2. **Should we log "partial" status?** A partial sync means some data was fetched but not all (e.g. 20 of 25 posts). Is this useful? Yes — it distinguishes "complete failure" from "degraded success". Recommend logging partial when `records_synced > 0` but an exception occurred mid-sync.
3. **Error message sanitisation depth:** Should we write a dedicated sanitiser that scrubs known secret patterns (tokens, API keys, DB URLs)? Yes — a simple regex-based scrubber in `social-data-collector/src/social_data_collector/logging_setup.py` or a new `sanitise.py` module.
4. **Sync log vs. existing structured logs:** We already have structured JSON logs (`structlog`). Is `sync_logs` table redundant? No — structured logs are for operational debugging (engineers); `sync_logs` table is for user-facing health indicators and historical queries.
5. **Should SYNC_FAILURE be a separate rule type or a setting on STALL?** They are semantically different. STALL = "data is stale"; SYNC_FAILURE = "sync task crashed". Keep separate. Users may want one without the other.

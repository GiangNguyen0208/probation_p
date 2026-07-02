# Feature Spec: Weekly / Monthly Automated Reports via Telegram

## Overview

Deliver **periodic performance summaries** to users automatically via Telegram, leveraging the existing Telegram Bot infrastructure. Sprout Social calls this "Report Scheduled Delivery" (recurring weekly/monthly PDF reports via email); Sendible has "Automated Reports" that "never miss a report deadline." Our system already has a Telegram Bot (`@socialTracking_bot`), webhook handlers, and an alert engine that sends notifications. This feature adds a **scheduled report generation and delivery system** that runs on the alert engine's Celery beat schedule, composes a formatted report from subject data, and sends it to a configured Telegram chat/channel.

## Goals

- [ ] New `ReportSchedule` schema + table: `subject_id`, `frequency` ("weekly" | "monthly"), `day_of_week` (0-6), `hour` (0-23), `channel_id`, `format` ("summary" | "detailed"), `is_active`.
- [ ] Gateway provides full CRUD API for report schedules: `GET/POST/PUT/DELETE /v1/report-schedules` (internal key required for write).
- [ ] Alert Engine runs a **Celery beat task** that checks for due schedules every hour, generates reports, and delivers via `notifier.py` (raw HTTP to Bot API).
- [ ] Report content includes:
  - Growth summary (followers gained/lost this period)
  - Top performing content (from Feature 1's `posts` table, or fallback to `activity_frequency`)
  - Alert summary (how many alerts fired this period, by type)
  - Platform breakdown (subjects by platform, avg growth per platform)
  - Sync health status (any subjects with stale data)
- [ ] Mini App has a **Report Scheduling UI** in Settings or Subject Detail, allowing users to:
  - Create a new schedule (pick frequency, day, time, channel)
  - View list of active schedules
  - Toggle on/off
  - Preview a report (generate now, send immediately)
- [ ] Reports are delivered as **formatted Telegram messages** (HTML or MarkdownV2); PDF generation is deferred to Phase 6+.

## Non-Goals

- **We do NOT generate PDF reports in MVP.** Telegram messages are the delivery format. PDF export (like Sprout's "presentation-ready PDF") requires a PDF library (ReportLab, WeasyPrint) and is deferred.
- **We do NOT send reports via email.** Only Telegram delivery. Email is a separate integration (SMTP service) and out of scope.
- **We do NOT build custom report builders.** Users cannot drag-and-drop widgets or customise report layouts. Reports have a fixed template.
- **We do NOT support per-user personal schedules.** Schedules are tied to a `channel_id` (Telegram chat), not to individual users. If multi-user support is needed later, we can add `user_id`.
- **We do NOT archive old reports.** Each report is generated on-demand and sent; no historical report storage. If needed later, add a `report_deliveries` table.

## Architecture

### Data Model Changes

#### New Table: `report_schedules`

Owned by `social-alert-engine` (same migration table as `alert_logs`).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUID` | PK | System ID |
| `subject_id` | `UUID` | FK → `subjects.id`, nullable | If NULL, report covers ALL subjects |
| `frequency` | `Enum('weekly', 'monthly')` | NOT NULL | |
| `day_of_week` | `Integer` | nullable, 0-6 | For weekly: Monday=0 ... Sunday=6 |
| `day_of_month` | `Integer` | nullable, 1-28 | For monthly: day of month (capped at 28 to avoid Feb issues) |
| `hour` | `Integer` | NOT NULL, 0-23 | UTC hour of delivery |
| `channel_id` | `String(64)` | NOT NULL | Telegram chat ID |
| `format` | `Enum('summary', 'detailed')` | NOT NULL | |
| `is_active` | `Boolean` | NOT NULL, default `true` | |
| `last_sent_at` | `TimestampTZ` | nullable | When the last report was delivered |
| `created_at` | `TimestampTZ` | NOT NULL | |
| `updated_at` | `TimestampTZ` | NOT NULL | |

**Index:** `CREATE INDEX idx_report_schedules_active ON report_schedules(is_active, frequency, day_of_week, hour);`

#### New Schema in `social-common`

```python
class ReportSchedule(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID | None = None  # None = all subjects
    frequency: str  # "weekly" | "monthly"
    day_of_week: int | None = Field(None, ge=0, le=6)
    day_of_month: int | None = Field(None, ge=1, le=28)
    hour: int = Field(ge=0, le=23)
    channel_id: str
    format: str  # "summary" | "detailed"
    is_active: bool = True
    last_sent_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
```

### Service Interactions

```
┌─────────────────────────────┐
│ social-mini-app             │
│  ReportSchedulePanel        │◄── CRUD /v1/report-schedules
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-api-gateway          │
│  report-schedules routes    │── Auth: internal key for write
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ PostgreSQL                  │
│  report_schedules           │── Owned by alert-engine migration
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-alert-engine         │
│  Celery Beat (hourly)       │── Check due schedules
│                             │
│  ┌───────────────────────┐  │
│  │ 1. Query active       │  │── SELECT * FROM report_schedules
│  │    schedules due now  │  │    WHERE is_active=true
│  │                       │  │    AND hour = EXTRACT(hour FROM NOW())
│  │                       │  │    AND (day_of_week = EXTRACT(dow) OR day_of_month = EXTRACT(day))
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 2. Generate report    │  │── Query activity_snapshots, posts, alert_logs
│  │    (ReportBuilder)    │  │
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 3. Deliver via        │  │── POST https://api.telegram.org/bot<token>/sendMessage
│  │    Telegram Bot API   │  │
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 4. Update last_sent_at│  │── UPDATE report_schedules SET last_sent_at=NOW()
│  └───────────────────────┘  │
└─────────────────────────────┘
```

### API Contract

#### `GET /v1/report-schedules`

```yaml
response: ReportScheduleListResponse
  data: ReportSchedule[]
  meta: { page, limit, total }
```

#### `POST /v1/report-schedules`

```yaml
body: ReportScheduleCreate
  subject_id: UUID | null
  frequency: "weekly" | "monthly"
  day_of_week: int (0-6, required if weekly)
  day_of_month: int (1-28, required if monthly)
  hour: int (0-23)
  channel_id: str
  format: "summary" | "detailed"

response: ReportScheduleResponse (201 Created)
```

**Validation:**
- If `frequency == "weekly"`, `day_of_week` is required and `day_of_month` must be null.
- If `frequency == "monthly"`, `day_of_month` is required and `day_of_week` must be null.

#### `PUT /v1/report-schedules/{schedule_id}`

Toggle `is_active`, change `hour`, `format`, etc.

#### `DELETE /v1/report-schedules/{schedule_id}`

204 No Content.

#### `POST /v1/report-schedules/{schedule_id}/preview` (optional)

Generate and send report immediately (one-off), regardless of schedule.

## Code Changes

### 1. `social-common` — Schema

**File:** `social_common/schemas.py`

```python
class ReportSchedule(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID | None = None
    frequency: str = Field(pattern=r"^(weekly|monthly)$")
    day_of_week: int | None = Field(None, ge=0, le=6)
    day_of_month: int | None = Field(None, ge=1, le=28)
    hour: int = Field(ge=0, le=23)
    channel_id: str
    format: str = Field(pattern=r"^(summary|detailed)$")
    is_active: bool = True
    last_sent_at: datetime | None = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
```

### 2. `social-alert-engine` — Report Builder & Delivery

**File:** `src/social_alert_engine/reports.py` (new)

```python
class ReportBuilder:
    """Generate formatted report content from database queries."""

    def __init__(self, db: AsyncSession, schedule: ReportScheduleModel):
        self.db = db
        self.schedule = schedule

    async def generate(self) -> str:
        """Return MarkdownV2 formatted report text for Telegram."""
        lines = ["📊 *Weekly Social Intelligence Report*"]
        
        if self.schedule.subject_id:
            lines.append(f"Subject: {await self._get_subject_name()}")
        else:
            lines.append("All monitored subjects")
        
        lines.append("")
        lines.extend(await self._growth_section())
        lines.append("")
        lines.extend(await self._top_content_section())
        lines.append("")
        lines.extend(await self._alert_summary_section())
        lines.append("")
        lines.extend(await self._platform_breakdown_section())
        lines.append("")
        lines.extend(await self._sync_health_section())
        
        return "\n".join(lines)

    async def _growth_section(self) -> list[str]:
        """Follower growth per subject over last 7 days."""
        ...

    async def _top_content_section(self) -> list[str]:
        """Top 3 posts by engagement rate (requires Feature 1)."""
        ...

    async def _alert_summary_section(self) -> list[str]:
        """Count of alerts fired this week by type."""
        ...

    async def _platform_breakdown_section(self) -> list[str]:
        """Subjects by platform + avg growth."""
        ...

    async def _sync_health_section(self) -> list[str]:
        """Subjects with stale data (>48h since last sync)."""
        ...
```

**File:** `src/social_alert_engine/tasks.py` (modify)

```python
@celery_app.task(name=TASK_NAMES["send_scheduled_reports"])
async def send_scheduled_reports() -> None:
    """Celery beat task: runs every hour. Checks for due report schedules and sends them."""
    now = datetime.now(UTC)
    async with async_session() as db:
        repo = ReportScheduleRepository(db)
        due_schedules = await repo.list_due_schedules(
            current_hour=now.hour,
            current_dow=now.weekday(),
            current_day=now.day,
        )
        for schedule in due_schedules:
            try:
                builder = ReportBuilder(db, schedule)
                report_text = await builder.generate()
                await send_telegram_message(
                    chat_id=schedule.channel_id,
                    text=report_text,
                    parse_mode="MarkdownV2",
                )
                await repo.mark_sent(schedule.id, sent_at=now)
                logger.info("report.sent", schedule_id=str(schedule.id))
            except Exception:
                logger.exception("report.failed", schedule_id=str(schedule.id))
                # Do NOT mark as sent — will retry next hour if still due
```

**File:** `src/social_alert_engine/models.py` (modify)

- Add `ReportScheduleModel` SQLAlchemy model.

**File:** `src/social_alert_engine/repository.py` (new or modify existing)

- Add `ReportScheduleRepository` with `list_due_schedules`, `mark_sent`, CRUD methods.

**File:** `migrations/versions/` (new)

- Migration: create `report_schedules` table.

**File:** `src/social_alert_engine/celery_app.py` (modify)

- Add beat schedule entry:
```python
"send-reports-hourly": {
    "task": TASK_NAMES["send_scheduled_reports"],
    "schedule": crontab(minute=0),  # Every hour at :00
}
```

### 3. `social-api-gateway` — Report Schedule API

**File:** `src/social_api_gateway/reports/__init__.py` (new package)

**File:** `src/social_api_gateway/reports/models.py` (new)

- Read-only mirror of `ReportScheduleModel`.

**File:** `src/social_api_gateway/reports/repository.py` (new)

- CRUD for `report_schedules` (read-only mirror; writes allowed via internal key).

**File:** `src/social_api_gateway/reports/routes.py` (new)

```python
router = APIRouter(prefix="/v1/report-schedules", tags=["report-schedules"])

@router.get("", response_model=ReportScheduleListResponse)
async def list_schedules(...)

@router.post("", status_code=201, response_model=ReportScheduleResponse)
async def create_schedule(...)

@router.put("/{schedule_id}", response_model=ReportScheduleResponse)
async def update_schedule(...)

@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(...)

@router.post("/{schedule_id}/preview", status_code=202)
async def preview_schedule(...)
```

**File:** `src/social_api_gateway/reports/schemas.py` (new)

- `ReportScheduleCreate`, `ReportScheduleUpdate`, `ReportScheduleResponse`, `ReportScheduleListResponse`.

**File:** `src/social_api_gateway/main.py` (modify)

- Mount `reports_router`.

### 4. `social-mini-app` — Report Scheduling UI

**File:** `src/api/hooks.ts`

```typescript
export function useReportSchedules() {
  return useQuery({ queryKey: ["report-schedules"], queryFn: () => apiGet<ReportSchedule[]>("/v1/report-schedules") });
}

export function useCreateReportSchedule() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ReportScheduleCreate) => apiPost<ReportSchedule>("/v1/report-schedules", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["report-schedules"] }),
  });
}

export function usePreviewReport() {
  return useMutation({
    mutationFn: (scheduleId: string) => apiPost(`/v1/report-schedules/${scheduleId}/preview`),
  });
}
```

**File:** `src/components/panels/ReportSchedulePanel.tsx` (new)

```tsx
// Settings page section or Subject Detail section
// 
// "Scheduled Reports" header
// List of active schedules (cards):
//   - "Weekly report every Monday at 09:00 to @channel"
//   - Toggle switch for is_active
//   - Delete button
//
// "Add Schedule" button → opens form:
//   - Scope: "This subject only" | "All subjects"
//   - Frequency: Weekly / Monthly segmented control
//   - If Weekly: Day picker (Mon-Sun buttons)
//   - If Monthly: Day picker (1-28)
//   - Time: Hour dropdown (00-23)
//   - Format: Summary / Detailed
//   - Channel: Text input (channel ID)
//   - "Preview now" button (triggers one-off report)
//   - "Save" button
```

**File:** `src/pages/SettingsPage.tsx` (modify)

- Add `ReportSchedulePanel` section at bottom of settings.

## Interface Changes (UI/UX)

### New Components

| Component | Description |
|---|---|
| `ReportSchedulePanel` | CRUD UI for report schedules |
| `ReportScheduleCard` | Single schedule row: frequency, time, channel, toggle, delete |
| `ReportScheduleForm` | Create/edit form with conditional day picker |

### Modified Screens

| Screen | Change |
|---|---|
| `SettingsPage` | Add ReportSchedulePanel at bottom |
| `SubjectDetailPage` | Optionally embed "Schedule report for this subject" quick action |

### Design Notes (Mobile-First)

- **Simple list, not calendar.** Each schedule is a compact card with key info and a toggle.
- **Day picker as 7 small buttons.** Mon Tue Wed Thu Fri Sat Sun — select one for weekly. Tap to toggle.
- **Time as simple dropdown.** 24-hour format, no minute precision needed.
- **Preview button is primary action.** Users should be able to test the report before saving the schedule.
- **Channel ID is technical.** Most users don't know their channel ID. Should we provide a "Use current chat" button that auto-fills from Telegram SDK (`initDataUnsafe.user.id`)? Recommend yes — add a "Use this chat" button that fills `channel_id` with the current Telegram user/chat ID.

## Files Relevant (Complete List)

| # | File | Action | Description |
|---|---|---|---|
| 1 | `social-common/social_common/schemas.py` | Modify | Add `ReportSchedule` schema |
| 2 | `social-alert-engine/migrations/versions/` | Create | Migration: `report_schedules` table |
| 3 | `social-alert-engine/src/social_alert_engine/models.py` | Modify | Add `ReportScheduleModel` |
| 4 | `social-alert-engine/src/social_alert_engine/repository.py` | Modify/Create | `ReportScheduleRepository` |
| 5 | `social-alert-engine/src/social_alert_engine/reports.py` | Create | `ReportBuilder` class |
| 6 | `social-alert-engine/src/social_alert_engine/tasks.py` | Modify | Add `send_scheduled_reports` beat task |
| 7 | `social-alert-engine/src/social_alert_engine/celery_app.py` | Modify | Add hourly beat schedule entry |
| 8 | `social-alert-engine/src/social_alert_engine/notifier.py` | Modify | Ensure it supports `parse_mode="MarkdownV2"` |
| 9 | `social-api-gateway/src/social_api_gateway/reports/__init__.py` | Create | Package init |
| 10 | `social-api-gateway/src/social_api_gateway/reports/models.py` | Create | Read-only mirror |
| 11 | `social-api-gateway/src/social_api_gateway/reports/repository.py` | Create | CRUD for report schedules |
| 12 | `social-api-gateway/src/social_api_gateway/reports/routes.py` | Create | `/v1/report-schedules` endpoints |
| 13 | `social-api-gateway/src/social_api_gateway/reports/schemas.py` | Create | Request/response schemas |
| 14 | `social-api-gateway/src/social_api_gateway/main.py` | Modify | Mount `reports_router` |
| 15 | `social-api-gateway/scripts/export_openapi.py` | Modify | Regenerate (automatic) |
| 16 | `social-mini-app/src/api/types.ts` | Regenerate | From OpenAPI spec |
| 17 | `social-mini-app/src/api/hooks.ts` | Modify | Add `useReportSchedules`, `useCreateReportSchedule`, `usePreviewReport` |
| 18 | `social-mini-app/src/components/panels/ReportSchedulePanel.tsx` | Create | Schedule CRUD UI |
| 19 | `social-mini-app/src/pages/SettingsPage.tsx` | Modify | Embed ReportSchedulePanel |
| 20 | `social-mini-app/src/pages/Subjects/SubjectDetail.tsx` | Modify | Add "Schedule report" quick action |

## Failure Scenarios

| Scenario | Detection | Impact | Mitigation |
|---|---|---|---|
| **Report schedule fires but no data** | All subjects have no snapshots in period | Empty report sent | ReportBuilder adds "No activity detected this period" message; still send so user knows it's working |
| **Telegram channel_id invalid** | Bot API returns 400 "chat not found" | Report not delivered | Log error; do NOT update `last_sent_at` so it retries next cycle; user must fix channel_id |
| **Bot blocked by user** | Bot API returns 403 "Forbidden: bot was blocked" | Report not delivered | Same as above; user must unblock bot or change channel |
| **Report text exceeds Telegram limit** | Message > 4096 chars | API rejects | Truncate each section; if still too long, send as 2 messages |
| **Feature 1 (posts) not shipped** | `posts` table missing | Top content section empty | Fallback: skip top content section or use `activity_frequency` as proxy |
| **Celery worker down during scheduled hour** | Beat runs but no worker | Report not generated | Beat + worker combined in dev (`worker --beat`); in prod, separate. Missing worker = queue builds up; restart worker catches up |
| **Database unavailable during report generation** | SQLAlchemy connection error | Report not sent | Exception caught; logged; retry next hour |
| **Duplicate reports sent** | Race condition between two workers | User gets 2 identical reports | Use `last_sent_at` check: only send if `last_sent_at` is older than `frequency_period - 1_hour` |

## Testing Strategy

### Unit Tests (Alert Engine)

- **ReportBuilder:** Mock DB with synthetic subjects + snapshots + alerts. Verify output Markdown contains expected sections and numbers.
- **ReportScheduleRepository:** Test `list_due_schedules` with various times/days. Verify only schedules matching current hour/day are returned.
- **Task logic:** Mock `now=Monday 09:00 UTC`. Verify weekly schedule with `day_of_week=0, hour=9` is included; `day_of_week=1` is excluded.

### Integration Tests

- Create schedule with `frequency="weekly"`, `day_of_week=now.weekday()`, `hour=now.hour`, `channel_id=test_channel`.
- Run `send_scheduled_reports` task manually.
- Verify Telegram message received in test channel.
- Verify `last_sent_at` updated.

### Mini App Tests

- `npm run lint && npm run typecheck && npm run build`.
- Manual: Create schedule → verify it appears in list → toggle off → verify toggle works → delete → verify removed.

## Rollout Plan

### Phase 1: Schema & Migration (Day 1)
1. Add `ReportSchedule` schema to `social-common`.
2. Create alert-engine migration for `report_schedules`.
3. Add `ReportScheduleModel`.

### Phase 2: Report Builder & Engine (Day 2-4)
1. Implement `ReportBuilder` with all 5 sections.
2. Implement `ReportScheduleRepository`.
3. Add `send_scheduled_reports` Celery task + beat schedule.
4. Write unit tests for builder and repository.

### Phase 3: Gateway API (Day 5-6)
1. Create `reports/` package with models, repository, routes, schemas.
2. Mount router in `main.py`.
3. Regenerate OpenAPI.

### Phase 4: Mini App UI (Day 7-9)
1. Add hooks for report schedules.
2. Build `ReportSchedulePanel` with form + list.
3. Embed in `SettingsPage`.
4. Add "Use this chat" button using Telegram SDK.

### Phase 5: End-to-End Verification (Day 10)
1. Create test schedule for current hour.
2. Trigger Celery task manually.
3. Verify Telegram delivery.
4. Verify Mini App schedule list reflects update.

## Open Questions

1. **Report frequency precision:** Should we support daily reports, or only weekly/monthly? Daily could be noisy. Recommend starting with weekly/monthly only; daily can be added if requested.
2. **Channel ID auto-detection:** Using Telegram SDK `initDataUnsafe.user.id` gives the individual user ID. But users might want reports sent to a group/channel. Should the form support both, with "Send to me" vs "Send to channel ID" options? Recommend yes — default to "Send to me" (auto-fill user ID), with optional "Custom channel ID" advanced toggle.
3. **Report timezone:** All schedules are in UTC. Should we store a timezone per schedule? For MVP, UTC only; user must convert. Add timezone support later.
4. **Report archival:** Should we store a copy of each sent report in the DB (e.g. `report_deliveries` table)? Not for MVP — Telegram chat history serves as archive.
5. **Preview vs. actual:** Should preview use the same `ReportBuilder` but with a "PREVIEW" header? Yes — preview should be indistinguishable from actual report except for a banner at top.

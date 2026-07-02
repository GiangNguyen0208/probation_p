# Feature Spec: Content Calendar (Read-Only Historical View)

## Overview

Provide a **calendar-based visualisation** of when tracked subjects published content. Every major social media management tool (Hootsuite, Sprout Social, Sendible) includes a content calendar as a core feature — usually for planning and scheduling. Since our platform is read-only monitoring (not publishing), the calendar serves as a **historical retrospection tool** that helps users see posting patterns, identify gaps in content strategy, and correlate posting dates with engagement spikes. This is a lightweight feature with no new backend tables: it is a read-only view over the existing `posts` table from Feature 1.

## Goals

- [ ] Gateway provides `GET /v1/subjects/{id}/calendar?from=&to=` returning posts grouped by date.
- [ ] Response format: `{ "2024-01-15": [Post, Post], "2024-01-16": [Post] }` — posts for each day in the range.
- [ ] Mini App renders a **monthly calendar view** (similar to native phone calendar apps):
  - Days with posts show a **colored dot** (platform colour: Facebook=blue, YouTube=red, TikTok=black)
  - Days with multiple posts show **multiple dots** or a count badge
  - Tap a day → bottom sheet slides up showing post cards for that day
  - Swipe left/right → change month
- [ ] Mini App also provides a **week view** toggle (7-day strip, more compact)
- [ ] Calendar is accessible from Subject Detail page via a "Calendar" tab or section.

## Non-Goals

- **We do NOT support drag-and-drop scheduling.** No post creation, no rescheduling, no moving posts between dates. This is strictly read-only.
- **We do NOT build a multi-subject calendar.** Each calendar is per-subject only. A unified calendar showing all subjects would require complex colour coding and is deferred.
- **We do NOT support calendar invites or ICS export.** No integration with Google Calendar, Outlook, etc.
- **We do NOT show future dates with planned content.** We have no planned content (no scheduling). Calendar only shows historical posts.
- **We do NOT add a new table.** The calendar is a presentation layer over `posts.published_at`.

## Architecture

### Data Model Changes

**None.** Reads from existing `posts` table (Feature 1 prerequisite).

### Service Interactions

```
┌─────────────────────────────┐
│ social-mini-app             │
│  CalendarView               │◄── GET /v1/subjects/{id}/calendar
│  DayDetailSheet             │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-api-gateway          │
│  CalendarService            │── Query posts by date range
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ PostgreSQL                  │
│  posts                      │── Filter: subject_id + published_at range
└─────────────────────────────┘
```

### API Contract

#### `GET /v1/subjects/{subject_id}/calendar`

```yaml
parameters:
  from: date (ISO 8601, default first day of current month)
  to: date (ISO 8601, default last day of current month)

response: CalendarResponse
  data: {
    "month": "2024-01",
    "from": "2024-01-01",
    "to": "2024-01-31",
    "days": {
      "2024-01-15": {
        "post_count": 2,
        "posts": [
          { /* Post schema (minimal: id, caption, published_at, platform, thumbnail_url, engagement_rate) */ }
        ],
        "platforms": ["facebook", "youtube"]  // platforms present on this day
      },
      "2024-01-16": {
        "post_count": 1,
        "posts": [...],
        "platforms": ["tiktok"]
      }
    }
  }
```

**Optimisation:** The query returns all posts for the month at once (typically <100 posts per month per subject). No pagination needed within the month.

## Code Changes

### 1. `social-common` — Schema

**File:** `social_common/schemas.py`

```python
class CalendarDay(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    date: str  # "2024-01-15"
    post_count: int
    posts: list[Post]  # Minimal embed — only id, caption, published_at, platform, thumbnail_url, engagement_rate
    platforms: list[str]

class CalendarResponseData(BaseModel):
    month: str
    from_date: str
    to_date: str
    days: dict[str, CalendarDay]
```

### 2. `social-api-gateway` — Calendar Service

**File:** `src/social_api_gateway/calendar/__init__.py` (new package)

**File:** `src/social_api_gateway/calendar/service.py` (new)

```python
class CalendarService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_calendar(
        self, subject_id: UUID, from_date: date, to_date: date
    ) -> CalendarResponseData:
        # Query all posts in range
        posts = await self._fetch_posts(subject_id, from_date, to_date)
        
        # Group by date
        days: dict[str, CalendarDay] = {}
        for post in posts:
            day_key = post.published_at.strftime("%Y-%m-%d")
            if day_key not in days:
                days[day_key] = CalendarDay(date=day_key, post_count=0, posts=[], platforms=[])
            days[day_key].posts.append(post)
            days[day_key].post_count += 1
            if post.platform not in days[day_key].platforms:
                days[day_key].platforms.append(post.platform)
        
        # Fill empty days with zero-count entries (optional — UI can handle missing keys)
        # But filling makes frontend simpler
        current = from_date
        while current <= to_date:
            key = current.strftime("%Y-%m-%d")
            if key not in days:
                days[key] = CalendarDay(date=key, post_count=0, posts=[], platforms=[])
            current += timedelta(days=1)
        
        return CalendarResponseData(
            month=from_date.strftime("%Y-%m"),
            from_date=from_date.isoformat(),
            to_date=to_date.isoformat(),
            days={k: days[k] for k in sorted(days.keys())},
        )
```

**File:** `src/social_api_gateway/calendar/routes.py` (new)

```python
router = APIRouter(prefix="/v1/subjects", tags=["calendar"])

@router.get("/{subject_id}/calendar", response_model=CalendarResponse)
async def get_calendar(
    subject_id: UUID,
    from_: date | None = Query(None, alias="from"),
    to: date | None = Query(None),
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
) -> CalendarResponse:
    # Default to current month
    today = date.today()
    from_date = from_ or today.replace(day=1)
    to_date = to or (from_date + relativedelta(months=1) - timedelta(days=1))
    
    service = CalendarService(db)
    data = await service.get_calendar(subject_id, from_date, to_date)
    return CalendarResponse(data=data, meta=ResponseMeta())
```

**File:** `src/social_api_gateway/calendar/schemas.py` (new)

- `CalendarResponse` envelope.

**File:** `src/social_api_gateway/main.py` (modify)

- Mount calendar routes.

### 3. `social-mini-app` — Calendar UI

**File:** `src/api/hooks.ts`

```typescript
export function useCalendar(subjectId: string, fromDate: string, toDate: string) {
  return useQuery({
    queryKey: ["calendar", subjectId, fromDate, toDate],
    queryFn: () => apiGet<CalendarResponseData>(`/v1/subjects/${subjectId}/calendar`, { from: fromDate, to: toDate }),
    enabled: !!subjectId,
    staleTime: 300_000,
  });
}
```

**File:** `src/components/calendar/CalendarView.tsx` (new)

```tsx
// Monthly calendar grid: 7 columns (Sun-Sat or Mon-Sun based on locale)
// Each cell:
//   - Day number (top-left)
//   - Colored dots at bottom (one per platform present that day)
//   - If >3 posts, show "+2" badge instead of individual dots
//   - Empty days have no dots
// Header: "January 2024" with left/right arrows for month navigation
// Tap cell → open DayDetailSheet

// Implementation note: Use CSS Grid. 7 columns, auto-rows.
// Cells are square-ish (aspect-ratio: 1/1) or slightly taller on mobile.
```

**File:** `src/components/calendar/DayDetailSheet.tsx` (new)

```tsx
// Bottom sheet (slides up from bottom, 60% height)
// Shows posts for selected day as vertical list of PostCards
// Swipe down to close
// Header: "Monday, January 15" + close button
```

**File:** `src/components/calendar/WeekStrip.tsx` (new)

```tsx
// Horizontal 7-day strip (compact view)
// Each day: day name (Mon) + date (15) + small dot if posts
// Tap day → show DayDetailSheet
// Good for quick overview without full month view
```

**File:** `src/pages/CalendarPage.tsx` (new)

```tsx
// Full-page calendar for a subject
// Top: Subject name + platform badge
// Toggle: Month view / Week view
// CalendarView or WeekStrip
// Accessed from SubjectDetail via "Calendar" tab or link
```

**File:** `src/pages/Subjects/SubjectDetail.tsx` (modify)

- Add a "Calendar" section/tab. Since Subject Detail is already long, add a compact `WeekStrip` inline (horizontal scroll, 7 days) with a "View full calendar" link.

## Interface Changes (UI/UX)

### New Components

| Component | Description |
|---|---|
| `CalendarView` | Monthly grid: 7×N cells with day numbers + platform dots |
| `DayDetailSheet` | Bottom sheet showing posts for a selected day |
| `WeekStrip` | Horizontal 7-day compact view |
| `CalendarPage` | Full-screen calendar page |

### Modified Screens

| Screen | Change |
|---|---|
| `SubjectDetailPage` | Add inline `WeekStrip` + "View full calendar" link |

### Design Notes (Mobile-First)

- **Grid cell size.** On a 375px wide screen, 7 columns = ~53px per cell. Day number is 14px. Dots are 6px circles. This is tight but readable.
- **Month navigation.** Left/right chevrons in header. Swipe gesture on calendar body is tempting but may conflict with vertical scroll. Recommend buttons only.
- **Platform dots.** Maximum 3 dots shown; "+N" badge if more. Dots use platform brand colours.
- **Today highlighting.** Current day gets a subtle ring border (not filled, to avoid confusion with platform dots).
- **Empty state.** If a month has 0 posts, show a friendly message: "No posts in January 2024. Next sync may find older posts."
- **Bottom sheet, not modal.** Day detail slides up from bottom (native mobile pattern). Background darkens. Swipe down to close. Inside Telegram WebView, this feels natural.

## Files Relevant (Complete List)

| # | File | Action | Description |
|---|---|---|---|
| 1 | `social-common/social_common/schemas.py` | Modify | Add `CalendarDay`, `CalendarResponseData` |
| 2 | `social-api-gateway/src/social_api_gateway/calendar/__init__.py` | Create | Package init |
| 3 | `social-api-gateway/src/social_api_gateway/calendar/service.py` | Create | `CalendarService` |
| 4 | `social-api-gateway/src/social_api_gateway/calendar/routes.py` | Create | `GET /v1/subjects/{id}/calendar` |
| 5 | `social-api-gateway/src/social_api_gateway/calendar/schemas.py` | Create | Response envelope |
| 6 | `social-api-gateway/src/social_api_gateway/main.py` | Modify | Mount calendar routes |
| 7 | `social-api-gateway/scripts/export_openapi.py` | Modify | Regenerate |
| 8 | `social-mini-app/src/api/types.ts` | Regenerate | From OpenAPI |
| 9 | `social-mini-app/src/api/hooks.ts` | Modify | Add `useCalendar` |
| 10 | `social-mini-app/src/components/calendar/CalendarView.tsx` | Create | Monthly grid |
| 11 | `social-mini-app/src/components/calendar/DayDetailSheet.tsx` | Create | Day detail bottom sheet |
| 12 | `social-mini-app/src/components/calendar/WeekStrip.tsx` | Create | Compact 7-day strip |
| 13 | `social-mini-app/src/pages/CalendarPage.tsx` | Create | Full calendar page |
| 14 | `social-mini-app/src/pages/Subjects/SubjectDetail.tsx` | Modify | Add WeekStrip + link |
| 15 | `social-mini-app/src/routes.tsx` | Modify | Add `/subjects/:id/calendar` route |

## Failure Scenarios

| Scenario | Detection | Impact | Mitigation |
|---|---|---|---|
| **Feature 1 not yet shipped** | `posts` table missing | Calendar empty | Show "Calendar requires post-level data" message. Blocker: Feature 1 must ship first. |
| **Subject has no posts in month** | `post_count=0` for all days | Empty calendar | Show empty state message; allow navigation to other months |
| **Many posts in one day (>10)** | `post_count > 10` | Day detail sheet becomes scroll-heavy | Cap DayDetailSheet to 10 posts with "Show all" link to paginated post list |
| **Date range too large** | User requests 1-year range | Slow query, large response | Enforce max 31-day range in API; return 422 if exceeded |
| **Timezone mismatch** | `published_at` is UTC, user thinks local | Posts appear on "wrong" day | Document that calendar uses UTC dates; add small "UTC" label |
| **Swipe gesture conflicts** | Calendar inside scrollable page | Accidental month change | Use tap-only navigation for month change; reserve swipe for page scroll |
| **Bottom sheet traps scroll** | User scrolls inside sheet, hits edge | Page scroll doesn't resume | Use `touch-action: none` on sheet container; proper React state management |

## Testing Strategy

### Unit Tests (Gateway)

- **CalendarService:** Mock 5 posts across 3 days → verify grouping correct.
- **Date range validation:** Request 60-day range → expect 422.
- **Empty month:** 0 posts → verify all days have `post_count=0`.

### Integration Tests

- Seed subject with 10 posts across 5 days.
- Call `/v1/subjects/{id}/calendar` → verify response shape and day grouping.

### Mini App Tests

- `npm run lint && npm run typecheck && npm run build`.
- Manual: Calendar renders 7×N grid; tap day opens sheet; month navigation works.

## Rollout Plan

### Phase 1: Gateway API (Day 1-2)
1. Add calendar schemas to `social-common`.
2. Implement `CalendarService` + route.
3. Write unit tests.
4. Regenerate OpenAPI.

### Phase 2: Mini App UI (Day 3-5)
1. Add `useCalendar` hook.
2. Build `CalendarView`, `DayDetailSheet`, `WeekStrip`.
3. Build `CalendarPage`.
4. Integrate `WeekStrip` into `SubjectDetailPage`.

### Phase 3: Verification (Day 6)
1. Run test suites.
2. Manual end-to-end: verify calendar dots match post dates.

## Open Questions

1. **Week starts on Monday or Sunday?** Most of the world uses Monday. Telegram's user base is global. Recommend Monday start with locale awareness (use `Intl.Locale` to detect). For MVP, hardcode Monday.
2. **Should we show engagement rate in calendar cells?** Adding numbers to tiny cells creates clutter. Recommend keeping it to dots only; engagement rate shown in DayDetailSheet per post.
3. **Multi-subject calendar future:** If we later want a calendar showing all subjects, how would platform colours work? Each day would have multiple dots of different colours. The grid cell would need to be larger or use a summary badge. Defer this design challenge to when the feature is requested.
4. **Calendar for subjects without Feature 1:** If a subject has no `posts` yet (Feature 1 not synced), can we use `activity_snapshots` to infer "posting days"? No — `activity_snapshots` don't tell us which days had posts, only cumulative counts. Calendar would be empty until Feature 1 syncs.
5. **Historical depth:** How many months back should we allow? There's no technical limit, but API enforces 31-day range per request. User can navigate month by month. Good.

# Feature Spec: Engagement Rate Analytics & Best Time to Post Insights

## Overview

Compute and surface **engagement rate** and **optimal posting time** insights for tracked subjects. Engagement rate is the industry-standard metric for content performance: `(likes + comments + shares) / views` (or per-follower when views are unavailable). Sprout Social's "ViralPost®" delivers content at optimal times, Sendible has "Optimal Times" to "reach your audience easily," and Hootsuite recommends "best times to post based on your audience and goals." Our system already collects post-level metrics (Feature 1) and time-series snapshots; this feature adds an **analytics computation layer** that calculates engagement rates, analyses peak engagement by hour-of-day and day-of-week, and surfaces actionable "best time to post" recommendations in the Mini App.

## Goals

- [ ] Gateway provides `GET /v1/subjects/{id}/engagement` endpoint returning:
  - Overall engagement rate (all-time average, last-30-day average)
  - Per-post engagement rates (for the top N posts)
  - Engagement by **hour of day** (0-23) — aggregated across all posts
  - Engagement by **day of week** (Mon-Sun)
  - **Optimal posting time recommendation** (top 3 hours + top day)
- [ ] Computation is done **on-demand from `posts` table** (Feature 1 prerequisite) + `activity_snapshots`. No pre-computed tables.
- [ ] Mini App shows:
  - **Engagement Rate badge** on Subject Detail header (e.g. "3.8% avg engagement")
  - **Best Time to Post** insight card ("Post on Tuesdays at 14:00 for +25% more engagement")
  - **Weekly Engagement Heatmap** (GitHub-style contribution graph) in Subject Detail
  - **Engagement breakdown** on each Post card (likes %, comments %, shares % mini-bars)
- [ ] Caching: engagement results cached for 15 minutes (frequent access, moderately expensive query).

## Non-Goals

- **We do NOT store pre-computed engagement aggregates.** All analytics are computed on-demand. If performance becomes an issue later, add a materialized view or continuous aggregate in TimescaleDB.
- **We do NOT implement true audience timezone analysis.** "Best time" is computed from post timestamps only; we do not know the audience's timezone or when they are online. This is a limitation we surface honestly ("Based on your post history").
- **We do NOT support cross-subject engagement comparison.** Engagement analytics are per-subject only. Cross-subject comparison is covered by Feature 2 (Benchmarking).
- **We do NOT build a content scheduling system.** We only *recommend* times; we do not queue or publish posts.
- **We do NOT implement click-through rate (CTR) or conversion tracking.** These require external analytics (Google Analytics, UTM tracking — Feature 4 mentions UTM but it's non-goal there too).

## Architecture

### Data Model Changes

**No new tables.** Pure analytics read-layer over:
- `posts` table (Feature 1) — `published_at`, `like_count`, `comment_count`, `share_count`, `view_count`, `engagement_rate`
- `activity_snapshots` — `captured_at`, `frequency` (as fallback if posts table missing)

### Computation Algorithms

#### 1. Engagement Rate (per post)

```python
def compute_engagement_rate(post: Post) -> float:
    """Return engagement rate as percentage."""
    interactions = post.like_count + post.comment_count + post.share_count
    if post.view_count > 0:
        return (interactions / post.view_count) * 100
    # Fallback: per-follower (less accurate but universal)
    # follower_count must be fetched from Subject or latest snapshot
    return (interactions / follower_count) * 100 if follower_count > 0 else 0.0
```

#### 2. Optimal Posting Time

```python
def compute_optimal_times(posts: list[Post]) -> dict:
    """Return top 3 hours and top day by average engagement rate."""
    # Group posts by hour-of-day
    by_hour: dict[int, list[float]] = {h: [] for h in range(24)}
    by_dow: dict[int, list[float]] = {d: [] for d in range(7)}  # Monday=0
    
    for post in posts:
        hour = post.published_at.hour
        dow = post.published_at.weekday()
        by_hour[hour].append(post.engagement_rate)
        by_dow[dow].append(post.engagement_rate)
    
    # Compute average per bucket, requiring at least 2 posts for statistical relevance
    hourly_avg = {h: statistics.mean(rates) for h, rates in by_hour.items() if len(rates) >= 2}
    daily_avg = {d: statistics.mean(rates) for d, rates in by_dow.items() if len(rates) >= 2}
    
    top_hours = sorted(hourly_avg.items(), key=lambda x: x[1], reverse=True)[:3]
    top_day = max(daily_avg.items(), key=lambda x: x[1]) if daily_avg else None
    
    return {
        "top_hours": [(h, round(v, 2)) for h, v in top_hours],
        "top_day": (top_day[0], round(top_day[1], 2)) if top_day else None,
        "post_count_by_hour": {h: len(rates) for h, rates in by_hour.items()},
        "post_count_by_day": {d: len(rates) for d, rates in by_dow.items()},
    }
```

**Edge case:** If a subject has <14 posts total, hourly/day-of-week buckets may have <2 posts. We still compute but mark `confidence: "low"` in the response.

### Service Interactions

```
┌─────────────────────────────┐
│ social-mini-app             │
│  SubjectDetail              │◄── GET /v1/subjects/{id}/engagement
│  EngagementHeatmap          │
│  OptimalTimePanel           │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-api-gateway          │
│  EngagementService          │── On-demand computation
│  CacheService (15min TTL)   │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ PostgreSQL                  │
│  posts                      │── Post-level metrics
│  subjects                   │── Follower count fallback
└─────────────────────────────┘
```

### API Contract

#### `GET /v1/subjects/{subject_id}/engagement`

```yaml
response: EngagementAnalyticsResponse
  data: {
    "subject_id": "...",
    "overall_engagement_rate": 3.8,
    "last_30d_engagement_rate": 4.2,
    "post_count": 45,
    "optimal_times": {
      "top_hours": [(14, 5.2), (9, 4.8), (20, 4.5)],  // (hour, avg_engagement)
      "top_day": (1, 5.1),  // (0=Monday, avg_engagement)
      "confidence": "medium"  // "low" | "medium" | "high" based on post count
    },
    "hourly_breakdown": [
      { "hour": 0, "avg_engagement": 1.2, "post_count": 2 },
      ... // 24 items
    ],
    "daily_breakdown": [
      { "day": 0, "day_name": "Mon", "avg_engagement": 3.5, "post_count": 8 },
      ... // 7 items
    ]
  }
```

## Code Changes

### 1. `social-common` — Schema

**File:** `social_common/schemas.py`

```python
class EngagementAnalytics(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    subject_id: UUID
    overall_engagement_rate: float
    last_30d_engagement_rate: float
    post_count: int
    optimal_times: OptimalTimes
    hourly_breakdown: list[HourlyEngagement]
    daily_breakdown: list[DailyEngagement]

class OptimalTimes(BaseModel):
    top_hours: list[tuple[int, float]]  # (hour, avg_engagement_rate)
    top_day: tuple[int, float] | None   # (weekday, avg_engagement_rate)
    confidence: str  # "low" | "medium" | "high"

class HourlyEngagement(BaseModel):
    hour: int  # 0-23
    avg_engagement: float
    post_count: int

class DailyEngagement(BaseModel):
    day: int  # 0-6 (Monday=0)
    day_name: str
    avg_engagement: float
    post_count: int
```

### 2. `social-api-gateway` — Engagement Service

**File:** `src/social_api_gateway/engagement/__init__.py` (new package)

**File:** `src/social_api_gateway/engagement/service.py` (new)

```python
class EngagementService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute(self, subject_id: UUID) -> EngagementAnalytics:
        posts = await self._fetch_posts(subject_id, since=datetime.now(UTC) - timedelta(days=90))
        
        if not posts:
            return EngagementAnalytics(
                subject_id=subject_id,
                overall_engagement_rate=0.0,
                last_30d_engagement_rate=0.0,
                post_count=0,
                optimal_times=OptimalTimes(top_hours=[], top_day=None, confidence="low"),
                hourly_breakdown=[HourlyEngagement(hour=h, avg_engagement=0.0, post_count=0) for h in range(24)],
                daily_breakdown=[DailyEngagement(day=d, day_name=self._day_name(d), avg_engagement=0.0, post_count=0) for d in range(7)],
            )
        
        # Compute rates (ensure stored engagement_rate is up to date, or recompute)
        rates = [p.engagement_rate for p in posts]
        recent_posts = [p for p in posts if p.published_at >= datetime.now(UTC) - timedelta(days=30)]
        recent_rates = [p.engagement_rate for p in recent_posts]
        
        optimal = self._compute_optimal_times(posts)
        hourly = self._compute_hourly_breakdown(posts)
        daily = self._compute_daily_breakdown(posts)
        
        return EngagementAnalytics(
            subject_id=subject_id,
            overall_engagement_rate=round(statistics.mean(rates), 2) if rates else 0.0,
            last_30d_engagement_rate=round(statistics.mean(recent_rates), 2) if recent_rates else 0.0,
            post_count=len(posts),
            optimal_times=optimal,
            hourly_breakdown=hourly,
            daily_breakdown=daily,
        )

    def _compute_optimal_times(self, posts: list[PostModel]) -> OptimalTimes:
        ...  # Algorithm described above

    def _compute_hourly_breakdown(self, posts: list[PostModel]) -> list[HourlyEngagement]:
        ...

    def _compute_daily_breakdown(self, posts: list[PostModel]) -> list[DailyEngagement]:
        ...

    def _day_name(self, day: int) -> str:
        return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][day]
```

**File:** `src/social_api_gateway/engagement/routes.py` (new)

```python
router = APIRouter(prefix="/v1/subjects", tags=["engagement"])

@router.get("/{subject_id}/engagement", response_model=EngagementAnalyticsResponse)
async def get_engagement_analytics(
    subject_id: UUID,
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
) -> EngagementAnalyticsResponse:
    cache_key = f"cache:engagement:{subject_id}"
    cached = await cache.get(cache_key)
    if cached:
        return EngagementAnalyticsResponse.model_validate(cached)
    
    service = EngagementService(db)
    data = await service.compute(subject_id)
    response = EngagementAnalyticsResponse(data=data, meta=ResponseMeta())
    await cache.set(cache_key, response.model_dump(mode="json"), ttl_seconds=900)
    return response
```

**File:** `src/social_api_gateway/engagement/schemas.py` (new)

- `EngagementAnalyticsResponse` envelope.

**File:** `src/social_api_gateway/main.py` (modify)

- Mount engagement routes (or add to subjects router since path is `/v1/subjects/{id}/engagement`).

### 3. `social-mini-app` — UI

**File:** `src/api/hooks.ts`

```typescript
export function useEngagementAnalytics(subjectId: string) {
  return useQuery({
    queryKey: ["engagement", subjectId],
    queryFn: () => apiGet<EngagementAnalytics>(`/v1/subjects/${subjectId}/engagement`),
    enabled: !!subjectId,
    staleTime: 900_000,  // 15 minutes
  });
}
```

**File:** `src/components/panels/OptimalTimePanel.tsx` (new)

```tsx
// Card in Subject Detail
// Title: "Best Time to Post"
// Content:
//   - Primary recommendation: "Tuesdays at 14:00" (largest text)
//   - Secondary: "Also good: 09:00, 20:00"
//   - Context: "Based on 45 posts. Confidence: medium."
//   - Mini stat: "+25% higher engagement than average"
// Design: Use a clock icon + highlighted hour
```

**File:** `src/components/charts/EngagementHeatmap.tsx` (new)

```tsx
// GitHub-contribution-graph style heatmap
// 7 rows (Mon-Sun) × 24 columns (hours) OR 7 columns × 24 rows
// On mobile, 7 rows (days) × scrollable horizontal hours works better
// Each cell color intensity = avg engagement rate for that (day, hour) bucket
// Tooltip/long-press shows "Mon 14:00 — 5.2% avg engagement (3 posts)"
// Empty cells (0 posts) are grey/transparent
```

**File:** `src/components/panels/EngagementBreakdown.tsx` (new)

```tsx
// Small panel showing:
// - Overall engagement rate: 3.8% (large number)
// - Last 30 days: 4.2% (with trend arrow)
// - Mini bar chart: Likes 60% | Comments 25% | Shares 15%
```

**File:** `src/pages/Subjects/SubjectDetail.tsx` (modify)

- Add `EngagementBreakdown` to Identity Card area (small metric below followers).
- Add `OptimalTimePanel` between Key Metrics and Charts.
- Add `EngagementHeatmap` below Charts section (if enough posts).

## Interface Changes (UI/UX)

### New Components

| Component | Description |
|---|---|
| `OptimalTimePanel` | Recommendation card: best day + hour + confidence |
| `EngagementHeatmap` | 7×24 cell heatmap (day × hour) colored by engagement rate |
| `EngagementBreakdown` | Overall rate + 30-day rate + likes/comments/shares ratio |

### Modified Screens

| Screen | Change |
|---|---|
| `SubjectDetailPage` | Add EngagementBreakdown badge, OptimalTimePanel, EngagementHeatmap |
| `PostCard` (Feature 1) | Add engagement rate badge + mini likes/comments/shares bars |

### Design Notes (Mobile-First)

- **Heatmap orientation.** On narrow screens, days as rows (Mon-Sun top to bottom) and hours as scrollable horizontal columns works best. Each cell is ~20px square.
- **Color scale.** Use 4-color discrete scale: grey (no data) → light accent → medium accent → dark accent. Avoid continuous gradients (hard to read on small screens).
- **Optimal time prominence.** The recommended time should be the biggest text on the card, with a clock icon. Secondary times are smaller.
- **Confidence indicator.** "Based on 45 posts" is reassuring; "Based on 3 posts" warns user that recommendation may not be reliable.
- **No "schedule now" button.** We only show insights; we do not schedule posts. Avoid confusing users into thinking we have publishing capability.

## Files Relevant (Complete List)

| # | File | Action | Description |
|---|---|---|---|
| 1 | `social-common/social_common/schemas.py` | Modify | Add `EngagementAnalytics`, `OptimalTimes`, `HourlyEngagement`, `DailyEngagement` |
| 2 | `social-api-gateway/src/social_api_gateway/engagement/__init__.py` | Create | Package init |
| 3 | `social-api-gateway/src/social_api_gateway/engagement/service.py` | Create | `EngagementService` with computation algorithms |
| 4 | `social-api-gateway/src/social_api_gateway/engagement/routes.py` | Create | `GET /v1/subjects/{id}/engagement` |
| 5 | `social-api-gateway/src/social_api_gateway/engagement/schemas.py` | Create | Response envelope |
| 6 | `social-api-gateway/src/social_api_gateway/main.py` | Modify | Mount engagement routes |
| 7 | `social-api-gateway/scripts/export_openapi.py` | Modify | Regenerate |
| 8 | `social-mini-app/src/api/types.ts` | Regenerate | From OpenAPI |
| 9 | `social-mini-app/src/api/hooks.ts` | Modify | Add `useEngagementAnalytics` |
| 10 | `social-mini-app/src/components/panels/OptimalTimePanel.tsx` | Create | Best time recommendation card |
| 11 | `social-mini-app/src/components/charts/EngagementHeatmap.tsx` | Create | 7×24 engagement heatmap |
| 12 | `social-mini-app/src/components/panels/EngagementBreakdown.tsx` | Create | Overall rate + composition bars |
| 13 | `social-mini-app/src/pages/Subjects/SubjectDetail.tsx` | Modify | Integrate new panels |
| 14 | `social-mini-app/src/components/subject/PostCard.tsx` | Modify | Add engagement rate badge (if Feature 1 shipped) |

## Failure Scenarios

| Scenario | Detection | Impact | Mitigation |
|---|---|---|---|
| **No posts for subject** | `posts` table empty | All analytics show 0.0 | UI shows "Not enough post data" with suggestion to wait for next sync |
| **Posts exist but no engagement data** | All counts are 0 | Engagement rate = 0% | Correct behaviour; subject may be new or inactive |
| **All posts published at same time** | All `published_at` identical | Optimal time cannot be determined | Show "All posts published at {time}" — no recommendation possible |
| **Feature 1 not yet shipped** | `posts` table missing | 500 error or empty response | Fallback to `activity_snapshots.frequency` for posting pattern, but engagement rate requires posts. Blocker: Feature 1 must ship first. |
| **Cache shows stale data after sync** | Old engagement numbers | User sees pre-sync rates | Invalidate `engagement` cache key in `useTriggerSync` onSuccess |
| **Very few posts (<14)** | `post_count < 14` | Low confidence recommendations | Mark `confidence: "low"`; UI shows warning "Recommendation based on limited data" |
| **Computation query too slow** | >2s for 1k posts | Gateway timeout | Add limit (max 500 posts considered); use indexed `published_at` query |

## Testing Strategy

### Unit Tests (Gateway)

- **EngagementService with mock posts:**
  - 50 posts across various hours/days → verify optimal time is correct hour/day
  - 3 posts all at same time → confidence="low", top_hours may be empty if <2 per bucket
  - 0 posts → all zeros, empty optimal times
- **Engagement rate formula:**
  - 100 likes, 50 comments, 10 shares, 1000 views → rate = 16.0%
  - 0 views, 1000 followers → rate = 16.0% (fallback)
  - 0 views, 0 followers → rate = 0.0%

### Integration Tests

- Seed subject with 20 posts across different hours.
- Call `/v1/subjects/{id}/engagement` → verify `hourly_breakdown` has non-zero values at correct hours.
- Verify cache: second request faster, cache key present in Redis.

### Mini App Tests

- `npm run lint && npm run typecheck && npm run build`.
- Manual: Subject Detail shows heatmap; tap a cell shows detail; optimal time card is prominent.

## Rollout Plan

### Phase 1: Gateway Analytics Service (Day 1-3)
1. Add engagement schemas to `social-common`.
2. Implement `EngagementService` with all computation methods.
3. Add `GET /v1/subjects/{id}/engagement` endpoint with caching.
4. Write unit tests for `EngagementService`.

### Phase 2: Mini App UI (Day 4-6)
1. Add `useEngagementAnalytics` hook.
2. Build `OptimalTimePanel`.
3. Build `EngagementHeatmap`.
4. Build `EngagementBreakdown`.
5. Integrate into `SubjectDetailPage`.

### Phase 3: Verification (Day 7)
1. Run `pytest` in gateway.
2. Build Mini App.
3. Manual end-to-end: verify heatmap colors and optimal time recommendation.

## Open Questions

1. **Fallback without views:** When `view_count == 0`, we use `followers` as denominator. Should we use *current* followers or followers *at post time*? Current followers is easier (from `Subject` table); followers at post time would require snapshot interpolation. Recommend current followers for simplicity, with a note that rate may be slightly inaccurate for old posts.
2. **Timezone handling:** Post `published_at` is stored in UTC (from platform APIs). Should we convert to a local timezone for "best time"? Without knowing the subject's timezone, we can't. Recommend showing times in UTC with a note: "Times shown in UTC. Convert to your local timezone."
3. **Heatmap vs. Bar chart:** Is a heatmap the best mobile visualization? Alternative: vertical bar chart per day (7 bars, one per day). Heatmap is more information-dense but harder to read on small screens. Recommend heatmap for detail view, simple "Top day: Tuesday" card for summary.
4. **Should we weight recent posts more heavily?** A post from 6 months ago may not reflect current audience behaviour. Should optimal time computation weight last-30-day posts 2× more? For MVP, equal weighting is fine. Weighted can be added later.
5. **Recomputing stored engagement_rate:** If we fix the engagement rate formula later (e.g. change fallback logic), stored values in `posts` table become stale. Should we recompute on read instead of storing? Storing is faster; recompute on read is more accurate. Recommend storing + periodic backfill if formula changes.

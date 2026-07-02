# Feature Spec: Cross-Subject Competitive Benchmarking

## Overview

Leverage the platform's existing multi-subject data to provide **comparative performance insights**. This is a standard feature in every major social media management tool: Hootsuite calls it "Competitive Analysis" (track competitor posting frequency, growth rates, share of voice), Sprout Social has dedicated "Competitor Reports" for Facebook/X/Instagram, and Sendible includes competitor benchmarking in analytics. Our system already tracks multiple subjects across platforms — this feature adds a **read-only analytics layer** that computes relative rankings, growth rates, and platform averages, exposed through a new API endpoint and a "Benchmarks" page in the Mini App.

## Goals

- [ ] Gateway provides `GET /v1/benchmarks` endpoint returning computed competitive metrics for all active subjects.
- [ ] Metrics computed: **7-day growth rate %**, **30-day growth rate %**, **average engagement rate**, **activity frequency ranking**, **post volume** (posts per week).
- [ ] Mini App has a new **Benchmarks** tab/page showing:
  - Leaderboard: subjects ranked by 7-day growth rate with trend arrows (↑/↓/→)
  - Platform comparison: aggregated averages per platform (Facebook vs YouTube vs TikTok)
  - "How you compare" context within each Subject Detail page (e.g. "Top 10% by growth this week")
- [ ] Data is **computed on-demand from existing `activity_snapshots`** — no new tables required.
- [ ] Caching: benchmark results cached for 5 minutes (same `CacheService` pattern as subjects list).

## Non-Goals

- **We do NOT create a "competitor" entity type.** Any subject can be benchmarked; there is no distinction between "owned account" and "competitor" in the data model.
- **We do NOT store pre-computed benchmark snapshots.** All metrics are computed on-demand from `activity_snapshots` to avoid data duplication. If query performance becomes an issue later, we can add a materialized view.
- **We do NOT implement industry/sector benchmarks.** We only compare subjects within the same platform instance (same database). External industry averages are out of scope.
- **We do NOT build detailed competitor post breakdowns.** Per-post comparison is covered by Feature 1 (Post Analytics). Benchmarking stays at account-level aggregates.
- **We do NOT support custom benchmark groups.** Users cannot create "Group A vs Group B" comparisons yet. Deferred to Phase 6+.

## Architecture

### Data Model Changes

**No new tables.** This is a pure analytics read-layer over existing data:

```sql
-- 7-day growth rate for a subject:
SELECT 
  (latest.followers - previous.followers) / NULLIF(previous.followers, 0) * 100
FROM (
  SELECT followers FROM activity_snapshots 
  WHERE subject_id = ? AND captured_at >= NOW() - INTERVAL '1 day'
  ORDER BY captured_at DESC LIMIT 1
) latest,
(
  SELECT followers FROM activity_snapshots 
  WHERE subject_id = ? AND captured_at <= NOW() - INTERVAL '7 days'
  ORDER BY captured_at DESC LIMIT 1
) previous;
```

**Optional future optimisation:** `CREATE MATERIALIZED VIEW benchmark_cache` (not required for MVP).

### Service Interactions

```
┌─────────────────────┐
│ social-mini-app     │
│  BenchmarkPage      │◄── GET /v1/benchmarks
│  SubjectDetail      │◄── "how you compare" badge
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ social-api-gateway  │
│  CacheService       │── cache hit? → return cached
│  BenchmarkService   │── cache miss? → compute from DB
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ TimescaleDB         │
│  activity_snapshots │── time-series queries
│  subjects           │── metadata (platform, status)
└─────────────────────┘
```

### API Contract

#### `GET /v1/benchmarks`

```yaml
parameters:
  platform: Platform | null  # Filter by platform
  period_days: int (default 7, ge=1, le=90)  # Growth lookback window
  page: int (default 1, ge=1)
  limit: int (default 20, ge=1, le=100)

response: BenchmarkListResponse
  data: BenchmarkItem[]
  meta: { page, limit, total }
  platform_averages: PlatformAverage[]  # Aggregated per platform
```

**`BenchmarkItem` schema:**
```json
{
  "subject": { /* embedded Subject schema, minimal */ },
  "growth_rate_7d": 12.5,
  "growth_rate_30d": 45.2,
  "avg_engagement_rate": 3.8,
  "posts_per_week": 4.2,
  "activity_frequency_rank": 3,
  "percentile": 85,  // "Top 15%"
  "trend": "up"      // "up" | "down" | "stable"
}
```

**`PlatformAverage` schema:**
```json
{
  "platform": "youtube",
  "avg_growth_rate_7d": 8.3,
  "avg_engagement_rate": 2.1,
  "avg_posts_per_week": 3.5,
  "subject_count": 12
}
```

#### `GET /v1/subjects/{subject_id}/benchmark`

Single-subject benchmark context (for embedding in Subject Detail).

```yaml
response: BenchmarkContextResponse
  data: {
    "subject_id": "...",
    "growth_rate_7d": 12.5,
    "platform_rank": 3,       // "3rd on YouTube"
    "overall_rank": 7,        // "7th across all platforms"
    "percentile": 85,
    "trend": "up",
    "platform_average": { /* PlatformAverage for this subject's platform */ }
  }
```

## Code Changes

### 1. `social-common` — Schemas

**File:** `social_common/schemas.py`

```python
class BenchmarkItem(BaseModel):
    """Computed competitive metrics for a single subject."""
    model_config = ConfigDict(from_attributes=True)

    subject: Subject          # Minimal embed (id, name, platform, followers)
    growth_rate_7d: float     # Percentage
    growth_rate_30d: float
    avg_engagement_rate: float
    posts_per_week: float
    activity_frequency_rank: int
    percentile: int           # 0-100
    trend: str                # "up" | "down" | "stable"

class PlatformAverage(BaseModel):
    """Aggregated metrics across all subjects on one platform."""
    platform: Platform
    avg_growth_rate_7d: float
    avg_engagement_rate: float
    avg_posts_per_week: float
    subject_count: int

class BenchmarkContext(BaseModel):
    """Single-subject benchmark context for detail page embedding."""
    subject_id: UUID
    growth_rate_7d: float
    platform_rank: int
    overall_rank: int
    percentile: int
    trend: str
    platform_average: PlatformAverage
```

### 2. `social-api-gateway` — Benchmark Service & API

**File:** `src/social_api_gateway/benchmarks/__init__.py` (new package)

**File:** `src/social_api_gateway/benchmarks/service.py` (new)

```python
class BenchmarkService:
    """Computes competitive metrics from activity_snapshots.

    All methods are pure SQL/SQLAlchemy queries — no external I/O.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def compute_growth_rate(
        self, subject_id: UUID, period_days: int
    ) -> float:
        """Return follower growth % over period_days.

        Formula: (latest.followers - previous.followers) / previous.followers * 100
        If no previous snapshot exists, return 0.0.
        If previous.followers == 0, return 0.0 (avoid div/0).
        """
        ...

    async def compute_posts_per_week(self, subject_id: UUID) -> float:
        """Average posts per week over last 30 days.
        Uses Post table (Feature 1 prerequisite) or falls back to activity_frequency."""
        ...

    async def rank_subjects(self, platform: Platform | None) -> list[BenchmarkItem]:
        """Compute full leaderboard ordered by growth_rate_7d DESC."""
        ...

    async def compute_platform_averages(self) -> list[PlatformAverage]:
        """Aggregate across all active subjects per platform."""
        ...

    async def get_subject_context(self, subject_id: UUID) -> BenchmarkContext:
        """Single-subject benchmark for detail page embedding."""
        ...
```

**File:** `src/social_api_gateway/benchmarks/routes.py` (new)

```python
router = APIRouter(prefix="/v1/benchmarks", tags=["benchmarks"])

@router.get("", response_model=BenchmarkListResponse)
async def list_benchmarks(
    platform: Platform | None = Query(None),
    period_days: int = Query(7, ge=1, le=90),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
) -> BenchmarkListResponse:
    ...

@router.get("/subjects/{subject_id}", response_model=BenchmarkContextResponse)
async def get_subject_benchmark(
    subject_id: UUID,
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
) -> BenchmarkContextResponse:
    ...
```

**File:** `src/social_api_gateway/benchmarks/schemas.py` (new)

Response envelope types: `BenchmarkListResponse`, `BenchmarkContextResponse`.

**File:** `src/social_api_gateway/main.py`

- Register `benchmarks_router` alongside existing routers.

### 3. `social-api-gateway` — Cache Integration

**File:** `src/social_api_gateway/benchmarks/routes.py`

- Cache key: `f"cache:benchmarks:{platform}:{period_days}:{page}:{limit}"`
- TTL: 300 seconds (5 minutes). Benchmarks are expensive to compute but do not need to be real-time.

### 4. `social-mini-app` — UI

**File:** `src/api/hooks.ts`

```typescript
export function useBenchmarks(platform?: string, periodDays: number = 7) {
  return useQuery({
    queryKey: ["benchmarks", platform, periodDays],
    queryFn: () => apiGet<BenchmarkItem[]>("/v1/benchmarks", { platform, period_days: periodDays }),
    staleTime: 300_000,  // 5 minutes
  });
}

export function useSubjectBenchmark(subjectId: string) {
  return useQuery({
    queryKey: ["benchmark", subjectId],
    queryFn: () => apiGet<BenchmarkContext>(`/v1/subjects/${subjectId}/benchmark`),
    enabled: !!subjectId,
    staleTime: 300_000,
  });
}
```

**File:** `src/pages/BenchmarkPage.tsx` (new)

```tsx
// Layout: Leaderboard (vertical scroll)
// Each row: Rank # | Platform badge | Subject name | Growth % | Trend arrow | "Top X%" badge
// Filter bar: Platform dropdown | Period toggle (7d / 30d)
// Sticky header: "Platform Comparison" card with 3-column bar chart (FB vs YT vs TT averages)
```

**File:** `src/components/panels/PlatformComparisonPanel.tsx` (new)

```tsx
// Horizontal bar chart: 3 bars (one per platform)
// Metrics: Avg Growth Rate | Avg Engagement | Avg Posts/Week
// User can toggle which metric to display
```

**File:** `src/components/subject/BenchmarkBadge.tsx` (new)

```tsx
// Small badge for Subject Detail header
// "Top 15% this week" with trend arrow (↑ green / ↓ red / → grey)
// Tappable → navigate to BenchmarkPage filtered by this subject's platform
```

**File:** `src/navigation/BottomNav.tsx`

- Add 4th tab: "Analytics" or "Benchmarks" (icon: `leaderboard` or `trending_up`).
- Update `routes.tsx` with `/benchmarks` route.

**File:** `src/pages/Subjects/SubjectDetail.tsx`

- Insert `<BenchmarkBadge subjectId={id!} />` next to the subject name in the Identity Card.
- Add "Compare" button linking to BenchmarkPage filtered by platform.

## Interface Changes (UI/UX)

### New Screens

| Screen | Route | Description |
|---|---|---|
| `BenchmarkPage` | `/benchmarks` | Full leaderboard + platform comparison |

### New Components

| Component | Description |
|---|---|
| `BenchmarkBadge` | Small inline badge: percentile + trend arrow |
| `PlatformComparisonPanel` | 3-bar chart comparing platform averages |
| `LeaderboardRow` | Single row in benchmark list: rank, name, growth %, badge |

### Modified Components

| Component | Change |
|---|---|
| `BottomNav` | Add "Benchmarks" tab (4th tab, or replace Settings if space limited) |
| `SubjectDetailPage` | Add `BenchmarkBadge` to header; "Compare" link |

### Design Notes (Mobile-First)

- **Leaderboard as cards.** Each subject is a full-width card with rank number, platform color bar, name, and big growth %.
- **Sticky platform filter.** Platform dropdown sticks to top when scrolling.
- **No tables.** Avoid multi-column layouts; use stacked metrics.
- **Tap to filter.** Tap a platform in the comparison chart → filter leaderboard to that platform.
- **Bottom nav consideration.** Current nav has 3 tabs (Subjects/Dashboard/Settings). Adding a 4th tab may crowd small screens. Alternative: put Benchmarks inside Dashboard as a sub-section, or use a segmented control on Dashboard.
  → **Decision:** Add as a section within `DashboardPage` first ("Leaderboard" + "Platform Comparison" cards), with a "View Full Rankings" link. This avoids nav crowding. If user feedback demands dedicated tab, migrate later.

## Files Relevant (Complete List)

| # | File | Action | Description |
|---|---|---|---|
| 1 | `social-common/social_common/schemas.py` | Modify | Add `BenchmarkItem`, `PlatformAverage`, `BenchmarkContext` |
| 2 | `social-api-gateway/src/social_api_gateway/benchmarks/__init__.py` | Create | Package init |
| 3 | `social-api-gateway/src/social_api_gateway/benchmarks/service.py` | Create | Core computation logic |
| 4 | `social-api-gateway/src/social_api_gateway/benchmarks/routes.py` | Create | `/v1/benchmarks` + `/v1/subjects/{id}/benchmark` |
| 5 | `social-api-gateway/src/social_api_gateway/benchmarks/schemas.py` | Create | Response envelope types |
| 6 | `social-api-gateway/src/social_api_gateway/main.py` | Modify | Mount `benchmarks_router` |
| 7 | `social-api-gateway/src/social_api_gateway/subjects/routes.py` | Modify | Optionally redirect or link |
| 8 | `social-api-gateway/scripts/export_openapi.py` | Modify | Regenerate (automatic) |
| 9 | `social-mini-app/src/api/types.ts` | Regenerate | From OpenAPI spec |
| 10 | `social-mini-app/src/api/hooks.ts` | Modify | Add `useBenchmarks`, `useSubjectBenchmark` |
| 11 | `social-mini-app/src/pages/BenchmarkPage.tsx` | Create | Leaderboard + platform comparison |
| 12 | `social-mini-app/src/components/panels/PlatformComparisonPanel.tsx` | Create | 3-bar platform chart |
| 13 | `social-mini-app/src/components/subject/BenchmarkBadge.tsx` | Create | Inline percentile badge |
| 14 | `social-mini-app/src/pages/DashboardPage.tsx` | Modify | Add "Leaderboard" + "Platform Comparison" sections |
| 15 | `social-mini-app/src/pages/Subjects/SubjectDetail.tsx` | Modify | Add `BenchmarkBadge` + compare link |
| 16 | `social-mini-app/src/routes.tsx` | Modify | Add `/benchmarks` route (or skip if embedded in Dashboard) |
| 17 | `social-mini-app/src/navigation/BottomNav.tsx` | Modify | Add tab or skip |

## Failure Scenarios

| Scenario | Detection | Impact | Mitigation |
|---|---|---|---|
| **Subject has <2 snapshots in period** | SQL returns NULL for `previous` | Growth rate shows 0.0 | Display "Not enough data" in UI; do not compute growth |
| **All subjects have zero followers** | `previous.followers == 0` | Divide-by-zero | Guard in SQL/Python: return 0.0 when denominator == 0 |
| **Database query too slow with many snapshots** | Query > 2s on 1k subjects × 90 days | Gateway timeout | Add `materialized view` or pre-aggregation in background task (deferred optimisation) |
| **Cache stampede on benchmark endpoint** | Many concurrent requests after cache expiry | DB overload | Use `CacheService` with TTL + single-flight pattern (if CacheService supports it, else add jitter) |
| **Mini App shows stale benchmark after sync** | Cache hit in React Query | Old growth numbers | Invalidate `benchmarks` query key in `useTriggerSync` onSuccess callback |
| **No subjects on a platform** | `subject_count == 0` | Empty platform in chart | Hide that platform from `PlatformComparisonPanel` |
| **Feature 1 (Post Analytics) not yet shipped** | `posts` table missing | `posts_per_week` cannot compute | Fallback: use `activity_frequency` from `Subject` table as proxy for posts_per_week. Remove fallback once Feature 1 ships. |

## Testing Strategy

### Unit Tests (Gateway)

- **BenchmarkService:** Mock `AsyncSession` with synthetic `activity_snapshots` data:
  - Subject A: 100 followers → 150 followers over 7 days → expect 50% growth
  - Subject B: 0 followers → cannot compute → expect 0.0
  - Subject C: only 1 snapshot → expect "not enough data" flag
- **Percentile ranking:** 10 subjects with known growth rates → verify rank and percentile correctness.

### Integration Tests (Gateway)

- `pytest` with `aiosqlite` + fakeredis (existing pattern) → verify `/v1/benchmarks` returns correct envelope shape.
- Test caching: first request hits DB, second request hits cache (verify via `CacheService` mock or Redis counter).

### Mini App Tests

- `npm run lint && npm run typecheck && npm run build`.
- Manual: Dashboard shows leaderboard cards; Subject Detail shows benchmark badge.

## Rollout Plan

### Phase 1: Gateway Computation Layer (Day 1-3)
1. Add benchmark schemas to `social-common`.
2. Create `BenchmarkService` with growth rate, ranking, and platform average queries.
3. Write unit tests for `BenchmarkService` with mock data.

### Phase 2: Gateway API (Day 4-5)
1. Create `benchmarks/routes.py` with `/v1/benchmarks` and `/v1/subjects/{id}/benchmark`.
2. Add caching (5-minute TTL).
3. Regenerate OpenAPI + `types.ts`.
4. Run `ruff check . && mypy src && pytest`.

### Phase 3: Mini App Integration (Day 6-8)
1. Add hooks: `useBenchmarks`, `useSubjectBenchmark`.
2. Build `PlatformComparisonPanel` (embedded in DashboardPage).
3. Build `BenchmarkBadge` (embedded in SubjectDetailPage).
4. Optionally build full `BenchmarkPage` if decided.

### Phase 4: Verification (Day 9)
1. Seed test data with 5-10 subjects and 30 days of snapshots.
2. Verify growth rates and rankings match expected values.
3. Verify cache invalidation after sync.

## Open Questions

1. **Dashboard vs. Dedicated Page:** Should benchmarking live entirely inside `DashboardPage` (as sections), or get its own `/benchmarks` route? Mobile screen real estate is limited. Recommend embedding in Dashboard first.
2. **Fallback for `posts_per_week`:** If Feature 1 is not shipped yet, `posts` table does not exist. Should we use `activity_frequency` (posts per day) as a proxy, or defer this metric? Recommend using `activity_frequency * 7` as temporary proxy.
3. **Growth rate accuracy:** Facebook follower counts are sometimes unstable (bot purges). Should we smooth growth rate with a 3-day rolling average instead of point-in-point? Point-to-point is simpler for MVP; smoothing can be added later.
4. **Benchmark scope:** Should inactive (`status = 'inactive'`) subjects be included in benchmarks? Recommend excluding them by default, with an "Include inactive" toggle in UI.
5. **Performance at scale:** With 1000 subjects × 90 days × hourly snapshots = ~2M rows, the benchmark query may be slow. Should we add a TimescaleDB `continuous aggregate` now or wait? Recommend waiting — measure first, optimise later.

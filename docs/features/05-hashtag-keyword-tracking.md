# Feature Spec: Hashtag & Keyword Performance Tracking

## Overview

Extract and track **hashtags** from post content across all platforms to surface trending topics and content opportunities. This is a core capability in social listening: Hootsuite monitors "trending topics and content opportunities before they peak", Sprout Social has "Brand Keywords" for "real-time brand monitoring with keyword and hashtag searches", and Sendible includes content curation tools that surface trending topics. The system already collects post captions/titles (via Feature 1's `Post` model); this feature adds a **hashtag extraction pipeline** during sync, normalises them to a unified `hashtag` table, and provides analytics on which hashtags drive the most engagement.

## Goals

- [ ] Collector extracts hashtags from `Post.caption` during sync using platform-specific parsing rules (e.g. `#word` for most platforms, TikTok's special hashtag format).
- [ ] New `hashtags` table: `name` (lowercase, normalised), `platform`, `first_seen_at`, `last_seen_at`, `usage_count`, `total_engagement`.
- [ ] New `subject_hashtags` link table: `subject_id`, `hashtag_id`, `post_count`, `avg_engagement_rate`, `last_used_at`.
- [ ] Gateway exposes:
  - `GET /v1/hashtags?platform=&sort=` — trending hashtags
  - `GET /v1/subjects/{id}/hashtags` — top hashtags for a subject
  - `GET /v1/hashtags/{name}` — hashtag detail: which subjects use it, trend over time
- [ ] Mini App shows:
  - **Top Hashtags** section in Subject Detail (top 5-10 hashtags with post count + avg engagement)
  - **Trending Hashtags** page/section (across all subjects, filterable by platform)
  - Subject list filter by hashtag (e.g. show only subjects that posted with `#marketing`)

## Non-Goals

- **We do NOT track keyword mentions outside owned posts.** This is not social listening (monitoring the entire platform for a keyword). We only extract hashtags from posts already collected for tracked subjects.
- **We do NOT implement real-time hashtag trend detection.** Trends are computed from our own data only, not from platform-wide APIs (e.g. Twitter Trending API, TikTok Trending page).
- **We do NOT store full post-hashtag mapping.** We link `Subject` ↔ `Hashtag` with aggregated stats, not individual `Post` ↔ `Hashtag` rows. Per-post mapping is too granular for MVP.
- **We do NOT support hashtag sentiment analysis.** Sentiment of posts containing a hashtag is out of scope (see Feature 9 for lite sentiment).
- **We do NOT build a hashtag suggestion engine.** We do not recommend hashtags to use; we only report which hashtags subjects *are already using*.

## Architecture

### Data Model Changes

#### New Table: `hashtags`

Owned by `social-data-collector`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `name` | `String(128)` | NOT NULL, lowercase | Normalised hashtag text |
| `platform` | `Enum(Platform)` | NOT NULL | Platform where first seen |
| `first_seen_at` | `TimestampTZ` | NOT NULL | First time observed |
| `last_seen_at` | `TimestampTZ` | NOT NULL | Most recent observation |
| `usage_count` | `Integer` | NOT NULL, default 0 | Total posts using this hashtag across all subjects |
| `total_engagement` | `Float` | NOT NULL, default 0.0 | Sum of engagement rates of all posts using this hashtag |
| `created_at` | `TimestampTZ` | NOT NULL | |

**Unique constraint:** `UNIQUE(name, platform)` — same hashtag on different platforms are separate rows (hashtag meanings differ by platform).

#### New Table: `subject_hashtags`

Owned by `social-data-collector`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `subject_id` | `UUID` | FK → `subjects.id`, `ON DELETE CASCADE` | |
| `hashtag_id` | `UUID` | FK → `hashtags.id`, `ON DELETE CASCADE` | |
| `post_count` | `Integer` | NOT NULL, default 0 | How many posts from this subject used this hashtag |
| `avg_engagement_rate` | `Float` | NOT NULL, default 0.0 | Average engagement rate of those posts |
| `last_used_at` | `TimestampTZ` | NOT NULL | Most recent post using this hashtag |
| `created_at` | `TimestampTZ` | NOT NULL | |

**Unique constraint:** `UNIQUE(subject_id, hashtag_id)`.

**Indexes:**
- `CREATE INDEX idx_subject_hashtags_subject ON subject_hashtags(subject_id);`
- `CREATE INDEX idx_subject_hashtags_hashtag ON subject_hashtags(hashtag_id);`
- `CREATE INDEX idx_hashtags_platform_usage ON hashtags(platform, usage_count DESC);`

### Service Interactions

```
┌─────────────────────────────┐
│ social-data-collector       │
│  (sync cycle)               │
│                             │
│  ┌───────────────────────┐  │
│  │ 1. Fetch posts        │  │── Feature 1 pipeline
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 2. Extract hashtags   │  │── Regex: #\w+ (platform-specific)
│  │    from captions      │  │
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 3. Upsert hashtags    │  │── INSERT ... ON CONFLICT (name, platform)
│  │    + subject_hashtags │  │    DO UPDATE usage_count++, total_engagement+=...
│  └───────────────────────┘  │
└─────────────────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ social-api-gateway            │
│  /v1/hashtags                 │── Trending hashtags
│  /v1/subjects/{id}/hashtags   │── Subject's top hashtags
└─────────────────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ social-mini-app             │
│  TopHashtagsPanel           │── Subject Detail section
│  TrendingHashtagsPage       │── Global view
│  HashtagFilter              │── Subject list filter
└─────────────────────────────┘
```

### API Contract

#### `GET /v1/hashtags`

```yaml
parameters:
  platform: Platform | null
  sort_by: enum ["usage_count", "avg_engagement", "last_seen_at"] (default "usage_count")
  page: int (default 1)
  limit: int (default 20, max 100)

response: HashtagListResponse
  data: Hashtag[]
  meta: { page, limit, total }
```

**`Hashtag` schema:**
```json
{
  "id": "...",
  "name": "marketing",
  "platform": "facebook",
  "usage_count": 42,
  "avg_engagement": 3.8,
  "first_seen_at": "...",
  "last_seen_at": "..."
}
```

#### `GET /v1/subjects/{subject_id}/hashtags`

```yaml
parameters:
  limit: int (default 10)

response: SubjectHashtagListResponse
  data: SubjectHashtag[]
```

**`SubjectHashtag` schema:**
```json
{
  "hashtag": { /* embedded Hashtag */ },
  "post_count": 5,
  "avg_engagement_rate": 4.2,
  "last_used_at": "..."
}
```

#### `GET /v1/hashtags/{hashtag_name}`

Detail page for a hashtag: which subjects use it, trend chart.

```yaml
response: HashtagDetailResponse
  data: {
    "hashtag": Hashtag,
    "subjects": [ { "subject": Subject, "post_count": 5, "avg_engagement_rate": 4.2 } ],
    "trend": [ { "date": "2024-01-01", "usage_count": 3 }, ... ]  // Daily usage over last 30 days
  }
```

## Code Changes

### 1. `social-common` — Schemas

**File:** `social_common/schemas.py`

```python
class Hashtag(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID = Field(default_factory=uuid4)
    name: str  # lowercase
    platform: Platform
    usage_count: int = Field(ge=0, default=0)
    total_engagement: float = Field(ge=0.0, default=0.0)
    first_seen_at: datetime
    last_seen_at: datetime
    created_at: datetime = Field(default_factory=_utcnow)

class SubjectHashtag(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID
    hashtag_id: UUID
    post_count: int = Field(ge=0, default=0)
    avg_engagement_rate: float = Field(ge=0.0, default=0.0)
    last_used_at: datetime
    created_at: datetime = Field(default_factory=_utcnow)
    # Embedded:
    hashtag: Hashtag | None = None
```

### 2. `social-data-collector` — Extraction & Persistence

**File:** `src/social_data_collector/persistence/models.py` (modify)

- Add `HashtagModel` and `SubjectHashtagModel` SQLAlchemy models.

**File:** `src/social_data_collector/persistence/repository.py` (modify)

- Add `upsert_hashtag(name, platform, engagement_rate) -> HashtagModel`.
- Add `upsert_subject_hashtag(subject_id, hashtag_id, post_count_delta, engagement_rate, last_used_at)`.

**File:** `src/social_data_collector/hashtags.py` (new)

```python
import re
from typing import Iterable

# Platform-specific regexes
HASHTAG_RE = re.compile(r"#(\w+)", re.UNICODE)


def extract_hashtags(text: str | None) -> list[str]:
    """Extract all hashtags from a post caption/title.
    
    Returns lowercase, deduplicated list.
    """
    if not text:
        return []
    tags = HASHTAG_RE.findall(text)
    # Deduplicate while preserving order
    seen = set()
    result = []
    for tag in tags:
        lower = tag.lower()
        if lower not in seen:
            seen.add(lower)
            result.append(lower)
    return result


def extract_hashtags_from_posts(posts: Iterable[PostModel]) -> dict[str, list[PostModel]]:
    """Group posts by hashtag."""
    mapping: dict[str, list[PostModel]] = {}
    for post in posts:
        for tag in extract_hashtags(post.caption):
            mapping.setdefault(tag, []).append(post)
    return mapping
```

**File:** `src/social_data_collector/scheduler/tasks.py` (modify)

- After upserting posts (Feature 1), extract hashtags from each post's caption:
```python
for post in posts:
    hashtags = extract_hashtags(post.caption)
    for tag in hashtags:
        hashtag = await repo.upsert_hashtag(name=tag, platform=subject.platform)
        await repo.upsert_subject_hashtag(
            subject_id=subject.id,
            hashtag_id=hashtag.id,
            post_count_delta=1,
            engagement_rate=post.engagement_rate,
            last_used_at=post.published_at,
        )
```

**Note:** `upsert_subject_hashtag` needs to recompute `avg_engagement_rate` and increment `post_count`. This requires reading the existing row first or using a database-level computation. For simplicity:
```sql
INSERT INTO subject_hashtags (subject_id, hashtag_id, post_count, avg_engagement_rate, last_used_at)
VALUES (?, ?, 1, ?, ?)
ON CONFLICT (subject_id, hashtag_id) DO UPDATE SET
  post_count = subject_hashtags.post_count + 1,
  avg_engagement_rate = (subject_hashtags.avg_engagement_rate * subject_hashtags.post_count + excluded.avg_engagement_rate) / (subject_hashtags.post_count + 1),
  last_used_at = GREATEST(subject_hashtags.last_used_at, excluded.last_used_at);
```

### 3. `social-api-gateway` — Hashtag API

**File:** `src/social_api_gateway/hashtags/__init__.py` (new package)

**File:** `src/social_api_gateway/hashtags/models.py` (new)

- Read-only mirrors: `HashtagModel`, `SubjectHashtagModel`.

**File:** `src/social_api_gateway/hashtags/repository.py` (new)

```python
class HashtagRepository:
    async def list_hashtags(self, platform, sort_by, limit, offset) -> tuple[list[HashtagModel], int]:
        ...

    async def get_subject_hashtags(self, subject_id, limit) -> list[SubjectHashtagModel]:
        ...

    async def get_hashtag_detail(self, name: str) -> dict:
        ...  # Includes subject list + daily trend
```

**File:** `src/social_api_gateway/hashtags/routes.py` (new)

```python
router = APIRouter(prefix="/v1/hashtags", tags=["hashtags"])

@router.get("", response_model=HashtagListResponse)
async def list_hashtags(...)

@router.get("/{hashtag_name}", response_model=HashtagDetailResponse)
async def get_hashtag_detail(...)

# Subject hashtags endpoint lives under subjects router:
# GET /v1/subjects/{subject_id}/hashtags
```

**File:** `src/social_api_gateway/subjects/routes.py` (modify)

- Add `GET /{subject_id}/hashtags` endpoint.

**File:** `src/social_api_gateway/main.py` (modify)

- Mount `hashtags_router`.

### 4. `social-mini-app` — UI

**File:** `src/api/hooks.ts`

```typescript
export function useSubjectHashtags(subjectId: string) {
  return useQuery({
    queryKey: ["hashtags", subjectId],
    queryFn: () => apiGet<SubjectHashtag[]>(`/v1/subjects/${subjectId}/hashtags`, { limit: 10 }),
    enabled: !!subjectId,
  });
}

export function useTrendingHashtags(platform?: string) {
  return useQuery({
    queryKey: ["trending-hashtags", platform],
    queryFn: () => apiGet<Hashtag[]>("/v1/hashtags", { platform, sort_by: "usage_count", limit: 20 }),
  });
}
```

**File:** `src/components/panels/TopHashtagsPanel.tsx` (new)

```tsx
// Subject Detail section
// Horizontal scrollable chips or small cards
// Each hashtag chip: #name | 5 posts | 4.2% avg engagement
// Tap chip → navigate to trending hashtags filtered by this tag
```

**File:** `src/pages/TrendingHashtagsPage.tsx` (new)

```tsx
// Full page: "Trending Hashtags"
// Filter bar: Platform dropdown
// List: each row is a card with hashtag name, usage count, platform badge, sparkline of last 7 days usage
// Tap row → hashtag detail with subject list
```

**File:** `src/components/subject/HashtagFilter.tsx` (new)

```tsx
// Subject list filter bar extension
// Search input that searches hashtags instead of subject names
// When active, filter subjects to only those that used the hashtag
```

**File:** `src/pages/Subjects/SubjectDetail.tsx` (modify)

- Add `<TopHashtagsPanel subjectId={id!} />` below ContentPerformancePanel.

## Interface Changes (UI/UX)

### New Components

| Component | Description |
|---|---|
| `TopHashtagsPanel` | Horizontal scrollable hashtag chips in Subject Detail |
| `TrendingHashtagsPage` | Full page listing trending hashtags across all subjects |
| `HashtagFilter` | Subject list filter by hashtag |
| `HashtagDetailPage` | Which subjects use a hashtag, trend sparkline |

### Modified Screens

| Screen | Change |
|---|---|
| `SubjectDetailPage` | Add `TopHashtagsPanel` section |
| `SubjectListPage` | Add `HashtagFilter` option in filter bar |
| `DashboardPage` | Optionally add "Top trending hashtags" summary card |

### Design Notes (Mobile-First)

- **Hashtag chips.** Small rounded pills with `#name`, post count, and mini engagement bar. Horizontal scroll to save vertical space.
- **No full hashtag tables.** Trending list uses cards, not grids.
- **Tap to explore.** Tap a hashtag chip → see all subjects using it. Tap a subject in that list → go to subject detail.
- **Filter integration.** When user searches in subject list, add a segmented control: "Subjects" | "Hashtags" — tapping "Hashtags" searches hashtag names instead.

## Files Relevant (Complete List)

| # | File | Action | Description |
|---|---|---|---|
| 1 | `social-common/social_common/schemas.py` | Modify | Add `Hashtag`, `SubjectHashtag` schemas |
| 2 | `social-data-collector/migrations/versions/` | Create | Migration: `hashtags` + `subject_hashtags` tables |
| 3 | `social-data-collector/src/social_data_collector/persistence/models.py` | Modify | Add `HashtagModel`, `SubjectHashtagModel` |
| 4 | `social-data-collector/src/social_data_collector/persistence/repository.py` | Modify | Add `upsert_hashtag`, `upsert_subject_hashtag` |
| 5 | `social-data-collector/src/social_data_collector/hashtags.py` | Create | `extract_hashtags`, `extract_hashtags_from_posts` |
| 6 | `social-data-collector/src/social_data_collector/scheduler/tasks.py` | Modify | Extract hashtags after post upsert |
| 7 | `social-api-gateway/src/social_api_gateway/hashtags/__init__.py` | Create | Package init |
| 8 | `social-api-gateway/src/social_api_gateway/hashtags/models.py` | Create | Read-only mirrors |
| 9 | `social-api-gateway/src/social_api_gateway/hashtags/repository.py` | Create | `HashtagRepository` |
| 10 | `social-api-gateway/src/social_api_gateway/hashtags/routes.py` | Create | `/v1/hashtags` endpoints |
| 11 | `social-api-gateway/src/social_api_gateway/hashtags/schemas.py` | Create | Response envelopes |
| 12 | `social-api-gateway/src/social_api_gateway/subjects/routes.py` | Modify | Add `GET /{subject_id}/hashtags` |
| 13 | `social-api-gateway/src/social_api_gateway/main.py` | Modify | Mount `hashtags_router` |
| 14 | `social-api-gateway/scripts/export_openapi.py` | Modify | Regenerate |
| 15 | `social-mini-app/src/api/types.ts` | Regenerate | From OpenAPI |
| 16 | `social-mini-app/src/api/hooks.ts` | Modify | Add `useSubjectHashtags`, `useTrendingHashtags` |
| 17 | `social-mini-app/src/components/panels/TopHashtagsPanel.tsx` | Create | Subject detail hashtag chips |
| 18 | `social-mini-app/src/pages/TrendingHashtagsPage.tsx` | Create | Global trending view |
| 19 | `social-mini-app/src/components/subject/HashtagFilter.tsx` | Create | Filter subjects by hashtag |
| 20 | `social-mini-app/src/pages/Subjects/SubjectDetail.tsx` | Modify | Add TopHashtagsPanel |
| 21 | `social-mini-app/src/pages/SubjectListPage.tsx` | Modify | Integrate HashtagFilter |
| 22 | `social-mini-app/src/routes.tsx` | Modify | Add `/hashtags` and `/hashtags/:name` routes |

## Failure Scenarios

| Scenario | Detection | Impact | Mitigation |
|---|---|---|---|
| **Post caption is None or empty** | `caption` is null | No hashtags extracted | `extract_hashtags` returns `[]`; no error |
| **Duplicate hashtags in same caption** | `#foo #foo` | Would double-count | `extract_hashtags` deduplicates per post |
| **Hashtag extraction regex misses platform formats** | TikTok uses Chinese hashtags, Unicode | Missed hashtags | Use `re.UNICODE` flag; test with international content |
| **Very long hashtag > 128 chars** | Regex match > 128 chars | Truncation or DB error | Truncate to 128 chars in normaliser |
| **Subject deleted** | CASCADE delete | `subject_hashtags` rows auto-deleted | FK with `ON DELETE CASCADE` |
| **Hashtag table grows too large** | Millions of unique hashtags | Query performance degrades | Add indexes; consider pruning hashtags with `usage_count=1` and `last_seen_at > 90 days` (deferred optimisation) |
| **Feature 1 not yet shipped** | `posts` table missing | Cannot extract hashtags from posts | Blocker: Feature 1 must ship before or concurrently with this feature. Cannot extract hashtags without posts. |
| **Mini App shows hashtags from old posts** | Hashtag `last_used_at` is stale | User sees outdated hashtag prominence | Sort by `last_used_at` DESC in TopHashtagsPanel; hide hashtags not used in last 30 days |

## Testing Strategy

### Unit Tests (Collector)

- **Hashtag extraction:**
  - Input: `"Check out our new product! #launch #product #Launch"` → Output: `["launch", "product"]` (deduped, lowercase)
  - Input: `"No hashtags here"` → Output: `[]`
  - Input: `"#\u4e2d\u6587"` (Chinese hashtag) → Output: `["\u4e2d\u6587"]` (Unicode support)
- **Repository upsert:** Test idempotency — same hashtag on same subject increments count, doesn't duplicate row.

### Integration Tests (Gateway)

- Seed 3 subjects with posts containing hashtags.
- Verify `/v1/hashtags` returns correct usage counts.
- Verify `/v1/subjects/{id}/hashtags` returns subject-specific stats.

### Mini App Tests

- `npm run lint && npm run typecheck && npm run build`.
- Manual: Subject Detail shows hashtag chips; tap chip navigates correctly.

## Rollout Plan

### Phase 1: Schema & Migration (Day 1)
1. Add `Hashtag`, `SubjectHashtag` schemas to `social-common`.
2. Create collector migration for `hashtags` + `subject_hashtags`.
3. Add SQLAlchemy models.

### Phase 2: Extraction Pipeline (Day 2-3)
1. Implement `extract_hashtags` with tests.
2. Add repository upsert methods.
3. Wire into Celery sync tasks (after post upsert).

### Phase 3: Gateway API (Day 4-5)
1. Create `hashtags/` package with repository, routes, schemas.
2. Add subject-hashtag endpoint.
3. Regenerate OpenAPI.

### Phase 4: Mini App (Day 6-8)
1. Add hooks.
2. Build `TopHashtagsPanel`.
3. Build `TrendingHashtagsPage`.
4. Build `HashtagFilter`.
5. Integrate into Subject Detail and Subject List.

### Phase 5: Verification (Day 9)
1. Run full test suites.
2. Manual end-to-end: sync a subject with hashtags → verify chips appear.

## Open Questions

1. **Dependency on Feature 1:** This feature is blocked by Feature 1 (Post Analytics) because we need `Post.caption` to extract hashtags. Should Feature 1 and 5 be developed in the same sprint, or back-to-back? Recommend back-to-back: ship Feature 1 first, then Feature 5 immediately after.
2. **Hashtag normalisation:** Should we strip non-alphanumeric characters? E.g. is `#foo-bar` one hashtag or two? Most platforms treat `#foo-bar` as one tag. Recommend matching platform behaviour: `#(\w+)` captures alphanumeric + underscore only; hyphens break the tag.
3. **Hashtag engagement attribution:** If a post has 3 hashtags, which hashtag "owns" the engagement? In `subject_hashtags`, we divide engagement equally? Or assign full engagement to all 3? Simpler: assign full engagement to all hashtags (overcounting). For MVP this is acceptable; weighted attribution is complex.
4. **Cross-platform hashtag identity:** `#marketing` on Facebook and `#marketing` on TikTok are stored as separate rows (unique on `(name, platform)`). Is this correct? Yes — hashtag ecosystems differ by platform.
5. **Pruning old hashtags:** Should we periodically delete hashtags with `usage_count=1` older than 90 days? Not for MVP; add a background job later if table grows too large.

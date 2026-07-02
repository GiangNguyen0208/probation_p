# Feature Spec: Post-Level Content Performance Analytics

## Overview

Extend the platform from **account-level metrics** (followers, post count) down to **individual post-level analytics** for every supported platform. This is a table-stakes feature in social media management: Hootsuite, Sprout Social, and Sendible all dedicate core product pillars to per-post performance. The system already has a `Video` model for YouTube; this feature generalises that pattern to **Facebook Posts** and **TikTok Videos**, and adds a unified `Post` schema with engagement rate calculation.

## Goals

- [ ] Collector fetches the most recent posts/videos for **every** platform during sync (not just YouTube).
- [ ] A unified `Post` schema stores: `platform_post_id`, `caption`, `media_type`, `published_at`, `like_count`, `comment_count`, `share_count`, `view_count`, `engagement_rate`, `thumbnail_url`.
- [ ] Gateway exposes `GET /v1/subjects/{id}/posts` with pagination, sorting, and filtering.
- [ ] Mini App renders a **Top Performing Posts** panel inside `SubjectDetailPage`, showing posts ranked by engagement rate with a mini sparkline of recent performance.
- [ ] Engagement rate is calculated consistently across all platforms: `(likes + comments + shares) / views` when views are available, else `(likes + comments + shares) / followers`.
- [ ] Posts are **idempotently upserted** (same pattern as `Video` and `Subject`) — duplicate syncs update metrics, not create new rows.

## Non-Goals

- **We do NOT build content creation or scheduling.** This is a read-only monitoring platform; post creation is out of scope.
- **We do NOT store full post media.** `thumbnail_url` only; no video download, no image caching.
- **We do NOT store historical post metric time-series.** Only the latest observed metrics per post (same pattern as `Video`). Full historical would require a `post_snapshots` hypertable — deferred to Phase 6+.
- **We do NOT support Instagram/Twitter/X in this feature** unless they are already supported by the collector. Focus on existing platforms: Facebook, YouTube, TikTok.
- **We do NOT build a full social inbox.** Comment replies, DMs, and moderation are out of scope (see Feature 9 for lite comment tracking).

## Architecture

### Data Model Changes

#### New Table: `posts`

Owned by `social-data-collector` (same migration table as `subjects`/`activity_snapshots`).

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUID` | PK, default `gen_random_uuid()` | System ID |
| `subject_id` | `UUID` | FK → `subjects.id`, `ON DELETE CASCADE` | Which subject this post belongs to |
| `platform_post_id` | `String(255)` | NOT NULL | Native platform ID |
| `platform` | `Enum(Platform)` | NOT NULL | facebook / youtube / tiktok |
| `caption` | `Text` | nullable | Post text / video title |
| `media_type` | `Enum('video', 'image', 'carousel', 'text', 'reel')` | nullable | Platform-specific type |
| `thumbnail_url` | `String(1024)` | nullable | Link to thumbnail image |
| `published_at` | `TimestampTZ` | NOT NULL | When the post was published |
| `like_count` | `Integer` | NOT NULL, default 0 | Reactions / likes |
| `comment_count` | `Integer` | NOT NULL, default 0 | Comments |
| `share_count` | `Integer` | NOT NULL, default 0 | Shares / retweets |
| `view_count` | `Integer` | NOT NULL, default 0 | Views (0 for platforms without view counts) |
| `engagement_rate` | `Float` | NOT NULL, default 0.0 | Computed on upsert |
| `last_synced_at` | `TimestampTZ` | NOT NULL | When we last updated this row |
| `created_at` | `TimestampTZ` | NOT NULL, default `now()` | First observed |

**Unique constraint:** `UNIQUE(subject_id, platform_post_id)` — idempotent upsert key.

**Index:** `CREATE INDEX idx_posts_subject_published ON posts(subject_id, published_at DESC);`

#### Modified Schema in `social-common`

- Add `Post` Pydantic model in `social_common/schemas.py`.
- Add `PostListResponse` / `PostResponse` envelope schemas in gateway `subjects/schemas.py` (gateway-local, not common).

### Service Interactions

```
┌─────────────────────┐         ┌─────────────────────┐
│ social-data-collector│         │  Facebook Graph API │
│  (sync cycle)       │────────→│  /{page-id}/posts  │
│                     │         │  ?fields=reactions,│
│  ┌───────────────┐  │         │  comments.summary, │
│  │ fetch posts   │  │         │  shares            │
│  │ → normalise   │  │         └─────────────────────┘
│  │ → upsert      │  │
│  └───────────────┘  │         ┌─────────────────────┐
│        │            │────────→│ YouTube Data API    │
│        ▼            │         │  /videos?part=stats │
│  ┌───────────────┐  │         └─────────────────────┘
│  │ posts table   │  │
│  └───────────────┘  │         ┌─────────────────────┐
└─────────────────────┘────────→│ TikTok API          │
                                │  /user/videos        │
                                └─────────────────────┘
         │
         │ (read)
         ▼
┌─────────────────────┐
│ social-api-gateway  │◄──── GET /v1/subjects/{id}/posts
│  (read-only query)  │       ?platform=&sort=engagement&limit=
└─────────────────────┘
         │
         │ (fetch)
         ▼
┌─────────────────────┐
│ social-mini-app     │
│  TopPostsPanel      │
│  EngagementSparkline│
└─────────────────────┘
```

### API Contract

#### `GET /v1/subjects/{subject_id}/posts`

```yaml
parameters:
  page: int (default 1, ge=1)
  limit: int (default 20, ge=1, le=100)
  sort_by: enum ["published_at", "engagement_rate", "view_count", "like_count"]
  sort_order: enum ["asc", "desc"] (default "desc")
  media_type: enum ["video", "image", "carousel", "text", "reel"] (optional filter)

response: PostListResponse
  data: Post[]
  meta: { page, limit, total }
```

#### `GET /v1/subjects/{subject_id}/posts/{post_id}`

Single post detail (for future expansion; not required for MVP).

## Code Changes

### 1. `social-common` — Shared Schema

**File:** `social_common/schemas.py`

```python
class Post(BaseModel):
    """Per-post engagement metrics for any platform.

    Upserted on every sync cycle. Stores the latest observed metrics;
    historical tracking is not maintained (same pattern as Video).
    """
    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID
    platform: Platform
    platform_post_id: str
    caption: str | None = None
    media_type: str | None = None  # video, image, carousel, text, reel
    thumbnail_url: str | None = None
    published_at: datetime
    like_count: int = Field(ge=0, default=0)
    comment_count: int = Field(ge=0, default=0)
    share_count: int = Field(ge=0, default=0)
    view_count: int = Field(ge=0, default=0)
    engagement_rate: float = Field(ge=0.0, default=0.0)
    last_synced_at: datetime
    created_at: datetime = Field(default_factory=_utcnow)
```

**File:** `social_common/enums.py` (no changes unless we want `MediaType` enum)
→ Recommend keeping `media_type` as plain `str` for flexibility.

### 2. `social-data-collector` — Fetch, Normalise, Persist

**File:** `src/social_data_collector/persistence/models.py`

- Add `PostModel` SQLAlchemy model (mirror of `Post` schema).
- Add relationship: `SubjectModel.posts` (lazy select, not eager — avoid N+1 in sync).

**File:** `src/social_data_collector/persistence/repository.py`

- Add `upsert_post(post: PostModel) -> PostModel` — same idempotent upsert pattern as `Video`.
- Add `list_posts(subject_id, limit, offset, sort_by, sort_order, media_type) -> tuple[list[PostModel], int]`.

**File:** `src/social_data_collector/clients/facebook.py`

- Extend `fetch_page_posts(page_id: str, limit: int = 25)` to call:
  `/{page_id}/posts?fields=id,message,created_time,attachments{media},reactions.summary(total_count),comments.summary(total_count),shares`
- Return raw JSON list; do not compute engagement_rate here.

**File:** `src/social_data_collector/clients/youtube.py`

- Extend `fetch_channel_videos()` to also return `caption` (video title + description truncated), `media_type='video'`, `published_at`.
- **Note:** YouTube already has `Video` model. We have two options:
  - **Option A (recommended):** Map existing `Video` model into `Post` schema via gateway transform. No collector change for YouTube.
  - **Option B:** Duplicate data into `posts` table from YouTube sync. Simpler for unified queries, but denormalised.
  → **Decision:** Option B for unified querying. Add a step in YouTube sync normaliser to also write to `posts` table with `platform='youtube'`, `media_type='video'`.

**File:** `src/social_data_collector/clients/tiktok.py`

- Add `fetch_user_videos(user_id: str)` → call TikTok Research API or scraper endpoint.
- Fields: `id`, `title` (caption), `create_time`, `video_description`, `like_count`, `comment_count`, `share_count`, `view_count`.
- Map to `PostModel`.

**File:** `src/social_data_collector/normalizers/facebook_post.py` (new)

```python
def normalize_page_post(raw: dict, subject_id: UUID) -> PostModel:
    """Map Facebook Graph API /posts item to PostModel."""
    reactions = raw.get("reactions", {}).get("summary", {}).get("total_count", 0)
    comments = raw.get("comments", {}).get("summary", {}).get("total_count", 0)
    shares = raw.get("shares", {}).get("count", 0)
    views = 0  # Facebook posts do not expose view counts via public Graph API
    
    return PostModel(
        subject_id=subject_id,
        platform=Platform.FACEBOOK,
        platform_post_id=raw["id"],
        caption=raw.get("message", "")[:2000],  # Facebook allows long posts
        media_type=_detect_fb_media_type(raw.get("attachments", {})),
        published_at=datetime.fromisoformat(raw["created_time"].replace("Z", "+00:00")),
        like_count=reactions,
        comment_count=comments,
        share_count=shares,
        view_count=views,
        last_synced_at=_utcnow(),
    )
```

**File:** `src/social_data_collector/normalizers/tiktok_post.py` (new)

Same pattern for TikTok video item → `PostModel`.

**File:** `src/social_data_collector/scheduler/tasks.py`

- Extend `sync_facebook_subject` task: after upserting `Subject`, call `fetch_page_posts` and upsert each into `posts`.
- Extend `sync_youtube_subject` task: after upserting `Videos`, also upsert each video into `posts` (denormalised).
- Extend `sync_tiktok_subject` task: fetch videos and upsert into `posts`.

### 3. `social-api-gateway` — Read API

**File:** `src/social_api_gateway/subjects/models.py`

- Add `PostModel` (read-only mirror of collector's table). No migration needed (owned by collector).

**File:** `src/social_api_gateway/subjects/repository.py`

- Add `list_posts(...)` method using the same pattern as `list_videos`.
- Compute `engagement_rate` on read if it's not stored (but we recommend storing it on write).

**File:** `src/social_api_gateway/subjects/routes.py`

- Add `GET /{subject_id}/posts` endpoint (same pattern as `/{subject_id}/videos`).
- Add `sort_by` / `sort_order` query params.

**File:** `src/social_api_gateway/subjects/schemas.py`

- Add `PostListResponse`, `PostResponse` envelope types.

### 4. `social-mini-app` — UI

**File:** `src/api/hooks.ts`

```typescript
export function usePosts(subjectId: string, sortBy: string = "engagement_rate") {
  return useQuery({
    queryKey: ["posts", subjectId, sortBy],
    queryFn: () => apiGet<Post[]>(`/v1/subjects/${subjectId}/posts`, { sort_by: sortBy, limit: 10 }),
    enabled: !!subjectId,
    staleTime: 60_000,
  });
}
```

**File:** `src/components/panels/ContentPerformancePanel.tsx` (new)

```tsx
// Shows top 5 posts by engagement rate
// Each post is a card: thumbnail, caption (2-line clamp), engagement bar (likes|comments|shares), engagement_rate badge
// Tap post → open external link (platform URL)
// For YouTube: use existing video card pattern, just add engagement_rate
```

**File:** `src/components/charts/PostEngagementSparkline.tsx` (new)

```tsx
// Tiny bar chart inside each Post card showing relative engagement (likes/comments/shares) vs max in list
// No axes, no grid — just 3 colored mini-bars (like Sprout Social's post cards)
```

**File:** `src/pages/Subjects/SubjectDetail.tsx`

- Insert `<ContentPerformancePanel subjectId={id!} />` between "Engagement Panel" và "Charts" sections.
- For YouTube subjects, keep existing video list but add engagement_rate to each card.

## Interface Changes (UI/UX)

### New Components

| Component | Location | Description |
|---|---|---|
| `ContentPerformancePanel` | `src/components/panels/` | Top 5-10 posts ranked by engagement rate |
| `PostEngagementSparkline` | `src/components/charts/` | 3-bar mini chart (likes/comments/shares) per post |
| `PostCard` | `src/components/subject/` | Reusable card: thumbnail + caption + engagement metrics |

### Modified Screens

| Screen | Change |
|---|---|
| `SubjectDetailPage` | Add `ContentPerformancePanel` section below platform engagement panel |
| `YouTubeEngagementPanel` | Add engagement_rate badge to existing video cards |

### Design Notes (Mobile-First)

- **Cards, not tables.** Each post is a vertical card with thumbnail on the left, text on the right.
- **Progressive disclosure.** Only top 5 posts shown by default; "Show more" button fetches next 5.
- **External link.** Tap post card → open platform URL in new tab (haptic feedback on tap).
- **No inline charts.** Sparkline only; full engagement breakdown is a future detail screen.

## Files Relevant (Complete List)

| # | File | Action | Description |
|---|---|---|---|
| 1 | `social-common/social_common/schemas.py` | Modify | Add `Post` schema |
| 2 | `social-data-collector/migrations/versions/` | Create | Alembic migration: add `posts` table |
| 3 | `social-data-collector/src/social_data_collector/persistence/models.py` | Modify | Add `PostModel` SQLAlchemy model |
| 4 | `social-data-collector/src/social_data_collector/persistence/repository.py` | Modify | Add `upsert_post`, `list_posts` |
| 5 | `social-data-collector/src/social_data_collector/clients/facebook.py` | Modify | Extend with `fetch_page_posts` |
| 6 | `social-data-collector/src/social_data_collector/clients/tiktok.py` | Modify | Add `fetch_user_videos` |
| 7 | `social-data-collector/src/social_data_collector/clients/youtube.py` | Modify | Extend to also write to `posts` |
| 8 | `social-data-collector/src/social_data_collector/normalizers/facebook_post.py` | Create | Normalise Facebook post → PostModel |
| 9 | `social-data-collector/src/social_data_collector/normalizers/tiktok_post.py` | Create | Normalise TikTok video → PostModel |
| 10 | `social-data-collector/src/social_data_collector/scheduler/tasks.py` | Modify | Call post fetch + upsert after subject sync |
| 11 | `social-api-gateway/src/social_api_gateway/subjects/models.py` | Modify | Add `PostModel` read-only mirror |
| 12 | `social-api-gateway/src/social_api_gateway/subjects/repository.py` | Modify | Add `list_posts` method |
| 13 | `social-api-gateway/src/social_api_gateway/subjects/routes.py` | Modify | Add `GET /{subject_id}/posts` endpoint |
| 14 | `social-api-gateway/src/social_api_gateway/subjects/schemas.py` | Modify | Add `PostListResponse`, `PostResponse` |
| 15 | `social-api-gateway/scripts/export_openapi.py` | Modify | Regenerate OpenAPI (automatic) |
| 16 | `social-mini-app/src/api/types.ts` | Regenerate | From OpenAPI spec |
| 17 | `social-mini-app/src/api/hooks.ts` | Modify | Add `usePosts` hook |
| 18 | `social-mini-app/src/components/panels/ContentPerformancePanel.tsx` | Create | Top posts panel |
| 19 | `social-mini-app/src/components/charts/PostEngagementSparkline.tsx` | Create | Mini engagement bar chart |
| 20 | `social-mini-app/src/components/subject/PostCard.tsx` | Create | Reusable post card |
| 21 | `social-mini-app/src/pages/Subjects/SubjectDetail.tsx` | Modify | Integrate ContentPerformancePanel |
| 22 | `social-mini-app/src/pages/Subjects/YouTubeEngagementPanel.tsx` | Modify | Add engagement_rate to video cards |

## Failure Scenarios

| Scenario | Detection | Impact | Mitigation |
|---|---|---|---|
| **Facebook API returns empty posts list** | `fetch_page_posts` returns `[]` | User sees "No posts yet" | Log warning; show empty state with "First sync may not have captured posts yet" |
| **Facebook API rate limit on post fetch** | HTTP 429 from Graph API | Posts section missing | Skip post fetch for this sync cycle; subject sync still succeeds. Retry next scheduled sync. |
| **TikTok API/scraper returns malformed video data** | KeyError in normaliser | Post not stored | Wrap normaliser in try/except; log error with raw payload; continue to next post. |
| **Engagement rate divide-by-zero** | `view_count == 0` and `followers == 0` | `NaN` in database | Guard: if denominator == 0, set `engagement_rate = 0.0`. |
| **Duplicate post rows** | Violation of unique constraint | 500 error on upsert | Use `INSERT ... ON CONFLICT (subject_id, platform_post_id) DO UPDATE` (PostgreSQL) or SQLAlchemy's `on_conflict_do_update`. |
| **Facebook post caption exceeds Text column** | String length > 2000 | Truncation or error | Truncate caption to 2000 chars in normaliser before insert. |
| **Mini App shows stale engagement after sync** | Cache hit in React Query | Old engagement numbers | Invalidate `posts` query key on successful sync mutation in `useTriggerSync`. |

## Testing Strategy

### Unit Tests

- **Collector normalisers:** `tests/normalizers/test_facebook_post.py` — fixtures with real Facebook Graph API post JSON; verify correct field mapping and engagement rate formula.
- **Collector repository:** `tests/persistence/test_repository.py` — test `upsert_post` idempotency (same `platform_post_id` updates, not duplicates).
- **Gateway routes:** `tests/subjects/test_routes.py` — mock DB to return posts; verify response envelope shape, pagination, sorting.

### Integration Tests

- **Collector live Facebook:** `RUN_INTEGRATION=1 pytest -m integration` — verify `fetch_page_posts` returns non-empty list for test page.
- **End-to-end:** Trigger sync → verify `GET /v1/subjects/{id}/posts` returns data within 60 seconds.

### Mini App Tests

- `npm run lint && npm run typecheck && npm run build` — no TS errors.
- Manual: Open Subject Detail → verify Post cards render with correct engagement rate formatting.

## Rollout Plan

### Phase 1: Schema & Migration (Day 1-2)
1. Add `Post` schema to `social-common`.
2. Create migration in `social-data-collector` for `posts` table.
3. Add `PostModel` to collector persistence layer.

### Phase 2: Collector Implementation (Day 3-5)
1. Implement `fetch_page_posts` for Facebook + normaliser.
2. Implement TikTok video fetch + normaliser.
3. Extend YouTube sync to also write `posts`.
4. Wire into Celery sync tasks.
5. Run `alembic upgrade head` + seed test data.

### Phase 3: Gateway API (Day 6-7)
1. Add `PostModel` mirror + repository method.
2. Add `/posts` endpoint.
3. Regenerate OpenAPI + `types.ts`.

### Phase 4: Mini App UI (Day 8-10)
1. Add `usePosts` hook.
2. Build `PostCard` + `ContentPerformancePanel`.
3. Integrate into `SubjectDetailPage`.
4. Update YouTube video cards with engagement rate.

### Phase 5: Verification (Day 11)
1. Run full test suite: `ruff`, `mypy`, `pytest` for all Python packages.
2. Run Mini App build.
3. Manual end-to-end: trigger sync → verify posts appear in Mini App.

## Open Questions

1. **Facebook Graph API permissions:** Does the current access token have `pages_read_engagement` or `read_insights` permission? Without it, we may not get `reactions.summary(total_count)`. Need to verify in `scripts/crawl_facebook.py` test.
2. **TikTok API source:** Is TikTok data coming from the official Research API, an unofficial API, or a scraper? The `fetch_user_videos` implementation depends heavily on this.
3. **YouTube duplication:** Writing `Video` data to both `videos` and `posts` tables is denormalised. Is this acceptable, or should we migrate `Video` to be a view on `posts`? For simplicity, denormalisation is acceptable at this scale.
4. **Media type mapping:** Facebook "attachments" can be complex (single image, multiple images, video, link, share). Should we normalise all to `image` / `video` / `carousel` / `link`? Recommend simple mapping in normaliser.
5. **Post fetch volume:** How many recent posts should we fetch per sync? 25? 50? All? Recommend 25 most recent to limit API calls; older posts can be fetched on first sync via pagination.

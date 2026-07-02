# Feature Spec: Social Listening Lite — Comment Volume & Sentiment

## Overview

Extend monitoring from **account-level metrics** and **post-level engagement** down to **audience reactions** by collecting comments on tracked posts and performing lightweight sentiment classification. This is the first step toward social listening — a capability present in every major platform: Hootsuite's "Lumen" monitors brand mentions and sentiment, Sprout Social has "Listening" with sentiment analysis, and Brandwatch is built entirely on consumer intelligence. Our "Lite" version is deliberately scoped: we only collect comments on posts already owned by tracked subjects (not the entire platform), use simple keyword-based sentiment (not ML/NLP), and surface comment volume trends and sentiment ratios.

## Goals

- [ ] Collector collects **top-level comments** from Facebook posts and YouTube videos during sync (platform APIs permitting).
- [ ] New `comments` table: `post_id`, `platform_comment_id`, `author`, `content`, `published_at`, `like_count`, `sentiment` ("positive" | "negative" | "neutral").
- [ ] Sentiment classification is **keyword-based** (not ML):
  - Positive keywords: "good", "great", "awesome", "love", "best", "thanks", "nice", "happy", "excellent"
  - Negative keywords: "bad", "terrible", "hate", "worst", "awful", "disappointed", "poor", "sad", "angry"
  - Score: count(positive) - count(negative). Score > 0 → "positive", < 0 → "negative", else "neutral".
- [ ] Gateway exposes:
  - `GET /v1/subjects/{id}/comments` — paginated comments for a subject
  - `GET /v1/subjects/{id}/sentiment` — aggregated sentiment snapshot: `{ positive_count, negative_count, neutral_count, total_comments, sentiment_ratio }`
- [ ] Mini App shows:
  - **Sentiment pie chart** in Subject Detail (3 segments: positive/negative/neutral)
  - **Comment volume sparkline** (comments per day over last 30 days)
  - **Recent comments** section (top 5 most-liked comments, with sentiment badge)
  - **Comment spike alert** (Feature 3 extension): new rule type `COMMENT_SPIKE` fires when comment volume > baseline + 2σ

## Non-Goals

- **We do NOT perform ML/NLP sentiment analysis.** No BERT, no LLM calls. Keyword matching is fast, deterministic, and sufficient for "Lite" positioning.
- **We do NOT monitor the entire platform for mentions.** We only collect comments on posts already fetched for tracked subjects. True social listening (tracking any mention of a brand anywhere) requires firehose APIs (Twitter/X, Reddit, etc.) and is out of scope.
- **We do NOT collect replies-to-comments (nested threads).** Only top-level comments. Nested thread analysis is too complex for MVP.
- **We do NOT support comment moderation.** No delete, hide, or reply actions. Read-only.
- **We do NOT track comment author history.** Author names are stored as strings, not linked to profiles or historical comment counts.
- **We do NOT build a full social inbox.** Unified inbox with DMs, mentions, reviews is out of scope (see Hootsuite Nest / Sprout Smart Inbox for comparison).

## Architecture

### Data Model Changes

#### New Table: `comments`

Owned by `social-data-collector`.

| Column | Type | Constraints | Notes |
|---|---|---|---|
| `id` | `UUID` | PK | |
| `subject_id` | `UUID` | FK → `subjects.id`, `ON DELETE CASCADE` | Denormalised for easy querying |
| `post_id` | `UUID` | FK → `posts.id`, `ON DELETE CASCADE` | Which post this comment belongs to |
| `platform_comment_id` | `String(255)` | NOT NULL | Native comment ID |
| `platform` | `Enum(Platform)` | NOT NULL | |
| `author` | `String(255)` | nullable | Commenter name (may be "Anonymous" or empty) |
| `content` | `Text` | nullable | Comment text (truncated to 2000 chars) |
| `published_at` | `TimestampTZ` | NOT NULL | When comment was posted |
| `like_count` | `Integer` | NOT NULL, default 0 | Comment likes/reactions |
| `sentiment` | `Enum('positive', 'negative', 'neutral')` | NOT NULL, default 'neutral' | Computed on insert |
| `last_synced_at` | `TimestampTZ` | NOT NULL | |
| `created_at` | `TimestampTZ` | NOT NULL | |

**Unique constraint:** `UNIQUE(post_id, platform_comment_id)` — idempotent upsert.

**Indexes:**
- `CREATE INDEX idx_comments_subject ON comments(subject_id, published_at DESC);`
- `CREATE INDEX idx_comments_sentiment ON comments(subject_id, sentiment, published_at DESC);`

### Service Interactions

```
┌─────────────────────────────┐
│ social-data-collector       │
│  (sync cycle)               │
│                             │
│  ┌───────────────────────┐  │
│  │ 1. Fetch posts      │  │── Feature 1 pipeline
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 2. Fetch comments    │  │── Facebook: /{post-id}/comments
│  │    per post          │  │── YouTube: /commentThreads?videoId=...
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 3. Classify sentiment│  │── Keyword matching
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 4. Upsert comments   │  │── INSERT ... ON CONFLICT
│  └───────────────────────┘  │
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-api-gateway          │
│  /v1/subjects/{id}/comments│── Paginated comments
│  /v1/subjects/{id}/sentiment│── Aggregated sentiment
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-alert-engine         │
│  COMMENT_SPIKE rule         │── Evaluate comment volume baseline
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-mini-app             │
│  SentimentPieChart           │
│  CommentVolumeSparkline      │
│  RecentCommentsPanel         │
└─────────────────────────────┘
```

### API Contract

#### `GET /v1/subjects/{subject_id}/comments`

```yaml
parameters:
  page: int (default 1)
  limit: int (default 20, max 100)
  sentiment: enum ["positive", "negative", "neutral"] | null
  sort_by: enum ["published_at", "like_count"] (default "published_at")

response: CommentListResponse
  data: Comment[]
  meta: { page, limit, total }
```

**`Comment` schema:**
```json
{
  "id": "...",
  "post_id": "...",
  "author": "Jane Doe",
  "content": "Great video! Love the tips.",
  "published_at": "2024-01-15T14:30:00Z",
  "like_count": 12,
  "sentiment": "positive"
}
```

#### `GET /v1/subjects/{subject_id}/sentiment`

```yaml
response: SentimentResponse
  data: {
    "positive_count": 45,
    "negative_count": 8,
    "neutral_count": 27,
    "total_comments": 80,
    "sentiment_ratio": 0.56,  // positive / total
    "daily_trend": [
      { "date": "2024-01-01", "positive": 3, "negative": 1, "neutral": 2 },
      ...
    ]
  }
```

## Code Changes

### 1. `social-common` — Schema

**File:** `social_common/schemas.py`

```python
class Comment(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID
    post_id: UUID
    platform_comment_id: str
    platform: Platform
    author: str | None = None
    content: str | None = None
    published_at: datetime
    like_count: int = Field(ge=0, default=0)
    sentiment: str = Field(pattern=r"^(positive|negative|neutral)$", default="neutral")
    last_synced_at: datetime
    created_at: datetime = Field(default_factory=_utcnow)

class SentimentSnapshot(BaseModel):
    """Aggregated sentiment for a subject at a point in time."""
    positive_count: int
    negative_count: int
    neutral_count: int
    total_comments: int
    sentiment_ratio: float  # positive / total
    daily_trend: list[DailySentiment]

class DailySentiment(BaseModel):
    date: str  # "2024-01-15"
    positive: int
    negative: int
    neutral: int
```

### 2. `social-data-collector` — Comment Collection

**File:** `src/social_data_collector/persistence/models.py` (modify)

- Add `CommentModel` SQLAlchemy model.

**File:** `src/social_data_collector/persistence/repository.py` (modify)

- Add `upsert_comment(comment: CommentModel)` — idempotent upsert.
- Add `list_comments(subject_id, sentiment, limit, offset)`.
- Add `get_sentiment_aggregates(subject_id, since)` — returns counts grouped by sentiment and date.

**File:** `src/social_data_collector/clients/facebook.py` (modify)

```python
async def fetch_post_comments(self, post_id: str, limit: int = 25) -> list[dict]:
    """Fetch top-level comments for a Facebook post."""
    url = f"/{post_id}/comments"
    params = {
        "fields": "id,from{name},message,created_time,like_count",
        "limit": limit,
    }
    # ... existing client pattern ...
```

**Risk:** Facebook Graph API v18+ requires `pages_read_user_content` permission to read post comments. Without it, comments are inaccessible. We must handle 403 gracefully.

**File:** `src/social_data_collector/clients/youtube.py` (modify)

```python
async def fetch_video_comments(self, video_id: str, limit: int = 100) -> list[dict]:
    """Fetch top-level comments for a YouTube video via commentThreads.list."""
    url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "maxResults": min(limit, 100),  # YouTube API max is 100
        "order": "time",  # newest first
    }
    # Map snippet.topLevelComment.snippet.{authorDisplayName, textDisplay, publishedAt, likeCount}
```

**File:** `src/social_data_collector/sentiment.py` (new)

```python
POSITIVE_WORDS = {
    "good", "great", "awesome", "love", "best", "thanks", "nice", "happy",
    "excellent", "amazing", "wonderful", "perfect", "fantastic", "brilliant",
    "helpful", "useful", "informative", "top", "cool", "super", "lovely",
}

NEGATIVE_WORDS = {
    "bad", "terrible", "hate", "worst", "awful", "disappointed", "poor",
    "sad", "angry", "useless", "boring", "annoying", "horrible", "trash",
    "waste", "fail", "broken", "slow", "difficult", "confusing",
}


def classify_sentiment(text: str | None) -> str:
    """Return 'positive', 'negative', or 'neutral' based on keyword counts.

    Case-insensitive. Non-English comments default to 'neutral' unless keywords match.
    """
    if not text:
        return "neutral"
    
    words = set(re.findall(r"\b\w+\b", text.lower()))
    pos_score = len(words & POSITIVE_WORDS)
    neg_score = len(words & NEGATIVE_WORDS)
    
    if pos_score > neg_score:
        return "positive"
    if neg_score > pos_score:
        return "negative"
    return "neutral"
```

**File:** `src/social_data_collector/scheduler/tasks.py` (modify)

- After upserting posts, iterate posts and fetch comments:
```python
for post in posts:
    try:
        if subject.platform == Platform.FACEBOOK:
            raw_comments = await facebook_client.fetch_post_comments(post.platform_post_id)
        elif subject.platform == Platform.YOUTUBE:
            raw_comments = await youtube_client.fetch_video_comments(post.platform_video_id)
        else:
            continue
        
        for raw in raw_comments:
            comment = CommentModel(
                subject_id=subject.id,
                post_id=post.id,
                # ... map fields ...
                sentiment=classify_sentiment(raw.get("message", "")),
                last_synced_at=_utcnow(),
            )
            await comment_repo.upsert(comment)
    except Exception:
        logger.exception("comments.fetch_failed", post_id=post.platform_post_id)
        continue  # Don't fail the whole sync because comments failed
```

### 3. `social-api-gateway` — Comment API

**File:** `src/social_api_gateway/subjects/routes.py` (modify)

- Add `GET /{subject_id}/comments` endpoint.
- Add `GET /{subject_id}/sentiment` endpoint.

**File:** `src/social_api_gateway/subjects/repository.py` (modify)

- Add `list_comments` and `get_sentiment_aggregates` methods.

**File:** `src/social_api_gateway/subjects/schemas.py` (modify)

- Add `CommentListResponse`, `SentimentResponse` envelopes.

### 4. `social-alert-engine` — COMMENT_SPIKE Rule

**File:** `src/social_alert_engine/evaluator.py` (modify)

```python
if rule.rule_type == AlertRuleType.COMMENT_SPIKE:
    # Requires comment count time-series. We don't have a hypertable for this.
    # Option A: Compute from comments table (slower but no schema change)
    # Option B: Create a comment_snapshots hypertable (overkill for Lite)
    # Recommend Option A for MVP.
    
    recent_counts = await repo.get_daily_comment_counts(subject_id, window_hours=rule.baseline_window_hours)
    if len(recent_counts) < rule.baseline_min_snapshots:
        return None
    
    mean = statistics.mean(recent_counts)
    std_dev = statistics.stdev(recent_counts) if len(recent_counts) > 1 else 0.0
    latest_count = recent_counts[-1]
    
    if latest_count > mean + rule.threshold * std_dev:
        return {
            "triggered": True,
            "metric_value": latest_count,
            "threshold": mean + rule.threshold * std_dev,
            "baseline_value": mean,
            "std_dev": std_dev,
            "message": f"Comment spike: {latest_count} comments (baseline: {mean:.1f} ± {std_dev:.1f})",
        }
```

### 5. `social-mini-app` — Sentiment UI

**File:** `src/api/hooks.ts`

```typescript
export function useComments(subjectId: string, sentiment?: string) {
  return useQuery({
    queryKey: ["comments", subjectId, sentiment],
    queryFn: () => apiGet<Comment[]>(`/v1/subjects/${subjectId}/comments`, { sentiment, limit: 5 }),
    enabled: !!subjectId,
  });
}

export function useSentiment(subjectId: string) {
  return useQuery({
    queryKey: ["sentiment", subjectId],
    queryFn: () => apiGet<SentimentSnapshot>(`/v1/subjects/${subjectId}/sentiment`),
    enabled: !!subjectId,
  });
}
```

**File:** `src/components/charts/SentimentPieChart.tsx` (new)

```tsx
// Small donut chart: 3 segments
// Green = positive, Red = negative, Grey = neutral
// Center text: "80% positive" or total comment count
// No legend needed — colors are intuitive
```

**File:** `src/components/charts/CommentVolumeSparkline.tsx` (new)

```tsx
// Line sparkline: 30 data points (daily comment count)
// Fill area under line with light accent color
// Tooltip on tap shows "Jan 15: 12 comments"
```

**File:** `src/components/panels/RecentCommentsPanel.tsx` (new)

```tsx
// List of 5 most-liked comments
// Each row: Author name | Sentiment badge (green/red/grey dot) | Like count | Content (2-line clamp)
// Tap row → expand to full content
```

**File:** `src/pages/Subjects/SubjectDetail.tsx` (modify)

- Add "Comments" section below Sync History:
  - `SentimentPieChart` + `CommentVolumeSparkline` side by side (or stacked)
  - `RecentCommentsPanel` below

## Interface Changes (UI/UX)

### New Components

| Component | Description |
|---|---|
| `SentimentPieChart` | Donut chart: positive/negative/neutral ratios |
| `CommentVolumeSparkline` | 30-day daily comment count line chart |
| `RecentCommentsPanel` | Top 5 most-liked comments with sentiment badges |

### Modified Screens

| Screen | Change |
|---|---|
| `SubjectDetailPage` | Add Comments section with sentiment + volume + recent comments |

### Design Notes (Mobile-First)

- **Sentiment pie chart is small.** 120px diameter is enough on mobile. Use thick segments (donut, not thin pie) for readability.
- **Sparkline is inline.** 40px height, full width. No axes, just the shape.
- **Comments are cards.** Each comment is a card with author, content, and a small sentiment dot. No avatars (we don't have profile images for commenters).
- **Hide if no comments.** If a subject has 0 comments, show "No comments collected yet" with a note about API permissions.
- **Tap to expand.** Long comments are truncated to 3 lines; tap to expand in place.

## Files Relevant (Complete List)

| # | File | Action | Description |
|---|---|---|---|
| 1 | `social-common/social_common/schemas.py` | Modify | Add `Comment`, `SentimentSnapshot`, `DailySentiment` |
| 2 | `social-data-collector/migrations/versions/` | Create | Migration: `comments` table |
| 3 | `social-data-collector/src/social_data_collector/persistence/models.py` | Modify | Add `CommentModel` |
| 4 | `social-data-collector/src/social_data_collector/persistence/repository.py` | Modify | Add `upsert_comment`, `list_comments`, `get_sentiment_aggregates` |
| 5 | `social-data-collector/src/social_data_collector/clients/facebook.py` | Modify | Add `fetch_post_comments` |
| 6 | `social-data-collector/src/social_data_collector/clients/youtube.py` | Modify | Add `fetch_video_comments` |
| 7 | `social-data-collector/src/social_data_collector/sentiment.py` | Create | `classify_sentiment` keyword classifier |
| 8 | `social-data-collector/src/social_data_collector/scheduler/tasks.py` | Modify | Fetch + classify + upsert comments after post sync |
| 9 | `social-api-gateway/src/social_api_gateway/subjects/repository.py` | Modify | Add `list_comments`, `get_sentiment_aggregates` |
| 10 | `social-api-gateway/src/social_api_gateway/subjects/routes.py` | Modify | Add `GET /{id}/comments` and `GET /{id}/sentiment` |
| 11 | `social-api-gateway/src/social_api_gateway/subjects/schemas.py` | Modify | Add `CommentListResponse`, `SentimentResponse` |
| 12 | `social-alert-engine/src/social_alert_engine/evaluator.py` | Modify | Add `COMMENT_SPIKE` rule evaluation |
| 13 | `social-alert-engine/src/social_alert_engine/repository.py` | Modify | Add `get_daily_comment_counts` |
| 14 | `social-api-gateway/scripts/export_openapi.py` | Modify | Regenerate |
| 15 | `social-mini-app/src/api/types.ts` | Regenerate | From OpenAPI |
| 16 | `social-mini-app/src/api/hooks.ts` | Modify | Add `useComments`, `useSentiment` |
| 17 | `social-mini-app/src/components/charts/SentimentPieChart.tsx` | Create | Donut sentiment chart |
| 18 | `social-mini-app/src/components/charts/CommentVolumeSparkline.tsx` | Create | 30-day comment volume line |
| 19 | `social-mini-app/src/components/panels/RecentCommentsPanel.tsx` | Create | Top 5 comments list |
| 20 | `social-mini-app/src/pages/Subjects/SubjectDetail.tsx` | Modify | Add Comments section |

## Failure Scenarios

| Scenario | Detection | Impact | Mitigation |
|---|---|---|---|
| **Facebook API denies comment access** | HTTP 403 on `/comments` endpoint | No comments collected | Log warning; show "Comment access restricted" in UI; continue sync without failing |
| **YouTube API quota exceeded** | HTTP 429 or quota error | Comment collection skipped | Skip comment fetch; log quota warning; subject sync still succeeds |
| **Comment text is non-English** | No keyword matches | Classified as "neutral" | Acceptable for MVP; add language detection later if needed |
| **Sarcasm / negation** | "Not bad" contains "bad" | Misclassified as negative | Known limitation of keyword approach; document it. Future: upgrade to ML |
| **Comment table grows large** | 100k+ comments per popular subject | Slow queries | Add partitioning by `subject_id` or time-based pruning (keep 90 days). Defer optimisation. |
| **Feature 1 not yet shipped** | `posts` table missing | Cannot fetch comments | Blocker: Feature 1 must ship first. Comments are fetched per-post. |
| **TikTok comments** | TikTok API does not provide comment access via current integration | No TikTok comments | Skip TikTok comment fetch; only collect for Facebook + YouTube. Document limitation. |
| **Privacy: comment contains PII** | Email/phone in comment text | Stored in database | Sanitise `content` field: regex scrub for email, phone, URLs before storage |

## Testing Strategy

### Unit Tests (Collector)

- **Sentiment classification:**
  - "This is great and awesome!" → positive (2 positive, 0 negative)
  - "Terrible and awful experience" → negative (0 positive, 2 negative)
  - "The video is 10 minutes long" → neutral (0 positive, 0 negative)
  - "Not bad" → negative (contains "bad"; 0 positive, 1 negative) — document known limitation
- **Comment upsert:** Test idempotency with same `platform_comment_id`.

### Integration Tests

- Use Facebook test page with public comments.
- Use YouTube test video with comments enabled.
- Verify `/v1/subjects/{id}/sentiment` returns correct counts.

### Alert Engine Tests

- Insert 7 days of comment counts: `[5, 6, 5, 7, 6, 5, 6]` → mean=5.7, σ≈0.76
- Latest count = 12 → 12 > 5.7 + 2×0.76 = 7.22 → COMMENT_SPIKE fires.

### Mini App Tests

- `npm run lint && npm run typecheck && npm run build`.
- Manual: Sentiment pie chart renders; comment list shows sentiment badges.

## Rollout Plan

### Phase 1: Schema & Migration (Day 1)
1. Add `Comment`, `SentimentSnapshot` schemas to `social-common`.
2. Create collector migration for `comments`.
3. Add `CommentModel`.

### Phase 2: Collector Comment Pipeline (Day 2-3)
1. Implement `fetch_post_comments` for Facebook + YouTube.
2. Implement `classify_sentiment` with tests.
3. Add repository methods.
4. Wire into Celery sync tasks (after post upsert).
5. Handle 403/429 gracefully.

### Phase 3: Gateway API (Day 4)
1. Add `list_comments` and `get_sentiment_aggregates`.
2. Add endpoints.
3. Regenerate OpenAPI.

### Phase 4: Alert Engine (Day 5)
1. Add `COMMENT_SPIKE` rule evaluation.
2. Add `get_daily_comment_counts` repository method.

### Phase 5: Mini App (Day 6-7)
1. Add hooks.
2. Build `SentimentPieChart`, `CommentVolumeSparkline`, `RecentCommentsPanel`.
3. Integrate into `SubjectDetailPage`.

### Phase 6: Verification (Day 8)
1. Run all test suites.
2. Manual: verify comments appear after sync; sentiment classification is plausible.

## Open Questions

1. **Facebook comment permissions:** Does the current Facebook app have `pages_read_user_content` permission? Without it, `/comments` returns empty or 403. Need to verify before implementation.
2. **YouTube comment quota:** YouTube Data API has a 10,000 unit daily quota. `commentThreads.list` costs ~1 unit per call. With 100 subjects × 10 videos × daily sync = 1000 units/day. Within quota, but need monitoring.
3. **Comment depth:** Should we collect **all** comments per post or cap at top N (e.g. 50 most recent)? Cap at 50 to limit API calls and storage. Document: "Top 50 most recent comments per post are tracked."
4. **Sentiment keyword list expansion:** Should keywords be configurable per subject/platform? Not for MVP. A single global list is fine. Can be moved to config later.
5. **Multi-language support:** The keyword list is English-only. If subjects have non-English audiences, sentiment will always be "neutral". Should we document this prominently? Yes — add a note in UI: "Sentiment analysis currently supports English comments only."
6. **Privacy & GDPR:** Storing user-generated comments (even public ones) may have compliance implications. Comments are public data, but we should have a data retention policy. Recommend 90-day retention for comments, same as sync logs.

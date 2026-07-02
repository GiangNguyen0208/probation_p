# Feature Spec: AI-Powered Insights Summary

## Overview

Integrate a **Large Language Model (LLM)** to generate natural-language summaries of subject performance, transforming raw metrics into actionable narratives. This is the bleeding-edge capability that distinguishes modern social media platforms: Hootsuite's "Wisdom" (Social-first AI) generates captions, summarises data, and detects trends; Sprout Social embeds AI in premium analytics for contextual insights; and Sendible has "AI Assist" for content optimisation. Our "AI Insights" feature is deliberately scoped as a **read-only summarisation layer** — it consumes collected data (subjects, posts, snapshots, alerts) and produces concise, human-readable insights delivered via the Mini App and optionally via Telegram. It does not write data, schedule posts, or make autonomous decisions.

## Goals

- [ ] Backend integrates with an **LLM API** (OpenAI GPT-4o / Anthropic Claude / Google Gemini) via HTTP client (`httpx`).
- [ ] `InsightsService` constructs structured prompts from database queries and sends them to the LLM with **caching** (1-24h TTL) to reduce API costs.
- [ ] Two insight types:
  - **Weekly Subject Summary:** "TikTok grew 15% this week, driven by 3 viral videos. Facebook engagement dropped 8% — consider posting more frequently."
  - **Anomaly Explanation:** "Follower drop on Jan 15 coincides with no posts for 3 days. Previous pattern: consistent daily posting maintained growth."
- [ ] Mini App shows:
  - **AI Insights card** on Dashboard (top-level summary across all subjects)
  - **AI Insights card** on Subject Detail (subject-specific narrative)
  - **"Generate Insight" button** for on-demand one-off summaries
- [ ] Telegram delivery: insights can be included in automated reports (Feature 4) as a "🤖 AI Summary" section.
- [ ] **Fallback:** If LLM API is unavailable or returns an error, show a template-based summary (pre-computed text using simple rules) instead of failing.

## Non-Goals

- **We do NOT use AI for decision-making.** AI only generates text summaries; it does not create alert rules, adjust thresholds, trigger syncs, or modify any data.
- **We do NOT fine-tune a model.** We use off-the-shelf LLM APIs with prompt engineering only. Fine-tuning is expensive and out of scope.
- **We do NOT generate content (captions, posts).** AI Assist for content creation is a separate feature space. We only summarise existing data.
- **We do NOT stream responses.** Full response is generated and cached before display. No real-time streaming tokens.
- **We do NOT implement multi-modal AI.** No image/video analysis. Text-only insights from structured data.
- **We do NOT expose raw LLM output without sanitisation.** Responses are validated for length, content safety, and formatting before display.

## Architecture

### Data Model Changes

**No new tables required** if we cache in Redis only. If we want persistent audit history, add optional `ai_insights` table:

#### Optional Table: `ai_insights`

| Column | Type | Notes |
|---|---|---|
| `id` | `UUID` | PK |
| `subject_id` | `UUID` | FK, nullable (null = global/dashboard insight) |
| `insight_type` | `String` | "weekly_summary" | "anomaly_explanation" | "on_demand" |
| `prompt_hash` | `String(64)` | SHA-256 of prompt for cache invalidation |
| `generated_text` | `Text` | LLM output |
| `model_used` | `String` | "gpt-4o", "claude-3.5-sonnet", etc. |
| `generated_at` | `TimestampTZ` | |
| `created_at` | `TimestampTZ` | |

**Decision:** Start with **Redis-only caching** (no table). Add table later if users request insight history.

### Service Interactions

```
┌─────────────────────────────┐
│ social-mini-app             │
│  AIInsightsCard             │◄── GET /v1/insights?subject_id=&type=
│  GenerateInsightButton      │◄── POST /v1/insights/generate (bypass cache)
└─────────────────────────────┘
         │
         ▼
┌─────────────────────────────┐
│ social-api-gateway          │
│  InsightsService            │
│                             │
│  ┌───────────────────────┐  │
│  │ 1. Check Redis cache  │  │── cache hit? → return cached text
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 2. Query DB          │  │── Fetch snapshots, posts, alerts
│  │    (data context)     │  │
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 3. Build prompt      │  │── Structured prompt with data
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 4. Call LLM API      │  │── POST https://api.openai.com/v1/chat/completions
│  │    (httpx)           │  │
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 5. Parse & validate   │  │── Check length, extract text
│  │    response           │  │
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 6. Cache in Redis    │  │── TTL 24h for weekly, 1h for on-demand
│  │    + return          │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

### Prompt Engineering

#### Weekly Subject Summary Prompt

```
You are a social media analyst. Summarise the performance of a monitored social media account based on the following data. Write 2-3 concise sentences in a friendly, professional tone. Highlight the most significant change and provide one actionable recommendation.

Platform: {platform}
Subject: {subject_name}
Period: Last 7 days ({from_date} to {to_date})

Metrics:
- Followers: {followers_start} → {followers_end} ({growth_pct}% change)
- Posts published: {post_count}
- Average engagement rate: {avg_engagement}%
- Most engaged post: "{top_post_caption}" ({top_post_engagement}% engagement)
- Alerts fired: {alert_count} ({alert_types})

Recommendations should be specific and based on the data. Do not invent facts not in the data. If growth is flat, suggest why. If engagement is high, identify what worked.

Summary:
```

#### Anomaly Explanation Prompt

```
You are a social media analyst. Explain an unusual metric change for a monitored account. The user wants to understand WHY a spike or drop occurred.

Platform: {platform}
Subject: {subject_name}
Metric: {metric_name}
Change: {metric_before} → {metric_after} ({change_pct}%)
Date of change: {change_date}

Context (7 days before and after):
{time_series_data}

Posts around this date:
{recent_posts}

Provide a 1-2 sentence explanation. Be factual. If the cause is unclear, say so. Do not speculate beyond the data.

Explanation:
```

### API Contract

#### `GET /v1/insights`

```yaml
parameters:
  subject_id: UUID | null  # If null, dashboard-level summary across all subjects
  type: enum ["weekly_summary", "anomaly_explanation"] (default "weekly_summary")
  force_refresh: bool (default false)  # Bypass cache

response: InsightResponse
  data: {
    "generated_text": "TikTok grew 15% this week...",
    "generated_at": "2024-01-15T10:00:00Z",
    "model_used": "gpt-4o",
    "cached": false,
    "fallback_used": false
  }
```

#### `POST /v1/insights/generate` (on-demand)

Same parameters but always bypasses cache. Returns 202 Accepted if async generation is used, or 200 if synchronous.

## Code Changes

### 1. `social-common` — Schema

**File:** `social_common/schemas.py`

```python
class AIInsight(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    generated_text: str
    generated_at: datetime
    model_used: str
    cached: bool
    fallback_used: bool
```

### 2. `social-api-gateway` — Insights Service

**File:** `src/social_api_gateway/insights/__init__.py` (new package)

**File:** `src/social_api_gateway/insights/service.py` (new)

```python
import hashlib
import json
from datetime import UTC, datetime, timedelta

import httpx
from social_common.schemas import AIInsight

from ..config import get_settings
from ..logging_setup import get_logger

logger = get_logger("social_api_gateway.insights")


class InsightsService:
    def __init__(self, db: AsyncSession, cache: CacheService, http_client: httpx.AsyncClient):
        self.db = db
        self.cache = cache
        self.http = http_client
        self.settings = get_settings()

    async def generate_weekly_summary(self, subject_id: UUID | None) -> AIInsight:
        cache_key = self._cache_key("weekly_summary", subject_id)
        
        if not self.settings.insights.force_refresh:
            cached = await self.cache.get(cache_key)
            if cached:
                return AIInsight.model_validate({**cached, "cached": True, "fallback_used": False})
        
        # Gather data
        data = await self._gather_weekly_data(subject_id)
        prompt = self._build_weekly_prompt(data)
        
        try:
            text = await self._call_llm(prompt)
            insight = AIInsight(
                generated_text=text,
                generated_at=datetime.now(UTC),
                model_used=self.settings.insights.model,
                cached=False,
                fallback_used=False,
            )
            await self.cache.set(cache_key, insight.model_dump(mode="json"), ttl_seconds=86_400)
            return insight
        except Exception:
            logger.exception("llm.failed", subject_id=str(subject_id))
            fallback = self._fallback_weekly_summary(data)
            return AIInsight(
                generated_text=fallback,
                generated_at=datetime.now(UTC),
                model_used="fallback-template",
                cached=False,
                fallback_used=True,
            )

    async def _call_llm(self, prompt: str) -> str:
        """Call OpenAI/Anthropic API."""
        settings = self.settings.insights
        
        if settings.provider == "openai":
            response = await self.http.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {settings.api_key}"},
                json={
                    "model": settings.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.7,
                },
                timeout=30.0,
            )
            response.raise_for_status()
            body = response.json()
            return body["choices"][0]["message"]["content"].strip()
        
        elif settings.provider == "anthropic":
            response = await self.http.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.api_key,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model": settings.model,
                    "max_tokens": 300,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30.0,
            )
            response.raise_for_status()
            body = response.json()
            return body["content"][0]["text"].strip()
        
        else:
            raise ValueError(f"Unknown LLM provider: {settings.provider}")

    def _fallback_weekly_summary(self, data: dict) -> str:
        """Template-based summary when LLM is unavailable."""
        lines = [
            f"**{data['subject_name']}** on **{data['platform']}** — Last 7 days:",
            f"- Followers: {data['followers_start']} → {data['followers_end']} ({data['growth_pct']}%)",
            f"- Posts: {data['post_count']}",
            f"- Avg engagement: {data['avg_engagement']}%",
        ]
        if data["growth_pct"] > 10:
            lines.append("📈 Strong growth this week. Keep up the momentum!")
        elif data["growth_pct"] < -5:
            lines.append("📉 Growth declined. Consider increasing posting frequency.")
        else:
            lines.append("➡️ Steady performance. No major changes.")
        return "\n".join(lines)

    def _cache_key(self, insight_type: str, subject_id: UUID | None) -> str:
        return f"cache:insights:{insight_type}:{subject_id or 'global'}:{datetime.now(UTC).strftime('%Y%m%d')}"
```

**File:** `src/social_api_gateway/insights/routes.py` (new)

```python
router = APIRouter(prefix="/v1/insights", tags=["insights"])

@router.get("", response_model=InsightResponse)
async def get_insight(
    subject_id: UUID | None = Query(None),
    type_: str = Query("weekly_summary", alias="type"),
    force_refresh: bool = Query(False),
    api_key: APIKeyModel = Depends(rate_limit),
    db: AsyncSession = Depends(get_db_session),
    cache: CacheService = Depends(get_cache_service),
    http_client: httpx.AsyncClient = Depends(get_http_client),
) -> InsightResponse:
    service = InsightsService(db, cache, http_client)
    if type_ == "weekly_summary":
        data = await service.generate_weekly_summary(subject_id)
    else:
        raise HTTPException(400, "Unsupported insight type")
    return InsightResponse(data=data, meta=ResponseMeta())
```

**File:** `src/social_api_gateway/config.py` (modify)

```python
class InsightsSettings(BaseModel):
    provider: str = "openai"  # or "anthropic"
    model: str = "gpt-4o-mini"  # cost-effective
    api_key: str = ""  # Loaded from env
    enabled: bool = False  # Feature flag — disabled by default until configured
    force_refresh: bool = False
```

**File:** `src/social_api_gateway/deps.py` (modify)

- Add `get_http_client()` dependency returning a shared `httpx.AsyncClient`.

**File:** `src/social_api_gateway/main.py` (modify)

- Mount insights router.
- Ensure `httpx.AsyncClient` lifecycle (open on startup, close on shutdown).

### 3. `social-mini-app` — AI Insights UI

**File:** `src/api/hooks.ts`

```typescript
export function useInsight(subjectId?: string, type: string = "weekly_summary") {
  return useQuery({
    queryKey: ["insight", subjectId, type],
    queryFn: () => apiGet<AIInsight>("/v1/insights", { subject_id: subjectId, type }),
    staleTime: 3_600_000,  // 1 hour
  });
}

export function useGenerateInsight() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ subjectId, type }: { subjectId?: string; type: string }) =>
      apiPost<AIInsight>("/v1/insights/generate", { subject_id: subjectId, type }),
    onSuccess: (_data, vars) => {
      qc.invalidateQueries({ queryKey: ["insight", vars.subjectId, vars.type] });
    },
  });
}
```

**File:** `src/components/panels/AIInsightsCard.tsx` (new)

```tsx
// Card with subtle gradient background or sparkle icon to distinguish from data cards
// Header: "AI Insight" with robot/sparkle icon
// Body: Generated text (Markdown-lite formatting supported: **bold**, emojis)
// Footer: "Generated by GPT-4o · 2h ago" | "Template summary (AI unavailable)" if fallback_used
// Actions: "Refresh" button (triggers mutation, shows spinner)
// If insights.enabled is false in settings: show "AI insights not configured" with link to docs
```

**File:** `src/pages/DashboardPage.tsx` (modify)

- Add `AIInsightsCard` (global insight, no subject_id) at the top, below SyncHealthCard.

**File:** `src/pages/Subjects/SubjectDetail.tsx` (modify)

- Add `AIInsightsCard` (subject-specific) below the Identity Card or above Key Metrics.

## Interface Changes (UI/UX)

### New Components

| Component | Description |
|---|---|
| `AIInsightsCard` | AI-generated summary card with refresh button and model attribution |

### Modified Screens

| Screen | Change |
|---|---|
| `DashboardPage` | Add global `AIInsightsCard` at top |
| `SubjectDetailPage` | Add subject-specific `AIInsightsCard` |

### Design Notes (Mobile-First)

- **Differentiate from data cards.** Use a subtle purple/blue gradient background or a "sparkle" icon to signal "this is AI-generated, not raw data".
- **Transparency is key.** Always show which model generated the text and when. If fallback was used, show "Summary generated by rule-based template" (not "AI").
- **Refresh affordance.** A small circular arrow button in the card header lets users regenerate. Haptic feedback on tap.
- **Length limit.** AI summaries are capped at 3 sentences (~300 chars). Long text is truncated with "..." and expandable.
- **Error state.** If AI is unavailable and fallback is also insufficient, show "Unable to generate insight. Check back later." with a retry button.
- **Feature flag.** If `INSIGHTS_ENABLED=false` (default), the card shows a setup prompt instead of trying to call the API. This prevents errors for users who haven't configured an API key.

## Files Relevant (Complete List)

| # | File | Action | Description |
|---|---|---|---|
| 1 | `social-common/social_common/schemas.py` | Modify | Add `AIInsight` schema |
| 2 | `social-api-gateway/src/social_api_gateway/insights/__init__.py` | Create | Package init |
| 3 | `social-api-gateway/src/social_api_gateway/insights/service.py` | Create | `InsightsService` with LLM integration + fallback |
| 4 | `social-api-gateway/src/social_api_gateway/insights/routes.py` | Create | `GET /v1/insights` |
| 5 | `social-api-gateway/src/social_api_gateway/insights/schemas.py` | Create | Response envelope |
| 6 | `social-api-gateway/src/social_api_gateway/config.py` | Modify | Add `InsightsSettings` |
| 7 | `social-api-gateway/src/social_api_gateway/deps.py` | Modify | Add `get_http_client` dependency |
| 8 | `social-api-gateway/src/social_api_gateway/main.py` | Modify | Mount insights router; manage httpx client lifecycle |
| 9 | `social-api-gateway/.env.example` | Modify | Add `INSIGHTS_PROVIDER`, `INSIGHTS_MODEL`, `INSIGHTS_API_KEY`, `INSIGHTS_ENABLED` |
| 10 | `social-api-gateway/scripts/export_openapi.py` | Modify | Regenerate |
| 11 | `social-mini-app/src/api/types.ts` | Regenerate | From OpenAPI |
| 12 | `social-mini-app/src/api/hooks.ts` | Modify | Add `useInsight`, `useGenerateInsight` |
| 13 | `social-mini-app/src/components/panels/AIInsightsCard.tsx` | Create | AI summary card |
| 14 | `social-mini-app/src/pages/DashboardPage.tsx` | Modify | Add global AIInsightsCard |
| 15 | `social-mini-app/src/pages/Subjects/SubjectDetail.tsx` | Modify | Add subject AIInsightsCard |

## Failure Scenarios

| Scenario | Detection | Impact | Mitigation |
|---|---|---|---|
| **LLM API key invalid / missing** | HTTP 401 from OpenAI/Anthropic | No AI insights | Return fallback template summary; show "AI not configured" in UI |
| **LLM API rate limit** | HTTP 429 | Slow or failed insight generation | Cache aggressively (24h); fallback template for immediate response; queue retry |
| **LLM API timeout** | `httpx.TimeoutException` after 30s | Gateway request hangs | Set `timeout=30s`; on timeout, return fallback immediately |
| **LLM returns nonsensical / hallucinated text** | Text contains facts not in prompt | Misleading insight | Post-process validation: check for hallucination markers ("I think", "perhaps"). If detected, regenerate or fallback. |
| **LLM response too long** | >300 tokens | Truncated or rambling text | Set `max_tokens=300` in API call; truncate at sentence boundary if still too long |
| **Cost overrun** | Many users, frequent refreshes | High API bill | Cache 24h; rate-limit insight generation per API key (e.g. max 10/day per subject); require internal API key for on-demand generation |
| **Feature flag disabled** | `INSIGHTS_ENABLED=false` | Card shows "Not configured" | UI gracefully degrades; no backend errors |
| **Prompt injection via data** | Malicious comment text in prompt | LLM manipulated | Sanitise all data fields before inserting into prompt: strip control chars, limit length, escape quotes |
| **Privacy: sensitive data in prompt** | Prompt contains follower counts, post text | Sent to third-party LLM | Document that data is processed by external LLM; allow users to opt-out; do not include PII in prompts |

## Testing Strategy

### Unit Tests (Gateway)

- **InsightsService with mocked LLM:**
  - Mock `httpx` response with known text → verify `generated_text` matches.
  - Mock 429 response → verify fallback text is returned, `fallback_used=True`.
  - Mock timeout → verify fallback returned, no exception propagated.
- **Fallback template:**
  - Data with +15% growth → fallback contains "Strong growth".
  - Data with -10% growth → fallback contains "declined".
- **Cache hit:** Mock Redis cache with stored insight → verify no HTTP call made, `cached=True`.

### Integration Tests

- Configure test API key (OpenAI or mock server).
- Call `/v1/insights?subject_id=...` → verify response shape and non-empty text.
- Call again → verify faster (cache hit).

### Mini App Tests

- `npm run lint && npm run typecheck && npm run build`.
- Manual: AI card renders with summary; tap refresh shows spinner then updates.

## Rollout Plan

### Phase 1: Backend Service (Day 1-3)
1. Add `AIInsight` schema to `social-common`.
2. Implement `InsightsService` with OpenAI + Anthropic support.
3. Implement fallback template generator.
4. Add caching with Redis.
5. Write unit tests with mocked HTTP.

### Phase 2: Gateway API (Day 4)
1. Create insights routes + schemas.
2. Add config settings + env vars.
3. Mount router; manage httpx client lifecycle.
4. Regenerate OpenAPI.

### Phase 3: Mini App (Day 5-6)
1. Add hooks.
2. Build `AIInsightsCard`.
3. Integrate into Dashboard and Subject Detail.

### Phase 4: Cost Monitoring & Safety (Day 7)
1. Add logging for every LLM call: tokens used, cost estimate, latency.
2. Verify fallback works when API key is removed.
3. Document privacy implications in README.

## Open Questions

1. **LLM provider choice:** Should we default to OpenAI, Anthropic, or a local model (Ollama/Llama)? OpenAI has the best price/quality for short summaries. Anthropic has better safety. Local models avoid API costs but require GPU infra. Recommend OpenAI `gpt-4o-mini` as default (cheap, fast, good enough for summaries).
2. **Cost control:** At $0.60/1M tokens (GPT-4o-mini), a 500-token prompt + 200-token response = $0.00042 per insight. 1000 insights/day = $0.42. Acceptable for small scale. Should we add a daily spend cap? Yes — add `INSIGHTS_DAILY_BUDGET_USD` env var; if exceeded, disable AI and use fallback.
3. **Language:** Should insights be generated in the user's language? The system currently has i18n support. Should we pass `language` to the LLM prompt? Yes — add `Accept-Language` header handling and include "Write in {language}" in prompt.
4. **Data privacy compliance:** Sending subject performance data to OpenAI may violate some enterprise policies. Should we add a "self-hosted model" option? Document the external data processing clearly. For enterprise deployments, offer Ollama/Llama integration as an alternative.
5. **Insight types beyond weekly:** Should we also generate "competitive comparison narratives" (comparing 2 subjects) or "platform strategy recommendations"? Not for MVP. Weekly summary + anomaly explanation are sufficient. Add more types based on user feedback.

# Phân tích & Đề xuất Feature Mới cho Social Intelligence Platform

## Executive Summary

Dựa trên phân tích sâu hệ thống hiện tại và research các platform quản lý social media hàng đầu (Hootsuite, Sprout Social, Sendible), tài liệu này đề xuất **10 feature directions** phù hợp với kiến trúc non-trẻ của dự án, follow các pattern đã được market validate bởi các ông lớn, không tạo hướng đi riêng gây risk.

## Current System State

### Architecture (4 services)
| Service | Role | Data Owned |
|---|---|---|
| `social-data-collector` | Facebook/YouTube/TikTok sync worker | `subjects`, `activity_snapshots`, `videos` |
| `social-api-gateway` | FastAPI public API | `api_keys`, read-only queries |
| `social-alert-engine` | Alert evaluation + Telegram notify | `alert_logs` |
| `social-mini-app` | Telegram WebView frontend | UI for all features |
| `social-common` | Shared schemas | Pydantic contracts |

### Existing Features
1. **Subject Management**: List/filter/paginate subjects by platform/status/search
2. **Metrics Tracking**: Followers, post count, activity frequency, last sync
3. **Time-series Charts**: Follower growth, activity frequency (line/bar/area configurable)
4. **Platform-specific Panels**: YouTube videos (views/likes/comments), Facebook/TikTok engagement
5. **Alert System**: Threshold-based rules with cooldown, Telegram notifications
6. **Alert History**: Log of triggered alerts with delivery status
7. **Dashboard KPI**: Total subjects, platform breakdown, most active platform, last sync
8. **Manual Sync**: On-demand sync trigger via Celery task
9. **Telegram Integration**: Bot webhook, Mini App, haptic feedback, theme sync
10. **Settings**: Theme mode, chart style, compact view

### Data Model (Existing)
- `Subject`: platform, platform_id, name, followers, post_count, activity_frequency, status, last_synced_at, extended_data
- `ActivitySnapshot`: time-series (followers, post_count, frequency) captured_at
- `Video` (YouTube): title, views, likes, comments, published_at, thumbnail
- `AlertRule`: rule_type, threshold, cooldown_seconds, channel_id, is_active
- `AlertLog`: triggered_at, metric_value, threshold, message, delivered
- `PlatformConfig` / `PlatformCredential`: OAuth/config management

---

## Research: What the Big Players Do

### Hootsuite (Market Leader - "Everything social. One place.")
**Core Pillars:**
1. **Perch** - Content creation, planning, publishing
2. **Nest** - Social inbox and customer care
3. **Lumen** - Insights and listening (AI-powered)
4. **Wisdom** - Social-first AI
5. **Parliament** - Employee advocacy

**Key Features Relevant to Our Domain:**
- **Social Listening**: Monitor brand mentions, sentiment, trending topics across 30+ networks, 300+ review sites
- **Analytics & ROI**: Live engagement analytics, audience insights, sentiment tracking, industry benchmarks
- **Competitive Analysis**: Track competitor performance, posting frequency, growth rates, share of voice
- **Brand Health Monitoring**: Real-time mention alerts, predictive crisis monitoring, negative sentiment detection
- **Best Time to Post**: AI-recommended optimal posting times based on audience behavior
- **Custom Reporting**: Scheduled report delivery, branded PDF exports

### Sprout Social (Enterprise Focus - "Humanize the social experience")
**Core Pillars:**
1. **Smart Inbox** - Unified message monitoring across networks
2. **Publishing** - Content calendar, ViralPost optimal send times
3. **Analytics** - Group/profile/post-level reporting, competitor benchmarks
4. **Listening** - Query builder, sentiment analysis, trend detection
5. **Engagement** - Case management, collision detection, team productivity

**Key Features Relevant to Our Domain:**
- **Post Performance Reports**: Reach, impression, click, engagement metrics per post
- **Competitor Reports**: Facebook/X/Instagram competitor benchmarking
- **Message Spike Alerts**: Alert when message volume higher than usual
- **Tag Reporting**: Track trends in tagged messages for campaign success
- **Engagement Reporting**: Response rates and times benchmarking
- **Automated Reports**: Recurring weekly/monthly PDF delivery via email
- **Content Suggestions**: Aggregated list of shared links across channels

### Sendible (Agency Focus - "Simplify how you manage social")
**Core Pillars:**
1. **Scheduling** - Content calendar, smart queues, bulk import
2. **Priority Inbox** - Comments and messages in one place
3. **Analytics** - Dynamic insights, automated reports
4. **Campaign Management** - Organize content by campaigns
5. **Content Library** - Store and reuse on-brand content

**Key Features Relevant to Our Domain:**
- **Automated Reports**: Never miss a report deadline
- **Optimal Times**: Reach audience at best engagement times
- **UTM Links**: Track social traffic in Google Analytics
- **Campaign Management**: Stay organized and plan ahead
- **Content Calendar**: View and manage across multiple profiles

---

## Pattern Analysis: What Makes a Social Intelligence Tool Valuable

### Must-Have ( table stakes for any social tool)
| # | Feature | Implemented by | Our Status |
|---|---|---|---|
| 1 | Multi-platform subject tracking | All 3 | ✅ Done |
| 2 | Time-series metrics visualization | All 3 | ✅ Done |
| 3 | Basic alerting (threshold-based) | All 3 | ✅ Done |
| 4 | Dashboard with KPIs | All 3 | ✅ Done |
| 5 | Manual sync / refresh | All 3 | ✅ Done |

### Should-Have (differentiators that users expect)
| # | Feature | Implemented by | Our Status |
|---|---|---|---|
| 6 | Competitive benchmarking | Hootsuite, Sprout | ❌ Missing |
| 7 | Post/Content-level analytics | Sprout, Sendible | ⚠️ Partial (YouTube only) |
| 8 | Trend detection / anomaly alerts | Hootsuite, Sprout | ❌ Missing |
| 9 | Automated scheduled reports | Sprout, Sendible | ❌ Missing |
| 10 | Hashtag/keyword tracking | Hootsuite, Sprout | ❌ Missing |
| 11 | Engagement rate calculation | Sprout, Sendible | ❌ Missing |
| 12 | Cross-platform aggregated view | All 3 | ⚠️ Partial (Dashboard) |
| 13 | Sync health monitoring | None explicit | ❌ Missing |
| 14 | Content calendar (read-only) | All 3 | ❌ Missing |
| 15 | Social listening lite (comments) | Hootsuite, Sprout | ❌ Missing |

### Could-Have (advanced features for mature products)
| # | Feature | Implemented by | Our Status |
|---|---|---|---|
| 16 | AI-powered insights | Hootsuite Wisdom | ❌ Missing |
| 17 | Sentiment analysis | Hootsuite, Sprout | ❌ Missing |
| 18 | ROI tracking / UTM | Sendible | ❌ Missing |
| 19 | Team collaboration / case mgmt | Sprout | ❌ Missing |
| 20 | Employee advocacy | Hootsuite Parliament | ❌ Missing |

---

## Feature Recommendations (Prioritized)

### 🎯 Tier 1: High Impact, Low Risk (Implement First)

#### Feature 1: Post-level Content Performance Analytics
**Why this feature:**
- Sprout Social dedicates an entire feature pillar to "Post Performance Report"
- Sendible has "Analytics and Reporting" as core feature
- System đã có `Video` model cho YouTube → extend pattern sang Facebook posts và TikTok videos

**What to build:**
- **Collector**: Thu thập posts từ Facebook (recent posts) và TikTok videos, tương tự `Video` cho YouTube
- **Schema**: `Post` model với fields: `platform_post_id`, `caption`, `media_url`, `published_at`, `like_count`, `comment_count`, `share_count`, `view_count`, `engagement_rate`
- **Gateway**: `GET /v1/subjects/{id}/posts` endpoint (tương tự `/videos`)
- **Mini App**: Content Performance section trong Subject Detail:
  - Top performing posts card (sorted by engagement rate)
  - Post engagement breakdown (likes/comments/shares mini-bars)
  - "Best performing content" badge

**Acceptance Criteria:**
- [ ] Collector fetches Facebook posts và TikTok videos sau mỗi sync
- [ ] Gateway serves paginated post list per subject
- [ ] Mini App shows top 5 posts by engagement rate
- [ ] Engagement rate calculated as `(likes + comments + shares) / views` (hoặc followers nếu không có views)

**Files touched:**
- `social-data-collector/src/social_data_collector/clients/facebook.py` (extend)
- `social-data-collector/src/social_data_collector/normalizers/` (new)
- `social-common/social_common/schemas.py` (add `Post` schema)
- `social-api-gateway/src/social_api_gateway/subjects/routes.py` (add endpoint)
- `social-mini-app/src/api/hooks.ts` (add `usePosts` hook)
- `social-mini-app/src/components/panels/ContentPerformancePanel.tsx` (new)

**Estimated scope:** Medium (5-8 files)

---

#### Feature 2: Cross-Subject Competitive Benchmarking
**Why this feature:**
- Hootsuite có "Competitive Analysis" pillar với competitor engagement stats
- Sprout Social có "Facebook Competitor Report", "X Competitor Report", "Instagram Competitor Report"
- System đã track nhiều subjects → dữ liệu đã sẵn có, chỉ cần so sánh

**What to build:**
- **Gateway**: `GET /v1/benchmarks` endpoint trả về aggregated comparison:
  - Growth rate % (followers change over last 7/30 days)
  - Average engagement rate per platform
  - Activity frequency ranking
  - "Top performer" và "Most improved" badges
- **Mini App**: New "Benchmarks" tab/page:
  - Leaderboard cards: subjects ranked by growth rate
  - Platform comparison chart (bar chart comparing avg metrics per platform)
  - "Your subjects vs Industry average" (nếu có dữ liệu public)

**Acceptance Criteria:**
- [ ] API returns benchmark data for all active subjects
- [ ] Mini App renders leaderboard with growth rate badges
- [ ] Platform comparison chart shows Facebook vs YouTube vs TikTok averages
- [ ] Subject detail có "how you compare" context (e.g. "Top 10% by growth")

**Files touched:**
- `social-api-gateway/src/social_api_gateway/` (new `benchmarks/` module)
- `social-mini-app/src/pages/BenchmarkPage.tsx` (new)
- `social-mini-app/src/navigation/BottomNav.tsx` (add tab)
- `social-mini-app/src/routes.tsx` (add route)
- `social-mini-app/src/api/hooks.ts` (add `useBenchmarks` hook)

**Estimated scope:** Medium (4-6 files)

---

#### Feature 3: Enhanced Alert Engine - Trend Detection & Anomaly Alerts
**Why this feature:**
- Hootsuite: "predictive crisis monitoring", "detect brand mentions in photos/video"
- Sprout Social: "Message Spike Alerts" - "Get alerted when message volume is higher than usual"
- Current system chỉ có threshold-based alerts (e.g. "followers > 1000") → cần anomaly detection

**What to build:**
- **Alert Engine**: Extend rule types:
  - `SPIKE`: Trigger khi metric tăng/giảm > X% so với baseline window (7-day rolling avg)
  - `DROP`: Trigger khi metric giảm đột ngột (e.g. followers drop > 5% in 24h)
  - `STALL`: Trigger khi không có activity trong X giờ
- **Baseline Algorithm**: Thay vì fixed threshold, dùng statistical baseline:
  - 7-day rolling average + standard deviation
  - Trigger khi value nằm ngoài 2-sigma (95%) hoặc 3-sigma (99.7%)
- **Mini App**: Alert config panel thêm rule type dropdown với descriptions

**Acceptance Criteria:**
- [ ] New enum values in `AlertRuleType`: `SPIKE`, `DROP`, `STALL`
- [ ] Baseline calculator computes rolling avg + std dev from activity_snapshots
- [ ] Anomaly alerts trigger correctly on test data
- [ ] Mini App shows rule type descriptions và recommended thresholds

**Files touched:**
- `social-common/social_common/enums.py` (extend `AlertRuleType`)
- `social-alert-engine/src/social_alert_engine/baseline.py` (enhance)
- `social-alert-engine/src/social_alert_engine/evaluator.py` (extend logic)
- `social-api-gateway/src/social_api_gateway/alerts/schemas.py` (update validation)
- `social-mini-app/src/components/panels/AlertConfigPanel.tsx` (enhance)

**Estimated scope:** Medium (5-7 files)

---

### 🎯 Tier 2: Medium Impact, Medium Risk

#### Feature 4: Weekly/Monthly Automated Reports via Telegram
**Why this feature:**
- Sprout Social: "Report Scheduled Delivery" - "Set up recurring weekly or monthly delivery of any report via email"
- Sendible: "Automated Reports" - "Never miss a report deadline"
- System đã có Telegram Bot → gửi report qua Telegram là natural extension

**What to build:**
- **Schema**: `ReportSchedule` model: `subject_id`, `frequency` (weekly/monthly), `day_of_week`, `hour`, `channel_id`, `format` (summary/detailed), `is_active`
- **Alert Engine / New Service**: Scheduled Celery beat task tạo report:
  - Growth summary (followers gained/lost)
  - Top performing content
  - Alert summary (how many fired this period)
  - Platform breakdown
- **Telegram Delivery**: Gửi formatted message hoặc PDF qua bot
- **Mini App**: Report scheduling UI trong Settings hoặc Subject Detail

**Acceptance Criteria:**
- [ ] Report schedule CRUD API
- [ ] Weekly report generated every Monday 9am (configurable)
- [ ] Report delivered to configured Telegram channel
- [ ] Report contains: growth summary, top content, alert count, health status

**Files touched:**
- `social-common/social_common/schemas.py` (add `ReportSchedule`)
- `social-api-gateway/src/social_api_gateway/` (new `reports/` module)
- `social-alert-engine/src/social_alert_engine/reports.py` (new)
- `social-alert-engine/src/social_alert_engine/tasks.py` (add scheduled task)
- `social-mini-app/src/components/panels/ReportSchedulePanel.tsx` (new)

**Estimated scope:** Large (7-10 files) - consider splitting into smaller tasks

---

#### Feature 5: Hashtag & Keyword Performance Tracking
**Why this feature:**
- Hootsuite: "Monitor brand mentions and trends", "Find trending topics and content opportunities"
- Sprout Social: "Brand Keywords" - "Execute real-time brand monitoring with keyword, hashtag and location searches"
- Sendible: Content curation và trending topic tracking

**What to build:**
- **Collector**: Parse hashtags từ post captions/descriptions trong sync process
- **Schema**: `Hashtag` model: `name`, `platform`, `first_seen_at`, `last_seen_at`, `usage_count`
- **Schema**: `SubjectHashtag` link table: `subject_id`, `hashtag_id`, `post_count`, `avg_engagement`
- **Gateway**: `GET /v1/hashtags?platform=&sort=` endpoint
- **Mini App**: 
  - Top hashtags section trong Subject Detail
  - Hashtag detail page: which subjects use it, trend over time
  - Subject list filter by hashtag

**Acceptance Criteria:**
- [ ] Hashtags extracted from post content during sync
- [ ] API returns trending hashtags by platform
- [ ] Mini App shows top 10 hashtags per subject
- [ ] Hashtag filter works trong subject list

**Files touched:**
- `social-data-collector/src/social_data_collector/` (hashtag extraction)
- `social-common/social_common/schemas.py` (add `Hashtag`, `SubjectHashtag`)
- `social-api-gateway/src/social_api_gateway/` (new `hashtags/` module)
- `social-mini-app/src/api/hooks.ts` (add `useHashtags`)
- `social-mini-app/src/pages/HashtagDetailPage.tsx` (new)

**Estimated scope:** Large (7-10 files)

---

#### Feature 6: Engagement Rate Analytics & Best Time to Post Insights
**Why this feature:**
- Sprout Social: "ViralPost® Send Time Optimization" - "Deliver your content at optimal times"
- Hootsuite: "Best times to post" recommendations
- Sendible: "Optimal Times" - "Reach your audience easily by scheduling at an optimal time"

**What to build:**
- **Gateway**: Analytics endpoint tính toán:
  - Engagement rate = (likes + comments + shares) / followers (hoặc views)
  - Peak engagement times (hour-of-day, day-of-week heatmap)
  - Optimal posting time recommendation
- **Mini App**:
  - Engagement rate display trên mỗi post/card
  - "Best time to post" insight card trong Subject Detail
  - Weekly engagement heatmap (giống GitHub contribution graph)

**Acceptance Criteria:**
- [ ] Engagement rate calculated for all platforms
- [ ] Peak time analysis from post publish timestamps + engagement data
- [ ] Mini App shows optimal posting time recommendation
- [ ] Weekly heatmap renders correctly

**Files touched:**
- `social-api-gateway/src/social_api_gateway/analytics/` (new module)
- `social-mini-app/src/components/charts/EngagementHeatmap.tsx` (new)
- `social-mini-app/src/components/panels/OptimalTimePanel.tsx` (new)

**Estimated scope:** Medium (4-6 files)

---

### 🎯 Tier 3: Lower Priority / Future Considerations

#### Feature 7: Sync Health Monitoring & Failure Alerts
**Why this feature:**
- System đã có health check (`health.py`) nhưng chưa có historical tracking
- Operations team cần biết khi nào sync fail liên tục
- Natural extension của alert system hiện tại

**What to build:**
- **Schema**: `SyncLog` model: `subject_id`, `started_at`, `completed_at`, `status` (success/failure), `error_message`, `records_synced`
- **Collector**: Ghi sync log sau mỗi sync attempt
- **Alert Engine**: Rule type `SYNC_FAILURE` - trigger khi sync fail N lần liên tiếp
- **Mini App**: 
  - Sync status indicator trong Subject List (green/yellow/red dot)
  - Sync history trong Subject Detail

**Acceptance Criteria:**
- [ ] Every sync attempt logged
- [ ] Sync failure alert triggers after 3 consecutive failures
- [ ] Mini App shows sync health indicator
- [ ] Admin can view sync logs

**Estimated scope:** Medium (5-7 files)

---

#### Feature 8: Content Calendar (Read-Only Historical View)
**Why this feature:**
- Hootsuite, Sprout Social, Sendible đều có content calendar là core feature
- System này là read-only monitor → không cần scheduling capability, chỉ cần historical view

**What to build:**
- **Gateway**: `GET /v1/subjects/{id}/calendar?from=&to=` trả về posts trong date range
- **Mini App**: Calendar view (month/week/day) showing:
  - Ngày nào có post (colored dots theo platform)
  - Post frequency heatmap
  - Tap a day to see posts

**Acceptance Criteria:**
- [ ] Calendar API returns posts by date range
- [ ] Mini App renders monthly calendar with post indicators
- [ ] Tap day shows post list for that day
- [ ] Works for all platforms (Facebook, YouTube, TikTok)

**Estimated scope:** Medium (4-5 files)

---

#### Feature 9: Social Listening Lite (Comment Volume & Sentiment)
**Why this feature:**
- Hootsuite Lumen: "Insights and listening" - "detect brand mentions in photos, videos, and GIFs"
- Sprout Social: "Listening" - "multi-dimensional social listening across all major social channels"
- Lite version vì full sentiment analysis cần NLP model phức tạp

**What to build:**
- **Collector**: Thu thập comments từ Facebook posts và YouTube videos (nếu API cho phép)
- **Schema**: `Comment` model: `post_id`, `author`, `content`, `published_at`, `like_count`
- **Schema**: `SentimentSnapshot` model: `subject_id`, `captured_at`, `positive_count`, `negative_count`, `neutral_count`, `total_comments`
- **Mini App**:
  - Comment volume chart (line chart)
  - Simple sentiment ratio (pie chart: positive/negative/neutral)
  - "Comment spike" alert rule

**Acceptance Criteria:**
- [ ] Comments collected during sync (platform API permitting)
- [ ] Sentiment classified by keyword matching (positive: "good", "love", "great"; negative: "bad", "hate", "terrible")
- [ ] Mini App shows comment volume và sentiment breakdown
- [ ] Comment spike alert triggers on unusual volume

**Estimated scope:** Large (7-10 files)
**Risk:** Facebook Graph API có restrictions với comment data; cần verify API permissions trước implementation.

---

#### Feature 10: AI-Powered Insights Summary (Future / Phase 5+)
**Why this feature:**
- Hootsuite Wisdom: "Social-first AI" - "AI caption generation, best-time-to-post recommendations, summarize large volumes of social data"
- Sprout Social: AI trong premium analytics
- Industry trend: mọi social tool đều integrate AI năm 2024-2025

**What to build (MVP):**
- **Backend**: Integration với LLM API (OpenAI/Anthropic) để generate:
  - Weekly performance summary ("TikTok grew 15% this week, driven by 3 viral videos")
  - Content recommendations ("Your audience engages most with video content under 60 seconds")
  - Anomaly explanation ("Follower drop coincides with no posts for 3 days")
- **Mini App**: "AI Insights" card trong Dashboard và Subject Detail
- **Prompt Engineering**: Structured prompts using collected data

**Acceptance Criteria:**
- [ ] AI summary generated from subject data
- [ ] Summary delivered via Telegram hoặc trong Mini App
- [ ] Caching to reduce API costs
- [ ] Fallback khi AI service unavailable

**Estimated scope:** Large (5-8 files)
**Risk:** External API dependency, cost considerations. Recommend Phase 5+.

---

## Implementation Roadmap

### Phase 1 (Immediate - Sprint 7-8)
**Goal**: Solidify foundation với content-level analytics + competitive benchmarking

```
Sprint 7: Post-level Content Performance
├── Task 1: Add Post schema + Facebook/TikTok post collection
├── Task 2: Gateway /posts endpoint
├── Task 3: Mini App ContentPerformancePanel
└── Checkpoint: All platforms show top posts by engagement

Sprint 8: Competitive Benchmarking
├── Task 1: Benchmark API (growth rates, rankings)
├── Task 2: Mini App Benchmarks page + navigation
├── Task 3: Subject detail "how you compare" context
└── Checkpoint: Leaderboard + platform comparison works
```

### Phase 2 (Short-term - Sprint 9-10)
**Goal**: Intelligence layer với anomaly detection + automated reporting

```
Sprint 9: Enhanced Alert Engine (Anomaly Detection)
├── Task 1: Extend AlertRuleType enum
├── Task 2: Statistical baseline calculator (rolling avg + std dev)
├── Task 3: Mini App enhanced alert config
└── Checkpoint: SPIKE/DROP alerts trigger correctly

Sprint 10: Automated Reports
├── Task 1: ReportSchedule schema + API
├── Task 2: Report generator (Celery task)
├── Task 3: Telegram report delivery
├── Task 4: Mini App report scheduling UI
└── Checkpoint: Weekly report auto-delivered to Telegram
```

### Phase 3 (Medium-term - Sprint 11-12)
**Goal**: Discovery layer với hashtag tracking + engagement insights

```
Sprint 11: Hashtag Performance Tracking
├── Task 1: Hashtag extraction in collector
├── Task 2: Hashtag schema + API
├── Task 3: Mini App hashtag panels + filter
└── Checkpoint: Top hashtags visible per subject

Sprint 12: Engagement Analytics & Best Time
├── Task 1: Engagement rate calculation API
├── Task 2: Peak time analysis
├── Task 3: Engagement heatmap component
├── Task 4: Optimal time recommendation panel
└── Checkpoint: Mini App shows best posting time
```

### Phase 4 (Long-term - Sprint 13-15)
**Goal**: Operations + advanced features

```
Sprint 13: Sync Health Monitoring
├── Task 1: SyncLog schema + collection
├── Task 2: SYNC_FAILURE alert rules
├── Task 3: Mini App health indicators
└── Checkpoint: Sync failure alerts work

Sprint 14: Content Calendar View
├── Task 1: Calendar API endpoint
├── Task 2: Calendar UI component
└── Checkpoint: Monthly calendar renders posts

Sprint 15: Social Listening Lite
├── Task 1: Comment collection (verify API perms)
├── Task 2: Sentiment keyword classifier
├── Task 3: Comment volume + sentiment UI
└── Checkpoint: Sentiment pie chart visible
```

### Phase 5 (Future)
**Goal**: AI-powered differentiators

```
Sprint 16+: AI Insights Summary
├── Task 1: LLM integration (OpenAI/Anthropic)
├── Task 2: Prompt engineering for social data
├── Task 3: AI Insights card in Mini App
└── Checkpoint: AI generates coherent weekly summaries
```

---

## Risk Analysis

| Risk | Impact | Mitigation |
|------|--------|------------|
| Facebook Graph API restricts comment access | High | Verify API permissions trước khi implement Social Listening Lite; có fallback plan (skip comments, track reactions only) |
| TikTok API không public/stable | High | Use unofficial/scraping APIs (risky) hoặc postpone TikTok features; có thể dùng `extended_data` để store raw metrics |
| TimescaleDB query performance với large datasets | Medium | Add proper indexing, materialized views cho benchmarks; test với 1M+ snapshots |
| Telegram message length limits cho reports | Low | Split long reports into multiple messages; use Telegram's HTML formatting |
| AI API costs và rate limits | Medium | Cache AI responses (1-24h TTL); implement fallback to template-based summaries |
| Feature scope creep | High | Strict vertical slicing; mỗi sprint chỉ 1 feature; không parallelize foundation + advanced |

---

## Open Questions

1. **TikTok API Access**: Hiện tại TikTok data lấy từ đâu? Có official API access không, hay đang dùng scraper? Điều này ảnh hưởng feature design cho TikTok-specific analytics.

2. **Facebook Post Permissions**: Facebook Graph API cho Pages có cho phép lấy individual post engagement metrics (reactions, comments, shares) không? Cần verify trước implement Post analytics.

3. **User Segmentation**: Có cần phân biệt "tracked subjects" (competitors) và "owned accounts" (internal) không? Hootsuite và Sprout Social đều có concept này, ảnh hưởng benchmark logic.

4. **Data Retention Policy**: Activity snapshots lưu bao lâu? 30 ngày, 90 ngày, forever? Ảnh hưởng baseline calculation và trend detection accuracy.

5. **Report Audience**: Automated reports gửi cho ai? Chỉ admin, hay tất cả users trong channel? Ảnh hưởng `ReportSchedule` schema design.

---

## Conclusion

Hệ thống hiện tại đã có solid foundation với multi-platform tracking, time-series storage, alert engine, và Telegram integration. Để tiến lên, cần follow market patterns:

**Next 2 sprints (highest ROI):**
1. **Post-level analytics** - Extend existing `Video` pattern sang Facebook/TikTok, add engagement metrics
2. **Competitive benchmarking** - Leverage existing multi-subject data để so sánh performance

**Sau đó:**
3. **Anomaly alerts** - Nâng cấp alert engine từ threshold-based lên statistical baseline
4. **Automated reports** - Dùng existing Telegram infrastructure để deliver periodic insights

Các feature này đều có thể implement incrementally, không cần redesign architecture, và phù hợp với mobile-first Telegram Mini App context.

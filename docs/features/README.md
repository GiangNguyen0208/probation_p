# Feature Specifications Index

This directory contains detailed implementation specifications for all proposed new features for the Social Intelligence Platform. Each file follows a standard template covering: Overview, Goals, Non-Goals, Architecture, Data Model, API Contracts, Code Changes (per service), Interface Changes, Files Relevant, Failure Scenarios, Testing Strategy, Rollout Plan, and Open Questions.

## Feature Roadmap

| # | Feature | Priority | Effort | Dependencies | File |
|---|---|---|---|---|---|
| 1 | **Post-Level Content Performance Analytics** | Tier 1 (Immediate) | Medium (5-8 files) | None (extends existing `Video` pattern) | [`01-post-level-content-performance.md`](01-post-level-content-performance.md) |
| 2 | **Cross-Subject Competitive Benchmarking** | Tier 1 (Immediate) | Medium (4-6 files) | None (uses existing `activity_snapshots`) | [`02-competitive-benchmarking.md`](02-competitive-benchmarking.md) |
| 3 | **Enhanced Alert Engine — Anomaly Detection** | Tier 1 (Immediate) | Medium (5-7 files) | None (extends existing alert engine) | [`03-anomaly-detection-alerts.md`](03-anomaly-detection-alerts.md) |
| 4 | **Weekly/Monthly Automated Reports via Telegram** | Tier 2 (Short-term) | Large (7-10 files) | Feature 1 (for post data in reports) | [`04-automated-telegram-reports.md`](04-automated-telegram-reports.md) |
| 5 | **Hashtag & Keyword Performance Tracking** | Tier 2 (Short-term) | Large (7-10 files) | Feature 1 (needs `Post.caption`) | [`05-hashtag-keyword-tracking.md`](05-hashtag-keyword-tracking.md) |
| 6 | **Engagement Rate & Best Time to Post Insights** | Tier 2 (Short-term) | Medium (4-6 files) | Feature 1 (needs `posts` table) | [`06-engagement-rate-best-time.md`](06-engagement-rate-best-time.md) |
| 7 | **Sync Health Monitoring & Failure Alerts** | Tier 3 (Medium-term) | Medium (5-7 files) | None (additive observability) | [`07-sync-health-monitoring.md`](07-sync-health-monitoring.md) |
| 8 | **Content Calendar (Read-Only Historical View)** | Tier 3 (Medium-term) | Medium (4-5 files) | Feature 1 (needs `posts.published_at`) | [`08-content-calendar-view.md`](08-content-calendar-view.md) |
| 9 | **Social Listening Lite — Comment Volume & Sentiment** | Tier 3 (Medium-term) | Large (7-10 files) | Feature 1 (needs posts to fetch comments) | [`09-social-listening-lite.md`](09-social-listening-lite.md) |
| 10 | **AI-Powered Insights Summary** | Tier 4 (Future / Phase 5+) | Large (5-8 files) | Features 1-3 (needs rich data for prompts) | [`10-ai-powered-insights.md`](10-ai-powered-insights.md) |

## Cross-Feature Dependencies

```
Feature 1 (Post Analytics)
    ├── Feature 4 (Reports) ── needs Post data in report builder
    ├── Feature 5 (Hashtags) ── needs Post.caption for extraction
    ├── Feature 6 (Engagement) ── needs Post metrics
    ├── Feature 8 (Calendar) ── needs Post.published_at
    └── Feature 9 (Comments) ── needs Post IDs to fetch comments

Feature 2 (Benchmarking)
    └── Feature 6 (Engagement) ── optionally uses engagement rate for ranking

Feature 3 (Anomaly Alerts)
    ├── Feature 7 (Sync Health) ── adds SYNC_FAILURE rule type
    └── Feature 9 (Comments) ── adds COMMENT_SPIKE rule type

Feature 7 (Sync Health)
    └── Feature 4 (Reports) ── sync health status included in reports
```

## Critical Path

The **minimum viable path** to deliver the most value with the least risk:

```
Sprint 7:  Feature 1 (Post Analytics)
Sprint 8:  Feature 2 (Benchmarking)
Sprint 9:  Feature 3 (Anomaly Alerts)
Sprint 10: Feature 7 (Sync Health)
Sprint 11: Feature 6 (Engagement + Best Time)
Sprint 12: Feature 4 (Automated Reports)
Sprint 13: Feature 8 (Content Calendar)
Sprint 14: Feature 5 (Hashtag Tracking)
Sprint 15: Feature 9 (Social Listening Lite)
Sprint 16+: Feature 10 (AI Insights)
```

## Implementation Notes

### Sprint Pairing Recommendations
- **Sprint 7-8:** Features 1 + 2 can be developed in parallel by different developers (1 = collector-heavy, 2 = gateway-heavy).
- **Sprint 9-10:** Features 3 + 7 both touch the alert engine; recommend same developer for continuity.
- **Sprint 11-12:** Features 6 + 4 both are analytics/reporting layers; can share `BenchmarkService` patterns.

### Blocking Dependencies
| Feature | Blocked By | Resolution |
|---|---|---|
| Feature 5 (Hashtags) | Feature 1 (Posts) | Develop back-to-back or in same sprint |
| Feature 6 (Engagement) | Feature 1 (Posts) | Develop back-to-back |
| Feature 8 (Calendar) | Feature 1 (Posts) | Develop back-to-back |
| Feature 9 (Comments) | Feature 1 (Posts) | Develop back-to-back |
| Feature 10 (AI) | Features 1-3 | Defer to Phase 5+ |

### Per-Service File Count Estimate

| Service | Total Files Touched (all 10 features) | Notes |
|---|---|---|
| `social-common` | ~15 files | Schema additions only |
| `social-data-collector` | ~30 files | Models, migrations, clients, normalizers, tasks |
| `social-api-gateway` | ~40 files | New modules (reports, benchmarks, engagement, etc.), route mounts |
| `social-alert-engine` | ~10 files | Baseline, evaluator, tasks, notifier, models |
| `social-mini-app` | ~45 files | New components, pages, hooks, route additions |

**Total estimated files across all features:** ~140 files.

## How to Use These Specs

1. **Pick a feature** from the roadmap based on current sprint capacity.
2. **Read the spec file** completely before writing any code.
3. **Verify dependencies** are already implemented (check the spec's Dependencies section).
4. **Follow the Rollout Plan** phase by phase — do not skip phases.
5. **Update this index** if implementation details change (e.g. a new file is needed, or a file is no longer touched).
6. **Mark features as shipped** in the roadmap table by updating the Priority column to "Shipped".

## Open Questions Across All Features

1. **TikTok API source** — Official Research API, unofficial API, or scraper? Affects Features 1, 5, 6, 8, 9.
2. **Facebook Graph API permissions** — Do we have `pages_read_engagement` and `pages_read_user_content`? Affects Features 1 and 9.
3. **Data retention policy** — How long are `activity_snapshots` retained? Affects baseline accuracy in Feature 3 and historical depth in Features 2, 6.
4. **User segmentation** — Do we need "owned accounts" vs "competitors" distinction? Affects Feature 2 benchmark logic.
5. **Report audience** — Who receives automated reports? Affects Feature 4 `ReportSchedule` schema design.

## Related Documents

- [`../feature-analysis-and-recommendations.md`](../feature-analysis-and-recommendations.md) — Market research, pattern analysis, and original feature recommendations
- [`../sprints/phase-3-plan.md`](../sprints/phase-3-plan.md) — Phase 3 master plan (Mini App, Telegram integration)
- [`../sprints/phase-4-alert-engine.md`](../sprints/phase-4-alert-engine.md) — Phase 4 alert engine plan
- [`../tracking/phase-3-implementation.md`](../tracking/phase-3-implementation.md) — Phase 3 implementation status
- [`../tracking/phase-4-implementation.md`](../tracking/phase-4-implementation.md) — Phase 4 implementation status

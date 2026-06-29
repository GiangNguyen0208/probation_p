```
SOCIAL INTELLIGENCE PLATFORM
Full Architecture & System Design Document
Document Type
Architecture Design
Project
GHN Social Intelligence Monitoring
Version
v1.0
Date
June 2026
```

## `1. Executive Summary` 

```
This document describes the complete architecture, repository structure, service
boundaries, data flows, and execution roadmap for the Social Intelligence
Monitoring Platform. The system is designed to collect public data on-demand
about subjects (pages, channels, profiles) on Facebook and YouTube, normalise
that data into a unified schema, expose it through a secure public API, and
surface it to analysts through a Telegram Mini App with real-time alerting.
The design is derived from the probationary evaluation requirements (GHN DPA
assessment) and is authored from the perspective of a senior system architect.
It covers everything a development team needs to plan, estimate, and begin
building the platform from zero.
```

```
Key numbers at a glance
6 Git repositories   |   4 runtime services   |   1 shared library   |   1
infrastructure repo
```

```
3 core platform tasks covering 80% of evaluation weight (Data Collector 30%, API
Gateway 25%, Mini App 25%)
5 execution phases from foundation to production handover   |   Target
completion: 8 weeks
```

```
2. Problem Statement & Goals
```

```
2.1 Business context
```

```
The organisation needs to monitor multiple public social media subjects
(Facebook pages and YouTube channels) in a systematic, automated way. Currently
this is a manual process. The platform replaces it with a centralised system where users can trigger on-demand monitoring that:

• Automatically collects and normalises subject data from external platform APIs
when manually triggered

• Stores the data centrally in a way that supports trend analysis and anomaly
detection
```

```
• Exposes the data via a secure, documented API for internal and third-party
consumers
```

```
• Delivers a Telegram-native user interface so analysts can monitor subjects and
receive alerts without leaving their communication tool
```

```
2.2 Scope
In Scope
Out of Scope
Facebook Graph API data collection
Content sentiment analysis or NLP
YouTube Data API v3 data collection
Private / authenticated subject data
Unified subject schema and central storage
Web dashboard (beyond Telegram Mini App)
Public REST API with API Key auth and rate limiting
Paid data sources or commercial scrapers
Telegram Mini App for subject monitoring
Mobile native applications
Telegram Bot for push alerts
```

```
Billing or subscription management
Scheduled data crawling (cron jobs)
```

```
Alert rules engine configurable from Mini App
```

```
3. Architecture Overview
```

```
The platform is structured as a set of independent services connected through a
shared data store. There is no direct service-to-service HTTP communication at
runtime - all services read from and write to the central storage layer. This
design choice maximises resilience: a failure in the collector does not bring
down the API gateway or the Mini App.
```

```
3.1 Layered architecture
Layer
Components
Responsibility
External sources
Facebook Graph API, YouTube Data API v3
Source of raw subject data
Ingestion layer
Data Collector Service
Pull, normalise, and persist subject data on-demand
Storage layer
Primary DB, Time-series Store, Cache
Durable storage of current state and historical trends
API layer
Public API Gateway
Serve subject data securely to all consumers
Consumption layer
Telegram Mini App, Alert Engine, 3rd-party consumers
Read and act on subject data
Notification layer
Telegram Bot Service
Push alerts to analysts in Telegram
```

```
3.2 Core architecture principles
```

```
• Ingestion decoupled from serving
```

```
◦ The Collector writes to storage; the API Gateway only reads. A platform API
outage does not affect data serving.
```

```
• Schema-first design
```

```
◦ The unified Subject schema is defined once in the shared library and imported
by every service. Adding a new platform (e.g. TikTok) requires only a new
normaliser - no changes to storage or API contracts.
```

```
• Independent deployability
```

```
◦ Each service has its own repository and can be deployed, scaled, and restarted
without affecting others.
```

```
• Fail-safe alerting
```

```
◦ The Alert Engine never blocks the API or Mini App. It operates as a background
consumer with its own queue and deduplication logic.
• API as the single external interface
```

```
◦ The Mini App and 3rd-party consumers both go through the same API Gateway.
Internal consumers use a privileged key; external consumers use restricted keys
with rate limits.
```

## `4. Repository Structure` 

```
The platform is organised into 6 repositories. Each service repository is
independently deployable. The shared library is versioned and published
internally so all services import the same contracts.
```

```
Repository
Type
```

```
Runtime
Primary Responsibility
social-data-collector
Service
Yes
Platform API ingestion, normalisation, scheduled sync
social-api-gateway
Service
Yes
Public REST API, auth, rate limiting, Swagger docs
social-alert-engine
Service
Yes
Anomaly detection, alert rules evaluation, bot push
social-mini-app
Service
Yes
Telegram Mini App frontend, alert config UI
social-common
Shared library
No
Subject schema, DTOs, error codes, shared interfaces
social-infra
Infrastructure
No
IaC, CI/CD, DB migrations, env config, secrets
```

## `4.1 social-data-collector` 

```
The most critical service by complexity and evaluation weight (30%). Responsible
for all platform data ingestion. Implements a separate API client per platform
so each can evolve independently. The normaliser maps platform-specific
responses to the unified Subject schema from social-common. It executes sync tasks upon receiving trigger requests.
```

```
• Facebook Graph API client: page/profile data, followers, post count, activity
frequency, all public fields
```

```
• YouTube Data API v3 client: channel stats, subscriber count, video count,
upload frequency
```

```
• Normaliser: platform-specific response → unified Subject schema
```

- `Persistence layer: writes to Primary DB (current state) and Time-series Store (historical snapshots)` 

- `On-demand Sync: triggered manually via API request, per-platform rate-limit awareness` 

```
• Error handling: API quota exceeded, partial data, network failures - all
logged and recovered gracefully without crashing the service
```

## `4.2 social-api-gateway` 

```
The external face of the system (25% weight). All reads from any consumer - Mini
App, Alert Engine, or 3rd-party - come through here. Never touches platform APIs
directly.
```

```
• REST endpoints: GET /subjects, GET /subjects/:id, GET /subjects/:id/activity
• API Key authentication middleware: validate on every request, reject invalid
keys with 401 before any business logic runs
```

- `Rate limiting: per-key quotas, 429 response with Retry-After header` 

```
• Query parameters: filter by platform, status, date range; pagination via page
and limit
```

```
• Cache integration: hot paths read from cache, TTL-based invalidation, fallback
to DB on cache miss
```

```
• OpenAPI/Swagger docs: complete enough for external integrators to onboard
without asking questions
```

```
• API versioning: /v1/ prefix on all routes, documented upgrade path for future
versions
```

## `4.3 social-alert-engine` 

```
Background service that evaluates alert rules against incoming data and pushes
```

```
notifications via the Telegram Bot. Operates asynchronously - never in the
request path of the API.
```

```
• Anomaly detector: compares current subject metrics against rolling baseline
(configurable window)
```

```
• Alert rules engine: reads per-subject rules from DB (set by users via Mini
App), evaluates after each manual sync
```

```
• Deduplication: one alert per event per cooldown window - prevents notification
floods on sustained anomalies
```

```
• Telegram Bot service: sends formatted alert messages to configured chat IDs or
groups
```

- `Alert log: full history of all sent alerts, query-able from Mini App` 

## `4.4 social-mini-app` 

```
The Telegram Mini App is the analyst-facing interface. It runs as a WebApp
inside Telegram and consumes the public API Gateway exclusively. It also writes
alert configuration back to the system through the API.
```

```
• Subject list screen: name, platform badge, follower count, post frequency,
status, last sync time
```

```
• Search and filter: by platform, priority level, status - all combinable in one
query
```

```
• Subject detail screen: time-series charts of follower trends and post
frequency, raw activity metrics
```

```
• Summary dashboard: total subjects tracked, alerts today, most active platform,
last sync timestamp
```

```
• Alert config panel: configure alert thresholds per subject directly inside the
Mini App - no web portal needed
```

```
• Telegram WebApp SDK integration: expand/collapse, back button, safe area
insets, theme variable binding
```

## `4.5 social-common (shared library)` 

```
The single source of truth for all data contracts. Any change here triggers a
version bump and coordinated updates across service repos. This is the most
important asset to get right in Phase 0.
```

```
• Unified Subject schema: id (UUID), platform (enum: facebook | youtube),
platform_id, name, display_name, followers, post_count, activity_frequency,
status (enum: active | inactive | suspended), last_synced_at, created_at
```

- `Activity snapshot DTO: subject_id, captured_at, followers, post_count, frequency - used by time-series store` 

- `Alert rule DTO: subject_id, rule_type, threshold, cooldown_seconds, channel_id` 

- `Shared error codes and response envelope format` 

- `API client stub interfaces (implemented per service)` 

## `4.6 social-infra` 

```
Centralises all operational concerns. No infrastructure logic lives inside
service repos. This repo is the single place to change deployment topology, add
environments, or rotate secrets.
```

- `Container definitions and orchestration configuration for all services` 

- `CI/CD pipeline definitions: lint, test, build, deploy stages per repo` 

- `Database migration scripts: versioned, rollback-safe, run as part of deployment` 

- `Environment configuration templates: dev, staging, production` 

- `Secrets management integration: API keys, DB credentials, Telegram bot token` 

## `5. Data Architecture` 

```
5.1 Storage layers
Store
What it holds
Access pattern
Notes
Primary DB
Current subject state: profile data, status, latest metrics
Read-heavy; write on sync cycle
Source of truth for API responses
```

```
Time-series Store
Activity snapshots: followers, post_count, frequency over time
Append-only writes; range reads for charts
Enables trend charts in Mini App
Cache Layer
Hot subject data, paginated API responses
Read-first; TTL-based expiry
Reduces DB load on popular subjects
5.2 Unified Subject schema
Defined in social-common. Every service uses this schema - the Collector writes
to it, storage persists it, the Gateway exposes it, the Mini App renders it.
Field
Type
Description
id
UUID
System-generated primary key
platform
Enum
facebook | youtube (extensible)
platform_id
String
Native ID on the source platform (page ID, channel ID)
name
String
Canonical name / handle
display_name
String
Human-readable display name
followers
Integer
Follower / subscriber count at last sync
post_count
Integer
Total posts / videos at last sync
activity_frequency
Float
Average posts per day (rolling 30-day window)
status
Enum
active | inactive | suspended
last_synced_at
Timestamp
When the Collector last successfully fetched data
created_at
Timestamp
When the subject was first added to the system
5.3 Data flow
The canonical data flow from external platform to analyst notification:
• A client or analyst triggers a manual sync for a given subject via the API Gateway
• Data Collector calls the platform API (Facebook or YouTube) with appropriate
credentials and scope
• Raw response is passed to the platform-specific Normaliser which maps it to
the unified Subject schema
• Normalised subject is upserted into the Primary DB; a time-series snapshot is
appended to the Time-series Store
• Cache entries for affected subjects are invalidated
• Alert Engine picks up the updated metrics, evaluates all active alert rules
for the subject, and fires Telegram Bot notifications for any rules that trigger
• Mini App and 3rd-party consumers query the API Gateway, which reads from cache
(or falls back to DB) and returns structured JSON responses
```

```
6. API Design
6.1 Authentication
All API requests require an API Key passed in the Authorization header (Bearer
scheme) or as an X-API-Key header. Keys are stored hashed in the Primary DB. The
gateway validates on every request before any business logic runs. Two key tiers
exist:
• Internal keys: used by Mini App and Alert Engine; higher rate limits, access
to write endpoints (alert rule config)
```

```
• External keys: issued to 3rd-party consumers; read-only access, strict rate
limits, subject to revocation
```

```
6.2 Core endpoints
Method
Path
Description
Auth required
GET
/v1/subjects
List subjects with filtering and pagination
API Key
GET
/v1/subjects/:id
Get single subject by ID
API Key
GET
/v1/subjects/:id/activity
Get time-series activity data for a subject
API Key
POST
/v1/subjects/:id/sync
Trigger on-demand data sync for a subject
API Key
GET
/v1/subjects/search
Search subjects by name or platform_id
API Key
GET
/v1/alerts
List alert rules (internal key only)
Internal Key
PUT
/v1/alerts/:subject_id
Configure alert rules for a subject (Mini App)
Internal Key
GET
/v1/health
Service health check
None
6.3 Rate limiting
Rate limits are enforced per API Key at the gateway level. Requests exceeding
the limit receive a 429 response with a Retry-After header indicating when the
window resets. Limits are configurable per key tier in the DB.
Key tier
Requests / minute
Requests / day
Burst allowance
External (default)
60
10,000
10 requests in 1 second
External (elevated)
200
50,000
20 requests in 1 second
Internal
```

```
1,000
Unlimited
100 requests in 1 second
```

```
7. Alerting System Design
```

```
7.1 Alert rule model
Alert rules are stored as data in the Primary DB and are fully configurable by
analysts through the Telegram Mini App without any code deployments. Each rule
is scoped to a specific subject.
Rule type
Description
Example threshold
follower_spike
Follower count increases by more than X% between consecutive manual syncs
> 10% increase
follower_drop
Follower count decreases by more than X%
> 5% decrease
activity_spike
Post frequency exceeds X posts per day
> 5 posts/day
activity_silence
No new posts detected for X consecutive manual syncs
3 consecutive manual syncs
status_change
Subject status changes (e.g. active to suspended)
Any status change
```

```
7.2 Alert deduplication
A subject entering an anomalous state will trigger exactly one alert per
cooldown window. The Alert Engine maintains a sent_alerts log and checks for
recent alerts of the same type and subject before firing. This prevents
notification floods when a subject sustains an unusual activity level across
multiple manual sync cycles.
```

```
7.3 Telegram Bot notification format
Each alert is sent as a formatted Telegram message to the configured chat ID.
The message includes the subject name, platform, the alert type that triggered,
the current metric value vs the baseline, and a timestamp. Deep links into the
Mini App for quick context access should be included where the platform supports
them.
```

```
8. Execution Roadmap (Zero to Hero)
The roadmap sequences work to de-risk the highest-weight items first and ensure
each phase produces a runnable, testable artifact - not just design documents.
```

```
Phase 0 - Foundation (Week 0)
Goal: everything is ready to build on Day 1
Create all 6 repositories with branch protection, PR conventions, and lint
configuration
Define and publish v1.0 of the unified Subject schema in social-common
Set up social-infra: local dev environment, DB migrations scaffold, basic CI
pipeline
Agree on coding conventions, PR description template, and daily progress
reporting format
Validate Facebook Graph API access and required permission scopes (highest-risk
item - do this first)
```

```
Phase 1 - Data Collector (Weeks 1-2)
Goal: data is flowing into storage from both platforms automatically
Facebook Graph API client: page data, followers, post count, activity frequency,
all public fields
```

```
YouTube Data API v3 client: channel stats, subscriber count, video count, upload
frequency
Normaliser: map both platform responses to unified Subject schema
Persist to Primary DB (current state) and Time-series Store (snapshots)
On-demand Sync: triggered manually via API request, retry / exponential back-off
Error handling: quota exceeded, partial data, network failures - log and recover
```

```
Phase 2 - Public API Gateway (Weeks 3-4)
Goal: data is accessible to all consumers through a stable, documented API
REST endpoints: /v1/subjects, /v1/subjects/:id, /v1/subjects/:id/activity
API Key authentication middleware: validate, reject invalid keys with 401
Rate limiting: per-key quotas, 429 with Retry-After
Query params: filter by platform, status, date range; pagination (page + limit)
Cache integration: read from cache first, fallback to DB, TTL-based invalidation
OpenAPI / Swagger docs: complete enough for external integrators to onboard
unassisted
```

```
Phase 3 - Telegram Mini App (Weeks 4-6)
Goal: analysts can monitor all subjects from inside Telegram
Subject list screen: name, platform badge, status, follower count, last activity
Search + filter UI: by platform, priority, status - all combinable
Subject detail screen: time-series charts of follower trends and post frequency
Summary dashboard: total subjects tracked, alerts today, most active platforms
Alert config panel: configure alert thresholds per subject directly in the Mini
App
Telegram WebApp SDK integration: lifecycle events, safe areas, theme variables
```

```
Phase 4 - Alert Engine (Weeks 6-7)
Goal: analysts receive automatic notifications when subjects behave unusually
Anomaly detector: compare current metrics against rolling baseline, flag
significant deviations
Alert rules engine: read per-subject rules from DB, evaluate after each manual sync
Telegram Bot service: send formatted alert messages to configured chat IDs
Deduplication: one alert per event per cooldown window, sustained anomalies do
not flood
Alert log: full history queryable from Mini App
```

```
Phase 5 - Hardening & Handover (Week 8)
Goal: the system is production-ready, observable, and documented
End-to-end smoke tests: ingest → store → API → Mini App → alert
Structured logging and health-check endpoints on every service
README per repo: local setup, env vars, how to run, how to test
Lint clean on all PRs, no repeated convention violations, PR descriptions
complete
Load test the API Gateway at expected peak traffic
```

```
9. Key Risks & Mitigations
Risk
Severity
Probability
Mitigation
Facebook API access / permission scopes insufficient
High
High
Validate API access and exact permission grants on Day 1, before any development
begins. A token without the right scopes returns empty data silently.
Subject schema changes mid-development
High
Medium
Lock schema in social-common Phase 0. Any change goes through a versioned
migration process. All services pin to a specific version.
Telegram Mini App WebApp rendering quirks
```

```
Medium
High
Test in actual Telegram (not just a browser) from the first day of Mini App
development. Viewport, safe areas, and theming behave differently in the
Telegram WebView.
Platform API rate limit exhaustion during sync
Medium
Medium
Implement exponential back-off and per-platform rate-limit configuration from the
start. Never assume quota is unlimited.
Alert noise causing analyst fatigue
Medium
Medium
Implement deduplication and cooldown windows before any alerts are enabled.
Default thresholds should be conservative.
Time-series data volume growth
Low
High
Design the time-series store with a retention policy and downsampling strategy
from day one. Raw snapshots retained for 90 days; aggregated data indefinitely.
```

## `10. Code Quality Standards` 

```
Quality is a first-class concern in this platform, not an afterthought. The
following standards apply to all service repositories and are enforced through
CI/CD.
```

## `10.1 Pull request standards` 

```
• Every PR must have a description explaining: what changed, why it changed, and
how to test it
```

```
• No lint errors when the PR is submitted - run lint locally before pushing
```

```
• The same convention error must not appear more than twice across PRs from the
same author
```

```
• Logic that is not immediately obvious must have an inline comment explaining
the intent
```

```
10.2 Progress and communication
```

```
• Daily progress report: what was completed, what is in progress, what is
blocked
```

```
• Any task blocked for more than 2 hours must be escalated - do not silently
work around it
```

```
• No task can be reported as late without prior notice - flag delays as soon as
they are anticipated
```

```
• Feedback from code review must be acknowledged and acted on within one working
day
```

```
11. Starter Repositories & Recommended Tech Stack
No single public repository implements this full system end to end. The
combination of multi-platform ingestion, time-series storage, a secured public
API, a Telegram Mini App, and an alert bot is custom to this project. The
recommendation below is therefore split: reuse well-maintained building blocks
for the genuinely solved sub-problems, and build the differentiated logic from
zero.
```

```
11.1 Starter repositories to clone
Repository
Use for
Why
Telegram-Mini-Apps/reactjs-template (official org, MIT)
social-mini-app
Official Telegram Mini Apps team template. Pre-wires the tma.js SDK, theming,
viewport handling, and safe-area insets - directly addresses the Mini App
WebView risk noted in Section 9.
```

```
telegraf/telegraf (9.1k stars, MIT, actively maintained)
social-alert-engine (dependency, not a clone)
De facto standard Telegram Bot framework for Node.js. Full Bot API coverage,
built-in Fastify/Express webhook support. Install as a library, do not fork.
```

```
11.2 Repositories reviewed and rejected
Repository
Verdict
Reason
TID-Lab/aggie
Reference only, do not fork
Closest conceptual match (ingests and normalises social data) but unmaintained
for years and built around CrowdTangle, which has been shut down. Useful only
for schema design ideas.
openstream/open-social-media-monitoring
Reject
Abandoned PHP/MySQL keyword-monitoring tool for legacy Twitter/Facebook APIs.
Wrong stack, wrong era, unmaintained.
Kuew / ib777 social-media-monitoring-open-source forks
Reject
Generic reputation-management clones with no clear architecture match or
maintenance activity.
```

```
11.3 Recommended language and framework per repository
Repository
Language
Framework / key libraries
Rationale
social-data-collector
TypeScript (Node.js)
BullMQ, PostgreSQL driver
I/O-bound scheduled API calls suit Node's event loop. BullMQ (Redis-backed)
provides retry, back-off, and per-platform rate-limit queues without hand-
rolling a scheduler.
social-api-gateway
TypeScript (Node.js)
Fastify, Zod, Redis client
Fastify offers 2-3x the throughput of Express plus native JSON-schema validation
and OpenAPI generation - satisfies the Swagger requirement with minimal extra
code.
social-alert-engine
TypeScript (Node.js)
Telegraf, BullMQ
Telegraf is the standard, well-maintained Telegram Bot framework. Reuses the
same BullMQ patterns as the collector for consistency.
social-mini-app
TypeScript
React, Vite, @telegram-apps/sdk
Official Telegram Mini Apps recommendation. Fast HMR, small bundle, first-class
React bindings for theming and lifecycle events.
social-common
TypeScript
Zod, npm workspaces
Zod schemas double as runtime validators and compile-time types - one definition
used everywhere, eliminating schema drift.
social-infra
YAML / Dockerfile
Docker, Docker Compose, GitHub Actions
Docker Compose is sufficient at 4-service scale. No Kubernetes complexity until
real multi-region or autoscaling needs emerge.
```

```
11.4 Why one language end to end
TypeScript is recommended across every service rather than mixing languages by
service type, for four concrete reasons:
```

```
• The same Subject schema (Zod / TS types) is imported in every service - the
compiler catches mismatches before they reach runtime
```

```
• One language the whole team can hire for, review, and rotate across services
without a ramp-up cost
```

```
• Every service in this system is I/O-bound (API calls, DB reads, HTTP serving)
- none of it benefits from a CPU-heavy-compute language
```

```
• The official Telegram Mini Apps and Telegraf ecosystems are TypeScript-first,
with the best documentation and community support in that exact stack
```

```
Appendix A - Evaluation Weight Mapping
The following table maps the 5 evaluated tasks from the probationary assessment
to their corresponding repositories and phases in this architecture document.
```

```
Task #
Evaluation task
Weight
Repo(s)
Phase
1
Data collection from Facebook & YouTube
30%
social-data-collector, social-common
Phase 1
2
Telegram Mini App - subject monitoring & alerts
25%
social-mini-app
Phase 3
3
Independent data store & public API endpoint
25%
social-api-gateway, social-infra
Phase 2
4
Code quality
10%
All repos
All phases
5
Independent problem-solving
10%
All repos
All phases
Appendix B - Glossary
Term
Definition
Subject
A social media entity being monitored (Facebook page, YouTube channel, or public
profile)
Normaliser
A component that maps platform-specific API responses to the unified Subject
schema
Sync cycle
One complete execution of the Job Scheduler for a given platform and set of
subjects
Alert rule
A configurable condition that triggers a Telegram notification when met (e.g.
follower drop > 5%)
Cooldown window
A time period after an alert fires during which duplicate alerts for the same
event are suppressed
DXA
```

```
Device-independent unit used in Word document layout (1440 DXA = 1 inch)
Internal key
An API key with elevated privileges used by the Mini App and Alert Engine
External key
```

```
An API key issued to third-party consumers with read-only access and strict rate
limits
```

```
Social Intelligence PlatformArchitecture & Design Document
```

```
Confidential - Internal Use OnlyPage 1
```


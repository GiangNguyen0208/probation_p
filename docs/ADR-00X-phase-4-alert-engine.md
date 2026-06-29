# ADR-00X: Phase 4 — Alert Engine Architecture Decisions

**Status:** Accepted
**Date:** 2026-06-25
**Phase:** Phase 4 — Alert Engine

## Context

Phase 4 introduces a new standalone service, `social-alert-engine`, responsible for
evaluating alert rules against subject activity data and delivering Telegram
notifications. This service sits alongside the existing `social-data-collector`
(crawls + persists subject/activity data) and `social-api-gateway` (public REST API).

Four architectural questions needed to be settled before implementation could
proceed. This ADR records the decisions and the reasoning behind each, including
trade-offs that were considered and rejected.

## Decision 1 — Separate Celery app, not shared with the collector

**Decision:** `social-alert-engine` runs its own Celery app (`celery_app.py`), with
its own Beat scheduler, pointed at the same Redis broker/backend used by the
collector.

**Reasoning:**
- Keeps the two services independently deployable — the alert engine can be
  scaled, restarted, or rolled back without touching the collector's worker pool.
- Cross-service task dispatch uses `send_task()` with a string task name
  (`'social-alert-engine.tasks.evaluate_subject_alerts'`), so the collector does
  **not** need to import alert-engine code. This avoids a Python-level dependency
  between the two services — only a Redis-level coupling, which is acceptable.

**Trade-off accepted:** Task name strings are not type-checked across the
boundary. A rename of the task function in `social-alert-engine` without a
corresponding update in the collector's `send_task()` call will fail silently
at runtime (task simply never executes, no import error). Mitigation: cover this
with an integration test that asserts the task name string resolves to a
registered task in `social-alert-engine`'s Celery app.

## Decision 2 — Raw HTTP for Telegram delivery, not aiogram

**Decision:** `notifier.py` uses `httpx` to POST directly to
`https://api.telegram.org/bot{token}/sendMessage`, mirroring the pattern already
used in the gateway's `bot.py`.

**Reasoning:**
- The alert engine only sends outgoing messages — no webhook handling, no
  polling, no command routing. aiogram's framework features (dispatcher,
  filters, FSM) solve problems this service doesn't have.
- Consistency with the existing gateway pattern reduces the number of HTTP
  client patterns engineers need to learn across the codebase.

**Trade-off accepted:** If a future phase needs richer Telegram interaction
(inline buttons, callback queries, multi-step flows), this raw-HTTP approach
will need to be revisited or replaced. This is considered acceptable scope for
a future ADR rather than a reason to adopt a heavier framework now.

## Decision 3 — `alert_logs` ownership: revised to alert-engine's own migration

**Original proposal:** `alert_logs` created in the collector's migration history,
following the same pattern as `alert_rules`, with the gateway and alert engine
mirroring it as read-only models.

**Revised decision:** `alert_logs` is owned by **`social-alert-engine`'s own
Alembic migration history**, pointed at the same database. The collector and
gateway mirror it as read-only models (same mirroring pattern, reversed
direction).

**Reasoning:**
- The ownership convention being followed elsewhere in this system is
  "the service that **writes** to a table owns its migration; services that
  only read mirror it as a read-only model."
- `alert_rules` is correctly owned by the collector because the collector reads
  it during sync to know which rules apply to a subject — but `alert_rules` rows
  are written via the gateway's CRUD endpoints, not the collector. (Worth a
  follow-up note: by the same logic, `alert_rules` write-ownership sits with the
  gateway, not the collector — this ADR does not change that decision, since it
  was made in an earlier phase, but flags it for awareness.)
- `alert_logs` rows are exclusively written by the alert engine
  (`evaluator.py`, after a rule fires). Neither the collector nor the gateway
  ever inserts into this table. Placing the migration in the collector creates
  a dependency in the wrong direction: any future schema change to
  `alert_logs` (e.g. adding `escalation_level`) requires modifying a different
  service's migration history than the one that actually needs the new column.
- This directly undermines Decision 1's goal of independent deployability: if
  `social-alert-engine`'s schema changes require a `social-data-collector`
  release, the two services are no longer independently deployable in
  practice, only in process topology.

**Trade-off accepted:** The system now has Alembic migration history split
across three services (collector, gateway for `alert_rules`-adjacent
schema if applicable, alert-engine) instead of one central history. This adds
operational overhead — multiple `alembic upgrade head` commands to run across
services during a full deployment, and multiple `alembic_version` tracking
points in the shared database. This is accepted because schema-ownership
correctness is judged more important than centralized migration tooling
convenience; if this becomes painful in practice, a future ADR could
consolidate all migrations into a single "schema service," but that is out of
scope here.

**Action item:** Update Step 2 and Step 3 of the implementation plan:
- Remove `social-data-collector/migrations/versions/0003_add_alert_logs.py`.
- Add `social-alert-engine/migrations/versions/0001_add_alert_logs.py` (or
  appropriately numbered if alert-engine already has prior migrations).
- Collector and gateway add read-only `AlertLogModel` mirrors, same as planned.

## Decision 4 — Baseline window: time-based, not count-based

**Original proposal:** `compute_baseline(subject_id)` reads the last 10 activity
snapshots (fixed count), requires at least 3 to compute a baseline.

**Revised decision:** `compute_baseline(subject_id, window_hours=24,
min_snapshots=3)` reads snapshots where `created_at >= now - window_hours`,
and still requires at least `min_snapshots` within that window to return a
baseline; otherwise returns `None`.

**Reasoning:**
- A fixed count of snapshots does not have a stable meaning across subjects or
  over time, because snapshot frequency depends on the sync interval
  (`alert_evaluation_interval_seconds`, and the collector's own sync schedule).
  10 snapshots at a 5-minute sync interval span under an hour; 10 snapshots at
  a 1-hour interval span nearly half a day. The same `window=10` parameter
  produces baselines with very different real-world meaning depending on
  unrelated scheduling config.
- Count-based windows are also distorted by sync gaps: if a subject's crawl
  fails for a period and then catches up, 10 "most recent" snapshots could be
  clustered within a much shorter real time span than intended, making the
  baseline overly sensitive to a brief period rather than representative of
  normal variation.
- A time-based window keeps baseline semantics stable and independent of sync
  scheduling: "what does normal look like over the last 24 hours" stays a
  fixed, interpretable definition regardless of how often syncs happen to run.

**Trade-off accepted:** Subjects with very infrequent syncs (e.g. once every 12
hours) may rarely accumulate 3+ snapshots within a 24h window, meaning
`compute_baseline` returns `None` more often and evaluation is skipped more
often for those subjects. This is the same "insufficient data" behavior already
planned in the Risks table (sparse subjects → skip evaluation), so no new
failure mode is introduced — it simply triggers more often for low-frequency
subjects. If this proves too aggressive in practice, `window_hours` can be made
configurable per alert rule or per subject in a later iteration.

## Summary of Changes to the Implementation Plan

| Item | Original plan | Revised |
|---|---|---|
| `alert_logs` migration | `social-data-collector/migrations/versions/0003_add_alert_logs.py` | `social-alert-engine/migrations/versions/000N_add_alert_logs.py` |
| Collector role re: `alert_logs` | Owner | Read-only mirror |
| `compute_baseline` signature | `compute_baseline(subject_id)`, last 10 snapshots | `compute_baseline(subject_id, window_hours=24, min_snapshots=3)`, time-windowed |
| Celery app split | Confirmed, unchanged | Confirmed, unchanged |
| Telegram delivery | Confirmed, unchanged | Confirmed, unchanged |

## Follow-up flagged (not actioned in this ADR)

- `alert_rules` write-ownership currently sits with the collector's migration
  despite being written via the gateway's CRUD endpoints. This predates Phase 4
  and is out of scope here, but the same reasoning in Decision 3 would apply if
  revisited.
- `status_change` rule tie-break behavior (when baseline status distribution is
  evenly split) should be explicitly documented in `evaluator.py`: prefer the
  most recent status on a tie, to avoid non-deterministic flakiness between
  evaluation runs.

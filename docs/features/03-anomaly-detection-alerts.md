# Feature Spec: Enhanced Alert Engine — Trend Detection & Anomaly Alerts

## Overview

Upgrade the alert system from simple **threshold-based rules** ("followers > 1000") to **statistical anomaly detection** that understands normal behaviour and alerts on deviations. This is a critical differentiator in social media intelligence: Hootsuite has "predictive crisis monitoring" and "real-time mention alerts", Sprout Social has "Message Spike Alerts" that fire when volume is higher than usual, and Brandwatch uses statistical baselines for trend detection. Our current system computes a 24-hour baseline with a minimum of 3 snapshots; this feature extends the evaluator to support **spike detection**, **drop detection**, and **stall detection** using rolling averages and standard deviations computed from the `activity_snapshots` hypertable.

## Goals

- [ ] Extend `AlertRuleType` enum with three new rule types: `SPIKE`, `DROP`, `STALL`.
- [ ] `SPIKE`: Fire when a metric exceeds the **2-sigma (or configurable) threshold** above the rolling baseline. E.g. "Followers grew >20% above normal this week."
- [ ] `DROP`: Fire when a metric drops below the **2-sigma threshold** below the rolling baseline. E.g. "Engagement dropped >30% below normal."
- [ ] `STALL`: Fire when **no activity snapshot** has been recorded for the subject in the last `X` hours (configurable per rule). E.g. "No new posts in 72 hours."
- [ ] Baseline computation window is **configurable per rule** (default 7 days, min 3 snapshots) — moving beyond the current fixed 24h/3-snapshot baseline.
- [ ] Mini App alert config panel shows **descriptions and recommended thresholds** for each rule type, with a "Smart detect" toggle that auto-fills statistical thresholds.
- [ ] Alert logs distinguish between `threshold` (user-configured) and `baseline_value` + `std_dev` (computed) for transparency.

## Non-Goals

- **We do NOT implement machine learning anomaly detection.** Pure statistical baselines (rolling mean + std dev) are sufficient for MVP. ML (isolation forest, LSTM) is deferred to Phase 6+.
- **We do NOT add anomaly detection to the gateway.** All evaluation logic stays in `social-alert-engine` (existing architecture). The gateway only serves alert rules and logs read-only.
- **We do NOT support multi-metric compound rules.** Rules are single-metric only (e.g. "followers AND engagement" combined is out of scope).
- **We do NOT implement automatic rule tuning.** The system does not auto-adjust thresholds based on historical alert frequency. Users must manually tune.
- **We do NOT change the existing `THRESHOLD` rule type.** It continues to work exactly as before — this is an additive change.

## Architecture

### Data Model Changes

#### Modified Enum: `AlertRuleType`

**File:** `social_common/enums.py`

```python
class AlertRuleType(str, Enum):
    THRESHOLD = "threshold"   # Existing: fixed value comparison
    SPIKE = "spike"           # NEW: metric > baseline + N*std_dev
    DROP = "drop"             # NEW: metric < baseline - N*std_dev
    STALL = "stall"           # NEW: no snapshot in X hours
```

#### Modified Schema: `AlertRule`

**File:** `social_common/schemas.py`

```python
class AlertRule(BaseModel):
    # ... existing fields ...
    rule_type: AlertRuleType
    threshold: float          # For THRESHOLD: the fixed value
                              # For SPIKE/DROP: the multiplier (e.g. 2.0 = 2-sigma)
                              # For STALL: hours of inactivity (e.g. 72.0)
    baseline_window_hours: int = Field(default=168, ge=24, le=720)  # NEW: 7 days default
    baseline_min_snapshots: int = Field(default=3, ge=2, le=50)       # NEW
    # cooldown_seconds, channel_id, is_active ... unchanged
```

#### Modified Schema: `AlertLog`

```python
class AlertLog(BaseModel):
    # ... existing fields ...
    # NEW fields for anomaly transparency:
    baseline_value: float | None = None
    std_dev: float | None = None
    window_hours: int | None = None
```

**Note:** `baseline_value` and `std_dev` are optional because `THRESHOLD` and `STALL` rules do not compute them. The database column must be nullable.

### Service Interactions

```
┌─────────────────────────────┐
│ social-data-collector       │
│  (sync cycle completes)     │── send_task("evaluate-subject", subject_id)
└─────────────────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ social-alert-engine         │
│  Celery worker              │
│                             │
│  ┌───────────────────────┐  │
│  │ 1. Fetch active rules │  │── SELECT * FROM alert_rules WHERE subject_id=? AND is_active=true
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 2. Fetch snapshots    │  │── SELECT * FROM activity_snapshots WHERE subject_id=? AND captured_at >= NOW()-window
│  │    (baseline data)    │  │
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 3. Compute baseline   │  │── rolling mean, std dev, min/max
│  │    (mean + std_dev)   │  │
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 4. Evaluate rule      │  │
│  │    SPIKE: val > mean + threshold*std_dev  │
│  │    DROP:  val < mean - threshold*std_dev  │
│  │    STALL: last_snapshot_age > threshold hours │
│  └───────────────────────┘  │
│             │               │
│  ┌───────────────────────┐  │
│  │ 5. Write AlertLog     │  │── INSERT INTO alert_logs
│  │    + Notify Telegram  │  │── POST to Bot API
│  └───────────────────────┘  │
└─────────────────────────────┘
```

### Baseline Computation Algorithm

```python
def compute_baseline(
    snapshots: list[ActivitySnapshot],
    metric: str,          # "followers" | "post_count" | "frequency"
    window_hours: int,
    min_snapshots: int,
) -> tuple[float, float] | None:
    """Return (mean, std_dev) for the given metric over the window.

    Returns None if not enough snapshots.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    filtered = [s for s in snapshots if s.captured_at >= cutoff]
    
    if len(filtered) < min_snapshots:
        return None
    
    values = [getattr(s, metric) for s in filtered]
    mean = statistics.mean(values)
    std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
    return mean, std_dev
```

**Edge case:** If `std_dev == 0` (all values identical), SPIKE/DROP rules with `threshold > 0` will never trigger. This is correct behaviour — a flat line has no anomalies.

## Code Changes

### 1. `social-common` — Enum & Schema Extensions

**File:** `social_common/enums.py`

```python
class AlertRuleType(str, Enum):
    THRESHOLD = "threshold"
    SPIKE = "spike"
    DROP = "drop"
    STALL = "stall"
```

**File:** `social_common/schemas.py`

```python
class AlertRule(BaseModel):
    # ... existing fields ...
    rule_type: AlertRuleType
    threshold: float
    baseline_window_hours: int = Field(default=168, ge=24, le=720)
    baseline_min_snapshots: int = Field(default=3, ge=2, le=50)
    # ...

class AlertLog(BaseModel):
    # ... existing fields ...
    baseline_value: float | None = None
    std_dev: float | None = None
    window_hours: int | None = None
```

### 2. `social-alert-engine` — Core Logic

**File:** `src/social_alert_engine/baseline.py` (modify)

```python
import statistics
from datetime import UTC, datetime, timedelta

from social_common.schemas import ActivitySnapshot


def compute_baseline(
    snapshots: list[ActivitySnapshot],
    metric: str,
    window_hours: int,
    min_snapshots: int,
) -> tuple[float, float] | None:
    """Return (mean, std_dev) for metric over window. None if insufficient data."""
    cutoff = datetime.now(UTC) - timedelta(hours=window_hours)
    filtered = [s for s in snapshots if s.captured_at >= cutoff]

    if len(filtered) < min_snapshots:
        return None

    values = [getattr(s, metric) for s in filtered]
    mean = statistics.mean(values)
    # statistics.stdev raises StatisticsError if < 2 values
    std_dev = statistics.stdev(values) if len(values) >= 2 else 0.0
    return mean, std_dev
```

**File:** `src/social_alert_engine/evaluator.py` (modify)

```python
from social_common.enums import AlertRuleType
from social_common.schemas import ActivitySnapshot, AlertRule


def evaluate_rule(
    rule: AlertRule,
    latest_snapshot: ActivitySnapshot,
    baseline_snapshots: list[ActivitySnapshot],
) -> dict | None:
    """Evaluate a single alert rule against latest snapshot + baseline.

    Returns dict with trigger details if rule fires, else None.
    """
    if rule.rule_type == AlertRuleType.THRESHOLD:
        # Existing logic unchanged
        metric_value = getattr(latest_snapshot, _metric_for_rule(rule))
        if metric_value > rule.threshold:
            return {
                "triggered": True,
                "metric_value": metric_value,
                "threshold": rule.threshold,
                "message": f"Metric {metric_value} exceeded threshold {rule.threshold}",
            }
        return None

    if rule.rule_type in (AlertRuleType.SPIKE, AlertRuleType.DROP):
        metric = _metric_for_rule(rule)  # "followers" | "post_count" | "frequency"
        baseline = compute_baseline(
            baseline_snapshots,
            metric=metric,
            window_hours=rule.baseline_window_hours,
            min_snapshots=rule.baseline_min_snapshots,
        )
        if baseline is None:
            return None  # Not enough data to establish baseline
        
        mean, std_dev = baseline
        metric_value = getattr(latest_snapshot, metric)
        
        # threshold field serves as sigma multiplier for SPIKE/DROP
        sigma_threshold = rule.threshold  # e.g. 2.0
        
        if rule.rule_type == AlertRuleType.SPIKE:
            if metric_value > mean + sigma_threshold * std_dev:
                return {
                    "triggered": True,
                    "metric_value": metric_value,
                    "threshold": mean + sigma_threshold * std_dev,
                    "baseline_value": mean,
                    "std_dev": std_dev,
                    "window_hours": rule.baseline_window_hours,
                    "message": (
                        f"Spike detected: {metric}={metric_value} "
                        f"is {sigma_threshold}σ above baseline (mean={mean:.1f}, σ={std_dev:.1f})"
                    ),
                }
        else:  # DROP
            if metric_value < mean - sigma_threshold * std_dev:
                return {
                    "triggered": True,
                    "metric_value": metric_value,
                    "threshold": mean - sigma_threshold * std_dev,
                    "baseline_value": mean,
                    "std_dev": std_dev,
                    "window_hours": rule.baseline_window_hours,
                    "message": (
                        f"Drop detected: {metric}={metric_value} "
                        f"is {sigma_threshold}σ below baseline (mean={mean:.1f}, σ={std_dev:.1f})"
                    ),
                }
        return None

    if rule.rule_type == AlertRuleType.STALL:
        # threshold field is hours of inactivity
        max_hours = rule.threshold
        last_sync_age_hours = (datetime.now(UTC) - latest_snapshot.captured_at).total_seconds() / 3600
        if last_sync_age_hours > max_hours:
            return {
                "triggered": True,
                "metric_value": last_sync_age_hours,
                "threshold": max_hours,
                "message": f"Stall detected: no activity in {last_sync_age_hours:.1f} hours (limit: {max_hours}h)",
            }
        return None

    return None


def _metric_for_rule(rule: AlertRule) -> str:
    """Map rule_type to the metric field name in ActivitySnapshot.
    
    This is a convention; we may need to add a 'metric' field to AlertRule
    schema to make this explicit.
    """
    # For now, hardcode: all rules operate on 'followers' by default
    # Future: AlertRule.metric field
    return "followers"
```

**File:** `src/social_alert_engine/tasks.py` (modify)

- Extend `evaluate_subject(subject_id)` task to pass `baseline_snapshots` (windowed) to `evaluate_rule`, not just the latest snapshot.
- Fetch `baseline_snapshots` with a time range query: `captured_at >= NOW() - max(baseline_window_hours)`.

**File:** `src/social_alert_engine/models.py` (modify)

- Add nullable columns to `AlertLogModel`: `baseline_value`, `std_dev`, `window_hours`.
- Create migration in `social-alert-engine/migrations/versions/`.

### 3. `social-api-gateway` — Schema Validation

**File:** `src/social_api_gateway/alerts/schemas.py`

- Update `AlertRuleCreate` and `AlertRuleUpdate` to accept `baseline_window_hours` and `baseline_min_snapshots`.
- Add validation: for `SPIKE`/`DROP`, `threshold` must be `> 0` (it's a multiplier). For `STALL`, `threshold` must be `>= 1` (hours).
- Update `AlertLogResponse` to include new fields.

**File:** `src/social_api_gateway/alerts/models.py`

- Add `baseline_value`, `std_dev`, `window_hours` nullable columns (read-only mirror).

**File:** `src/social_api_gateway/alerts/repository.py`

- No functional changes needed if columns are added to model; list/get methods already return all columns.

### 4. `social-mini-app` — Alert Config Panel Enhancement

**File:** `src/api/hooks.ts`

No changes needed if OpenAPI types are regenerated; the new fields appear in `components["schemas"]["AlertRuleCreate"]`.

**File:** `src/components/panels/AlertConfigPanel.tsx` (modify)

```tsx
// Rule type selector now has 4 options:
// - "Threshold" (fixed value)
// - "Spike" (above normal)
// - "Drop" (below normal)
// - "Stall" (no activity)

// When "Spike" or "Drop" is selected:
// - Show "Baseline window" slider (24h - 30d, default 7d)
// - Show "Min snapshots" input (default 3)
// - Show "Sigma threshold" input (default 2.0, step 0.5)
// - Display helper text: "Alert when value is X standard deviations above/below the rolling average"

// When "Stall" is selected:
// - Show "Hours of inactivity" input (default 72)
// - Helper text: "Alert when no new posts/metrics are detected for X hours"

// "Smart detect" toggle:
// - Auto-fills recommended sigma (2.0) and window (7d) for SPIKE/DROP
// - Auto-fills recommended hours (72) for STALL
```

**File:** `src/components/panels/AlertHistoryPanel.tsx` (modify)

```tsx
// For SPIKE/DROP alerts, show additional context:
// "Baseline: 1,234 ± 56 over 7 days"
// "Detected: 1,450 (2.1σ above normal)"
```

## Interface Changes (UI/UX)

### Modified Components

| Component | Change |
|---|---|
| `AlertConfigPanel` | Rule type dropdown expanded to 4 options; conditional fields for baseline window, min snapshots, sigma threshold, stall hours |
| `AlertHistoryPanel` | Show `baseline_value`, `std_dev`, `window_hours` for SPIKE/DROP entries |

### Design Notes (Mobile-First)

- **Rule type as segmented control, not dropdown.** 4 options fit horizontally if abbreviated: "Fixed" | "Spike" | "Drop" | "Stall". If too wide, use 2×2 grid.
- **Progressive disclosure.** Only show baseline/sigma fields when Spike/Drop selected. Only show hours input when Stall selected.
- **Smart defaults.** Pre-fill sensible values so user can just tap "Create" without tuning.
- **Visual explanation.** Add a tiny inline chart showing "normal range (shaded) vs. current value (dot)" when editing a Spike/Drop rule — helps user understand what will trigger.

## Files Relevant (Complete List)

| # | File | Action | Description |
|---|---|---|---|
| 1 | `social-common/social_common/enums.py` | Modify | Add `SPIKE`, `DROP`, `STALL` to `AlertRuleType` |
| 2 | `social-common/social_common/schemas.py` | Modify | Add `baseline_window_hours`, `baseline_min_snapshots` to `AlertRule`; add `baseline_value`, `std_dev`, `window_hours` to `AlertLog` |
| 3 | `social-api-gateway/src/social_api_gateway/alerts/schemas.py` | Modify | Update `AlertRuleCreate`/`Update` validation; add new fields to response |
| 4 | `social-api-gateway/src/social_api_gateway/alerts/models.py` | Modify | Add nullable columns to `AlertLogModel` mirror |
| 5 | `social-alert-engine/migrations/versions/` | Create | Migration: add `baseline_value`, `std_dev`, `window_hours` to `alert_logs` |
| 6 | `social-alert-engine/src/social_alert_engine/models.py` | Modify | Add nullable columns to `AlertLogModel` |
| 7 | `social-alert-engine/src/social_alert_engine/baseline.py` | Modify | Extend `compute_baseline` to accept configurable window + min_snapshots |
| 8 | `social-alert-engine/src/social_alert_engine/evaluator.py` | Modify | Add SPIKE, DROP, STALL evaluation logic |
| 9 | `social-alert-engine/src/social_alert_engine/tasks.py` | Modify | Pass baseline_snapshots to evaluator |
| 10 | `social-alert-engine/src/social_alert_engine/notifier.py` | Modify | Format messages with baseline context for SPIKE/DROP |
| 11 | `social-api-gateway/scripts/export_openapi.py` | Modify | Regenerate (automatic) |
| 12 | `social-mini-app/src/api/types.ts` | Regenerate | From OpenAPI spec |
| 13 | `social-mini-app/src/components/panels/AlertConfigPanel.tsx` | Modify | Add rule type options + conditional config fields |
| 14 | `social-mini-app/src/components/panels/AlertHistoryPanel.tsx` | Modify | Show baseline context for anomaly alerts |

## Failure Scenarios

| Scenario | Detection | Impact | Mitigation |
|---|---|---|---|
| **Not enough snapshots for baseline** | `len(filtered) < baseline_min_snapshots` | Rule never triggers | Log "insufficient data for baseline"; show "Waiting for more data" in alert status |
| **Zero standard deviation (flat line)** | `std_dev == 0` | SPIKE/DROP never trigger | Correct behaviour — no variation means no anomaly |
| **Very high sigma threshold** | User sets `threshold = 10.0` | Rule effectively never triggers | UI warns: "10σ is extremely rare (≈ never). Consider 2-3σ." |
| **STALL rule on subject that syncs weekly** | `threshold=24h` but sync is weekly | False positive every week | User education: stall threshold should be > sync interval + margin |
| **Baseline window longer than data retention** | `window_hours=720` but only 30 days of snapshots | Baseline computed on partial data | Limit `baseline_window_hours` max to data retention policy (e.g. 720h = 30d); validate in gateway schema |
| **Cooldown shorter than sync interval** | `cooldown=300s` but sync is hourly | Same alert fires multiple times | UI warning: "Cooldown should be >= expected sync interval" |
| **Telegram message too long with baseline info** | Message > 4096 chars | Telegram API rejects | Truncate message; baseline details stay in AlertLog |

## Testing Strategy

### Unit Tests (Alert Engine)

- **Baseline computation:**
  - 10 snapshots over 7 days, values `[100, 101, 100, 102, 100, 99, 100, 101, 100, 100]` → mean=100.3, std_dev≈0.82
  - Latest value=105 → 105 > 100.3 + 2×0.82=101.94 → SPIKE fires
  - Latest value=95 → 95 < 100.3 - 2×0.82=98.66 → DROP fires
- **Insufficient data:** 2 snapshots with `min_snapshots=3` → no trigger.
- **Flat line:** 10 snapshots all value=100 → std_dev=0 → SPIKE with threshold=2.0 never fires.
- **STALL:** Last snapshot 100 hours ago, threshold=72 → fires.

### Integration Tests

- Create alert rule `SPIKE` with `threshold=2.0`, `window_hours=24`, `min_snapshots=3`.
- Insert 3 baseline snapshots (value=100 each) + 1 latest snapshot (value=110).
- Run `evaluate-one <subject_id>` → verify AlertLog created with `baseline_value=100.0`, `std_dev=0.0` (wait, if all 3 are 100, std_dev=0, so 110 > 100 + 0 = 100 → fires because mean + 2*0 = 100, and 110 > 100). Actually with 3 identical values, mean=100, std_dev=0, trigger is `110 > 100 + 2*0` → true. So flat lines with large absolute jumps still trigger. Good.

### Mini App Tests

- `npm run lint && npm run typecheck && npm run build`.
- Manual: Create SPIKE rule → verify baseline fields appear in config; verify alert history shows baseline context after trigger.

## Rollout Plan

### Phase 1: Schema & Migration (Day 1)
1. Extend `AlertRuleType` enum in `social-common`.
2. Add new fields to `AlertRule` and `AlertLog` schemas.
3. Create alert-engine migration for `alert_logs` columns.

### Phase 2: Alert Engine Logic (Day 2-3)
1. Extend `compute_baseline` to accept configurable window.
2. Implement SPIKE, DROP, STALL evaluation in `evaluator.py`.
3. Update `tasks.py` to fetch baseline_snapshots.
4. Update `notifier.py` message formatting.

### Phase 3: Gateway Validation (Day 4)
1. Update `AlertRuleCreate`/`Update` schemas with new fields + validation.
2. Update `AlertLogModel` mirror with new columns.
3. Regenerate OpenAPI.

### Phase 4: Mini App UI (Day 5-6)
1. Update `AlertConfigPanel` with new rule types and conditional fields.
2. Update `AlertHistoryPanel` to show baseline context.

### Phase 5: Verification (Day 7)
1. Run `pytest` in alert-engine.
2. Run `pytest` in gateway.
3. Build Mini App.
4. Manual end-to-end: create SPIKE rule → trigger sync with artificial data → verify alert fires with baseline info.

## Open Questions

1. **Which metric for SPIKE/DROP?** Currently all rules implicitly target `followers`. Should we add a `metric` field to `AlertRule` ("followers" | "post_count" | "frequency") so users can choose? Recommend yes — add `metric: str = "followers"` to `AlertRule` schema. This is a small additive change.
2. **STALL on metric vs. overall sync:** Should STALL check `last_synced_at` on the `Subject` table, or `captured_at` on the most recent `ActivitySnapshot`? They should be the same, but `Subject.last_synced_at` is more reliable. Recommend using `Subject.last_synced_at` for STALL.
3. **Baseline window default:** Is 7 days (168h) the right default? Hootsuite often uses 30-day baselines for trend detection. 7 days is more responsive to recent changes; 30 days is more stable. Recommend making it user-configurable (which we do) with 7d as default.
4. **Should THRESHOLD rules also support baseline comparison?** E.g. "alert when followers > baseline + 500"? Not for MVP — keep THRESHOLD as absolute fixed value. Users who want relative thresholds use SPIKE/DROP.
5. **Alert fatigue prevention:** If a subject is very volatile, SPIKE/DROP with 2σ might fire frequently. Should we add an optional "minimum alerts per day" limit? Defer — users can tune threshold or cooldown.

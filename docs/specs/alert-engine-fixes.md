# Spec: Alert-Engine Bug Fixes + Unit Tests

## Objective

Fix two bugs in the alert-engine evaluator and add targeted unit tests so the
core evaluation logic has a safety net before Phase 5 changes. The existing
codebase has lint, type, and pytest passing — this work keeps that clean.

Success criteria:
- Hardcoded cooldown replaced with `rule.cooldown_seconds` read from the DB model
- First-evaluation false-positive for `STATUS_CHANGE` eliminated
- At least 5 unit tests covering evaluator and baseline logic, all green
- `ruff`, `mypy`, `pytest` all clean after changes

## Tech Stack

- Python 3.11+, `pytest>=8`, `structlog`, `SQLAlchemy>=2.0`
- No new dependencies. Tests use in-memory SQLite where DB is needed.

## Commands

```
# from social-alert-engine/
ruff check .
mypy src
pytest -v
```

## Files Touched

| File | Change |
|---|---|
| `src/social_alert_engine/evaluator.py` | Fix Bug 1 (cooldown) + Bug 2 (first-eval status) |
| `tests/test_evaluator.py` | New file — 5+ unit tests |
| `tests/conftest.py` | New file — shared test fixtures |

## Code Style

Existing pattern in evaluator uses instance-level `get_logger()` and explicit
`FiredAlert` / `_evaluate_*` functions. New tests follow the same style as
existing gateway tests: `async def` with explicit assertions, no external
dependencies.

<example>
```python
# Good — matches existing style
def test_follower_spike_triggers():
    rule = _make_rule(AlertRuleType.FOLLOWER_SPIKE, threshold=2.0)
    subject = _make_subject(followers=500)
    baseline = BaselineResult(followers=[100, 110, 120], frequencies=[1.0, 1.1, 1.2])
    fired = _evaluate_follower_rules([rule], subject, baseline, "Test")
    assert len(fired) == 1
```
</example>

## Testing Strategy

**Framework:** pytest (already configured in `pyproject.toml`)

**Test locations:** All new tests in `tests/test_evaluator.py`. Fixtures in
`tests/conftest.py`.

**No external deps:** Tests use in-memory objects / fake sessions, never real
DB or Redis.

**Test cases:**

1. **FOLLOWER_SPIKE** — current >= mean + threshold * stdev → fires
2. **FOLLOWER_DROP** — current <= mean - threshold * stdev → fires
3. **No trigger below threshold** — current below both spike/drop → no alert
4. **ACTIVITY_SILENCE** — raw frequency < threshold → fires
5. **STATUS_CHANGE first evaluation** — no prior log → no false positive
6. **Cooldown respects rule.cooldown_seconds** — not hardcoded 3600
7. **No baseline data** — follower/activity rules skipped, status_change still runs

## Boundaries

- **Always:** Run `ruff check . && mypy src && pytest -v` before committing.
  Keep test count >= 5. Use explicit assertions (no `assert True` placeholders).
- **Ask first:** Adding new dependencies, modifying the notifier/baseline/health
  modules (out of scope), changing the production behavior of non-bug paths.
- **Never:** Remove existing lint/mypy configs, introduce new hardcoded values,
  leave dead code commented out, or write tests that require a real DB/Redis.

## Success Criteria

- [ ] `_check_cooldown` reads `rule.cooldown_seconds` from the `AlertRuleModel`
      instead of hardcoding `3600`
- [ ] `_evaluate_status_change` does NOT fire on first evaluation when no prior
      log exists (i.e., only fires on an *actual* transition)
- [ ] 7 unit tests exist in `tests/test_evaluator.py`, all passing
- [ ] `ruff check .` — 0 issues
- [ ] `mypy src` — 0 issues
- [ ] `pytest -v` — 7/7 passed

## Open Questions

None — requirements are well-defined from the initial audit.

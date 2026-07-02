# Spec: social-data-collector Data Completeness Update

## Objective
Close the data-collection and API-client gaps between the pilot `test-getinsight` project and the production `social-data-collector`. Specifically: make the collector as resilient and complete as the pilot for Facebook, YouTube, and TikTok, while keeping all production features (persistence, scheduling, unified schema) intact.

## Tech Stack
- Python 3.11+ (same as repo)
- `httpx` + `tenacity` for HTTP clients
- `sqlalchemy` + PostgreSQL/TimescaleDB for persistence
- `celery` for background sync
- `cryptography.fernet` for credential encryption

## Commands
```bash
cd social-data-collector

# Lint / typecheck / test (run in order)
ruff check .
ruff format --check .
mypy src
pytest

# Manual sync (debugging)
python -m social_data_collector.main sync-tiktok-one <open_id>
python -m social_data_collector.main sync-facebook-one <page_id>

# Platform seeding (includes TikTok after this spec)
python -m social_data_collector.main seed-platforms

# Credential storage CLI
python -m social_data_collector.main store-credential \
  --platform-slug tiktok \
  --label "My TikTok Account" \
  --data '{"access_token":"..."}'

# Probe tool
python scripts/probe_facebook.py --page-id <id> --token <token> --pretty
```

## Project Structure (relevant files)
```
social-data-collector/
  src/social_data_collector/
    clients/
      facebook.py       # per-metric insights
      tiktok.py         # pagination loop
    normalizers/
      facebook.py       # enriched extended_data
    scheduler/
      tasks.py          # TikTok sync uses paginated video list
    main.py             # new CLI subcommands
  scripts/
    probe_facebook.py   # new diagnostic script
```

## Code Style
Same as existing collector: Ruff (line-length 100), strict mypy, `from __future__ import annotations`, type-hint everything, use structlog for logs, wrap external calls in try/except and map to `PermanentPlatformError` / `TransientPlatformError`.

Example snippet:
```python
from __future__ import annotations

from typing import Any

from social_common.errors import PermanentPlatformError


def get_page_insights(...) -> list[dict[str, Any]]:
    results = []
    for metric in metrics:
        try:
            response = self.get_json(...)
            results.extend(response.get("data", []))
        except PermanentPlatformError as exc:
            if "nonexisting field" in str(exc) or "Permissions error" in str(exc):
                logger.warning("insight.metric_skipped", metric=metric, error=str(exc))
                continue
            raise
    return results
```

## Testing Strategy
- Unit tests for `clients/tiktok.py` with mocked multi-page responses.
- Unit tests for `clients/facebook.py` per-metric resilience (one metric 400, others succeed).
- Normalizer fixture tests for extended_data mapping.
- No integration tests required for the CLI tooling (developer-only).

## Boundaries
- **Always:** Run `ruff check . && mypy src && pytest` before finishing a task.
- **Ask first:** Adding new dependencies, changing DB schema, modifying OAuth callback endpoints in the gateway.
- **Never:** Remove existing normalizer fields, break the `Subject` schema contract, commit real tokens.

## Success Criteria
1. `TikTokClient.get_video_list()` returns up to 100 videos when a user has >20 videos.
2. `FacebookClient.get_page_insights()` calls each metric individually; a single bad metric no longer fails the entire batch.
3. `FacebookNormalizer` explicitly maps `category`, `about`, `description`, `username`, `website`, `verification_status`, `cover` into `extended_data`.
4. `python -m social_data_collector.main seed-platforms` creates the TikTok platform row.
5. `python -m social_data_collector.main store-credential` encrypts and stores a credential blob in `platform_credentials`.
6. `scripts/probe_facebook.py` runs without crashing and dumps a JSON file with field catalog + metric probe results.
7. All existing unit tests pass; new tests cover changes above.

## Open Questions (resolved)
1. Store tokens in `platform_credentials`? → Yes, provide a CLI utility.
2. TikTok video cap? → 100 videos max.
3. Facebook insights period? → `day` only; no multi-period support needed.
4. Probe tool owner? → Developer-only CLI script.

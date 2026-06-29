# social-api-gateway

Python FastAPI gateway skeleton for public and internal platform reads.

Phase 0 prepares tooling and service conventions. Route implementation starts in Phase 2.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Commands

```bash
ruff check .
ruff format --check .
pytest
mypy src
uvicorn social_api_gateway.main:app --reload
```

## API Direction

- All routes live under `/v1`.
- FastAPI OpenAPI output is the public integration contract.
- API key auth rejects invalid keys before business logic.
- Redis is used for cache and rate-limit counters.
- DTOs come from `social-common`.

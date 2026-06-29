# CI Template Notes

Use these checks as the minimum Phase 0 quality gate.

## Python Backend Repositories

Applies to `social-common`, `social-data-collector`, `social-api-gateway`, and `social-alert-engine`.

```bash
python -m pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
mypy src
```

## Mini App

Applies to `social-mini-app`.

```bash
npm ci
npm run lint
npm run typecheck
npm run build
```

## Infrastructure

Applies to `social-infra`.

```bash
docker compose config
alembic -c alembic.ini current
```

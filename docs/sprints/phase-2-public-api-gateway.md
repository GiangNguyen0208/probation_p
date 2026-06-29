# Phase 2 - Public API Gateway

Window: Weeks 3-4  
Sprints: Sprints 3-4  
Goal: data is accessible to all consumers through a stable, documented API.

## Scope

Build the API Gateway as the single external interface for Mini App, Alert Engine, and third-party consumers. The gateway reads from storage and cache only; it does not call platform APIs.

Implement the gateway in Python with FastAPI. Use Pydantic models from `social-common`, SQLAlchemy for database access, Redis for caching and rate-limit counters, and FastAPI's generated OpenAPI documentation as the public integration contract.

## Repositories

- `social-api-gateway`
- `social-common`
- `social-infra`

## Sprint 3 Focus

- Implement FastAPI service skeleton with `/v1` route prefix.
- Add health check endpoint.
- Implement API key authentication with hashed key lookup.
- Add `GET /v1/subjects`, `GET /v1/subjects/:id`, and `GET /v1/subjects/:id/activity`.
- Validate query params using shared Pydantic schemas or compatible request models.
- Return shared response envelopes and structured errors.

## Sprint 4 Focus

- Add pagination, platform/status/date filters, and subject search.
- Implement per-key rate limiting with `429` and `Retry-After`.
- Integrate Redis cache for hot subject reads and paginated list responses.
- Add internal-key-only alert endpoints and sync trigger endpoint: `GET /v1/alerts`, `PUT /v1/alerts/:subject_id`, and `POST /v1/subjects/:id/sync`.
- Generate OpenAPI/Swagger documentation through FastAPI for all public routes.
- Add API integration tests for auth, rate limits, pagination, cache fallback, and error responses.

## Deliverables

- Secured REST API under `/v1`.
- API key auth for internal and external key tiers.
- Rate limiting by key tier.
- Filtered, paginated subject reads.
- Activity time-series read endpoint.
- Alert rule endpoints and on-demand sync trigger endpoint for internal consumers.
- OpenAPI/Swagger documentation.
- Python test suite covering route handlers, dependencies, auth behavior, and response validation.

## Acceptance Criteria

- Requests without a valid key are rejected with `401` before business logic.
- External keys are read-only and rate limited.
- Internal keys can access alert rule endpoints.
- Cache miss falls back to DB and returns the same response shape as cache hit.
- API docs are sufficient for a new integrator to call the API without asking for hidden details.

## Dependencies

- Collector writes usable subject and activity data.
- API key storage and migrations exist.
- Redis and database services are available from local infrastructure.
- Shared Pydantic models are versioned and compatible with the API response envelope.

## Risks

- Incorrect auth boundaries could expose internal write endpoints.
- Cache invalidation must align with on-demand collector writes.
- Poor pagination defaults can create avoidable DB load.
- Async database and Redis usage must be consistent to avoid connection pool exhaustion.

## Sprint Exit

The phase exits when consumers can securely read subjects and activity history through documented endpoints, and internal clients can manage alert rules through the same gateway.

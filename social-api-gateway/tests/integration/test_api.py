"""End-to-end integration tests for the API gateway.

Covers cross-cutting behavior that crosses multiple modules: auth
+ rate limit headers, cache hit/miss, OpenAPI, error envelope shape.
"""

from __future__ import annotations


async def test_health_endpoint(client):
    response = await client.get("/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] in ("ok", "degraded")
    assert "checks" in body
    assert "database" in body["checks"]


async def test_openapi_json_available(client):
    response = await client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert "paths" in spec
    assert "/v1/subjects" in spec["paths"]
    assert "/v1/subjects/{subject_id}" in spec["paths"]
    assert "/v1/subjects/{subject_id}/activity" in spec["paths"]
    assert "/v1/health" in spec["paths"]


async def test_docs_page_available(client):
    response = await client.get("/docs")
    assert response.status_code == 200
    assert "swagger" in response.text.lower()


async def test_unauthenticated_request_returns_401_envelope(client):
    response = await client.get("/v1/subjects")
    assert response.status_code == 401
    body = response.json()
    assert "error" in body
    assert "code" in body["error"]
    assert "message" in body["error"]


async def test_invalid_key_returns_401_envelope(client):
    response = await client.get(
        "/v1/subjects", headers={"X-API-Key": "ghn_test_invalid_value_here"}
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "invalid_api_key"


async def test_rate_limit_headers_present(client, internal_api_key):
    response = await client.get("/v1/subjects", headers={"X-API-Key": internal_api_key})
    assert response.status_code == 200
    assert "X-RateLimit-Limit-Minute" in response.headers
    assert "X-RateLimit-Limit-Day" in response.headers
    assert "X-RateLimit-Remaining-Minute" in response.headers
    assert "X-RateLimit-Remaining-Day" in response.headers
    assert response.headers["X-RateLimit-Limit-Minute"] == "1000"


async def test_external_key_has_stricter_limit(client, external_api_key):
    response = await client.get("/v1/subjects", headers={"X-API-Key": external_api_key})
    assert response.status_code == 200
    assert response.headers["X-RateLimit-Limit-Minute"] == "60"


async def test_rate_limit_exceeded_returns_429(client, external_api_key, monkeypatch):
    """Verify 429 + Retry-After when the rate limit service reports exceeded."""
    from social_api_gateway.rate_limit.service import (
        RateLimitResult,
        RateLimitService,
    )

    async def mock_check(self, key_id, tier):
        return RateLimitResult(
            allowed=False,
            count_minute=100,
            count_day=100,
            limit_minute=60,
            limit_day=10000,
            retry_after_seconds=42,
        )

    monkeypatch.setattr(RateLimitService, "check", mock_check)
    response = await client.get("/v1/subjects", headers={"X-API-Key": external_api_key})
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "42"
    body = response.json()
    assert body["error"]["code"] == "rate_limited"


async def test_cache_hit_returns_same_data_as_db(client, internal_api_key, more_subjects):
    r1 = await client.get("/v1/subjects?limit=10", headers={"X-API-Key": internal_api_key})
    assert r1.status_code == 200
    r2 = await client.get("/v1/subjects?limit=10", headers={"X-API-Key": internal_api_key})
    assert r2.status_code == 200
    assert r1.json() == r2.json()


async def test_full_workflow_list_then_get(client, internal_api_key, more_subjects):
    list_response = await client.get(
        "/v1/subjects?limit=2", headers={"X-API-Key": internal_api_key}
    )
    assert list_response.status_code == 200
    subjects = list_response.json()["data"]
    assert len(subjects) == 2

    first_id = subjects[0]["id"]
    get_response = await client.get(
        f"/v1/subjects/{first_id}", headers={"X-API-Key": internal_api_key}
    )
    assert get_response.status_code == 200
    assert get_response.json()["data"]["id"] == first_id


async def test_bearer_token_works(client, internal_api_key):
    response = await client.get(
        "/v1/subjects",
        headers={"Authorization": f"Bearer {internal_api_key}"},
    )
    assert response.status_code == 200

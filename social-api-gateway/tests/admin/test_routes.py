"""Tests for the admin endpoints (POST /v1/admin/keys)."""

from __future__ import annotations

from httpx import AsyncClient


async def test_create_key_requires_admin_token(client: AsyncClient):
    """No Authorization header -> 401 with `missing_admin_token`."""
    response = await client.post(
        "/v1/admin/keys",
        json={"name": "Test Key", "tier": "internal"},
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "missing_admin_token"


async def test_create_key_rejects_wrong_admin_token(client: AsyncClient):
    """Wrong bearer token -> 403 with `invalid_admin_token`."""
    response = await client.post(
        "/v1/admin/keys",
        json={"name": "Test Key", "tier": "internal"},
        headers={"Authorization": "Bearer this_is_not_the_right_token"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["error"]["code"] == "invalid_admin_token"


async def test_create_key_returns_raw_key_once(client: AsyncClient, admin_token: str):
    """Happy path: returns 201 with the raw api_key in `data`."""
    response = await client.post(
        "/v1/admin/keys",
        json={"name": "Swagger Dev Key", "tier": "internal"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201
    body = response.json()
    assert "data" in body
    assert "meta" in body

    data = body["data"]
    assert data["name"] == "Swagger Dev Key"
    assert data["tier"] == "internal"
    assert data["key_prefix"].startswith("ghn_live")
    assert len(data["key_prefix"]) == 16
    assert data["api_key"].startswith("ghn_live_")
    assert len(data["api_key"]) == 41
    # UUID-like id and ISO datetime
    assert len(data["id"]) == 36
    assert "T" in data["created_at"]


async def test_create_key_does_not_require_api_key(client: AsyncClient, admin_token: str):
    """The admin endpoint works without X-API-Key - only the admin token matters."""
    response = await client.post(
        "/v1/admin/keys",
        json={"name": "Test", "tier": "internal"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 201


async def test_create_key_supports_each_tier(client: AsyncClient, admin_token: str):
    """All three tiers are accepted."""
    for tier in ("internal", "external_default", "external_elevated"):
        response = await client.post(
            "/v1/admin/keys",
            json={"name": f"Test {tier}", "tier": tier},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert response.status_code == 201, f"tier={tier} failed: {response.text}"
        assert response.json()["data"]["tier"] == tier


async def test_create_key_rejects_missing_name(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/v1/admin/keys",
        json={"tier": "internal"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


async def test_create_key_rejects_invalid_tier(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/v1/admin/keys",
        json={"name": "Test", "tier": "super_admin"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


async def test_create_key_rejects_empty_name(client: AsyncClient, admin_token: str):
    response = await client.post(
        "/v1/admin/keys",
        json={"name": "", "tier": "internal"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422


async def test_created_key_can_authenticate_normal_endpoints(client: AsyncClient, admin_token: str):
    """End-to-end: create a key, then use it to call GET /v1/subjects."""
    create = await client.post(
        "/v1/admin/keys",
        json={"name": "End-to-end Test", "tier": "internal"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert create.status_code == 201
    new_key = create.json()["data"]["api_key"]

    response = await client.get(
        "/v1/subjects",
        headers={"X-API-Key": new_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"] == []
    assert body["meta"]["total"] == 0

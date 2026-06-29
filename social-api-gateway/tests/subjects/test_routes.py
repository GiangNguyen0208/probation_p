"""Tests for /v1/subjects endpoints."""

from __future__ import annotations


async def test_list_subjects_returns_envelope(client, internal_api_key, more_subjects):
    response = await client.get("/v1/subjects", headers={"X-API-Key": internal_api_key})
    assert response.status_code == 200
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["page"] == 1
    assert body["meta"]["limit"] == 20
    assert body["meta"]["total"] == 5
    assert len(body["data"]) == 5


async def test_list_subjects_pagination(client, internal_api_key, more_subjects):
    response = await client.get(
        "/v1/subjects?page=1&limit=2", headers={"X-API-Key": internal_api_key}
    )
    body = response.json()
    assert body["meta"]["page"] == 1
    assert body["meta"]["limit"] == 2
    assert body["meta"]["total"] == 5
    assert len(body["data"]) == 2


async def test_list_subjects_filter_by_platform(client, internal_api_key, more_subjects):
    response = await client.get(
        "/v1/subjects?platform=facebook", headers={"X-API-Key": internal_api_key}
    )
    body = response.json()
    # Indices 0, 2, 4 are facebook
    assert body["meta"]["total"] == 3
    for subject in body["data"]:
        assert subject["platform"] == "facebook"


async def test_list_subjects_filter_by_status(client, internal_api_key, more_subjects):
    response = await client.get(
        "/v1/subjects?status=active", headers={"X-API-Key": internal_api_key}
    )
    body = response.json()
    for subject in body["data"]:
        assert subject["status"] == "active"


async def test_list_subjects_invalid_platform_returns_422(client, internal_api_key):
    response = await client.get(
        "/v1/subjects?platform=tiktok", headers={"X-API-Key": internal_api_key}
    )
    assert response.status_code == 422


async def test_list_subjects_search(client, internal_api_key, more_subjects):
    response = await client.get("/v1/subjects?q=Subject 1", headers={"X-API-Key": internal_api_key})
    body = response.json()
    assert body["meta"]["total"] == 1
    assert body["data"][0]["name"] == "Subject 1"


async def test_list_subjects_page_must_be_positive(client, internal_api_key):
    response = await client.get("/v1/subjects?page=0", headers={"X-API-Key": internal_api_key})
    assert response.status_code == 422


async def test_list_subjects_limit_capped(client, internal_api_key):
    response = await client.get("/v1/subjects?limit=10000", headers={"X-API-Key": internal_api_key})
    assert response.status_code == 422


async def test_get_subject_by_id(client, internal_api_key, sample_subject):
    response = await client.get(
        f"/v1/subjects/{sample_subject.id}",
        headers={"X-API-Key": internal_api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id"] == str(sample_subject.id)
    assert body["data"]["name"] == "Example Page"


async def test_get_subject_not_found(client, internal_api_key):
    response = await client.get(
        "/v1/subjects/00000000-0000-0000-0000-000000000000",
        headers={"X-API-Key": internal_api_key},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "subject_not_found"


async def test_get_subject_invalid_uuid(client, internal_api_key):
    response = await client.get(
        "/v1/subjects/not-a-uuid",
        headers={"X-API-Key": internal_api_key},
    )
    assert response.status_code == 422


async def test_get_activity_returns_snapshots(
    client, internal_api_key, sample_subject, sample_snapshots
):
    response = await client.get(
        f"/v1/subjects/{sample_subject.id}/activity",
        headers={"X-API-Key": internal_api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["meta"]["total"] == 3
    captured = [s["captured_at"] for s in body["data"]]
    assert captured == sorted(captured, reverse=True)


async def test_get_activity_404_for_missing_subject(client, internal_api_key):
    response = await client.get(
        "/v1/subjects/00000000-0000-0000-0000-000000000000/activity",
        headers={"X-API-Key": internal_api_key},
    )
    assert response.status_code == 404
    body = response.json()
    assert body["error"]["code"] == "subject_not_found"

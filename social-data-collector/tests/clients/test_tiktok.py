"""Tests for the TikTok Display API client."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from social_data_collector.clients.base import RetryPolicy
from social_data_collector.clients.tiktok import TikTokClient


def _make_client() -> TikTokClient:
    return TikTokClient(
        access_token="test-token",
        retry_policy=RetryPolicy(max_attempts=1, initial_seconds=1, max_seconds=1),
        timeout_seconds=5.0,
    )


def _video(id: str) -> dict[str, Any]:
    return {
        "id": id,
        "create_time": 1700000000,
        "title": f"Video {id}",
        "like_count": 10,
        "comment_count": 2,
        "share_count": 1,
    }


class TestGetVideoList:
    def test_single_page_no_pagination(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client()
        called = {"count": 0}

        def _fake_request(
            method: str,
            url: str,
            params: dict[str, Any] | None = None,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
        ) -> Any:
            called["count"] += 1
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "data": {"videos": [_video("v1")], "has_more": False, "cursor": 0},
                "error": {"code": "ok"},
            }
            return resp

        monkeypatch.setattr(client._client, "request", _fake_request)
        result = client.get_video_list("uid123")
        assert len(result) == 1
        assert result[0]["id"] == "v1"
        assert called["count"] == 1

    def test_pagination_collects_multiple_pages(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client()
        calls: list[dict[str, Any]] = []

        def _fake_request(
            method: str,
            url: str,
            params: dict[str, Any] | None = None,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
        ) -> Any:
            body = json or {}
            cursor = body.get("cursor", 0)
            calls.append(body)
            resp = MagicMock()
            resp.status_code = 200
            if cursor == 0:
                resp.json.return_value = {
                    "data": {
                        "videos": [_video("v1"), _video("v2")],
                        "has_more": True,
                        "cursor": 2,
                    },
                    "error": {"code": "ok"},
                }
            else:
                resp.json.return_value = {
                    "data": {"videos": [_video("v3")], "has_more": False, "cursor": 2},
                    "error": {"code": "ok"},
                }
            return resp

        monkeypatch.setattr(client._client, "request", _fake_request)
        result = client.get_video_list("uid123", overall_limit=100)
        assert len(result) == 3
        assert [v["id"] for v in result] == ["v1", "v2", "v3"]
        assert len(calls) == 2

    def test_overall_limit_stops_early(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client()
        calls: list[dict[str, Any]] = []

        def _fake_request(
            method: str,
            url: str,
            params: dict[str, Any] | None = None,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
        ) -> Any:
            body = json or {}
            cursor = body.get("cursor", 0)
            calls.append(body)
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {
                "data": {
                    "videos": [_video(f"v{cursor + 1}"), _video(f"v{cursor + 2}")],
                    "has_more": True,
                    "cursor": cursor + 2,
                },
                "error": {"code": "ok"},
            }
            return resp

        monkeypatch.setattr(client._client, "request", _fake_request)
        result = client.get_video_list("uid123", overall_limit=3)
        assert len(result) == 3
        assert len(calls) == 2  # first page 2 videos, second page 1 video then capped

    def test_error_returns_partial(self, monkeypatch: pytest.MonkeyPatch) -> None:
        client = _make_client()
        calls: list[dict[str, Any]] = []

        def _fake_request(
            method: str,
            url: str,
            params: dict[str, Any] | None = None,
            headers: dict[str, Any] | None = None,
            json: dict[str, Any] | None = None,
        ) -> Any:
            body = json or {}
            cursor = body.get("cursor", 0)
            calls.append(body)
            resp = MagicMock()
            if cursor == 0:
                resp.status_code = 200
                resp.json.return_value = {
                    "data": {"videos": [_video("v1")], "has_more": True, "cursor": 1},
                    "error": {"code": "ok"},
                }
            else:
                resp.status_code = 401
                resp.text = "unauthorized"
            return resp

        monkeypatch.setattr(client._client, "request", _fake_request)
        result = client.get_video_list("uid123", overall_limit=100)
        assert len(result) == 1
        assert result[0]["id"] == "v1"

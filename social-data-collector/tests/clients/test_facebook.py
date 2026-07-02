"""Tests for the Facebook Graph API client."""

from __future__ import annotations

import httpx
import pytest
import respx
from social_common.errors import PermanentPlatformError, SubjectNotFoundError

from social_data_collector.clients.base import RetryPolicy
from social_data_collector.clients.facebook import FacebookClient
from social_data_collector.config import FacebookSettings


def _settings() -> FacebookSettings:
    return FacebookSettings(
        graph_api_version="v25.0",
        app_id="test_app_id",
        app_secret="test_secret",
        app_access_token="test_token",
        test_page_id="1234567890",
        test_page_ids="1234567890,9876543210",
    )


def _retry() -> RetryPolicy:
    return RetryPolicy(max_attempts=2, initial_seconds=1, max_seconds=10)


def test_get_page_returns_profile():
    settings = _settings()
    with respx.mock(base_url="https://graph.facebook.com/v25.0") as mock:
        route = mock.get("/1234567890").mock(
            return_value=httpx.Response(200, json={"id": "1234567890", "name": "Example"})
        )
        with FacebookClient(settings, _retry()) as client:
            result = client.get_page("1234567890")
        assert result["id"] == "1234567890"
        assert result["name"] == "Example"
        assert route.called


def test_get_page_maps_404_to_subject_not_found():
    settings = _settings()
    with respx.mock(base_url="https://graph.facebook.com/v25.0") as mock:
        mock.get("/9999999999").mock(
            return_value=httpx.Response(404, json={"error": {"message": "not found"}})
        )
        with FacebookClient(settings, _retry()) as client, pytest.raises(SubjectNotFoundError):
            client.get_page("9999999999")


def test_get_page_maps_401_to_permanent_error():
    settings = _settings()
    with respx.mock(base_url="https://graph.facebook.com/v25.0") as mock:
        mock.get("/1234567890").mock(
            return_value=httpx.Response(401, json={"error": {"message": "unauthorized"}})
        )
        with FacebookClient(settings, _retry()) as client, pytest.raises(PermanentPlatformError):
            client.get_page("1234567890")


def test_get_recent_posts_returns_data_list():
    settings = _settings()
    with respx.mock(base_url="https://graph.facebook.com/v25.0") as mock:
        mock.get("/1234567890/posts").mock(
            return_value=httpx.Response(200, json={"data": [{"id": "p1"}, {"id": "p2"}]})
        )
        with FacebookClient(settings, _retry()) as client:
            posts = client.get_recent_posts("1234567890", limit=10)
        assert len(posts) == 2


def test_get_recent_posts_returns_empty_on_404():
    settings = _settings()
    with respx.mock(base_url="https://graph.facebook.com/v25.0") as mock:
        mock.get("/1234567890/posts").mock(
            return_value=httpx.Response(404, json={"error": {"message": "not found"}})
        )
        with FacebookClient(settings, _retry()) as client:
            posts = client.get_recent_posts("1234567890")
        assert posts == []


def test_client_requires_credentials():
    settings = FacebookSettings(
        graph_api_version="v25.0",
        app_id="",
        app_secret="",
        app_access_token="",
        page_access_token="",
    )
    with pytest.raises(PermanentPlatformError):
        FacebookClient(settings, _retry())


def test_get_page_insights_per_metric_skips_invalid():
    settings = _settings()
    with respx.mock(base_url="https://graph.facebook.com/v25.0") as mock:
        # metric A succeeds
        mock.get("/1234567890/insights", params={"metric": "page_views_total", "period": "day", "access_token": "test_token"}).mock(
            return_value=httpx.Response(200, json={"data": [{"name": "page_views_total", "values": [{"value": 100}]}]})
        )
        # metric B fails with invalid metric
        mock.get("/1234567890/insights", params={"metric": "page_bad_metric", "period": "day", "access_token": "test_token"}).mock(
            return_value=httpx.Response(400, json={"error": {"message": "nonexisting field page_bad_metric"}})
        )
        # metric C succeeds
        mock.get("/1234567890/insights", params={"metric": "page_follows", "period": "day", "access_token": "test_token"}).mock(
            return_value=httpx.Response(200, json={"data": [{"name": "page_follows", "values": [{"value": 50}]}]})
        )
        with FacebookClient(settings, _retry()) as client:
            result = client.get_page_insights(
                "1234567890",
                metrics="page_views_total,page_bad_metric,page_follows",
                period="day",
            )
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert names == {"page_views_total", "page_follows"}


def test_get_page_insights_returns_partial_on_blanket_403():
    settings = _settings()
    with respx.mock(base_url="https://graph.facebook.com/v25.0") as mock:
        # first metric succeeds
        mock.get("/1234567890/insights", params={"metric": "page_views_total", "period": "day", "access_token": "test_token"}).mock(
            return_value=httpx.Response(200, json={"data": [{"name": "page_views_total", "values": [{"value": 100}]}]})
        )
        # second metric triggers blanket 403 (no read_insights permission)
        mock.get("/1234567890/insights", params={"metric": "page_follows", "period": "day", "access_token": "test_token"}).mock(
            return_value=httpx.Response(403, json={"error": {"message": "Permissions error"}})
        )
        with FacebookClient(settings, _retry()) as client:
            result = client.get_page_insights(
                "1234567890",
                metrics="page_views_total,page_follows",
                period="day",
            )
        # Should return partial results instead of crashing
        assert len(result) == 1
        assert result[0]["name"] == "page_views_total"

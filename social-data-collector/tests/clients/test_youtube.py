"""Tests for the YouTube Data API v3 client."""

from __future__ import annotations

import httpx
import pytest
import respx
from social_common.errors import PermanentPlatformError, SubjectNotFoundError

from social_data_collector.clients.base import RetryPolicy
from social_data_collector.clients.youtube import YouTubeClient
from social_data_collector.config import YouTubeSettings


def _settings() -> YouTubeSettings:
    return YouTubeSettings(
        api_key="test_api_key",
        test_channel_id="UC_x5XG1OV2P6uZZ5FSM9Ttw",
        test_channel_ids="UC_x5XG1OV2P6uZZ5FSM9Ttw",
    )


def _retry() -> RetryPolicy:
    return RetryPolicy(max_attempts=2, initial_seconds=1, max_seconds=10)


def test_get_channel_returns_response():
    settings = _settings()
    with respx.mock(base_url="https://www.googleapis.com/youtube/v3") as mock:
        route = mock.get("/channels").mock(
            return_value=httpx.Response(200, json={"items": [{"id": "UC_x5XG1OV2P6uZZ5FSM9Ttw"}]})
        )
        with YouTubeClient(settings, _retry()) as client:
            result = client.get_channel("UC_x5XG1OV2P6uZZ5FSM9Ttw")
        assert "items" in result
        assert route.called


def test_get_uploads_playlist_id_extracts_field():
    response = {
        "items": [
            {
                "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                "contentDetails": {"relatedPlaylists": {"uploads": "UU_x5XG1OV2P6uZZ5FSM9Ttw"}},
            }
        ]
    }
    playlist_id = YouTubeClient._extract_uploads_playlist_id(response)
    assert playlist_id == "UU_x5XG1OV2P6uZZ5FSM9Ttw"


def test_get_uploads_playlist_id_returns_none_on_empty_items():
    assert YouTubeClient._extract_uploads_playlist_id({"items": []}) is None


def test_get_recent_uploads_returns_items():
    settings = _settings()
    channel_response = {
        "items": [
            {
                "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                "contentDetails": {"relatedPlaylists": {"uploads": "UU_x5XG1OV2P6uZZ5FSM9Ttw"}},
            }
        ]
    }
    with respx.mock(base_url="https://www.googleapis.com/youtube/v3") as mock:
        route = mock.get("/playlistItems").mock(
            return_value=httpx.Response(
                200,
                json={"items": [{"contentDetails": {"videoPublishedAt": "2026-06-18T00:00:00Z"}}]},
            )
        )
        with YouTubeClient(settings, _retry()) as client:
            items = client.get_recent_uploads(channel_response)
        assert len(items) == 1
        assert route.called


def test_get_channel_maps_404_to_subject_not_found():
    settings = _settings()
    with respx.mock(base_url="https://www.googleapis.com/youtube/v3") as mock:
        mock.get("/channels").mock(
            return_value=httpx.Response(404, json={"error": {"message": "not found"}})
        )
        with YouTubeClient(settings, _retry()) as client, pytest.raises(SubjectNotFoundError):
            client.get_channel("UC_does_not_exist")


def test_client_requires_credentials():
    settings = YouTubeSettings(api_key="")
    with pytest.raises(PermanentPlatformError):
        YouTubeClient(settings, _retry())

"""Tests for the YouTube normalizer."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from social_common.enums import Platform, SubjectStatus

from social_data_collector.normalizers.base import NormalizerError
from social_data_collector.normalizers.youtube import YouTubeNormalizer

SYNCELED_AT = datetime(2026, 6, 19, 12, 0, 0, tzinfo=UTC)


def test_normalize_active_channel(youtube_channel_fixture, youtube_playlist_items_fixture):
    normalizer = YouTubeNormalizer()
    subject = normalizer.normalize(
        platform_id=youtube_channel_fixture["items"][0]["id"],
        raw_response=youtube_channel_fixture,
        activity_data=youtube_playlist_items_fixture["items"],
        synced_at=SYNCELED_AT,
    )
    assert subject.platform == Platform.YOUTUBE
    assert subject.platform_id == "UC_x5XG1OV2P6uZZ5FSM9Ttw"
    assert subject.name == "Example Channel"
    assert subject.followers == 50000
    # videoCount=120 is higher than the 2-item sample, so the larger wins.
    assert subject.post_count == 120
    assert subject.status == SubjectStatus.ACTIVE
    # Both uploads fall inside the 30-day window.
    # Frequency = 2 posts / 30 days ≈ 0.0667.
    assert 0.06 <= subject.activity_frequency <= 0.07
    # viewCount from statistics is stored in extended_data.
    assert subject.extended_data is not None
    assert subject.extended_data["view_count"] == 1000000


def test_normalize_inactive_channel_zero_followers_zero_videos():
    """A channel with 0 subscribers and 0 videos is INACTIVE."""
    response = {
        "items": [
            {
                "id": "UC_empty",
                "snippet": {"title": "Empty Channel"},
                "statistics": {"subscriberCount": "0", "videoCount": "0", "viewCount": "0"},
            }
        ]
    }
    normalizer = YouTubeNormalizer()
    subject = normalizer.normalize(
        platform_id="UC_empty",
        raw_response=response,
        activity_data=[],
        synced_at=SYNCELED_AT,
    )
    assert subject.status == SubjectStatus.INACTIVE
    assert subject.extended_data is None


def test_normalize_empty_items_raises(youtube_playlist_items_fixture):
    normalizer = YouTubeNormalizer()
    with pytest.raises(NormalizerError):
        normalizer.normalize(
            platform_id="UC_x5XG1OV2P6uZZ5FSM9Ttw",
            raw_response={"items": []},
            activity_data=youtube_playlist_items_fixture["items"],
            synced_at=SYNCELED_AT,
        )


def test_normalize_missing_title_raises(youtube_channel_fixture, youtube_playlist_items_fixture):
    response = {
        "items": [
            {
                "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                "snippet": {},
                "statistics": {"subscriberCount": "10", "videoCount": "0"},
            }
        ]
    }
    normalizer = YouTubeNormalizer()
    with pytest.raises(NormalizerError):
        normalizer.normalize(
            platform_id="UC_x5XG1OV2P6uZZ5FSM9Ttw",
            raw_response=response,
            activity_data=youtube_playlist_items_fixture["items"],
            synced_at=SYNCELED_AT,
        )


def test_normalize_zero_when_statistics_missing(youtube_playlist_items_fixture):
    response = {
        "items": [
            {
                "id": "UC_x5XG1OV2P6uZZ5FSM9Ttw",
                "snippet": {"title": "Example Channel"},
                "contentDetails": {"relatedPlaylists": {"uploads": "UU_x5XG1OV2P6uZZ5FSM9Ttw"}},
            }
        ]
    }
    normalizer = YouTubeNormalizer()
    subject = normalizer.normalize(
        platform_id="UC_x5XG1OV2P6uZZ5FSM9Ttw",
        raw_response=response,
        activity_data=youtube_playlist_items_fixture["items"],
        synced_at=SYNCELED_AT,
    )
    assert subject.followers == 0
    assert subject.post_count == 2


def test_normalize_naive_synced_at_gets_utc(
    youtube_channel_fixture, youtube_playlist_items_fixture
):
    normalizer = YouTubeNormalizer()
    naive = datetime(2026, 6, 19, 12, 0, 0)
    subject = normalizer.normalize(
        platform_id=youtube_channel_fixture["items"][0]["id"],
        raw_response=youtube_channel_fixture,
        activity_data=youtube_playlist_items_fixture["items"],
        synced_at=naive,
    )
    assert subject.last_synced_at.tzinfo is not None
    assert subject.last_synced_at == naive.replace(tzinfo=UTC)

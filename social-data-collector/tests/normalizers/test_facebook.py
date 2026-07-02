"""Tests for the Facebook normalizer."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from social_common.enums import Platform, SubjectStatus

from social_data_collector.normalizers.base import NormalizerError
from social_data_collector.normalizers.facebook import FacebookNormalizer

SYNCELED_AT = datetime(2026, 6, 19, 12, 0, 0, tzinfo=UTC)


def test_normalize_active_page_with_recent_posts(facebook_page_fixture, facebook_posts_fixture):
    normalizer = FacebookNormalizer()
    subject = normalizer.normalize(
        platform_id=facebook_page_fixture["id"],
        raw_response=facebook_page_fixture,
        activity_data=facebook_posts_fixture["data"],
        synced_at=SYNCELED_AT,
    )
    assert subject.platform == Platform.FACEBOOK
    assert subject.platform_id == "1234567890"
    assert subject.name == "Example Page"
    assert subject.display_name == "Example Page"
    assert subject.followers == 12500
    assert subject.post_count == 3
    assert subject.status == SubjectStatus.ACTIVE
    assert subject.last_synced_at == SYNCELED_AT
    # Two posts inside the 30-day window (post_1 and post_2).
    # Frequency = 2 posts / 30 days ≈ 0.0667.
    assert 0.06 <= subject.activity_frequency <= 0.07


def test_normalize_falls_back_to_fan_count(facebook_page_fixture, facebook_posts_fixture):
    page = dict(facebook_page_fixture)
    page.pop("followers_count")
    normalizer = FacebookNormalizer()
    subject = normalizer.normalize(
        platform_id=page["id"],
        raw_response=page,
        activity_data=facebook_posts_fixture["data"],
        synced_at=SYNCELED_AT,
    )
    assert subject.followers == 12500


def test_normalize_zero_followers_when_field_missing(facebook_page_fixture, facebook_posts_fixture):
    page = {
        k: v for k, v in facebook_page_fixture.items() if k not in ("followers_count", "fan_count")
    }
    normalizer = FacebookNormalizer()
    subject = normalizer.normalize(
        platform_id=page["id"],
        raw_response=page,
        activity_data=facebook_posts_fixture["data"],
        synced_at=SYNCELED_AT,
    )
    assert subject.followers == 0


def test_normalize_empty_posts_yields_zero_frequency(facebook_page_fixture):
    normalizer = FacebookNormalizer()
    subject = normalizer.normalize(
        platform_id=facebook_page_fixture["id"],
        raw_response=facebook_page_fixture,
        activity_data=[],
        synced_at=SYNCELED_AT,
    )
    assert subject.post_count == 0
    assert subject.activity_frequency == 0.0
    # followers=12500 > 0, so status stays ACTIVE even with no posts.
    assert subject.status == SubjectStatus.ACTIVE


def test_normalize_inactive_page_zero_followers_zero_posts():
    """A page with 0 followers and 0 posts is INACTIVE."""
    page = {"id": "999", "name": "Dead Page", "followers_count": 0, "fan_count": 0}
    normalizer = FacebookNormalizer()
    subject = normalizer.normalize(
        platform_id="999",
        raw_response=page,
        activity_data=[],
        synced_at=SYNCELED_AT,
    )
    assert subject.status == SubjectStatus.INACTIVE
    assert subject.followers == 0
    assert subject.post_count == 0


def test_normalize_raises_on_missing_name(facebook_page_fixture, facebook_posts_fixture):
    page = {k: v for k, v in facebook_page_fixture.items() if k != "name"}
    normalizer = FacebookNormalizer()
    with pytest.raises(NormalizerError):
        normalizer.normalize(
            platform_id="1234567890",
            raw_response=page,
            activity_data=facebook_posts_fixture["data"],
            synced_at=SYNCELED_AT,
        )


def test_normalize_assigns_uuid(facebook_page_fixture, facebook_posts_fixture):
    normalizer = FacebookNormalizer()
    s1 = normalizer.normalize(
        platform_id=facebook_page_fixture["id"],
        raw_response=facebook_page_fixture,
        activity_data=facebook_posts_fixture["data"],
        synced_at=SYNCELED_AT,
    )
    s2 = normalizer.normalize(
        platform_id=facebook_page_fixture["id"],
        raw_response=facebook_page_fixture,
        activity_data=facebook_posts_fixture["data"],
        synced_at=SYNCELED_AT,
    )
    # Each call produces a fresh UUID; the DB upsert collapses these by
    # (platform, platform_id), so the IDs being different in-memory is
    # expected.
    assert s1.id != s2.id


def test_normalize_maps_extended_fields(facebook_posts_fixture):
    page = {
        "id": "999",
        "name": "Rich Page",
        "followers_count": 100,
        "category": "Media",
        "about": "About text",
        "description": "Desc text",
        "username": "richpage",
        "website": "https://example.com",
        "verification_status": "blue_verified",
        "talking_about_count": 42,
        "cover": {"source": "https://cover.jpg"},
    }
    normalizer = FacebookNormalizer()
    subject = normalizer.normalize(
        platform_id="999",
        raw_response=page,
        activity_data=facebook_posts_fixture["data"],
        synced_at=SYNCELED_AT,
        extended_data={"insights": {"views": 100}},
    )
    assert subject.extended_data is not None
    ed = subject.extended_data
    assert ed["category"] == "Media"
    assert ed["about"] == "About text"
    assert ed["description"] == "Desc text"
    assert ed["username"] == "richpage"
    assert ed["website"] == "https://example.com"
    assert ed["verification_status"] == "blue_verified"
    assert ed["talking_about_count"] == 42
    assert ed["cover"] == {"source": "https://cover.jpg"}
    # Caller-provided extended_data merged on top
    assert ed["insights"] == {"views": 100}

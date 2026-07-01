"""TikTok normalizer.

Maps TikTok Display API v2 responses to the unified Subject schema.
TikTok provides snapshot metrics (follower_count, likes_count, etc.)
but no time-series analytics — extended_data stores raw numbers.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from social_common.enums import Platform, SubjectStatus
from social_common.schemas import Subject

from .base import BaseNormalizer

_ACTIVITY_WINDOW_DAYS = 30


def _compute_activity_frequency(
    videos: list[dict[str, Any]], now: datetime
) -> float:
    """Videos per day over the last 30 days."""
    if not videos:
        return 0.0

    window_start = now - timedelta(days=_ACTIVITY_WINDOW_DAYS)
    recent = 0
    for video in videos:
        create_time = video.get("create_time")
        if not create_time:
            continue
        try:
            ts = datetime.fromtimestamp(int(create_time), tz=UTC)
        except (ValueError, TypeError, OSError):
            continue
        if ts >= window_start:
            recent += 1

    elapsed_days = max((now - window_start).total_seconds() / 86400, 1.0)
    return round(recent / elapsed_days, 4)


def _aggregate_video_stats(
    videos: list[dict[str, Any]],
) -> dict[str, int]:
    """Sum like/comment/share counts across a list of videos.

    TikTok Display API v2 does not expose view_count; only
    like_count, comment_count, and share_count are available.
    """
    totals: dict[str, int] = {
        "like_count": 0,
        "comment_count": 0,
        "share_count": 0,
    }
    for video in videos:
        for key, field in [
            ("like_count", "like_count"),
            ("comment_count", "comment_count"),
            ("share_count", "share_count"),
        ]:
            try:
                totals[key] += int(video.get(field, 0))
            except (TypeError, ValueError):
                continue
    return totals


class TikTokNormalizer(BaseNormalizer):
    def normalize(
        self,
        platform_id: str,
        raw_response: dict[str, Any],
        activity_data: list[dict[str, Any]],
        synced_at: datetime,
    ) -> Subject:
        if synced_at.tzinfo is None:
            synced_at = synced_at.replace(tzinfo=UTC)

        user = raw_response
        open_id = user.get("open_id") or platform_id
        display_name = user.get("display_name") or user.get("username") or "Unknown"
        username = user.get("username") or ""

        try:
            followers = int(user.get("follower_count", 0))
        except (TypeError, ValueError):
            followers = 0
        try:
            following = int(user.get("following_count", 0))
        except (TypeError, ValueError):
            following = 0
        try:
            likes = int(user.get("likes_count", 0))
        except (TypeError, ValueError):
            likes = 0
        try:
            video_count = int(user.get("video_count", 0))
        except (TypeError, ValueError):
            video_count = 0

        post_count = max(video_count, len(activity_data))
        activity_frequency = _compute_activity_frequency(activity_data, synced_at)

        if followers == 0 and post_count == 0 or activity_frequency == 0.0:
            status = SubjectStatus.INACTIVE
        else:
            status = SubjectStatus.ACTIVE

        extended_data: dict[str, Any] = {
            "following_count": following,
            "likes_count": likes,
            "video_count": video_count,
            "username": username,
        }
        if user.get("avatar_url"):
            extended_data["avatar_url"] = user["avatar_url"]
        if user.get("is_verified") is not None:
            extended_data["is_verified"] = bool(user["is_verified"])

        if activity_data:
            totals = _aggregate_video_stats(activity_data)
            extended_data["sample_video_count"] = len(activity_data)
            extended_data["sample_like_count"] = totals["like_count"]
            extended_data["sample_comment_count"] = totals["comment_count"]
            extended_data["sample_share_count"] = totals["share_count"]

            total_engagement = (
                totals["like_count"]
                + totals["comment_count"]
                + totals["share_count"]
            )
            if total_engagement > 0 and followers > 0:
                extended_data["sample_engagement_rate"] = round(
                    total_engagement / followers, 6
                )

        return Subject(
            platform=Platform.TIKTOK,
            platform_id=str(open_id),
            name=display_name,
            display_name=display_name,
            followers=followers,
            post_count=post_count,
            activity_frequency=activity_frequency,
            status=status,
            last_synced_at=synced_at,
            extended_data=extended_data or None,
        )

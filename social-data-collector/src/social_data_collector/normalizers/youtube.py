"""YouTube normalizer.

Maps YouTube Data API v3 and Analytics API v2 responses to the
unified Subject schema.  Analytics data is pivoted from the
column/row format into a metric-keyed dict stored in
``extended_data["analytics"]``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from social_common.enums import Platform, SubjectStatus
from social_common.schemas import Subject

from .base import BaseNormalizer, NormalizerError

# Labels matching the Analytics API metric names.
_ANALYTIC_LABELS: dict[str, str] = {
    "views": "Views",
    "estimatedMinutesWatched": "Watch Time (min)",
    "subscribersGained": "Subscribers Gained",
    "subscribersLost": "Subscribers Lost",
    "likes": "Likes",
    "comments": "Comments",
    "shares": "Shares",
}


def pivot_analytics(json: dict[str, Any]) -> list[dict[str, Any]]:
    """Pivot YouTube Analytics API column/row format → unified insight list.

    The Analytics API returns results in column/row format::

        {
          "columnHeaders": [{"name": "day"}, {"name": "views"}, ...],
          "rows": [["2026-06-01", 150, ...], ...]
        }

    This function pivots to the same shape used by Facebook insights::

        [
          {"name": "views", "title": "Views",
           "values": [{"value": 150, "end_time": "2026-06-01"}, ...]},
          ...
        ]
    """
    headers = json.get("columnHeaders", [])
    rows = json.get("rows", [])
    if not headers or not rows:
        return []

    day_idx = next((i for i, h in enumerate(headers) if h["name"] == "day"), -1)
    metrics: list[dict[str, Any]] = []

    for idx, header in enumerate(headers):
        if idx == day_idx:
            continue
        name = header["name"]
        title = _ANALYTIC_LABELS.get(name, name)
        values: list[dict[str, Any]] = []
        for row in rows:
            if day_idx >= 0 and idx < len(row):
                values.append(
                    {
                        "value": row[idx],
                        "end_time": row[day_idx] if day_idx < len(row) else None,
                    }
                )
        metrics.append({"name": name, "title": title, "values": values})

    return metrics


_ACTIVITY_WINDOW_DAYS = 30


def _parse_youtube_time(value: str) -> datetime:
    """Parse a YouTube `videoPublishedAt` string into an aware datetime."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _compute_activity_frequency(uploads: list[dict[str, Any]], now: datetime) -> float:
    """Uploads per day over the last 30 days."""
    if not uploads:
        return 0.0

    window_start = now - timedelta(days=_ACTIVITY_WINDOW_DAYS)
    recent = []
    for item in uploads:
        content_details = item.get("contentDetails", {})
        published = content_details.get("videoPublishedAt")
        if not published:
            continue
        try:
            ts = _parse_youtube_time(published)
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if ts >= window_start:
            recent.append(ts)

    elapsed_days = max((now - window_start).total_seconds() / 86400, 1.0)
    return round(len(recent) / elapsed_days, 4)


def _aggregate_video_stats(video_stats: list[dict[str, Any]]) -> dict[str, int]:
    """Sum viewCount/likeCount/commentCount across a list of videos.list items.

    Values are returned by the API as strings; missing/malformed fields
    are treated as 0 rather than raising, since stats are best-effort.
    """
    totals = {"view_count": 0, "like_count": 0, "comment_count": 0}
    for item in video_stats:
        stats = item.get("statistics", {})
        for key, field in (
            ("view_count", "viewCount"),
            ("like_count", "likeCount"),
            ("comment_count", "commentCount"),
        ):
            try:
                totals[key] += int(stats.get(field, 0))
            except (TypeError, ValueError):
                continue
    return totals


class YouTubeNormalizer(BaseNormalizer):
    def normalize(
        self,
        platform_id: str,
        raw_response: dict[str, Any],
        activity_data: list[dict[str, Any]],
        synced_at: datetime,
        video_stats: list[dict[str, Any]] | None = None,
        analytics: list[dict[str, Any]] | None = None,
    ) -> Subject:
        if synced_at.tzinfo is None:
            synced_at = synced_at.replace(tzinfo=UTC)

        items = raw_response.get("items", [])
        if not items:
            raise NormalizerError(
                f"YouTube channel response has no items for platform_id={platform_id}"
            )

        resource = items[0]
        channel_id = resource.get("id") or platform_id
        snippet = resource.get("snippet", {})
        title = snippet.get("title")

        thumbnails = snippet.get("thumbnails", {})
        avatar_url = (
            thumbnails.get("high", {}).get("url")
            or thumbnails.get("medium", {}).get("url")
            or thumbnails.get("default", {}).get("url")
        )
        if not title:
            raise NormalizerError(f"YouTube channel response missing snippet.title: {resource!r}")

        statistics = resource.get("statistics", {})
        try:
            followers = int(statistics.get("subscriberCount", 0))
        except (TypeError, ValueError):
            followers = 0
        try:
            video_count = int(statistics.get("videoCount", 0))
        except (TypeError, ValueError):
            video_count = 0
        try:
            view_count = int(statistics.get("viewCount", 0))
        except (TypeError, ValueError):
            view_count = 0

        post_count = max(video_count, len(activity_data))
        activity_frequency = _compute_activity_frequency(activity_data, synced_at)

        # Status reflects whether the channel currently shows activity,
        # not merely whether it has ever posted. A channel with uploads
        # but nothing in the last _ACTIVITY_WINDOW_DAYS is INACTIVE.
        if followers == 0 and post_count == 0 or activity_frequency == 0.0:
            status = SubjectStatus.INACTIVE
        else:
            status = SubjectStatus.ACTIVE

        extended_data: dict[str, Any] = {}
        if avatar_url:
            extended_data["avatar_url"] = avatar_url
        if view_count:
            extended_data["view_count"] = view_count

        if video_stats:
            sample_totals = _aggregate_video_stats(video_stats)
            extended_data["sample_video_count"] = len(video_stats)
            extended_data["sample_view_count"] = sample_totals["view_count"]
            extended_data["sample_like_count"] = sample_totals["like_count"]
            extended_data["sample_comment_count"] = sample_totals["comment_count"]
            if sample_totals["view_count"] > 0:
                engagement = (
                    sample_totals["like_count"] + sample_totals["comment_count"]
                ) / sample_totals["view_count"]
                extended_data["sample_engagement_rate"] = round(engagement, 6)

        if analytics:
            extended_data["analytics"] = analytics

        return Subject(
            platform=Platform.YOUTUBE,
            platform_id=str(channel_id),
            name=title,
            display_name=title,
            followers=followers,
            post_count=post_count,
            activity_frequency=activity_frequency,
            status=status,
            last_synced_at=synced_at,
            extended_data=extended_data or None,
        )

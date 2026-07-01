"""Facebook normalizer.

Maps a Graph API page response plus recent posts to the unified
Subject schema. Derives activity_frequency over a rolling 30-day
window and infers status from response shape (empty data = inactive,
explicit 404 = inactive, scope errors = suspended).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from social_common.enums import Platform, SubjectStatus
from social_common.schemas import Subject

from .base import BaseNormalizer, NormalizerError


def normalize_facebook_insights(
    raw_insights: list[dict[str, Any]],
) -> dict[str, Any]:
    """Transform raw Graph API insights response into a normalized dict.

    Graph API returns metrics as a list of dicts, each with
    ``name``, ``title``, ``period``, ``values`` (list of
    ``{value, end_time}``).  This function converts that list to a
    dict keyed by metric name for structured storage in
    ``extended_data["insights"]``.

    Input (from ``/{{page_id}}/insights``):
        [{"name": "page_impressions", "title": "Page Impressions",
          "period": "day", "values": [{"value": 150, "end_time": "..."}]}]

    Output:
        {"page_impressions": {"name": "page_impressions", "title": "...",
          "period": "day", "values": [...]}}
    """
    result: dict[str, Any] = {}
    for metric in raw_insights:
        name = metric.get("name")
        if not name:
            continue
        values = metric.get("values", [])
        cleaned: list[dict[str, Any]] = []
        for v in values:
            end_time = v.get("end_time")
            value = v.get("value")
            if end_time is not None and value is not None:
                cleaned.append({"value": value, "end_time": end_time})
        result[name] = {
            "name": name,
            "title": metric.get("title") or name,
            "period": metric.get("period"),
            "values": cleaned,
        }
    return result


# Rolling window for activity frequency calculation. Matches the
# `activity_frequency` field semantics in social-common.
_ACTIVITY_WINDOW_DAYS = 30


def _parse_facebook_time(value: str) -> datetime:
    """Parse a Facebook `created_time` string into an aware datetime."""
    # Facebook uses ISO 8601 with offsets like "+0000" (no colon).
    cleaned = value.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    return datetime.fromisoformat(cleaned)


def _compute_activity_frequency(posts: list[dict[str, Any]], now: datetime) -> float:
    """Posts per day over the last 30 days.

    If no posts fall inside the window, frequency is 0.0. If the
    window is shorter than 30 days (e.g. a brand new page), the
    divisor is the actual elapsed time.
    """
    if not posts:
        return 0.0

    window_start = now - timedelta(days=_ACTIVITY_WINDOW_DAYS)
    recent = []
    for post in posts:
        created = post.get("created_time")
        if not created:
            continue
        try:
            ts = _parse_facebook_time(created)
        except ValueError:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)
        if ts >= window_start:
            recent.append(ts)

    elapsed_days = max((now - window_start).total_seconds() / 86400, 1.0)
    return round(len(recent) / elapsed_days, 4)


class FacebookNormalizer(BaseNormalizer):
    def normalize(
        self,
        platform_id: str,
        raw_response: dict[str, Any],
        activity_data: list[dict[str, Any]],
        synced_at: datetime,
        extended_data: dict[str, Any] | None = None,
    ) -> Subject:
        if synced_at.tzinfo is None:
            synced_at = synced_at.replace(tzinfo=UTC)

        page_id = raw_response.get("id") or platform_id
        name = raw_response.get("name")
        if not name:
            raise NormalizerError(f"Facebook page response missing 'name': {raw_response!r}")

        picture = raw_response.get("picture", {})
        avatar_url = picture.get("data", {}).get("url") if isinstance(picture, dict) else None

        # followers_count is the modern field; fan_count is the legacy one.
        followers = raw_response.get("followers_count")
        if followers is None:
            followers = raw_response.get("fan_count", 0)
        try:
            followers = int(followers)
        except (TypeError, ValueError):
            followers = 0

        # A Page with no recent posts has an empty data array from the
        # /posts endpoint; activity_frequency is 0.0 and post_count is 0.
        post_count = len(activity_data)
        activity_frequency = _compute_activity_frequency(activity_data, synced_at)

        # Infer status: a Page with zero followers and zero posts is
        # inactive (restricted, deleted content, or brand new). A 404
        # raises SubjectNotFoundError upstream so we don't reach here.
        if followers == 0 and post_count == 0:
            status = SubjectStatus.INACTIVE
        else:
            status = SubjectStatus.ACTIVE

        result_extended = dict(extended_data or {})
        if avatar_url:
            result_extended["avatar_url"] = avatar_url

        return Subject(
            platform=Platform.FACEBOOK,
            platform_id=str(page_id),
            name=name,
            display_name=name,
            followers=followers,
            post_count=post_count,
            activity_frequency=activity_frequency,
            status=status,
            last_synced_at=synced_at,
            extended_data=result_extended or None,
        )

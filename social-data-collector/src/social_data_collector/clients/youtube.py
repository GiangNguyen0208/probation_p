"""YouTube Data API v3 client.

Fetches channel profile data and recent uploads for a given channel ID.
Authentication uses an API key (no OAuth required for public channel data).

Quota cost reference (per https://developers.google.com/youtube/v3/determine_quota_cost):
  - channels.list   → 1 unit
  - playlistItems.list → 1 unit per page (max 50 items/page)
  - activities.list → 1 unit  (not used here; playlist approach is preferred)

Per Phase 0 research: uploads playlist ID is discovered via channels.list
response (contentDetails.relatedPlaylists.uploads). No UC→UU conversion.
"""

from __future__ import annotations

from typing import Any

from social_common.errors import PermanentPlatformError, SubjectNotFoundError

from ..config import YouTubeSettings
from .base import BaseHTTPClient, RetryPolicy

# Fields returned by channels.list that the normalizer consumes.
_CHANNEL_PARTS = "snippet,statistics,contentDetails"

# Fields returned by playlistItems.list used to derive activity_frequency.
_PLAYLIST_ITEM_PARTS = "contentDetails"

# Max items per playlistItems.list page (API ceiling = 50).
_PAGE_SIZE = 50

# Parts returned by videos.list — snippet (title, thumbnails, publishedAt),
# statistics (view/like/comment counts), contentDetails (duration).
_VIDEO_PARTS = "snippet,statistics,contentDetails"


class YouTubeClient(BaseHTTPClient):
    """Thin wrapper around the YouTube Data API v3.

    Only public data is accessed; no OAuth flow is needed. The API key
    is sent as a query parameter on every request.
    """

    def __init__(
        self,
        settings: YouTubeSettings,
        retry_policy: RetryPolicy,
        api_key: str | None = None,
    ) -> None:
        if api_key is None and not settings.has_credentials:
            raise PermanentPlatformError(
                "YouTube credentials are not configured (set YOUTUBE_API_KEY)"
            )
        super().__init__(
            base_url=settings.base_url,
            retry_policy=retry_policy,
            platform_name="youtube",
        )
        self._api_key = api_key or settings.api_key.get_secret_value()

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_channel(self, channel_id: str) -> dict[str, Any]:
        """Fetch a channel's snippet, statistics, and contentDetails.

        Returns the raw channels.list API response dict.
        Quota cost: 1 unit.

        Raises SubjectNotFoundError when the channel ID is unknown or the
        channel has been deleted/made private.
        """
        try:
            response = self.get_json(
                "/channels",
                params={
                    "part": _CHANNEL_PARTS,
                    "id": channel_id,
                    "key": self._api_key,
                },
            )
        except PermanentPlatformError as exc:
            if "404" in str(exc):
                raise SubjectNotFoundError(f"YouTube channel not found: {channel_id}") from exc
            raise

        # channels.list returns HTTP 200 with an empty items list when
        # the channel ID is not found (rather than a 404 status).
        if not response.get("items"):
            raise SubjectNotFoundError(f"YouTube channel not found: {channel_id}")

        return response

    def get_recent_uploads(
        self,
        channel_response: dict[str, Any],
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Fetch recent uploads for a channel via its uploads playlist.

        The uploads playlist ID is read from the channels.list response
        (contentDetails.relatedPlaylists.uploads). This is the approach
        recommended in Phase 0 research; UC→UU conversion is not used.

        Each item contains `contentDetails.videoPublishedAt` which the
        normalizer uses to compute activity_frequency.

        Quota cost: 1 unit per page (max 50 items/page).
        For limit=50 → 1 unit. For limit=100 → 2 units.
        """
        uploads_playlist_id = self._extract_uploads_playlist_id(channel_response)
        if not uploads_playlist_id:
            # Channel has no uploads playlist (e.g. brand-new channel).
            return []

        items: list[dict[str, Any]] = []
        page_token: str | None = None

        while len(items) < limit:
            batch_size = min(_PAGE_SIZE, limit - len(items))
            params: dict[str, Any] = {
                "part": _PLAYLIST_ITEM_PARTS,
                "playlistId": uploads_playlist_id,
                "maxResults": str(batch_size),
                "key": self._api_key,
            }
            if page_token:
                params["pageToken"] = page_token

            try:
                response = self.get_json("/playlistItems", params=params)
            except PermanentPlatformError as exc:
                # 404 on the playlist means the channel has no public
                # uploads yet; return what we have rather than crashing.
                if "404" in str(exc):
                    break
                raise

            items.extend(response.get("items", []))
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return items

    def get_video_details(self, video_ids: list[str]) -> list[dict[str, Any]]:
        """Fetch snippet, statistics, and contentDetails for up to 50 videos.

        Returns the raw videos.list items. Each item contains:
          - snippet: title, description, thumbnails, publishedAt
          - statistics: viewCount, likeCount, commentCount
          - contentDetails: duration (ISO 8601)

        Quota cost: 1 unit per call (max 50 IDs).
        """
        if not video_ids:
            return []
        return list(
            self.get_json(
                "/videos",
                params={
                    "part": _VIDEO_PARTS,
                    "id": ",".join(video_ids[:50]),
                    "key": self._api_key,
                },
            ).get("items", [])
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_uploads_playlist_id(channel_response: dict[str, Any]) -> str | None:
        """Extract the uploads playlist ID from a channels.list response."""
        items = channel_response.get("items", [])
        if not items:
            return None
        content_details = items[0].get("contentDetails", {})
        related = content_details.get("relatedPlaylists", {})
        return related.get("uploads") or None

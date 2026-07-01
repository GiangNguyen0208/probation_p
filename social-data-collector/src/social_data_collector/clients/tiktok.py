"""TikTok Display API v2 client.

OAuth 2.0 Bearer token required. The Display API provides basic user
profile (followers, likes, video count) and video metadata (like,
comment, share counts) but does NOT expose:
  - view_count per video (only available via Research API)
  - time-series analytics (no equivalent of YouTube Analytics)

Reference: https://developers.tiktok.com/display-api/
"""

from __future__ import annotations

from typing import Any, cast

import httpx
from social_common.errors import PermanentPlatformError, SubjectNotFoundError

from ..logging_setup import get_logger
from .base import RetryPolicy

logger = get_logger("social_data_collector.clients.tiktok")

TIKTOK_BASE_URL = "https://open.tiktokapis.com/v2"

_USER_INFO_FIELDS = ",".join([
    "open_id",
    "union_id",
    "avatar_url",
    "display_name",
    "username",
    "follower_count",
    "is_verified",
    "following_count",
    "likes_count",
    "video_count",
])

_VIDEO_LIST_FIELDS = ",".join([
    "id",
    "create_time",
    "title",
    "like_count",
    "comment_count",
    "share_count",
])

_MAX_VIDEO_PAGE_SIZE = 20


class TikTokClient:
    """TikTok Display API v2 wrapper.

    All requests use Bearer token auth from a stored OAuth credential.
    The token is not refreshed here — callers should refresh before
    initializing this client.
    """

    def __init__(
        self,
        access_token: str,
        retry_policy: RetryPolicy,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._access_token = access_token
        self._retry_policy = retry_policy
        self._timeout = timeout_seconds
        self._client = httpx.Client(base_url=TIKTOK_BASE_URL, timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> TikTokClient:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a request to the TikTok API and check for errors.

        Raises PermanentPlatformError on API-level errors from TikTok's
        ``error.code`` field or HTTP-level errors.
        """
        headers: dict[str, str] = {
            "Authorization": f"Bearer {self._access_token}",
        }
        if json_body is not None:
            headers["Content-Type"] = "application/json"

        try:
            response = self._client.request(
                method=method,
                url=path,
                params=params,
                headers=headers,
                json=json_body,
            )
        except httpx.TransportError as exc:
            raise PermanentPlatformError(f"tiktok transport error: {exc}") from exc

        if response.status_code == 401:
            raise PermanentPlatformError(
                f"tiktok returned 401 for {path}: token expired or invalid"
            )
        if response.status_code == 403:
            raise PermanentPlatformError(
                f"tiktok returned 403 for {path}: insufficient permissions"
            )
        if response.status_code == 404:
            raise SubjectNotFoundError(f"tiktok resource not found: {path}")
        if response.status_code >= 400:
            body_text = response.text
            raise PermanentPlatformError(
                f"tiktok returned {response.status_code} for {path}: {body_text}"
            )

        body: dict[str, Any] = response.json()
        error = body.get("error", {})
        code = error.get("code")
        if code and code != "ok":
            msg = error.get("message", "unknown error")
            log_id = error.get("log_id", "")
            if code in ("access_token_invalid", "token_expired"):
                raise PermanentPlatformError(
                    f"tiktok token error ({code}): {msg} [log_id={log_id}]"
                )
            raise PermanentPlatformError(
                f"tiktok API error ({code}): {msg} [log_id={log_id}]"
            )

        return body

    def get_user_info(self, open_id: str) -> dict[str, Any]:
        """Fetch TikTok user profile info.

        Returns the ``data.user`` dict with fields:
          open_id, union_id, avatar_url, display_name, username,
          follower_count, is_verified, following_count, likes_count,
          video_count.

        Raises SubjectNotFoundError when the user is not found.
        """
        body = self._request(
            "GET",
            "/user/info/",
            params={"fields": _USER_INFO_FIELDS},
        )
        data = body.get("data", {})
        user = data.get("user")
        if not user:
            raise SubjectNotFoundError(f"TikTok user not found: {open_id}")
        return cast("dict[str, Any]", user)

    def get_video_list(
        self,
        open_id: str,
        max_count: int = _MAX_VIDEO_PAGE_SIZE,
        cursor: int = 0,
    ) -> list[dict[str, Any]]:
        """Fetch recent videos for a TikTok user.

        Returns a list of video dicts with fields:
          id, create_time, title, like_count, comment_count, share_count.

        Note: TikTok Display API v2 does not expose view_count per video.
        Returns empty list on any API error (best-effort).

        TikTok caps ``max_count`` at 20 per request, so any larger
        value is clamped.
        """
        clamped = min(max_count, _MAX_VIDEO_PAGE_SIZE)
        try:
            body = self._request(
                "POST",
                "/video/list/",
                params={"fields": _VIDEO_LIST_FIELDS},
                json_body={"max_count": clamped, "cursor": cursor},
            )
        except PermanentPlatformError as exc:
            logger.warning(
                "tiktok.video_list_error",
                open_id=open_id,
                error=str(exc),
            )
            return []

        data = body.get("data", {})
        videos = data.get("videos", [])
        return cast("list[dict[str, Any]]", videos)

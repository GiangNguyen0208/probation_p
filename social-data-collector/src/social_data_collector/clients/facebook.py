"""Facebook Graph API client.

Thin wrapper around the Graph API. Authentication uses the
App Access Token (long-lived token issued for the app, not a
user access token). The client only touches public Page fields
and recent public posts; no insights, no user data.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from social_common.errors import PermanentPlatformError, SubjectNotFoundError

from ..config import FacebookSettings
from .base import BaseHTTPClient, RetryPolicy

# Public Page fields the collector reads on every sync.
DEFAULT_PAGE_FIELDS = "id,name,fan_count"

# Default number of recent posts to fetch for activity frequency derivation.
DEFAULT_POSTS_LIMIT = 50


class FacebookClient(BaseHTTPClient):
    def __init__(
        self,
        settings: FacebookSettings,
        retry_policy: RetryPolicy,
        access_token: str | None = None,
        app_id: str | None = None,
        app_secret: str | None = None,
    ) -> None:
        if access_token is None and not settings.has_credentials:
            raise PermanentPlatformError(
                "Facebook credentials are not configured (set FACEBOOK_PAGE_ACCESS_TOKEN "
                "or FACEBOOK_APP_ACCESS_TOKEN, or provide an access_token)"
            )
        super().__init__(
            base_url=f"https://graph.facebook.com/{settings.graph_api_version}",
            retry_policy=retry_policy,
            platform_name="facebook",
        )
        # If a per-subject access token is provided, use it. Otherwise fall
        # back to the env-var-based global token.
        self._access_token = access_token or (
            settings.page_access_token.get_secret_value()
            or settings.app_access_token.get_secret_value()
        )
        self._app_secret = app_secret
        self._settings = settings

    def _auth_params(self, **params: str) -> dict[str, str]:
        """Return params dict with access_token and optional appsecret_proof."""
        params["access_token"] = self._access_token
        if self._app_secret:
            params["appsecret_proof"] = hmac.new(
                self._app_secret.encode(),
                self._access_token.encode(),
                hashlib.sha256,
            ).hexdigest()
        return params

    def get_page(self, page_id: str, fields: str = DEFAULT_PAGE_FIELDS) -> dict[str, Any]:
        """Fetch a public Page's profile fields.

        Returns the raw Graph API response dict. The normalizer maps
        this to the unified Subject schema.
        """
        try:
            return self.get_json(f"/{page_id}", params=self._auth_params(fields=fields))
        except PermanentPlatformError as exc:
            if "404" in str(exc):
                raise SubjectNotFoundError(f"Facebook page not found: {page_id}") from exc
            if "nonexisting field" in str(exc) and fields != "id,name":
                return self.get_page(page_id, fields="id,name")
            raise

    def get_recent_posts(
        self, page_id: str, limit: int = DEFAULT_POSTS_LIMIT
    ) -> list[dict[str, Any]]:
        """Fetch the most recent public posts for a Page.

        Returns a list of post dicts with at minimum `id` and
        `created_time`. Used by the normalizer to compute
        `activity_frequency`.
        """
        try:
            response = self.get_json(
                f"/{page_id}/posts",
                params=self._auth_params(
                    fields="id,created_time,message,permalink_url",
                    limit=str(limit),
                ),
            )
        except PermanentPlatformError as exc:
            if "404" in str(exc):
                # A Page may exist but have no public posts endpoint
                # accessible with the current token. Treat as empty
                # activity signal rather than crashing the subject.
                return []
            raise
        return list(response.get("data", []))

    def get_page_insights(
        self,
        page_id: str,
        metrics: str = "page_impressions,page_engaged_users,page_fans",
        period: str = "day",
    ) -> list[dict[str, Any]]:
        """Fetch Page insights (requires read_insights permission)."""
        try:
            response = self.get_json(
                f"/{page_id}/insights",
                params=self._auth_params(metric=metrics, period=period),
            )
            return list(response.get("data", []))
        except PermanentPlatformError as exc:
            # Insights often fail due to lack of read_insights permission on the token.
            # We return empty list instead of crashing the sync.
            if "403" in str(exc) or "400" in str(exc) or "Permissions error" in str(exc):
                return []
            raise

    def get_post_comments(self, post_id: str, limit: int = 50) -> list[dict[str, Any]]:
        """Fetch comments on a specific post."""
        try:
            response = self.get_json(
                f"/{post_id}/comments",
                params=self._auth_params(
                    fields="id,message,created_time,from,like_count",
                    limit=str(limit),
                ),
            )
            return list(response.get("data", []))
        except PermanentPlatformError as exc:
            if "403" in str(exc) or "400" in str(exc):
                return []
            raise

    def get_photos(self, page_id: str, limit: int = 25) -> list[dict[str, Any]]:
        """Fetch photos posted by the Page."""
        try:
            response = self.get_json(
                f"/{page_id}/photos",
                params=self._auth_params(
                    fields="id,created_time,name,link",
                    type="uploaded",
                    limit=str(limit),
                ),
            )
            return list(response.get("data", []))
        except PermanentPlatformError as exc:
            if "403" in str(exc):
                return []
            raise

    def get_videos(self, page_id: str, limit: int = 25) -> list[dict[str, Any]]:
        """Fetch videos posted by the Page."""
        try:
            response = self.get_json(
                f"/{page_id}/videos",
                params=self._auth_params(
                    fields="id,created_time,title,permalink_url",
                    limit=str(limit),
                ),
            )
            return list(response.get("data", []))
        except PermanentPlatformError as exc:
            if "403" in str(exc):
                return []
            raise

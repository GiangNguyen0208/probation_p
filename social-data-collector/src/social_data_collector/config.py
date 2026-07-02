"""Typed application configuration loaded from environment variables.

Settings are grouped by concern (database, redis, facebook, youtube, sync)
using pydantic-settings with `env_prefix` so each subgroup maps to a
predictable set of environment variables. The aggregator `Settings` is
the single object used everywhere in the application.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env from the project root so the same file works whether commands
# are run from the repo root or from the social-data-collector directory.
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / ".env", override=False)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    url: str = Field(alias="DATABASE_URL")
    pool_size: int = Field(default=5, alias="DATABASE_POOL_SIZE")
    pool_recycle_seconds: int = Field(default=3600, alias="DATABASE_POOL_RECYCLE_SECONDS")
    echo: bool = Field(default=False, alias="DATABASE_ECHO")


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    url: str = Field(alias="REDIS_URL")


class FacebookSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FACEBOOK_", env_file_encoding="utf-8", extra="ignore"
    )

    graph_api_version: str = "v25.0"
    app_id: str = ""
    app_secret: SecretStr = SecretStr("")
    app_access_token: SecretStr = SecretStr("")
    # Page-level access token (broader field access than app token).
    # Preferred over app_access_token when available.
    page_access_token: SecretStr = SecretStr("")
    test_page_id: str = ""
    # Comma-separated list of Page IDs to monitor. Used as a seed source
    # by `seed-subjects` CLI and as a fallback when the DB has no subjects.
    test_page_ids_raw: str = Field(default="", alias="test_page_ids")

    # Comma-separated list of insight metrics to fetch during sync.
    # These are the modern metrics confirmed valid via probe; deprecated
    # metrics (e.g. page_impressions, page_fans, page_engaged_users) are
    # excluded because they return #100 "invalid insights metric".
    insight_metrics: str = (
        "page_media_view,page_total_media_view_unique,"
        "page_views_total,page_post_engagements,"
        "page_follows,page_daily_follows,page_daily_follows_unique,"
        "page_daily_unfollows_unique,"
        "page_actions_post_reactions_total,"
        "page_video_views,page_total_actions"
    )

    @property
    def test_page_ids(self) -> list[str]:
        return [item.strip() for item in self.test_page_ids_raw.split(",") if item.strip()]

    @property
    def has_credentials(self) -> bool:
        return bool(
            self.app_access_token.get_secret_value() or self.page_access_token.get_secret_value()
        )


class YouTubeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="YOUTUBE_", env_file_encoding="utf-8", extra="ignore"
    )
    api_key: SecretStr = SecretStr("")
    base_url: str = Field(default="https://www.googleapis.com/youtube/v3", alias="YOUTUBE_BASE_URL")
    test_channel_id: str = ""
    test_channel_ids_raw: str = Field(default="", alias="test_channel_ids")
    # Kept for documentation and tooling. The client does not use this
    # for live sync — playlist IDs are discovered via channels.list per
    # the Phase 0 research note.
    uploads_playlist_id: str = ""

    @property
    def test_channel_ids(self) -> list[str]:
        return [item.strip() for item in self.test_channel_ids_raw.split(",") if item.strip()]

    @property
    def has_credentials(self) -> bool:
        return bool(self.api_key.get_secret_value())


class TikTokSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TIKTOK_", env_file_encoding="utf-8", extra="ignore"
    )
    client_key: str = ""
    client_secret: SecretStr = SecretStr("")
    test_open_id: str = ""

    @property
    def has_credentials(self) -> bool:
        return bool(self.client_key)


class SyncSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SYNC_", env_file_encoding="utf-8", extra="ignore")

    facebook_enabled: bool = True
    youtube_enabled: bool = True
    tiktok_enabled: bool = False
    # Beat schedule interval (minutes). 60 min = safe up to 100 subjects
    # per the Phase 0 quota worksheet (4,800 units/day, 10,000 default).
    default_interval_minutes: int = 60
    max_retries: int = 5
    backoff_initial_seconds: int = 60
    backoff_max_seconds: int = 3600
    # Cap on posts / playlist items to fetch per subject for activity
    # frequency derivation. Limits API quota usage.
    activity_sample_size: int = 50


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    log_level: str = "INFO"
    environment: str = "development"


class Settings(BaseSettings):
    """Aggregated application settings."""

    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)  # type: ignore[arg-type]
    redis: RedisSettings = Field(default_factory=RedisSettings)  # type: ignore[arg-type]
    facebook: FacebookSettings = Field(default_factory=FacebookSettings)
    youtube: YouTubeSettings = Field(default_factory=YouTubeSettings)
    tiktok: TikTokSettings = Field(default_factory=TikTokSettings)
    sync: SyncSettings = Field(default_factory=SyncSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()

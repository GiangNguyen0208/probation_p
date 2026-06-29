"""Typed application configuration for the API gateway.

Mirrors the pattern from `social-data-collector/config.py`: groups
settings by concern using pydantic-settings with `env_prefix`, then
aggregates them into a single `Settings` object. A process-wide
cached instance is returned by `get_settings()`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(_PROJECT_ROOT / ".env", override=False)


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    url: str = Field(alias="DATABASE_URL")
    pool_size: int = Field(default=10, alias="DATABASE_POOL_SIZE")
    pool_recycle_seconds: int = Field(default=3600, alias="DATABASE_POOL_RECYCLE_SECONDS")
    echo: bool = Field(default=False, alias="DATABASE_ECHO")


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    url: str = Field(alias="REDIS_URL")


class GatewaySettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GATEWAY_", env_file_encoding="utf-8", extra="ignore"
    )

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    api_prefix: str = "/v1"


class CacheSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="CACHE_", env_file_encoding="utf-8", extra="ignore"
    )

    subject_ttl_seconds: int = 300  # 5 min
    list_ttl_seconds: int = 60  # 1 min
    activity_ttl_seconds: int = 60  # 1 min


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    pepper: SecretStr = Field(alias="API_KEY_PEPPER")


class CredentialSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    encryption_key: SecretStr = Field(alias="CREDENTIAL_ENCRYPTION_KEY", default=SecretStr(""))


class AdminSettings(BaseSettings):
    """Settings for privileged admin endpoints (e.g. key creation).

    `ADMIN_TOKEN` is a static bearer token used to authenticate admin
    operations. It is separate from regular API keys so a compromised
    API key cannot be used to mint more keys. If the token is empty,
    admin endpoints reject every request.
    """

    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    token: SecretStr = Field(alias="ADMIN_TOKEN")


class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    bot_token: SecretStr = Field(alias="TELEGRAM_BOT_TOKEN")
    app_url: str = Field(alias="TELEGRAM_APP_URL", default="")
    bot_username: str = Field(alias="TELEGRAM_BOT_USERNAME", default="")


class CORSSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CORS_", env_file_encoding="utf-8", extra="ignore")

    allow_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def origin_list(self) -> list[str]:
        return [o.strip() for o in self.allow_origins.split(",") if o.strip()]


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    log_level: str = "INFO"
    environment: str = "development"


class Settings(BaseSettings):
    """Aggregated gateway settings."""

    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)  # type: ignore[arg-type]
    redis: RedisSettings = Field(default_factory=RedisSettings)  # type: ignore[arg-type]
    gateway: GatewaySettings = Field(default_factory=GatewaySettings)
    cache: CacheSettings = Field(default_factory=CacheSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)  # type: ignore[arg-type]
    admin: AdminSettings = Field(default_factory=AdminSettings)  # type: ignore[arg-type]
    credential: CredentialSettings = Field(default_factory=CredentialSettings)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)  # type: ignore[arg-type]
    cors: CORSSettings = Field(default_factory=CORSSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()

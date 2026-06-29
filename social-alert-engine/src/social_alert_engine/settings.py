"""Typed application configuration loaded from environment variables."""

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
    pool_size: int = Field(default=5, alias="DATABASE_POOL_SIZE")
    pool_recycle_seconds: int = Field(default=3600, alias="DATABASE_POOL_RECYCLE_SECONDS")
    echo: bool = Field(default=False, alias="DATABASE_ECHO")


class RedisSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    url: str = Field(alias="REDIS_URL")


class TelegramSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TELEGRAM_", env_file_encoding="utf-8", extra="ignore"
    )

    bot_token: SecretStr = Field(default=SecretStr(""))
    default_chat_id: str = ""


class AlertSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ALERT_", env_file_encoding="utf-8", extra="ignore"
    )

    evaluation_interval_seconds: int = 300
    default_cooldown_seconds: int = 3600


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    log_level: str = "INFO"
    environment: str = "development"


class Settings(BaseSettings):
    """Aggregated alert-engine settings."""

    model_config = SettingsConfigDict(env_file_encoding="utf-8", extra="ignore")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)  # type: ignore[arg-type]
    redis: RedisSettings = Field(default_factory=RedisSettings)  # type: ignore[arg-type]
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    alert: AlertSettings = Field(default_factory=AlertSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a process-wide cached Settings instance."""
    return Settings()

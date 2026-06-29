"""Unified data contracts for the Social Intelligence Platform.

These Pydantic models are the single source of truth for the shape of a
subject, an activity snapshot, and an alert rule. They are imported by
every service (collector, gateway, mini app, alert engine) so a schema
change here is a coordinated change everywhere.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field

from .enums import AlertRuleType, Platform, SubjectStatus


def _utcnow() -> datetime:
    return datetime.now(UTC)


class Subject(BaseModel):
    """Current state of a monitored subject.

    Written by the collector, read by the API gateway. The `id` is a
    system-generated UUID; `platform_id` is the native identifier on
    the source platform (Facebook Page ID, YouTube Channel ID).
    """

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: UUID = Field(default_factory=uuid4)
    platform: Platform
    platform_id: str
    name: str
    display_name: str
    followers: int = Field(ge=0)
    post_count: int = Field(ge=0)
    activity_frequency: float = Field(ge=0.0)
    status: SubjectStatus
    last_synced_at: datetime
    created_at: datetime = Field(default_factory=_utcnow)
    extended_data: dict[str, Any] | None = None


class Video(BaseModel):
    """Per-video data for a YouTube subject.

    Upserted on every sync cycle. Stores the latest observed metrics for
    each video; historical tracking is not maintained.
    """

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID
    platform_video_id: str
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    published_at: datetime
    duration: str | None = None
    view_count: int = Field(ge=0, default=0)
    like_count: int = Field(ge=0, default=0)
    comment_count: int = Field(ge=0, default=0)
    last_synced_at: datetime
    created_at: datetime = Field(default_factory=_utcnow)


class ActivitySnapshot(BaseModel):
    """Point-in-time metrics for a subject, stored as a time-series row.

    Appended to the time-series store on every successful sync. Used by
    the Mini App for trend charts.
    """

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    subject_id: UUID
    captured_at: datetime
    followers: int = Field(ge=0)
    post_count: int = Field(ge=0)
    frequency: float = Field(ge=0.0)


class AlertRule(BaseModel):
    """Configurable alert condition scoped to one subject.

    Created and updated by analysts through the Mini App; evaluated by
    the alert engine on each sync cycle. Phase 1 defines the contract
    and table; the engine itself ships in Phase 4.
    """

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID
    rule_type: AlertRuleType
    threshold: float
    cooldown_seconds: int = Field(ge=0)
    channel_id: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class PlatformConfig(BaseModel):
    """Registered platform definition.

    Stored in the `platforms` table. The `config_schema` describes what
    credential fields are required when connecting an account on this
    platform (e.g. `{"access_token": {"type": "string", ...}}`).
    """

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: UUID = Field(default_factory=uuid4)
    name: str
    slug: str
    description: str | None = None
    auth_type: str
    config_schema: dict[str, Any]
    icon_url: str | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class PlatformCredential(BaseModel):
    """Stored credentials for one connected account on a platform.

    The `credentials` field contains platform-specific auth data
    (access tokens, API keys, etc.) and is encrypted at rest via
    `cryptography.fernet`. The decrypted value is never exposed
    through the API.
    """

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: UUID = Field(default_factory=uuid4)
    platform_id: UUID
    label: str
    credentials: dict[str, Any]
    status: str = "active"
    last_verified_at: datetime | None = None
    is_active: bool = True
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class AlertLog(BaseModel):
    """Record of a single alert firing event.

    Written by the alert engine after rule evaluation. The gateway serves
    these read-only to the mini-app's alert history panel. The `delivered`
    flag is set to False if the Telegram notification failed.
    """

    model_config = ConfigDict(from_attributes=True, use_enum_values=False)

    id: UUID = Field(default_factory=uuid4)
    subject_id: UUID
    rule_id: UUID
    rule_type: AlertRuleType
    triggered_at: datetime
    metric_value: float | None = None
    threshold: float
    message: str
    delivered: bool = False

"""Pydantic schemas for platform and credential admin endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# ──────────────────────────────────────────────
# Platform schemas
# ──────────────────────────────────────────────


class CreatePlatformRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$")
    description: str | None = None
    auth_type: str = Field(min_length=1, max_length=50)
    config_schema: dict[str, Any]
    icon_url: str | None = None


class UpdatePlatformRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    description: str | None = None
    auth_type: str | None = None
    config_schema: dict[str, Any] | None = None
    icon_url: str | None = None
    is_active: bool | None = None


class PlatformResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: UUID
    name: str
    slug: str
    description: str | None
    auth_type: str
    config_schema: dict[str, Any]
    icon_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ──────────────────────────────────────────────
# Credential schemas
# ──────────────────────────────────────────────


class CreateCredentialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    platform_slug: str = Field(
        min_length=1,
        max_length=50,
        description="Platform slug (e.g. 'facebook', 'youtube').",
    )
    label: str = Field(
        min_length=1,
        max_length=255,
        description="Human-friendly label (e.g. 'GHN Careers FB').",
    )
    credentials: dict[str, Any] = Field(
        description="Platform-specific auth data. Keys must match the platform's config_schema.",
    )


class UpdateCredentialRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    credentials: dict[str, Any] | None = None
    is_active: bool | None = None


class CredentialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: str
    platform_id: str
    platform_slug: str = ""
    label: str
    status: str
    last_verified_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CredentialDetailResponse(CredentialResponse):
    """Extended credential response with credential field names (not values).

    The actual credential values are never exposed through the API.
    This response lists which fields are configured (redacted).
    """

    configured_fields: list[str]

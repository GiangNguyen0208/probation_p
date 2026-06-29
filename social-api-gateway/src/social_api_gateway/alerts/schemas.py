"""Pydantic schemas for alert rule endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field
from social_common.enums import AlertRuleType
from social_common.envelope import ResponseEnvelope
from social_common.schemas import AlertLog, AlertRule


class AlertRuleCreate(BaseModel):
    rule_type: AlertRuleType
    threshold: float = Field(ge=0)
    cooldown_seconds: int = Field(ge=0, default=3600)
    channel_id: str = Field(default="@default", min_length=1)


class AlertRuleUpdate(BaseModel):
    rule_type: AlertRuleType | None = None
    threshold: float | None = Field(default=None, ge=0)
    cooldown_seconds: int | None = Field(default=None, ge=0)
    channel_id: str | None = Field(default=None, min_length=1)
    is_active: bool | None = None


AlertRuleListResponse = ResponseEnvelope[list[AlertRule]]
AlertRuleResponse = ResponseEnvelope[AlertRule]

AlertLogListResponse = ResponseEnvelope[list[AlertLog]]


__all__ = [
    "AlertRuleCreate",
    "AlertRuleListResponse",
    "AlertRuleResponse",
    "AlertRuleUpdate",
    "AlertLogListResponse",
]

"""Shared data contracts for the Social Intelligence Platform."""

from .enums import AlertRuleType, Platform, SubjectStatus
from .envelope import ErrorDetail, ErrorResponse, ResponseEnvelope, ResponseMeta
from .errors import (
    PermanentPlatformError,
    SubjectNotFoundError,
    TransientPlatformError,
)
from .schemas import ActivitySnapshot, AlertRule, Subject

__all__ = [
    "ActivitySnapshot",
    "AlertRule",
    "AlertRuleType",
    "ErrorDetail",
    "ErrorResponse",
    "PermanentPlatformError",
    "Platform",
    "ResponseEnvelope",
    "ResponseMeta",
    "Subject",
    "SubjectNotFoundError",
    "SubjectStatus",
    "TransientPlatformError",
]

"""Enums shared across all services."""

from enum import StrEnum


class Platform(StrEnum):
    """Source platform for a subject."""

    FACEBOOK = "facebook"
    YOUTUBE = "youtube"
    TIKTOK = "tiktok"


class SubjectStatus(StrEnum):
    """Lifecycle status of a subject as observed by the collector."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class AlertRuleType(StrEnum):
    """Type of alert condition evaluated by the alert engine."""

    FOLLOWER_SPIKE = "follower_spike"
    FOLLOWER_DROP = "follower_drop"
    ACTIVITY_SPIKE = "activity_spike"
    ACTIVITY_SILENCE = "activity_silence"
    STATUS_CHANGE = "status_change"

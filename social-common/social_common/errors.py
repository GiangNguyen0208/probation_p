"""Error types shared across services."""


class PlatformError(Exception):
    """Base class for platform API errors."""


class TransientPlatformError(PlatformError):
    """Retryable platform error: rate limits, network failures, quota exhaustion.

    The caller should back off and retry. Used by the collector to skip
    crashing the service when one platform is temporarily unavailable.
    """


class PermanentPlatformError(PlatformError):
    """Non-retryable platform error: invalid ID, missing permissions, suspended subject.

    The caller should not retry. The collector should mark the subject as
    suspended or inactive and move on.
    """


class SubjectNotFoundError(PermanentPlatformError):
    """Raised when a subject ID does not exist on the source platform."""

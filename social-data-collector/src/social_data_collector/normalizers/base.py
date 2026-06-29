"""Base normalizer interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from social_common.schemas import Subject


class NormalizerError(Exception):
    """Raised when a platform response cannot be mapped to the Subject schema."""


class BaseNormalizer(ABC):
    """Maps a platform-specific response to a unified Subject.

    Concrete normalizers implement `normalize` to produce a Subject
    with consistent status, activity_frequency, and metrics.
    """

    @abstractmethod
    def normalize(
        self,
        platform_id: str,
        raw_response: dict[str, Any],
        activity_data: list[dict[str, Any]],
        synced_at: datetime,
    ) -> Subject:
        """Return a unified Subject built from the raw platform data.

        Parameters
        ----------
        platform_id:
            The native ID on the source platform.
        raw_response:
            The platform API response (page profile, channel resource, etc.).
        activity_data:
            Recent posts or uploads used to compute activity_frequency.
        synced_at:
            The timestamp the sync was performed, recorded in
            `last_synced_at` on the subject.
        """
        raise NotImplementedError

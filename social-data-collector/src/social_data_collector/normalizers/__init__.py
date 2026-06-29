"""Normalizers: platform-specific responses → unified Subject schema."""

from .base import BaseNormalizer, NormalizerError
from .facebook import FacebookNormalizer
from .youtube import YouTubeNormalizer

__all__ = [
    "BaseNormalizer",
    "FacebookNormalizer",
    "NormalizerError",
    "YouTubeNormalizer",
]

"""Pydantic response schemas for the subject endpoints.

Reuses the `Subject` and `ActivitySnapshot` models from `social-common`
and wraps them in the standard `ResponseEnvelope` for consistent wire
format. FastAPI uses these as `response_model` for OpenAPI generation.
"""

from __future__ import annotations

from social_common.envelope import ResponseEnvelope
from social_common.schemas import ActivitySnapshot, Subject, Video

SubjectListResponse = ResponseEnvelope[list[Subject]]
SubjectResponse = ResponseEnvelope[Subject]
ActivityListResponse = ResponseEnvelope[list[ActivitySnapshot]]
VideoListResponse = ResponseEnvelope[list[Video]]

__all__ = [
    "ActivityListResponse",
    "SubjectListResponse",
    "SubjectResponse",
    "VideoListResponse",
]

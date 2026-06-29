"""Shared response and error envelope types.

Defined here in `social-common` per the architecture document so every
HTTP-facing service uses the same wire format. The gateway wraps every
success response in `ResponseEnvelope` and every error response in
`ErrorResponse`.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ResponseMeta(BaseModel):
    """Standard response metadata.

    Always present in success responses. Fields are optional so the
    same shape works for single-resource and paginated list responses.
    """

    page: int | None = None
    limit: int | None = None
    total: int | None = None
    request_id: str | None = None


class ResponseEnvelope(BaseModel, Generic[T]):
    """Standard success response envelope.

    Shape: `{ "data": <resource>, "meta": { ... } }`
    """

    data: T
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class ErrorDetail(BaseModel):
    """Structured error detail block."""

    code: str
    message: str
    details: dict | None = None


class ErrorResponse(BaseModel):
    """Standard error response envelope.

    Shape: `{ "error": { "code": ..., "message": ..., "details": ... } }`
    """

    error: ErrorDetail

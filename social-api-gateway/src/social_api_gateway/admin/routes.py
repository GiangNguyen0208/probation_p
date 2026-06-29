"""Admin endpoints for privileged operations.

Currently: `POST /v1/admin/keys` to create new API keys. Returns the
raw key exactly once in the response. The server only stores the
hash; the raw value cannot be recovered after creation.

Authentication is a static `ADMIN_TOKEN` bearer token (separate from
the X-API-Key used by regular endpoints). A compromised API key
cannot be used to mint more keys.
"""

from __future__ import annotations

import hmac
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field
from social_common.envelope import ResponseEnvelope, ResponseMeta
from sqlalchemy.ext.asyncio import AsyncSession

from social_api_gateway.auth.models import APIKeyTier
from social_api_gateway.auth.service import APIKeyService
from social_api_gateway.config import get_settings
from social_api_gateway.deps import get_db_session
from social_api_gateway.logging_setup import get_logger

logger = get_logger("social_api_gateway.admin.routes")

router = APIRouter(prefix="/v1/admin", tags=["admin"])

# `auto_error=False` so missing/invalid Authorization header does not
# raise FastAPI's default 403; we want to return our own 401 with a
# structured error envelope instead.
admin_security = HTTPBearer(
    description="Admin token from ADMIN_TOKEN env var.",
    auto_error=False,
)


class CreateKeyRequest(BaseModel):
    """Request body for creating a new API key."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        min_length=1,
        max_length=255,
        description="Human-readable label for the key (e.g. 'Mini App Prod').",
    )
    tier: APIKeyTier = Field(
        description="Tier: `internal`, `external_default`, or `external_elevated`.",
    )


class CreateKeyData(BaseModel):
    """Response body for a newly-created API key.

    The `api_key` field is the only place the raw key will ever appear.
    Save it immediately - the server cannot recover it later.
    """

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    tier: APIKeyTier
    key_prefix: str
    created_at: datetime
    api_key: str


@router.post(
    "/keys",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseEnvelope[CreateKeyData],
    summary="Create a new API key",
    description=(
        "Create a new API key. Returns the raw key exactly once in the response - "
        "the server only retains the hash. Requires the admin token in the "
        "`Authorization: Bearer <ADMIN_TOKEN>` header. This endpoint does not "
        "require or use a regular X-API-Key."
    ),
    responses={
        201: {
            "description": "Key created. The `api_key` field in `data` is the raw key, shown once."
        },
        401: {"description": "Missing admin token"},
        403: {"description": "Invalid admin token"},
        422: {"description": "Invalid request body"},
    },
    # Override the global X-API-Key security for this route so Swagger
    # renders the admin bearer dialog instead.
    openapi_extra={"security": [{"AdminAuth": []}]},
)
async def create_api_key(
    body: CreateKeyRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CreateKeyData]:
    """Create a new API key."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_admin_token", "message": "Admin token is required."},
        )

    settings = get_settings()
    expected = settings.admin.token.get_secret_value()

    if not hmac.compare_digest(credentials.credentials, expected):
        logger.warning("admin.key.create.unauthorized")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "invalid_admin_token", "message": "Admin token is invalid."},
        )

    service = APIKeyService(db)
    record, raw_key = await service.create(
        name=body.name,
        tier=body.tier,
        pepper=settings.auth.pepper.get_secret_value(),
    )

    logger.info(
        "admin.key.created",
        name=record.name,
        tier=record.tier.value,
        key_prefix=record.key_prefix,
        key_id=str(record.id),
    )

    return ResponseEnvelope(
        data=CreateKeyData(
            id=str(record.id),
            name=record.name,
            tier=record.tier,
            key_prefix=record.key_prefix,
            created_at=record.created_at,
            api_key=raw_key,
        ),
        meta=ResponseMeta(),
    )

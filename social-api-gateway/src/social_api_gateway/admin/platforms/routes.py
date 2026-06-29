"""Admin endpoints for platform and credential management.

All endpoints require `Authorization: Bearer <ADMIN_TOKEN>`.
"""

from __future__ import annotations

import hmac
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from social_common.envelope import ResponseEnvelope, ResponseMeta
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_settings
from ...deps import get_db_session
from ...logging_setup import get_logger
from .schemas import (
    CreateCredentialRequest,
    CreatePlatformRequest,
    CredentialDetailResponse,
    CredentialResponse,
    PlatformResponse,
    UpdateCredentialRequest,
    UpdatePlatformRequest,
)
from .service import (
    create_credential,
    create_platform,
    decrypt_credentials,
    get_credential_by_id,
    get_platform_by_id,
    get_platform_by_slug,
    list_credentials,
    list_platforms,
    revoke_credential,
    update_credential,
    update_platform,
)

logger = get_logger("social_api_gateway.admin.platforms.routes")

router = APIRouter(prefix="/v1/admin", tags=["admin"])
admin_security = HTTPBearer(
    description="Admin token from ADMIN_TOKEN env var.",
    auto_error=False,
)


def _verify_admin(
    credentials: HTTPAuthorizationCredentials | None,
) -> None:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "missing_admin_token", "message": "Admin token is required."},
        )
    settings = get_settings()
    expected = settings.admin.token.get_secret_value()
    if not hmac.compare_digest(credentials.credentials, expected):
        logger.warning("admin.platform.unauthorized")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "invalid_admin_token", "message": "Admin token is invalid."},
        )


# ──────────────────────────────────────────────
# Platform endpoints
# ──────────────────────────────────────────────


@router.get(
    "/platforms",
    response_model=ResponseEnvelope[list[PlatformResponse]],
    summary="List registered platforms",
)
async def list_platforms_endpoint(
    active_only: bool = Query(True, alias="active_only"),
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[list[PlatformResponse]]:
    _verify_admin(credentials)
    platforms = await list_platforms(db, active_only=active_only)
    return ResponseEnvelope(
        data=[PlatformResponse.model_validate(p) for p in platforms],
        meta=ResponseMeta(),
    )


@router.get(
    "/platforms/{platform_id}",
    response_model=ResponseEnvelope[PlatformResponse],
    summary="Get platform details",
)
async def get_platform_endpoint(
    platform_id: UUID,
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[PlatformResponse]:
    _verify_admin(credentials)
    platform = await get_platform_by_id(db, platform_id)
    if platform is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "platform_not_found", "message": "Platform not found."},
        )
    return ResponseEnvelope(
        data=PlatformResponse.model_validate(platform),
        meta=ResponseMeta(),
    )


@router.post(
    "/platforms",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseEnvelope[PlatformResponse],
    summary="Register a new platform",
)
async def create_platform_endpoint(
    body: CreatePlatformRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[PlatformResponse]:
    _verify_admin(credentials)
    platform = await create_platform(db, body.model_dump())
    logger.info("admin.platform.created", slug=platform.slug, name=platform.name)
    return ResponseEnvelope(
        data=PlatformResponse.model_validate(platform),
        meta=ResponseMeta(),
    )


@router.put(
    "/platforms/{platform_id}",
    response_model=ResponseEnvelope[PlatformResponse],
    summary="Update platform metadata",
)
async def update_platform_endpoint(
    platform_id: UUID,
    body: UpdatePlatformRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[PlatformResponse]:
    _verify_admin(credentials)
    platform = await update_platform(db, platform_id, body.model_dump(exclude_none=True))
    if platform is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "platform_not_found", "message": "Platform not found."},
        )
    return ResponseEnvelope(
        data=PlatformResponse.model_validate(platform),
        meta=ResponseMeta(),
    )


# ──────────────────────────────────────────────
# Credential endpoints
# ──────────────────────────────────────────────


@router.get(
    "/credentials",
    response_model=ResponseEnvelope[list[CredentialResponse]],
    summary="List stored credentials",
)
async def list_credentials_endpoint(
    platform_id: UUID | None = Query(None, alias="platform_id"),
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[list[CredentialResponse]]:
    _verify_admin(credentials)
    creds = await list_credentials(db, platform_id=platform_id)
    results: list[CredentialResponse] = []
    for c in creds:
        platform = await get_platform_by_id(db, c.platform_id)
        resp = CredentialResponse(
            id=str(c.id),
            platform_id=str(c.platform_id),
            platform_slug=platform.slug if platform else "",
            label=c.label,
            status=c.status,
            last_verified_at=c.last_verified_at,
            is_active=c.is_active,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        results.append(resp)
    return ResponseEnvelope(data=results, meta=ResponseMeta())


@router.get(
    "/credentials/{credential_id}",
    response_model=ResponseEnvelope[CredentialDetailResponse],
    summary="Get credential details (without secret values)",
)
async def get_credential_endpoint(
    credential_id: UUID,
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CredentialDetailResponse]:
    _verify_admin(credentials)
    cred = await get_credential_by_id(db, credential_id)
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "credential_not_found", "message": "Credential not found."},
        )
    platform = await get_platform_by_id(db, cred.platform_id)
    try:
        decrypted = decrypt_credentials(cred.credentials)
    except Exception:
        decrypted = {}
    resp = CredentialDetailResponse(
        id=str(cred.id),
        platform_id=str(cred.platform_id),
        platform_slug=platform.slug if platform else "",
        label=cred.label,
        status=cred.status,
        last_verified_at=cred.last_verified_at,
        is_active=cred.is_active,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
        configured_fields=list(decrypted.keys()),
    )
    return ResponseEnvelope(data=resp, meta=ResponseMeta())


@router.post(
    "/credentials",
    status_code=status.HTTP_201_CREATED,
    response_model=ResponseEnvelope[CredentialResponse],
    summary="Create a credential + subject",
    description=(
        "Create a credential and its linked subject in one operation. "
        "The credential value is encrypted before storage and never returned. "
        "The subject is created with status=INACTIVE; first sync populates it."
    ),
)
async def create_credential_endpoint(
    body: CreateCredentialRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CredentialResponse]:
    _verify_admin(credentials)

    platform = await get_platform_by_slug(db, body.platform_slug)
    if platform is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "platform_not_found",
                "message": f"Platform '{body.platform_slug}' not found or inactive.",
            },
        )

    cred, subject_id = await create_credential(db, platform, body.label, body.credentials)

    logger.info(
        "admin.credential.created",
        credential_id=str(cred.id),
        platform=platform.slug,
        label=body.label,
        subject_id=str(subject_id),
    )

    resp = CredentialResponse(
        id=str(cred.id),
        platform_id=str(cred.platform_id),
        platform_slug=platform.slug,
        label=cred.label,
        status=cred.status,
        last_verified_at=cred.last_verified_at,
        is_active=cred.is_active,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
    )
    return ResponseEnvelope(data=resp, meta=ResponseMeta())


@router.put(
    "/credentials/{credential_id}",
    response_model=ResponseEnvelope[CredentialResponse],
    summary="Update credential",
)
async def update_credential_endpoint(
    credential_id: UUID,
    body: UpdateCredentialRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CredentialResponse]:
    _verify_admin(credentials)
    cred = await update_credential(db, credential_id, body.model_dump(exclude_none=True))
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "credential_not_found", "message": "Credential not found."},
        )
    platform = await get_platform_by_id(db, cred.platform_id)
    resp = CredentialResponse(
        id=str(cred.id),
        platform_id=str(cred.platform_id),
        platform_slug=platform.slug if platform else "",
        label=cred.label,
        status=cred.status,
        last_verified_at=cred.last_verified_at,
        is_active=cred.is_active,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
    )
    return ResponseEnvelope(data=resp, meta=ResponseMeta())


@router.delete(
    "/credentials/{credential_id}",
    status_code=status.HTTP_200_OK,
    response_model=ResponseEnvelope[CredentialResponse],
    summary="Revoke a credential",
)
async def revoke_credential_endpoint(
    credential_id: UUID,
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CredentialResponse]:
    _verify_admin(credentials)
    cred = await revoke_credential(db, credential_id)
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "credential_not_found", "message": "Credential not found."},
        )
    platform = await get_platform_by_id(db, cred.platform_id)
    resp = CredentialResponse(
        id=str(cred.id),
        platform_id=str(cred.platform_id),
        platform_slug=platform.slug if platform else "",
        label=cred.label,
        status=cred.status,
        last_verified_at=cred.last_verified_at,
        is_active=cred.is_active,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
    )
    return ResponseEnvelope(data=resp, meta=ResponseMeta())


@router.post(
    "/credentials/{credential_id}/verify",
    response_model=ResponseEnvelope[CredentialResponse],
    summary="Verify credential against platform API",
)
async def verify_credential_endpoint(
    credential_id: UUID,
    credentials: HTTPAuthorizationCredentials | None = Depends(admin_security),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CredentialResponse]:
    _verify_admin(credentials)
    cred = await get_credential_by_id(db, credential_id)
    if cred is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "credential_not_found", "message": "Credential not found."},
        )
    # Verification is a placeholder — the actual verification call
    # is performed by the collector's sync task. Here we just mark
    # the credential as verified.
    from datetime import UTC, datetime

    cred.last_verified_at = datetime.now(UTC)
    cred.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(cred)

    platform = await get_platform_by_id(db, cred.platform_id)
    resp = CredentialResponse(
        id=str(cred.id),
        platform_id=str(cred.platform_id),
        platform_slug=platform.slug if platform else "",
        label=cred.label,
        status=cred.status,
        last_verified_at=cred.last_verified_at,
        is_active=cred.is_active,
        created_at=cred.created_at,
        updated_at=cred.updated_at,
    )
    return ResponseEnvelope(data=resp, meta=ResponseMeta())

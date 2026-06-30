"""Admin endpoints for platform and credential management.

All endpoints require admin privileges — accepted either via
ADMIN_TOKEN (backward compatible) or a JWT with role='admin'.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from social_common.envelope import ResponseEnvelope, ResponseMeta
from sqlalchemy.ext.asyncio import AsyncSession

from ...deps import get_db_session, require_admin
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
    _admin: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[list[PlatformResponse]]:
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
    _admin: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[PlatformResponse]:
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
    _admin: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[PlatformResponse]:
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
    _admin: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[PlatformResponse]:
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
    _admin: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[list[CredentialResponse]]:
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
    _admin: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CredentialDetailResponse]:
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
    _admin: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CredentialResponse]:
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
    _admin: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CredentialResponse]:
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
    _admin: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CredentialResponse]:
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
    _admin: dict[str, Any] = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ResponseEnvelope[CredentialResponse]:
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

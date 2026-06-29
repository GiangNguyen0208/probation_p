"""Business logic for platform and credential management.

Handles encryption/decryption of credentials via `cryptography.fernet`,
platform lookup, credential CRUD with automatic subject creation for the
1:1 credential-to-subject mapping.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from social_common.enums import Platform, SubjectStatus
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...config import get_settings
from ...logging_setup import get_logger
from ...subjects.models import SubjectModel
from .models import PlatformCredentialModel, PlatformModel

# Fields that are always present in a decrypted credentials dict but are not
# part of the platform config_schema (e.g. identifiers used during subject
# creation). These are not validated against config_schema.
_INTERNAL_CREDENTIAL_FIELDS = frozenset(["page_id", "channel_id"])

logger = get_logger("social_api_gateway.admin.platforms.service")


class CredentialEncryptionError(Exception):
    """Raised when credential encryption or decryption fails."""


def _get_fernet() -> Fernet:
    settings = get_settings()
    key = settings.credential.encryption_key.get_secret_value()
    if not key:
        raise CredentialEncryptionError(
            "CREDENTIAL_ENCRYPTION_KEY is not configured. "
            'Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_credentials(credentials: Mapping[str, Any]) -> dict[str, Any]:
    """Encrypt all sensitive fields in a credential dict.

    The entire credentials dict is JSON-serialized and encrypted as a
    single blob via Fernet. The stored value is `{"_encrypted": "<token>"}`.
    """
    fernet = _get_fernet()
    payload = json.dumps(credentials, sort_keys=True).encode()
    token = fernet.encrypt(payload)
    return {"_encrypted": token.decode()}


def decrypt_credentials(encrypted: dict[str, Any]) -> dict[str, Any]:
    """Decrypt a credentials blob.

    Expects `{"_encrypted": "<token>"}` format. Returns the original dict.
    Raises `CredentialEncryptionError` on invalid token or key mismatch.
    """
    token_raw = encrypted.get("_encrypted")
    if not token_raw:
        raise CredentialEncryptionError("Encrypted credentials missing '_encrypted' field")
    fernet = _get_fernet()
    try:
        payload = fernet.decrypt(token_raw.encode())
        return dict(json.loads(payload))
    except InvalidToken as exc:
        raise CredentialEncryptionError(
            "Failed to decrypt credentials: invalid token or key"
        ) from exc


async def get_platform_by_slug(db: AsyncSession, slug: str) -> PlatformModel | None:
    result = await db.execute(
        select(PlatformModel).where(PlatformModel.slug == slug, PlatformModel.is_active.is_(True))
    )
    return result.scalar_one_or_none()


async def get_platform_by_id(db: AsyncSession, platform_id: UUID) -> PlatformModel | None:
    result = await db.execute(select(PlatformModel).where(PlatformModel.id == platform_id))
    return result.scalar_one_or_none()


async def list_platforms(db: AsyncSession, active_only: bool = True) -> list[PlatformModel]:
    stmt = select(PlatformModel).order_by(PlatformModel.name)
    if active_only:
        stmt = stmt.where(PlatformModel.is_active.is_(True))
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_platform(db: AsyncSession, data: dict[str, Any]) -> PlatformModel:
    record = PlatformModel(**data)
    db.add(record)
    await db.flush()
    await db.commit()
    await db.refresh(record)
    return record


async def update_platform(db: AsyncSession, platform_id: UUID, data: dict[str, Any]) -> PlatformModel | None:
    record = await get_platform_by_id(db, platform_id)
    if record is None:
        return None
    for key, value in data.items():
        if value is not None:
            setattr(record, key, value)
    record.updated_at = datetime.now(UTC)
    await db.flush()
    await db.commit()
    await db.refresh(record)
    return record


async def list_credentials(
    db: AsyncSession, platform_id: UUID | None = None
) -> list[PlatformCredentialModel]:
    stmt = select(PlatformCredentialModel).order_by(PlatformCredentialModel.created_at.desc())
    if platform_id is not None:
        stmt = stmt.where(PlatformCredentialModel.platform_id == platform_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_credential_by_id(
    db: AsyncSession, credential_id: UUID
) -> PlatformCredentialModel | None:
    result = await db.execute(
        select(PlatformCredentialModel).where(PlatformCredentialModel.id == credential_id)
    )
    return result.scalar_one_or_none()


def _validate_credential_schema(raw_credentials: dict[str, Any], config_schema: dict[str, Any]) -> None:
    """Validate raw_credentials against the platform's config_schema.

    Raises HTTPException if required fields are missing.
    Only checks fields defined in config_schema; internal fields (page_id,
    channel_id) are excluded from validation.
    """
    from fastapi import HTTPException, status

    for field_name, schema in config_schema.items():
        if schema.get("required") and field_name not in raw_credentials:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={
                    "code": "missing_required_field",
                    "message": f"Missing required credential field: '{field_name}'.",
                    "field": field_name,
                },
            )


async def create_credential(
    db: AsyncSession,
    platform: PlatformModel,
    label: str,
    raw_credentials: dict[str, Any],
) -> tuple[PlatformCredentialModel, UUID]:
    """Create a credential + subject in one transaction.

    Returns (credential_record, subject_id).
    The subject is created with status=INACTIVE and will be populated
    on first sync.

    Validates raw_credentials against the platform's config_schema
    before encrypting.
    """
    _validate_credential_schema(raw_credentials, platform.config_schema)
    encrypted = encrypt_credentials(raw_credentials)

    credential = PlatformCredentialModel(
        platform_id=platform.id,
        label=label,
        credentials=encrypted,
    )
    db.add(credential)
    await db.flush()

    slug = platform.slug.upper()
    platform_enum = getattr(Platform, slug, None)
    platform_id_value = str(
        raw_credentials.get("page_id") or raw_credentials.get("channel_id") or ""
    )

    subject = SubjectModel(
        platform=platform_enum,
        platform_id=platform_id_value,
        name=f"Pending: {label}",
        display_name=f"Pending: {label}",
        followers=0,
        post_count=0,
        activity_frequency=0.0,
        status=SubjectStatus.INACTIVE,
        last_synced_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        credential_id=credential.id,
    )
    db.add(subject)
    await db.flush()
    await db.commit()
    await db.refresh(credential)

    logger.info(
        "credential.created",
        credential_id=str(credential.id),
        platform=platform.slug,
        label=label,
        subject_id=str(subject.id),
    )

    return credential, subject.id


async def update_credential(
    db: AsyncSession,
    credential_id: UUID,
    data: dict[str, Any],
) -> PlatformCredentialModel | None:
    record = await get_credential_by_id(db, credential_id)
    if record is None:
        return None
    if "credentials" in data and data["credentials"] is not None:
        record.credentials = encrypt_credentials(data["credentials"])
    if "label" in data:
        record.label = data["label"]
    if "is_active" in data:
        record.is_active = data["is_active"]
    record.updated_at = datetime.now(UTC)
    await db.flush()
    await db.commit()
    await db.refresh(record)
    return record


async def revoke_credential(
    db: AsyncSession, credential_id: UUID
) -> PlatformCredentialModel | None:
    record = await get_credential_by_id(db, credential_id)
    if record is None:
        return None
    record.is_active = False
    record.status = "revoked"
    record.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(record)

    # Cascade: mark linked subject as inactive too
    result = await db.execute(
        select(SubjectModel).where(
            SubjectModel.credential_id == credential_id,
            SubjectModel.status != SubjectStatus.SUSPENDED,
        )
    )
    subject = result.scalar_one_or_none()
    if subject is not None:
        subject.status = SubjectStatus.INACTIVE
        await db.flush()

    await db.commit()
    return record

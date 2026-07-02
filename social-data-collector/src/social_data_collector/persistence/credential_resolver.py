"""Lookup and decrypt platform credentials from the database.

Used by the sync tasks to resolve per-subject credentials when a subject
has a `credential_id`. Falls back to env-var credentials for legacy
subjects without a credential_id.
"""

from __future__ import annotations

import json
import os
from typing import Any
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select

from ..logging_setup import get_logger
from .db import get_session_factory
from .models import PlatformCredentialModel

logger = get_logger("social_data_collector.persistence.credential_resolver")


class CredentialResolutionError(Exception):
    """Raised when credential lookup or decryption fails."""


def _get_fernet() -> Fernet:
    """Return a Fernet instance configured from CREDENTIAL_ENCRYPTION_KEY."""
    key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY", "")
    if not key:
        raise CredentialResolutionError("CREDENTIAL_ENCRYPTION_KEY is not set in environment")
    return Fernet(key.encode() if isinstance(key, str) else key)


def _decrypt(encrypted: dict[str, Any]) -> dict[str, Any]:
    """Decrypt a credentials blob. Expects `{"_encrypted": "<token>"}`."""
    token_raw = encrypted.get("_encrypted")
    if not token_raw:
        raise CredentialResolutionError("Missing '_encrypted' field in credentials")
    fernet = _get_fernet()
    try:
        payload = fernet.decrypt(token_raw.encode())
        return dict(json.loads(payload))
    except InvalidToken as exc:
        raise CredentialResolutionError("Failed to decrypt credentials") from exc


def encrypt_credentials(data: dict[str, Any]) -> dict[str, Any]:
    """Encrypt a credentials dict and return the storage blob.

    The returned dict has the shape ``{"_encrypted": "<fernet-token>"}``
    and is what should be stored in the ``credentials`` JSONB column.
    """
    fernet = _get_fernet()
    payload = json.dumps(data).encode()
    token = fernet.encrypt(payload).decode()
    return {"_encrypted": token}


def resolve_credential(credential_id: UUID) -> dict[str, Any] | None:
    """Look up a credential by ID, decrypt it, and return the decrypted dict.

    Returns None if the credential is not found or not active.
    Raises `CredentialResolutionError` on decryption failure.
    """
    session_factory = get_session_factory()
    with session_factory() as session:
        stmt = select(PlatformCredentialModel).where(
            PlatformCredentialModel.id == credential_id,
            PlatformCredentialModel.is_active.is_(True),
        )
        result = session.execute(stmt)
        cred = result.scalar_one_or_none()

    if cred is None:
        return None

    try:
        return _decrypt(cred.credentials)
    except CredentialResolutionError:
        logger.error(
            "credential.decrypt_failed",
            credential_id=str(credential_id),
        )
        raise

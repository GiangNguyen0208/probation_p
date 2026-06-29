"""API key lookup, creation, and revocation."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import APIKeyModel, APIKeyTier
from .security import generate_key, hash_key, key_prefix


class APIKeyService:
    """Look up, create, and revoke API keys."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def lookup_by_prefix(self, prefix: str) -> APIKeyModel | None:
        """Find a key by its prefix. Returns None if not found."""
        result = await self._db.execute(select(APIKeyModel).where(APIKeyModel.key_prefix == prefix))
        return result.scalar_one_or_none()

    async def get_by_id(self, key_id: UUID) -> APIKeyModel | None:
        result = await self._db.execute(select(APIKeyModel).where(APIKeyModel.id == key_id))
        return result.scalar_one_or_none()

    async def create(
        self,
        name: str,
        tier: APIKeyTier,
        pepper: str,
    ) -> tuple[APIKeyModel, str]:
        """Create a new API key. Returns (record, raw_key).

        The raw key is returned exactly once. Store it securely; the
        server only retains the hash.
        """
        raw_key = generate_key()
        record = APIKeyModel(
            id=uuid4(),
            name=name,
            key_prefix=key_prefix(raw_key),
            key_hash=hash_key(raw_key, pepper),
            tier=tier,
            is_active=True,
        )
        self._db.add(record)
        await self._db.commit()
        await self._db.refresh(record)
        return record, raw_key

    async def revoke(self, key_id: UUID) -> bool:
        """Revoke a key. Returns True if the key existed and was revoked."""
        record = await self.get_by_id(key_id)
        if record is None:
            return False
        record.is_active = False
        record.revoked_at = datetime.now(UTC)
        await self._db.commit()
        return True

    async def mark_used(self, key_id: UUID) -> None:
        """Update `last_used_at` for a key. Best-effort, swallows errors."""
        record = await self.get_by_id(key_id)
        if record is not None:
            record.last_used_at = datetime.now(UTC)
            try:
                await self._db.commit()
            except Exception:  # noqa: BLE001
                await self._db.rollback()

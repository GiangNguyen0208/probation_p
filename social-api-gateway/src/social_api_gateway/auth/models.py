"""SQLAlchemy model and tier enum for API keys."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..db import Base


def _utcnow() -> datetime:
    return datetime.now(UTC)


class TelegramUserModel(Base):
    """Telegram users authenticated via initData login.

    ``telegram_id`` is the primary key (since Telegram provides it).
    On each login the user is upserted: ``last_login_at`` and profile
    fields are updated while ``created_at`` is preserved.
    """

    __tablename__ = "telegram_users"

    telegram_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=False,
        comment="Telegram user ID from initData.",
    )
    first_name: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    last_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_login_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class APIKeyTier(StrEnum):
    """API key tier. Controls rate limits and (in Sprint 2) write access."""

    INTERNAL = "internal"
    EXTERNAL_DEFAULT = "external_default"
    EXTERNAL_ELEVATED = "external_elevated"


class APIKeyModel(Base):
    __tablename__ = "api_keys"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # First 16 chars of the raw key (the literal prefix plus 7 random
    # base62 chars). Indexed unique for the lookup-then-verify pattern.
    # The full key is never stored.
    key_prefix: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    # HMAC-SHA-256 of the raw key with the server-side pepper.
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    tier: Mapped[APIKeyTier] = mapped_column(
        SAEnum(
            APIKeyTier, name="api_key_tier_enum", values_callable=lambda e: [m.value for m in e]
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

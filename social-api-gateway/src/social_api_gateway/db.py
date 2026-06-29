"""Async SQLAlchemy engine, session factory, and declarative base.

A single process-wide async engine is created lazily on first use.
The session factory yields short-lived `AsyncSession` instances for
request handlers. The same engine is used by Alembic for migrations.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import DatabaseSettings, Settings, get_settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


class Base(DeclarativeBase):
    """Declarative base for all ORM models in the gateway."""


def get_engine(settings: DatabaseSettings | Settings | None = None) -> AsyncEngine:
    """Return the process-wide async SQLAlchemy engine, creating it on first use."""
    global _engine
    if _engine is None:
        resolved = (
            settings.database
            if isinstance(settings, Settings)
            else (settings or get_settings().database)
        )
        _engine = create_async_engine(
            resolved.url,
            pool_size=resolved.pool_size,
            pool_recycle=resolved.pool_recycle_seconds,
            pool_pre_ping=True,
            echo=resolved.echo,
            future=True,
        )
    return _engine


def get_session_factory(engine: AsyncEngine | None = None) -> async_sessionmaker[AsyncSession]:
    """Return the process-wide session factory, creating it on first use."""
    global _session_factory
    if _session_factory is None:
        if engine is None:
            engine = get_engine()
        _session_factory = async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    return _session_factory


async def dispose_engine() -> None:
    """Dispose the engine. Call from app shutdown to release connections."""
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_factory = None

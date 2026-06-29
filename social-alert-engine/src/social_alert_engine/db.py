"""SQLAlchemy engine and session factory."""

from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import DatabaseSettings, Settings, get_settings

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


class Base(DeclarativeBase):
    pass


def get_engine(settings: DatabaseSettings | None = None) -> Engine:
    global _engine
    if _engine is None:
        resolved = settings or get_settings().database
        _engine = create_engine(
            resolved.url,
            pool_size=resolved.pool_size,
            pool_recycle=resolved.pool_recycle_seconds,
            pool_pre_ping=True,
            echo=resolved.echo,
            future=True,
        )
    return _engine


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        engine = get_engine((settings or get_settings()).database)
        _session_factory = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    return _session_factory


def reset_for_tests() -> None:
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None

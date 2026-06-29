"""Shared pytest fixtures for the API gateway tests.

Tests run against an in-memory SQLite database and a fakeredis client
so they need no external services. The `test_app` fixture builds a
FastAPI app instance with the DB and Redis dependencies overridden
to point at the test fixtures. Each test gets a fresh app and client
to keep state isolated.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import fakeredis.aioredis
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from social_common.enums import Platform, SubjectStatus
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from social_api_gateway.auth.models import APIKeyModel, APIKeyTier
from social_api_gateway.auth.security import generate_test_key, hash_key, key_prefix
from social_api_gateway.config import get_settings
from social_api_gateway.db import Base
from social_api_gateway.deps import get_db_session, get_redis_client
from social_api_gateway.subjects.models import ActivitySnapshotModel, SubjectModel

TEST_PEPPER = "test_pepper_do_not_use_in_production"
TEST_ADMIN_TOKEN = "test_admin_token_for_unit_tests_only"


@pytest_asyncio.fixture
async def db_engine(monkeypatch):
    """In-memory SQLite engine, schema created fresh per test."""
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("API_KEY_PEPPER", TEST_PEPPER)
    monkeypatch.setenv("ADMIN_TOKEN", TEST_ADMIN_TOKEN)
    get_settings.cache_clear()

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()
        get_settings.cache_clear()


@pytest_asyncio.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def fake_redis():
    redis = fakeredis.aioredis.FakeRedis()
    try:
        yield redis
    finally:
        await redis.aclose()


@pytest_asyncio.fixture
async def test_app(db_engine, fake_redis):
    """FastAPI app with DB and Redis dependencies overridden to test fixtures."""
    from social_api_gateway.main import create_app

    app = create_app()
    session_factory = async_sessionmaker(bind=db_engine, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    async def override_get_redis():
        yield fake_redis

    app.dependency_overrides[get_db_session] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis
    yield app


@pytest_asyncio.fixture
async def client(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def admin_token() -> str:
    """The admin token configured in the test environment."""
    return TEST_ADMIN_TOKEN


@pytest_asyncio.fixture
async def internal_api_key(db_session) -> str:
    raw = generate_test_key()
    db_session.add(
        APIKeyModel(
            id=uuid4(),
            name="Test Internal Key",
            key_prefix=key_prefix(raw),
            key_hash=hash_key(raw, TEST_PEPPER),
            tier=APIKeyTier.INTERNAL,
            is_active=True,
        )
    )
    await db_session.commit()
    return raw


@pytest_asyncio.fixture
async def external_api_key(db_session) -> str:
    raw = generate_test_key()
    db_session.add(
        APIKeyModel(
            id=uuid4(),
            name="Test External Key",
            key_prefix=key_prefix(raw),
            key_hash=hash_key(raw, TEST_PEPPER),
            tier=APIKeyTier.EXTERNAL_DEFAULT,
            is_active=True,
        )
    )
    await db_session.commit()
    return raw


@pytest_asyncio.fixture
async def revoked_api_key(db_session) -> str:
    raw = generate_test_key()
    db_session.add(
        APIKeyModel(
            id=uuid4(),
            name="Test Revoked Key",
            key_prefix=key_prefix(raw),
            key_hash=hash_key(raw, TEST_PEPPER),
            tier=APIKeyTier.INTERNAL,
            is_active=False,
            revoked_at=datetime.now(UTC),
        )
    )
    await db_session.commit()
    return raw


@pytest_asyncio.fixture
async def sample_subject(db_session) -> SubjectModel:
    subject = SubjectModel(
        id=uuid4(),
        platform=Platform.FACEBOOK,
        platform_id="1234567890",
        name="Example Page",
        display_name="Example Page",
        followers=10000,
        post_count=50,
        activity_frequency=0.5,
        status=SubjectStatus.ACTIVE,
        last_synced_at=datetime.now(UTC),
        created_at=datetime.now(UTC) - timedelta(days=30),
    )
    db_session.add(subject)
    await db_session.commit()
    await db_session.refresh(subject)
    return subject


@pytest_asyncio.fixture
async def more_subjects(db_session) -> list[SubjectModel]:
    now = datetime.now(UTC)
    subjects = []
    for i in range(5):
        s = SubjectModel(
            id=uuid4(),
            platform=Platform.FACEBOOK if i % 2 == 0 else Platform.YOUTUBE,
            platform_id=f"page_{i}",
            name=f"Subject {i}",
            display_name=f"Subject {i}",
            followers=1000 * (i + 1),
            post_count=10 * (i + 1),
            activity_frequency=0.1 * (i + 1),
            status=SubjectStatus.ACTIVE,
            last_synced_at=now - timedelta(hours=i),
            created_at=now - timedelta(days=10),
        )
        db_session.add(s)
        subjects.append(s)
    await db_session.commit()
    return subjects


@pytest_asyncio.fixture
async def sample_snapshots(db_session, sample_subject) -> list[ActivitySnapshotModel]:
    now = datetime.now(UTC)
    snapshots = []
    for i in range(3):
        snap = ActivitySnapshotModel(
            subject_id=sample_subject.id,
            captured_at=now - timedelta(days=i),
            followers=10000 - i * 100,
            post_count=50 - i,
            frequency=0.5,
        )
        db_session.add(snap)
        snapshots.append(snap)
    await db_session.commit()
    return snapshots

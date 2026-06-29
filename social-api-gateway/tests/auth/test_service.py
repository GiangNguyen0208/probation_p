"""Tests for the API key service."""

from __future__ import annotations

import pytest

from social_api_gateway.auth.models import APIKeyTier
from social_api_gateway.auth.security import (
    key_prefix,
    verify_key,
)
from social_api_gateway.auth.service import APIKeyService

TEST_PEPPER = "test_pepper"


@pytest.mark.asyncio
async def test_create_key_returns_record_and_raw_key(db_session):
    service = APIKeyService(db_session)
    record, raw = await service.create(name="Test", tier=APIKeyTier.INTERNAL, pepper=TEST_PEPPER)
    assert record.id is not None
    assert record.tier == APIKeyTier.INTERNAL
    assert record.is_active is True
    assert record.key_prefix == key_prefix(raw)
    assert verify_key(raw, record.key_hash, TEST_PEPPER)


@pytest.mark.asyncio
async def test_lookup_by_prefix_finds_existing_key(db_session):
    service = APIKeyService(db_session)
    record, raw = await service.create(name="Test", tier=APIKeyTier.INTERNAL, pepper=TEST_PEPPER)
    found = await service.lookup_by_prefix(key_prefix(raw))
    assert found is not None
    assert found.id == record.id


@pytest.mark.asyncio
async def test_lookup_unknown_prefix_returns_none(db_session):
    service = APIKeyService(db_session)
    found = await service.lookup_by_prefix("ghn_nope")
    assert found is None


@pytest.mark.asyncio
async def test_revoke_marks_key_inactive(db_session):
    service = APIKeyService(db_session)
    record, _ = await service.create(name="Test", tier=APIKeyTier.INTERNAL, pepper=TEST_PEPPER)
    result = await service.revoke(record.id)
    assert result is True

    found = await service.lookup_by_prefix(record.key_prefix)
    assert found is not None
    assert found.is_active is False
    assert found.revoked_at is not None


@pytest.mark.asyncio
async def test_revoke_unknown_id_returns_false(db_session):
    service = APIKeyService(db_session)
    import uuid as _uuid

    result = await service.revoke(_uuid.uuid4())
    assert result is False

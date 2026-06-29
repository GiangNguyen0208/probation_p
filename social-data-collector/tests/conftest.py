"""Shared pytest fixtures.

These tests are pure unit tests for normalizers and clients — they
do not require a running database or Redis. The mocked HTTP layer
isolates platform API behavior from the rest of the system.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    with (FIXTURES_DIR / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def facebook_page_fixture() -> dict:
    return _load_fixture("facebook_page.json")


@pytest.fixture
def facebook_posts_fixture() -> dict:
    return _load_fixture("facebook_posts.json")


@pytest.fixture
def youtube_channel_fixture() -> dict:
    return _load_fixture("youtube_channel.json")


@pytest.fixture
def youtube_playlist_items_fixture() -> dict:
    return _load_fixture("youtube_playlist_items.json")

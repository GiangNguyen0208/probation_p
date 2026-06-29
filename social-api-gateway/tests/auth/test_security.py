"""Tests for API key hashing, generation, and verification."""

from __future__ import annotations

from social_api_gateway.auth.security import (
    generate_key,
    generate_test_key,
    hash_key,
    key_prefix,
    verify_key,
)


def test_generate_key_format():
    key = generate_key()
    assert key.startswith("ghn_live_")
    assert len(key) == 41


def test_generate_test_key_format():
    key = generate_test_key()
    assert key.startswith("ghn_test_")
    assert len(key) == 41


def test_key_prefix_returns_first_sixteen_chars():
    # "ghn_live_" (9 chars) + 7 random chars = 16-char unique prefix
    assert key_prefix("ghn_live_0123456789") == "ghn_live_0123456"
    assert len(key_prefix(generate_key())) == 16


def test_hash_key_is_deterministic():
    h1 = hash_key("test_key", "pepper")
    h2 = hash_key("test_key", "pepper")
    assert h1 == h2


def test_hash_key_differs_with_pepper():
    h1 = hash_key("test_key", "pepper1")
    h2 = hash_key("test_key", "pepper2")
    assert h1 != h2


def test_hash_key_differs_with_key():
    h1 = hash_key("key_one", "pepper")
    h2 = hash_key("key_two", "pepper")
    assert h1 != h2


def test_verify_key_accepts_correct_key():
    h = hash_key("correct_key", "pepper")
    assert verify_key("correct_key", h, "pepper") is True


def test_verify_key_rejects_wrong_key():
    h = hash_key("correct_key", "pepper")
    assert verify_key("wrong_key", h, "pepper") is False

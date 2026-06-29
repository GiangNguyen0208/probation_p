"""API key generation, hashing, and verification.

The full raw key is never stored. We store:
- `key_prefix` (first 16 chars) — indexed unique for fast lookup
- `key_hash` (HMAC-SHA-256 with the server-side pepper) — for verification

The prefix must be unique per key so the lookup-then-verify pattern
narrows to a single candidate row. Using only the literal `ghn_live_`
segment would make every live key share the same prefix, defeating the
unique index and the lookup. The first 16 chars include 7 random base62
characters, which is enough to guarantee uniqueness across issued keys.

The pepper is read from `API_KEY_PEPPER` env var. Rotating the pepper
invalidates every issued key, which is the intended rotation mechanism.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import string

ALPHABET = string.ascii_letters + string.digits  # base62
_KEY_PREFIX_LENGTH = 16


def generate_key() -> str:
    """Generate a new production API key. Format: `ghn_live_<32 base62 chars>`."""
    random_part = "".join(secrets.choice(ALPHABET) for _ in range(32))
    return f"ghn_live_{random_part}"


def generate_test_key() -> str:
    """Generate a new test API key. Format: `ghn_test_<32 base62 chars>`."""
    random_part = "".join(secrets.choice(ALPHABET) for _ in range(32))
    return f"ghn_test_{random_part}"


def key_prefix(raw_key: str) -> str:
    """Return the lookup prefix (first 16 characters) for an API key.

    16 chars cover the 9-char literal segment plus 7 random base62 chars,
    giving each key a unique prefix for the lookup-then-verify pattern.
    """
    return raw_key[:_KEY_PREFIX_LENGTH]


def hash_key(raw_key: str, pepper: str) -> str:
    """Hash an API key with HMAC-SHA-256 and the server-side pepper.

    Returns a hex-encoded digest. The pepper protects keys even if
    the database is leaked.
    """
    return hmac.new(pepper.encode(), raw_key.encode(), hashlib.sha256).hexdigest()


def verify_key(raw_key: str, expected_hash: str, pepper: str) -> bool:
    """Verify an API key against its expected hash. Constant-time comparison."""
    actual = hash_key(raw_key, pepper)
    return hmac.compare_digest(actual, expected_hash)

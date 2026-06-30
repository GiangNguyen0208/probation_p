"""Tests for Telegram initData signature verification."""

from __future__ import annotations

import hmac
import json
import time
import urllib.parse
from hashlib import sha256

from social_api_gateway.telegram.initdata import verify_init_data


def _sign_init_data(params: dict[str, str], bot_token: str) -> str:
    """Sign a set of initData params with a bot token to produce a valid initData string.

    This mirrors what Telegram does server-side and is used to generate
    valid test vectors.
    """
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), sha256).digest()
    items = [(k, v) for k, v in params.items() if k != "hash"]
    items.sort(key=lambda x: x[0])
    data_check_string = "\n".join(f"{k}={v}" for k, v in items)
    hash_val = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()
    params["hash"] = hash_val
    return urllib.parse.urlencode(params)


# Shared test bot token — never a real secret.
_BOT_TOKEN = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
_USER_ID = 123456789


def _make_valid_params(user_override: dict | None = None) -> dict[str, str]:
    user = {
        "id": _USER_ID,
        "first_name": "Test",
        "last_name": "User",
        "username": "testuser",
        "language_code": "en",
    }
    if user_override:
        user.update(user_override)
    return {
        "query_id": "AAHdF6IQAAAAAN0XohDhrOrc",
        "user": json.dumps(user),
        "auth_date": str(int(time.time())),
    }


def test_valid_init_data() -> None:
    params = _make_valid_params()
    init_data = _sign_init_data(params, _BOT_TOKEN)
    result = verify_init_data(init_data, _BOT_TOKEN)
    assert result is not None
    assert result.id == _USER_ID
    assert result.first_name == "Test"
    assert result.last_name == "User"
    assert result.username == "testuser"
    assert result.language_code == "en"


def test_invalid_hash() -> None:
    params = _make_valid_params()
    init_data = _sign_init_data(params, _BOT_TOKEN)
    init_data = init_data.replace("hash=", "hash=badbadbad")
    result = verify_init_data(init_data, _BOT_TOKEN)
    assert result is None


def test_tampered_user() -> None:
    params = _make_valid_params()
    init_data = _sign_init_data(params, _BOT_TOKEN)
    # Modify the user field after signing.
    parsed = dict(urllib.parse.parse_qsl(init_data))
    user = json.loads(parsed["user"])
    user["id"] = 999
    parsed["user"] = json.dumps(user)
    init_data = urllib.parse.urlencode(parsed)
    result = verify_init_data(init_data, _BOT_TOKEN)
    assert result is None


def test_tampered_query_id() -> None:
    params = _make_valid_params()
    init_data = _sign_init_data(params, _BOT_TOKEN)
    init_data = init_data.replace("query_id=", "query_id=EVIL")
    result = verify_init_data(init_data, _BOT_TOKEN)
    assert result is None


def test_missing_hash() -> None:
    params = _make_valid_params()
    init_data = _sign_init_data(params, _BOT_TOKEN)
    # Remove the hash parameter entirely.
    parsed = dict(urllib.parse.parse_qsl(init_data))
    del parsed["hash"]
    init_data = urllib.parse.urlencode(parsed)
    result = verify_init_data(init_data, _BOT_TOKEN)
    assert result is None


def test_expired() -> None:
    params = _make_valid_params()
    params["auth_date"] = str(int(time.time()) - 90000)  # 25h ago
    init_data = _sign_init_data(params, _BOT_TOKEN)
    result = verify_init_data(init_data, _BOT_TOKEN, max_age_seconds=86400)
    assert result is None


def test_wrong_bot_token() -> None:
    params = _make_valid_params()
    init_data = _sign_init_data(params, _BOT_TOKEN)
    result = verify_init_data(init_data, "wrong:token")
    assert result is None


def test_missing_user_field() -> None:
    params = _make_valid_params()
    del params["user"]
    init_data = _sign_init_data(params, _BOT_TOKEN)
    result = verify_init_data(init_data, _BOT_TOKEN)
    assert result is None


def test_minimal_user() -> None:
    """Verify works with minimal user data (only id and first_name)."""
    params = _make_valid_params({
        "id": _USER_ID,
        "first_name": "Minimal",
        "last_name": None,
        "username": None,
    })
    init_data = _sign_init_data(params, _BOT_TOKEN)
    result = verify_init_data(init_data, _BOT_TOKEN)
    assert result is not None
    assert result.id == _USER_ID
    assert result.first_name == "Minimal"
    assert result.last_name is None
    assert result.username is None


def test_invalid_auth_date() -> None:
    params = _make_valid_params()
    params["auth_date"] = "not-a-number"
    init_data = _sign_init_data(params, _BOT_TOKEN)
    result = verify_init_data(init_data, _BOT_TOKEN)
    assert result is None


def test_not_url_encoded() -> None:
    """Pass garbage that isn't URL-encoded."""
    result = verify_init_data("this is not valid init data", _BOT_TOKEN)
    assert result is None

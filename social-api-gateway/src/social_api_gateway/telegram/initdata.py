"""Telegram WebApp initData signature verification.

Telegram signs the initData string with HMAC-SHA-256 using the bot token
as the secret (prefixed with "WebAppData" as per the Telegram documentation).
The mini-app sends this signed string to the backend, which verifies it
before issuing a session JWT.

Reference: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app
"""

from __future__ import annotations

import hmac
import json
import time
from hashlib import sha256
from typing import Any
from urllib.parse import parse_qsl


class TelegramUserData:
    """Parsed and verified Telegram user data from initData."""

    __slots__ = ("id", "first_name", "last_name", "username", "language_code", "auth_date")

    def __init__(
        self,
        id: int,
        first_name: str,
        last_name: str | None = None,
        username: str | None = None,
        language_code: str | None = None,
        auth_date: int = 0,
    ) -> None:
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.username = username
        self.language_code = language_code
        self.auth_date = auth_date


def _compute_secret_key(bot_token: str) -> bytes:
    """Compute the HMAC secret key from the bot token.

    Per Telegram docs: secret_key = HMAC-SHA-256("WebAppData", bot_token)
    """
    return hmac.new(b"WebAppData", bot_token.encode(), sha256).digest()


def _parse_init_data(init_data: str) -> dict[str, str]:
    """Parse a raw initData query string into a dict of key-value pairs."""
    return dict(parse_qsl(init_data, keep_blank_values=True))


def _build_data_check_string(params: dict[str, str]) -> str:
    """Build the data check string by sorting all key=value pairs excluding `hash`.

    Pairs are sorted alphabetically by key and joined with newlines.
    """
    items = [(k, v) for k, v in params.items() if k != "hash"]
    items.sort(key=lambda x: x[0])
    return "\n".join(f"{k}={v}" for k, v in items)


def verify_init_data(init_data: str, bot_token: str, max_age_seconds: int = 86400) -> TelegramUserData | None:
    """Verify a Telegram WebApp initData string.

    Returns a `TelegramUserData` object on success, or ``None`` if the
    signature is invalid, the data is tampered with, or the auth_date
    is too old (beyond *max_age_seconds*).

    Args:
        init_data: The raw initData string from Telegram (URL-encoded query string).
        bot_token: The Telegram bot token used to verify the signature.
        max_age_seconds: Maximum age of the auth_date in seconds (default 86400 = 24h).

    Returns:
        TelegramUserData on success, None on failure.
    """
    params = _parse_init_data(init_data)
    received_hash = params.get("hash")
    if not received_hash:
        return None

    try:
        auth_date = int(params.get("auth_date", "0"))
    except (ValueError, TypeError):
        return None

    now = time.time()
    if now - auth_date > max_age_seconds:
        return None

    secret_key = _compute_secret_key(bot_token)
    data_check_string = _build_data_check_string(params)
    expected_hash = hmac.new(secret_key, data_check_string.encode(), sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, received_hash):
        return None

    user_raw = params.get("user")
    if not user_raw:
        return None

    try:
        user_data: dict[str, Any] = json.loads(user_raw)
    except (json.JSONDecodeError, TypeError):
        return None

    user_id = user_data.get("id")
    if not isinstance(user_id, int):
        return None

    return TelegramUserData(
        id=user_id,
        first_name=user_data.get("first_name", ""),
        last_name=user_data.get("last_name"),
        username=user_data.get("username"),
        language_code=user_data.get("language_code"),
        auth_date=auth_date,
    )

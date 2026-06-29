"""Telegram Bot API helpers.

Thin wrappers around the Telegram Bot HTTP API. The webhook handler
calls these to send messages and build inline keyboards.
"""

from __future__ import annotations

import json
from typing import Any

from ..config import get_settings

_BASE = "https://api.telegram.org/bot"


def _bot_token() -> str:
    return get_settings().telegram.bot_token.get_secret_value()


def _url(method: str) -> str:
    return f"{_BASE}{_bot_token()}/{method}"


def _headers() -> dict[str, str]:
    return {"Content-Type": "application/json"}


def inline_keyboard_markup(buttons: list[list[dict[str, Any]]]) -> dict[str, Any]:
    """Build an inline keyboard markup object.

    Each button dict should have at least 'text' and one of
    'url', 'callback_data', or 'web_app'.
    """
    return {"inline_keyboard": [list(row) for row in buttons]}


async def send_message(
    chat_id: int | str,
    text: str,
    parse_mode: str = "HTML",
    reply_markup: dict[str, Any] | None = None,
) -> bool:
    """Send a text message to a Telegram chat.

    Returns True if the API call succeeded (HTTP 200).
    """
    import httpx

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                _url("sendMessage"),
                content=json.dumps(payload),
                headers=_headers(),
                timeout=10,
            )
        return resp.status_code == 200
    except Exception:  # noqa: BLE001
        return False

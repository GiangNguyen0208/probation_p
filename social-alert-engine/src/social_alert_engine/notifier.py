"""Telegram notification delivery via raw HTTP.

Mirrors the gateway's bot.py pattern (ADR-00X Decision 2). Sends alerts
to the Telegram chat ID stored in each alert rule's channel_id field.
If channel_id is missing, logs a warning and returns False — no silent
fallback to any global default (see docs/phase-4-implementation-notes.md).
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from .logging_setup import get_logger
from .settings import get_settings

logger = get_logger("social_alert_engine.notifier")

_BASE = "https://api.telegram.org/bot"


def _bot_token() -> str:
    return get_settings().telegram.bot_token.get_secret_value()


def _url(method: str) -> str:
    return f"{_BASE}{_bot_token()}/{method}"


def send_alert_notification(chat_id: str, message: str) -> bool:
    """Send an alert message to a Telegram chat.

    Returns True if Telegram accepted the message (HTTP 200).
    """
    if not chat_id:
        logger.warning("notifier.missing_chat_id")
        return False

    token = _bot_token()
    if not token:
        logger.error("notifier.missing_bot_token")
        return False

    payload: dict[str, Any] = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
    }

    try:
        resp = httpx.post(
            _url("sendMessage"),
            content=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        logger.warning(
            "notifier.api_error",
            status_code=resp.status_code,
            response=resp.text,
            chat_id=chat_id,
        )
        return False
    except httpx.RequestError as exc:
        logger.error("notifier.request_failed", error=str(exc), chat_id=chat_id)
        return False

"""Telegram webhook endpoint.

Receives updates from Telegram when users interact with the bot.
Phase 3 handles only:
- `/start` → welcome message + Mini App inline button
- `/help` → usage instructions
- Everything else → acknowledged and ignored

The webhook is NOT included in the OpenAPI schema (it is unauthenticated
and internal-only).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from ..config import get_settings
from ..logging_setup import get_logger
from .bot import inline_keyboard_markup, send_message

logger = get_logger("social_api_gateway.telegram.routes")

router = APIRouter(prefix="/api", tags=["telegram"])

# Include the router but exclude it from OpenAPI docs.
# We override include_router in main.py to pass include_in_schema=False.


@router.post(
    "/telegram-webhook",
    include_in_schema=False,
)
async def telegram_webhook(request: Request) -> dict[str, bool]:
    """Receive and process an update from Telegram.

    This endpoint is called by Telegram servers when users interact with
    the bot. It is not included in the public OpenAPI documentation.
    """
    try:
        update: dict[str, Any] = await request.json()
    except Exception as exc:
        logger.error("telegram.webhook.invalid_json", error=str(exc))
        return {"ok": False}

    logger.info("telegram.webhook.received", update_id=update.get("update_id"))

    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = (message.get("text") or "").strip().lower()

    if not chat_id or not text:
        return {"ok": True}

    settings = get_settings()
    bot_username = settings.telegram.bot_username

    if text == "/start":
        await _handle_start(chat_id, bot_username)
    elif text == "/help":
        await _handle_help(chat_id)
    else:
        logger.info("telegram.webhook.ignored", text=text)

    return {"ok": True}


async def _handle_start(chat_id: int | str, bot_username: str) -> None:
    mini_app_url = get_settings().telegram.app_url
    keyboard = inline_keyboard_markup(
        [
            [
                {
                    "text": "Open Social Intelligence",
                    "web_app": {"url": mini_app_url},
                }
            ]
        ]
    )
    await send_message(
        chat_id,
        (
            "<b>Welcome to Social Intelligence</b>\n\n"
            "Monitor your social media subjects, track follower trends, "
            "and set up alert rules — all from inside Telegram.\n\n"
            f"Bot: @{bot_username}"
        ),
        reply_markup=keyboard,
    )


async def _handle_help(chat_id: int | str) -> None:
    await send_message(
        chat_id,
        (
            "<b>Social Intelligence — Help</b>\n\n"
            "• Use the Mini App button below to open the dashboard\n"
            "• Browse and filter subjects\n"
            "• View follower and activity charts\n"
            "• Create alert rules for threshold breaches\n\n"
            "More features coming in future updates."
        ),
    )

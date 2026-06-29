"""Register the Telegram bot webhook URL.

Usage:
    python scripts/setup_webhook.py --token <BOT_TOKEN> --url <WEBHOOK_URL>

The URL should point to your gateway's /api/telegram-webhook endpoint
(e.g. https://abc123.ngrok-free.app/api/telegram-webhook).
"""

from __future__ import annotations

import argparse

import httpx

_API = "https://api.telegram.org/bot"


def main() -> None:
    parser = argparse.ArgumentParser(description="Set Telegram bot webhook")
    parser.add_argument("--token", required=True, help="Bot token from BotFather")
    parser.add_argument("--url", required=True, help="Webhook URL (HTTPS required by Telegram)")
    parser.add_argument(
        "--max-connections", type=int, default=40, help="Max simultaneous connections"
    )
    args = parser.parse_args()

    payload = {
        "url": args.url,
        "allowed_updates": ["message", "callback_query", "pre_checkout_query"],
        "max_connections": args.max_connections,
    }

    resp = httpx.post(
        f"{_API}{args.token}/setWebhook",
        json=payload,
        timeout=15,
    )
    data = resp.json()
    print(f"setWebhook response: {data}")

    if data.get("ok"):
        info_resp = httpx.get(f"{_API}{args.token}/getWebhookInfo", timeout=10)
        info = info_resp.json()
        print(f"\ngetWebhookInfo:\n{info.get('result', info)}")
    else:
        print(f"Failed: {data.get('description', 'unknown error')}")
        exit(1)


if __name__ == "__main__":
    main()

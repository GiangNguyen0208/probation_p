"""Print the current webhook status for a Telegram bot.

Usage:
    python scripts/webhook_info.py --token <BOT_TOKEN>
"""

from __future__ import annotations

import argparse

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Get Telegram webhook info")
    parser.add_argument("--token", required=True, help="Bot token from BotFather")
    args = parser.parse_args()

    resp = httpx.get(
        f"https://api.telegram.org/bot{args.token}/getWebhookInfo",
        timeout=10,
    )
    data = resp.json()
    print(data.get("result", data))


if __name__ == "__main__":
    main()

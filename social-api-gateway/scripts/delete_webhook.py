"""Remove the Telegram bot webhook.

Usage:
    python scripts/delete_webhook.py --token <BOT_TOKEN>
"""

from __future__ import annotations

import argparse

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Delete Telegram webhook")
    parser.add_argument("--token", required=True, help="Bot token from BotFather")
    args = parser.parse_args()

    resp = httpx.post(
        f"https://api.telegram.org/bot{args.token}/deleteWebhook",
        timeout=10,
    )
    data = resp.json()
    print(data)


if __name__ == "__main__":
    main()

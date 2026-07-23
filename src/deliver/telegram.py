"""Telegram delivery — push briefings to my phone, locked to my own chat ID.

Uses the raw Bot API over HTTPS (no framework) so it ports cleanly to a
Lambda webhook later.
"""
import os

import requests

API = "https://api.telegram.org/bot{token}/{method}"


def _token() -> str:
    return os.environ["TELEGRAM_BOT_TOKEN"]


def get_recent_chat_id(token: str | None = None) -> int | None:
    """Return the chat ID of the most recent message sent to the bot.

    Run this once after messaging your new bot to discover your chat ID.
    """
    token = token or _token()
    resp = requests.get(API.format(token=token, method="getUpdates"), timeout=15)
    resp.raise_for_status()
    updates = resp.json().get("result", [])
    for update in reversed(updates):
        msg = update.get("message") or update.get("edited_message")
        if msg and "chat" in msg:
            return msg["chat"]["id"]
    return None


def send_message(text: str, token: str | None = None, chat_id: str | None = None) -> None:
    """Send a message, but only to the configured (my) chat ID."""
    token = token or _token()
    chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]
    resp = requests.post(
        API.format(token=token, method="sendMessage"),
        json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"},
        timeout=15,
    )
    resp.raise_for_status()

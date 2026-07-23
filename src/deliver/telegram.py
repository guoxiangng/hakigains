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


def get_updates(offset: int | None = None, token: str | None = None, timeout: int = 30) -> list:
    """Long-poll for new updates. `offset` = last_update_id + 1 to acknowledge."""
    token = token or _token()
    params: dict = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    resp = requests.get(
        API.format(token=token, method="getUpdates"),
        params=params,
        timeout=timeout + 10,
    )
    resp.raise_for_status()
    return resp.json().get("result", [])


def send_message(
    text: str,
    token: str | None = None,
    chat_id: str | None = None,
    parse_mode: str | None = "Markdown",
) -> None:
    """Send a message. Defaults to the configured (owner's) chat ID.

    parse_mode=None sends plain text — safer for free-form LLM answers that may
    contain unbalanced Markdown characters.
    """
    token = token or _token()
    chat_id = chat_id or os.environ["TELEGRAM_CHAT_ID"]

    def _post(pm: str | None):
        payload: dict = {"chat_id": chat_id, "text": text}
        if pm:
            payload["parse_mode"] = pm
        return requests.post(
            API.format(token=token, method="sendMessage"), json=payload, timeout=15
        )

    resp = _post(parse_mode)
    if resp.status_code == 400 and parse_mode:
        # Markdown failed to parse (e.g. unbalanced *). Retry as plain text.
        resp = _post(None)
    resp.raise_for_status()

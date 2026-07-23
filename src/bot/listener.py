"""Interactive Telegram listener — GATED to the owner's chat ID.

Long-polls Telegram and ignores every sender except TELEGRAM_CHAT_ID. Anyone
can message a public bot; the gate is what keeps your data private. Commands:
  /brief (or "brief")  -> today's full briefing (ingest -> reason -> reply)
  /ping                -> health check
  <any other text>     -> coach Q&A grounded in today's readiness summary

Self-host: run this as an always-on process. On Lambda later it becomes a
webhook handler with the SAME gate and routing.
"""
import os
import sys
import time
from datetime import date

# Make `src/` importable regardless of launch dir (this file lives in src/bot/).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from deliver.telegram import get_updates, send_message
from garmin_client import get_client
from ingest.readiness import build_summary
from llm.factory import get_provider
from reason.coach import answer, recommend

load_dotenv()

ALLOWED_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])

# Cache the day's readiness so repeated questions don't re-hit Garmin each time.
_summary_cache: dict = {}


def _summary(client, d: str) -> dict:
    if d not in _summary_cache:
        _summary_cache[d] = build_summary(client, d)
    return _summary_cache[d]


def handle(text: str, client, llm) -> tuple[str, str | None]:
    """Return (reply_text, parse_mode). Markdown for structured briefs; plain
    (None) for free-form answers that may contain unbalanced Markdown."""
    text = (text or "").strip()
    low = text.lower()
    today = date.today().isoformat()

    if low in ("/ping", "ping"):
        return "pong — haki online.", None
    if low in ("/start", "/help", "help"):
        return (
            "hakigains 🏴‍☠️\n"
            "/brief — today's recommended session\n"
            "or just ask me anything about your training/recovery."
        ), None
    if low in ("/brief", "brief"):
        brief = recommend(_summary(client, today), llm)
        return f"🏴‍☠️ *HAKIGAINS — {today}*\n\n{brief}", "Markdown"

    # Anything else: treat as a coaching question grounded in today's data.
    return answer(text, _summary(client, today), llm), None


def main() -> None:
    print(f"hakigains listener starting — gated to chat {ALLOWED_CHAT_ID}")
    client = get_client()
    llm = get_provider()
    offset = None

    while True:
        try:
            updates = get_updates(offset=offset, timeout=30)
        except Exception as e:  # network hiccup — back off and retry
            print("poll error:", e)
            time.sleep(3)
            continue

        for u in updates:
            offset = u["update_id"] + 1
            msg = u.get("message") or u.get("edited_message")
            if not msg:
                continue

            chat_id = (msg.get("chat") or {}).get("id")
            # ---- THE GATE ----
            if chat_id != ALLOWED_CHAT_ID:
                print(f"[gate] ignored message from unauthorized chat {chat_id}")
                continue

            text = msg.get("text", "")
            print(f"[owner] {text!r}")
            try:
                reply, parse_mode = handle(text, client, llm)
            except Exception as e:
                reply, parse_mode = f"(hakigains hit an error: {e})", None
            send_message(reply, parse_mode=parse_mode)


if __name__ == "__main__":
    main()

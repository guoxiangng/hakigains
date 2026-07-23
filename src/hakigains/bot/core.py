"""Shared bot routing — used by BOTH the local long-poll listener and the Lambda
webhook. The chat-ID gate lives here so neither entry point can forget it.
"""
from datetime import date

from hakigains.config import Config, load_config, set_setting
from hakigains.deliver.telegram import send_message
from hakigains.ingest.readiness import build_summary
from hakigains.reason.coach import answer, recommend

# Cache the day's readiness (keyed by date + windows) to avoid re-hitting Garmin
# on every message.
_summary_cache: dict = {}

HELP = (
    "hakigains 🏴‍☠️\n"
    "/brief — today's recommended session\n"
    "/settings — show your current knobs\n"
    "/set <knob> <value> — e.g. /set intensity_bias aggressive\n"
    "…or just ask me anything about your training/recovery."
)

KNOBS = ("activity_window", "trend_days", "intensity_bias")


def _summary(client, config: Config, d: str) -> dict:
    key = (d, config.get("activity_window"), config.get("trend_days"))
    if key not in _summary_cache:
        _summary_cache[key] = build_summary(
            client,
            d,
            activity_window=config.get("activity_window"),
            trend_days=config.get("trend_days"),
        )
    return _summary_cache[key]


def handle(text: str, client, llm, config: Config) -> tuple[str, str | None]:
    """Route one message. Returns (reply, parse_mode)."""
    text = (text or "").strip()
    low = text.lower()
    today = date.today().isoformat()

    if low in ("/ping", "ping"):
        return "pong — haki online.", None
    if low in ("/start", "/help", "help"):
        return HELP, None
    if low in ("/settings", "/get"):
        lines = ["Current settings:"] + [f"  {k} = {config.get(k)}" for k in KNOBS]
        return "\n".join(lines), None
    if low.startswith("/set"):
        parts = text.split()
        if len(parts) != 3:
            return "Usage: /set <knob> <value>  (knobs: " + ", ".join(KNOBS) + ")", None
        return set_setting(parts[1], parts[2]), None
    if low in ("/brief", "brief"):
        brief = recommend(_summary(client, config, today), llm, config)
        return f"🏴‍☠️ *HAKIGAINS — {today}*\n\n{brief}", "Markdown"

    # Anything else: a coaching question grounded in today's data.
    return answer(text, _summary(client, config, today), llm, config), None


def process_update(update: dict, client, llm, allowed_chat_id: int) -> None:
    """Gate + handle a single Telegram update. Reloads config each call so /set
    changes take effect on the next message."""
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return

    chat_id = (msg.get("chat") or {}).get("id")
    # ---- THE GATE ----
    if chat_id != allowed_chat_id:
        print(f"[gate] ignored message from unauthorized chat {chat_id}")
        return

    text = msg.get("text", "")
    print(f"[owner] {text!r}")
    config = load_config()
    try:
        reply, parse_mode = handle(text, client, llm, config)
    except Exception as e:
        reply, parse_mode = f"(hakigains hit an error: {e})", None
    send_message(reply, parse_mode=parse_mode)

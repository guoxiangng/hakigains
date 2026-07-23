"""The morning briefing: ingest -> reason -> deliver. Importable core used by
both the local script (scripts/run_briefing.py) and the Lambda handler.
"""
from datetime import date

from hakigains.config import load_config
from hakigains.deliver.telegram import send_message
from hakigains.garmin_client import get_client
from hakigains.ingest.readiness import build_summary
from hakigains.llm.factory import get_provider
from hakigains.reason.coach import recommend


def generate_briefing(target_date: str | None = None) -> tuple[str, dict]:
    """Pull data + reason. Returns (briefing_text, readiness_summary)."""
    config = load_config()
    target = target_date or date.today().isoformat()

    client = get_client()
    summary = build_summary(
        client,
        target,
        activity_window=config.get("activity_window"),
        trend_days=config.get("trend_days"),
    )
    briefing = recommend(summary, get_provider(), config)
    return briefing, summary


def run_briefing(target_date: str | None = None, send: bool = True) -> str:
    """Generate today's briefing and (optionally) push it to Telegram."""
    target = target_date or date.today().isoformat()
    briefing, _ = generate_briefing(target)
    if send:
        send_message(f"🏴‍☠️ *HAKIGAINS — {target}*\n\n{briefing}", parse_mode="Markdown")
    return briefing

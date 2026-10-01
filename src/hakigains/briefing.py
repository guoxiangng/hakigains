"""The morning briefing: ingest -> reason -> deliver. Importable core used by
both the local script (scripts/run_briefing.py) and the Lambda handler.
"""
from datetime import date, timedelta

from hakigains.config import load_config, today
from hakigains.deliver.telegram import send_message
from hakigains.garmin_client import get_client
from hakigains.ingest.readiness import build_summary
from hakigains.llm.factory import get_provider
from hakigains.memory.factory import get_memory
from hakigains.reason.coach import build_memory_context, recommend


BRIEFING_QUERY = (
    "injuries, pain, illness, travel, schedule constraints, equipment and training "
    "preferences relevant to choosing today's session"
)


def briefing_context(day: str) -> str:
    """Memory block for a briefing: relevant long-term memories + yesterday's advice."""
    memory = get_memory()
    if not memory.enabled:
        return ""
    yesterday = (date.fromisoformat(day) - timedelta(days=1)).isoformat()
    briefs = [text for role, text in memory.turns(yesterday, limit=50) if role == "ASSISTANT"
              and "ACTIVITY RECOMMENDATION" in text]
    return build_memory_context(
        records=memory.recall(BRIEFING_QUERY),
        yesterday_brief=briefs[-1] if briefs else None,
    )


def save_briefing(day: str, briefing: str) -> None:
    """Keep the briefing as conversational context only — its daily numbers must
    not be extracted into long-term 'facts'."""
    get_memory().save_turns(day, [("ASSISTANT", briefing)], extract=False)


def generate_briefing(target_date: str | None = None) -> tuple[str, dict]:
    """Pull data + reason. Returns (briefing_text, readiness_summary)."""
    config = load_config()
    target = target_date or today()

    client = get_client()
    summary = build_summary(
        client,
        target,
        activity_window=config.get("activity_window"),
        trend_days=config.get("trend_days"),
    )
    briefing = recommend(summary, get_provider(), config, briefing_context(target))
    return briefing, summary


def run_briefing(target_date: str | None = None, send: bool = True) -> str:
    """Generate today's briefing and (optionally) push it to Telegram."""
    target = target_date or today()
    briefing, _ = generate_briefing(target)
    if send:
        save_briefing(target, briefing)
        send_message(f"🏴‍☠️ *HAKIGAINS — {target}*\n\n{briefing}", parse_mode="Markdown")
    return briefing

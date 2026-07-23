"""The morning briefing: ingest -> reason -> deliver.

Usage:
  python src/briefing.py                 # today, send to Telegram
  python src/briefing.py 2026-07-21      # a specific date
  python src/briefing.py 2026-07-21 --dry # print only, don't send
"""
import sys
from datetime import date

from dotenv import load_dotenv

from deliver.telegram import send_message
from garmin_client import get_client
from ingest.readiness import build_summary
from llm.factory import get_provider
from reason.coach import recommend

load_dotenv()


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry" in sys.argv
    target = args[0] if args else date.today().isoformat()

    client = get_client()
    summary = build_summary(client, target)

    if summary["sleep"]["hours"] is None:
        print(f"[warn] no sleep data for {target} yet — readiness may be incomplete.")

    llm = get_provider()
    briefing = recommend(summary, llm)

    print("=" * 60)
    print(briefing)
    print("=" * 60)

    if dry_run:
        print("[dry run] not sent to Telegram.")
        return

    send_message(f"🏴‍☠️ *hakigains — {target}*\n\n{briefing}")
    print("Sent to Telegram.")


if __name__ == "__main__":
    main()

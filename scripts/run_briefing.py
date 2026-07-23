"""Local CLI for the morning briefing.

  python scripts/run_briefing.py                   # today, send to Telegram
  python scripts/run_briefing.py 2026-07-21        # a specific date
  python scripts/run_briefing.py 2026-07-21 --dry  # print only, don't send
"""
import sys
from datetime import date

from dotenv import load_dotenv

from hakigains.briefing import generate_briefing, run_briefing

load_dotenv()


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    target = args[0] if args else date.today().isoformat()

    if dry:
        briefing, _ = generate_briefing(target)
        print("=" * 60, briefing, "=" * 60, "[dry run] not sent.", sep="\n")
    else:
        briefing = run_briefing(target)
        print("=" * 60, briefing, "=" * 60, "Sent to Telegram.", sep="\n")


if __name__ == "__main__":
    main()

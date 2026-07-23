"""Print the ingested readiness summary for a date (default: yesterday)."""
import json
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

from hakigains.config import load_config
from hakigains.garmin_client import get_client
from hakigains.ingest.readiness import build_summary

load_dotenv()


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else (date.today() - timedelta(days=1)).isoformat()
    config = load_config()
    client = get_client()
    summary = build_summary(
        client,
        target,
        activity_window=config.get("activity_window"),
        trend_days=config.get("trend_days"),
    )
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

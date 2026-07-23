"""Run ingest for a given date (default: yesterday) and print the summary."""
import json
import sys
from datetime import date, timedelta

from dotenv import load_dotenv

from garmin_client import get_client
from ingest.readiness import build_summary

load_dotenv()


def main() -> None:
    if len(sys.argv) > 1:
        target = sys.argv[1]
    else:
        target = (date.today() - timedelta(days=1)).isoformat()

    client = get_client()
    summary = build_summary(client, target)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

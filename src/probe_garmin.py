"""Throwaway probe: inspect the real shape of Garmin readiness endpoints so
ingest transforms actual fields, not guessed ones. Not part of the product.
"""
import json
import os
from datetime import date, timedelta

from dotenv import load_dotenv
from garminconnect import Garmin

load_dotenv()
TOKEN_STORE = os.path.expanduser("~/.hakigains/garth_token")


def shape(obj, depth=0):
    """Print keys + value types, not full payloads."""
    pad = "  " * depth
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, (dict, list)):
                print(f"{pad}{k}: {type(v).__name__}")
                if depth < 2:
                    shape(v, depth + 1)
            else:
                print(f"{pad}{k}: {v!r}")
    elif isinstance(obj, list):
        print(f"{pad}[list len={len(obj)}]")
        if obj and depth < 2:
            shape(obj[0], depth + 1)


def main() -> None:
    client = Garmin(os.environ["GARMIN_EMAIL"], os.environ["GARMIN_PASSWORD"])
    client.login(TOKEN_STORE)

    d = (date.today() - timedelta(days=2)).isoformat()
    print(f"=== probing for {d} ===\n")

    print("--- get_stats (user summary) ---")
    try:
        shape(client.get_stats(d))
    except Exception as e:
        print("ERR", e)

    print("\n--- get_sleep_data ---")
    try:
        s = client.get_sleep_data(d)
        shape(s.get("dailySleepDTO", {}))
    except Exception as e:
        print("ERR", e)

    print("\n--- get_hrv_data ---")
    try:
        shape(client.get_hrv_data(d))
    except Exception as e:
        print("ERR", e)

    print("\n--- get_training_status ---")
    try:
        ts = client.get_training_status(d)
        print(json.dumps(ts, indent=2, default=str)[:1500])
    except Exception as e:
        print("ERR", e)

    print("\n--- get_activities (last 5) ---")
    try:
        acts = client.get_activities(0, 5)
        for a in acts:
            print({
                "name": a.get("activityName"),
                "type": (a.get("activityType") or {}).get("typeKey"),
                "start": a.get("startTimeLocal"),
                "dur_min": round((a.get("duration") or 0) / 60, 1),
                "load": a.get("activityTrainingLoad"),
            })
    except Exception as e:
        print("ERR", e)


if __name__ == "__main__":
    main()

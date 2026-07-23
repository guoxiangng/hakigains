"""Milestone 1: auth to Garmin, pull one day of data, print it clean."""
import json
import os
from datetime import date

from dotenv import load_dotenv
from garminconnect import Garmin

load_dotenv()

TOKEN_STORE = os.path.expanduser("~/.hakigains/garth_token")


def get_client() -> Garmin:
    email = os.environ["GARMIN_EMAIL"]
    password = os.environ["GARMIN_PASSWORD"]

    client = Garmin(email, password)
    try:
        client.login(TOKEN_STORE)
    except Exception:
        client.login()
        client.garth.dump(TOKEN_STORE)
    return client


def main() -> None:
    client = get_client()
    today = date.today().isoformat()

    summary = {
        "date": today,
        "activities": client.get_activities_fordate(today),
        "sleep": client.get_sleep_data(today),
        "hrv": client.get_hrv_data(today),
        "body_battery": client.get_body_battery(today, today),
        "training_status": client.get_training_status(today),
    }

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()

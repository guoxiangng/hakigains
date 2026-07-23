"""Shared Garmin client with local token caching (avoids re-login / rate limits)."""
import os

from garminconnect import Garmin

# Env-overridable so Lambda can point at /tmp (ephemeral) with an S3-synced token.
TOKEN_STORE = os.environ.get(
    "HAKIGAINS_TOKEN_PATH", os.path.expanduser("~/.hakigains/garth_token")
)


def get_client() -> Garmin:
    client = Garmin(os.environ["GARMIN_EMAIL"], os.environ["GARMIN_PASSWORD"])
    try:
        client.login(TOKEN_STORE)
    except Exception:
        client.login()
        client.garth.dump(TOKEN_STORE)
    return client

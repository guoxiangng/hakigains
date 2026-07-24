"""Lambda entry points for hakigains — the SAME core logic as the local scripts.

- scheduled_briefing: EventBridge Scheduler -> the daily morning briefing.
- telegram_webhook:   Function URL -> the interactive bot (gated), one update/call.

Cold-start bootstrap (Lambda's filesystem is ephemeral):
- pull secrets from Secrets Manager into the environment
- sync the Garmin token + settings.json down from S3 to /tmp, and back up after,
  so auth isn't re-done every call (Garmin rate-limits logins) and /set persists.

NOTE: scaffolding — validated at deploy time, not in local unit tests.
"""
import json
import os

import boto3

_BOOTSTRAPPED = False
_CLIENT = None
_LLM = None

TOKEN_PREFIX = "token/"
SETTINGS_KEY = "settings.json"


def _load_secrets() -> None:
    name = os.environ.get("HAKIGAINS_SECRET_NAME")
    if not name:
        return
    secret = json.loads(
        boto3.client("secretsmanager").get_secret_value(SecretId=name)["SecretString"]
    )
    for k, v in secret.items():
        os.environ.setdefault(k, str(v))


def _settings_path() -> str:
    return os.path.join(os.environ["HAKIGAINS_DATA_DIR"], SETTINGS_KEY)


def _put_bytes(bucket: str, key: str, local: str) -> None:
    # Upload as bytes (files are tiny). Avoids botocore's UnseekableStreamError
    # from upload_file + default checksum streaming.
    if os.path.isfile(local):
        with open(local, "rb") as f:
            boto3.client("s3").put_object(Bucket=bucket, Key=key, Body=f.read())


def _get_bytes(bucket: str, key: str, local: str) -> None:
    try:
        body = boto3.client("s3").get_object(Bucket=bucket, Key=key)["Body"].read()
    except Exception:
        return  # first run — nothing stored yet
    os.makedirs(os.path.dirname(local) or ".", exist_ok=True)
    with open(local, "wb") as f:
        f.write(body)


def _put_dir(bucket: str, prefix: str, local_dir: str) -> None:
    """garth stores its token as a DIRECTORY of json files — sync each file."""
    if not os.path.isdir(local_dir):
        return
    for name in os.listdir(local_dir):
        _put_bytes(bucket, prefix + name, os.path.join(local_dir, name))


def _get_dir(bucket: str, prefix: str, local_dir: str) -> None:
    os.makedirs(local_dir, exist_ok=True)
    try:
        listing = boto3.client("s3").list_objects_v2(Bucket=bucket, Prefix=prefix)
    except Exception:
        return
    for obj in listing.get("Contents", []):
        name = obj["Key"][len(prefix):]
        if name:
            _get_bytes(bucket, obj["Key"], os.path.join(local_dir, name))


def _bootstrap() -> None:
    global _BOOTSTRAPPED
    if _BOOTSTRAPPED:
        return
    _load_secrets()
    os.environ.setdefault("HAKIGAINS_TOKEN_PATH", "/tmp/garth_token")
    os.environ.setdefault("HAKIGAINS_DATA_DIR", "/tmp/hakigains-data")
    os.makedirs(os.environ["HAKIGAINS_DATA_DIR"], exist_ok=True)
    bucket = os.environ.get("HAKIGAINS_STATE_BUCKET")
    if bucket:
        _get_dir(bucket, TOKEN_PREFIX, os.environ["HAKIGAINS_TOKEN_PATH"])
        _get_bytes(bucket, SETTINGS_KEY, _settings_path())
    _BOOTSTRAPPED = True


def _persist_state() -> None:
    bucket = os.environ.get("HAKIGAINS_STATE_BUCKET")
    if not bucket:
        return
    _put_dir(bucket, TOKEN_PREFIX, os.environ["HAKIGAINS_TOKEN_PATH"])
    _put_bytes(bucket, SETTINGS_KEY, _settings_path())


def _client():
    global _CLIENT
    if _CLIENT is None:
        from hakigains.garmin_client import get_client

        _CLIENT = get_client()
    return _CLIENT


def _llm():
    global _LLM
    if _LLM is None:
        from hakigains.llm.factory import get_provider

        _LLM = get_provider()
    return _LLM


def scheduled_briefing(event, context):
    _bootstrap()
    from hakigains.briefing import run_briefing

    text = run_briefing()
    _persist_state()
    return {"ok": True, "briefing": text[:200]}


def telegram_webhook(event, context):
    _bootstrap()
    from hakigains.bot.core import process_update

    update = json.loads(event.get("body") or "{}")
    allowed = int(os.environ["TELEGRAM_CHAT_ID"])
    process_update(update, _client(), _llm(), allowed)
    _persist_state()
    return {"statusCode": 200, "body": "ok"}

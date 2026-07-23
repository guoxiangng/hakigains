"""Local interactive listener — long-polls Telegram and routes each update
through the shared, GATED handler in bot/core.py.

Run it as an always-on process for self-hosting. On Lambda the same routing runs
as a webhook (see deploy/lambda/handler.py).
"""
import os
import time

from dotenv import load_dotenv

from hakigains.bot.core import process_update
from hakigains.deliver.telegram import get_updates
from hakigains.garmin_client import get_client
from hakigains.llm.factory import get_provider

load_dotenv()

ALLOWED_CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])


def main() -> None:
    print(f"hakigains listener starting — gated to chat {ALLOWED_CHAT_ID}")
    client = get_client()
    llm = get_provider()
    offset = None

    while True:
        try:
            updates = get_updates(offset=offset, timeout=30)
        except Exception as e:  # network hiccup — back off and retry
            print("poll error:", e)
            time.sleep(3)
            continue

        for u in updates:
            offset = u["update_id"] + 1
            process_update(u, client, llm, ALLOWED_CHAT_ID)


if __name__ == "__main__":
    main()

"""One-time helper: after creating the bot and messaging it, discover the chat
ID and send a confirmation message.

  1. Put TELEGRAM_BOT_TOKEN in .env
  2. Send any message to your new bot from Telegram
  3. Run this; it prints your chat ID and sends a test message
"""
from dotenv import load_dotenv

from hakigains.deliver.telegram import get_recent_chat_id, send_message

load_dotenv()


def main() -> None:
    chat_id = get_recent_chat_id()
    if chat_id is None:
        print("No messages found. Send any message to your bot first, then re-run.")
        return

    print(f"Your chat ID is: {chat_id}")
    print("Add this to .env as:  TELEGRAM_CHAT_ID=" + str(chat_id))
    send_message("hakigains is wired up. Haki online.", chat_id=str(chat_id))
    print("Sent a confirmation message to your Telegram.")


if __name__ == "__main__":
    main()

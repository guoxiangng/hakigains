"""Local entry point for the interactive listener (always-on process)."""
from dotenv import load_dotenv

from hakigains.bot.listener import main

load_dotenv()

if __name__ == "__main__":
    main()

"""Smoke test: verify the configured LLM provider is reachable and responds."""
from dotenv import load_dotenv

from llm.factory import get_provider

load_dotenv()


def main() -> None:
    llm = get_provider()
    resp = llm.complete(
        system="You are a laconic assistant.",
        user="Reply with exactly this text and nothing else: hakigains online.",
    )
    print("LLM replied:", repr(resp.text))


if __name__ == "__main__":
    main()

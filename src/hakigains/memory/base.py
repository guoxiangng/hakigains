"""Coach memory interface.

Memory is OPTIONAL. With no backend configured, `NullMemory` makes every call a
no-op, so the coach behaves exactly as it did before memory existed and a
self-hoster needs no extra infrastructure.

Three jobs, whatever the backend:
- follow the conversation  -> `turns(day)` / `save_turns(day, ...)`
- keep what the athlete says -> `recall(query)` / `records()` / `forget(record)`
- know its own advice       -> yesterday's briefing is just a saved turn
"""
import re
from dataclasses import dataclass
from typing import Protocol

Turn = tuple[str, str]  # (role, text) — role is "USER" or "ASSISTANT"


@dataclass
class Record:
    id: str
    kind: str   # "fact" | "preference"
    text: str
    noted: str  # ISO date the memory was written — lets the coach judge staleness
    namespace: str = ""

    def expired(self, today: str) -> bool:
        """Time-limited facts end with "until YYYY-MM-DD" (the extraction prompt
        requires it). Past that date the fact is dead."""
        dates = re.findall(r"until (\d{4}-\d{2}-\d{2})", self.text)
        return bool(dates) and dates[-1] < today


class Memory(Protocol):
    enabled: bool

    def save_turns(self, day: str, turns: list[Turn], extract: bool = True) -> None:
        """Append turns to the day's session. `extract=False` keeps them for
        conversational context only (no long-term memories are derived)."""
        ...

    def turns(self, day: str, limit: int = 12) -> list[Turn]:
        """The day's turns, oldest first."""
        ...

    def recall(self, query: str, top_k: int = 8) -> list[Record]:
        """Long-term memories relevant to `query`."""
        ...

    def records(self) -> list[Record]:
        """Everything held in long-term memory, oldest first."""
        ...

    def forget(self, record: Record) -> None:
        ...


class NullMemory:
    enabled = False

    def save_turns(self, day: str, turns: list[Turn], extract: bool = True) -> None:
        return None

    def turns(self, day: str, limit: int = 12) -> list[Turn]:
        return []

    def recall(self, query: str, top_k: int = 8) -> list[Record]:
        return []

    def records(self) -> list[Record]:
        return []

    def forget(self, record: Record) -> None:
        return None

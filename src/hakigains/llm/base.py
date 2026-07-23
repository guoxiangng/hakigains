"""Provider-agnostic LLM interface.

Callers depend only on this. Swapping Azure OpenAI (now) for Bedrock/Claude
(later) is a new implementation behind the same `complete()` signature.
"""
from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class LLMResponse:
    text: str
    raw: Any = None


class LLMProvider(Protocol):
    def complete(self, system: str, user: str) -> LLMResponse:
        """Single-turn completion: a system prompt + a user message -> text."""
        ...

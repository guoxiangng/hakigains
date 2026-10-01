"""Select a memory backend. Unset HAKIGAINS_MEMORY_ID -> no memory (the default)."""
import os

from .base import Memory, NullMemory

_memory: Memory | None = None


def get_memory() -> Memory:
    global _memory
    if _memory is None:
        memory_id = os.environ.get("HAKIGAINS_MEMORY_ID")
        if memory_id:
            from .agentcore import AgentCoreMemory

            _memory = AgentCoreMemory(memory_id)
        else:
            _memory = NullMemory()
    return _memory

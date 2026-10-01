"""Amazon Bedrock AgentCore Memory backend.

Every chat exchange is written as a raw *event*; AgentCore then extracts
long-term *memory records* (dated facts) from those events in the
background, and we search the records before building each prompt.

What gets extracted is decided by a custom extraction prompt on the memory's
strategy (see deploy/sam/template.yaml): only what the athlete said or agreed
to, never wearable numbers. The athlete's turns are stamped with their date so
the extractor can turn "next week" into absolute dates.

Briefings are saved with extraction skipped: they are useful as conversational
context ("why not a run?") but nothing in them was said by the athlete.

A memory failure must never take the coach down, so every call degrades to
"no memory" and logs instead of raising.
"""
import json
import os
import re
from datetime import date, datetime, timezone

import boto3

from .base import Record, Turn

# One strategy only: in testing, the semantic (facts) strategy also captured likes
# and dislikes, and running the preference strategy beside it just duplicated them.
KINDS = {"facts": "fact"}
MAX_EVENT_TEXT = 9000  # conversational payload text limit headroom
_STAMP = re.compile(r"^\[\w+ \d{4}-\d{2}-\d{2}\] ")


def _stamp(day: str, role: str, text: str) -> str:
    if role != "USER":
        return text
    return f"[{date.fromisoformat(day):%A} {day}] {text}"


class AgentCoreMemory:
    enabled = True

    def __init__(self, memory_id: str) -> None:
        self.memory_id = memory_id
        self.actor = os.environ.get("HAKIGAINS_ACTOR_ID", "athlete")
        self.client = boto3.client(
            "bedrock-agentcore", region_name=os.environ.get("HAKIGAINS_MEMORY_REGION")
        )

    def _namespace(self, kind: str) -> str:
        # Must match the NamespaceTemplates on the memory's strategies.
        return f"/athlete/{self.actor}/{kind}/"

    @staticmethod
    def _session(day: str) -> str:
        return f"day-{day}"

    # ---- short-term: raw events -------------------------------------------------
    def save_turns(self, day: str, turns: list[Turn], extract: bool = True) -> None:
        payload = [
            {"conversational": {"role": role,
                                "content": {"text": _stamp(day, role, text)[:MAX_EVENT_TEXT]}}}
            for role, text in turns
            if text
        ]
        if not payload:
            return
        kwargs = {} if extract else {"extractionMode": "SKIP"}
        try:
            self.client.create_event(
                memoryId=self.memory_id,
                actorId=self.actor,
                sessionId=self._session(day),
                eventTimestamp=datetime.now(timezone.utc),
                payload=payload,
                **kwargs,
            )
        except Exception as e:
            print(f"[memory] save failed: {e}")

    def turns(self, day: str, limit: int = 12) -> list[Turn]:
        try:
            resp = self.client.list_events(
                memoryId=self.memory_id,
                actorId=self.actor,
                sessionId=self._session(day),
                includePayloads=True,
                maxResults=100,
            )
        except Exception as e:
            print(f"[memory] list_events failed: {e}")
            return []
        events = sorted(resp.get("events", []), key=lambda ev: ev["eventTimestamp"])
        out: list[Turn] = []
        for ev in events:
            for item in ev.get("payload", []):
                conv = item.get("conversational")
                if conv:
                    out.append((conv["role"], _STAMP.sub("", conv["content"]["text"])))
        return out[-limit:]

    # ---- long-term: extracted records -------------------------------------------
    @staticmethod
    def _text(summary: dict) -> str:
        text = (summary.get("content") or {}).get("text", "").strip()
        # A preference strategy, if one is added, stores JSON ({"preference": ...}).
        if text.startswith("{"):
            try:
                text = json.loads(text).get("preference") or text
            except ValueError:
                pass
        return text

    def _record(self, summary: dict, kind: str) -> Record:
        created = summary.get("createdAt")
        return Record(
            id=summary["memoryRecordId"],
            kind=KINDS[kind],
            text=self._text(summary),
            noted=created.date().isoformat() if created else "",
            namespace=self._namespace(kind),
        )

    def recall(self, query: str, top_k: int = 8) -> list[Record]:
        out: list[Record] = []
        for kind in KINDS:
            try:
                resp = self.client.retrieve_memory_records(
                    memoryId=self.memory_id,
                    namespace=self._namespace(kind),
                    searchCriteria={"searchQuery": query[:1000], "topK": top_k},
                )
            except Exception as e:
                print(f"[memory] retrieve failed ({kind}): {e}")
                continue
            out += [self._record(s, kind) for s in resp.get("memoryRecordSummaries", [])]
        return out

    def records(self) -> list[Record]:
        out: list[Record] = []
        for kind in KINDS:
            try:
                resp = self.client.list_memory_records(
                    memoryId=self.memory_id, namespace=self._namespace(kind), maxResults=100
                )
            except Exception as e:
                print(f"[memory] list failed ({kind}): {e}")
                continue
            out += [self._record(s, kind) for s in resp.get("memoryRecordSummaries", [])]
        return sorted(out, key=lambda r: (r.noted, r.id))

    def forget(self, record: Record) -> None:
        self.client.delete_memory_record(
            memoryId=self.memory_id, memoryRecordId=record.id, namespace=record.namespace
        )

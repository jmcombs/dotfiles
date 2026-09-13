from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RunMetrics:
    turns: int
    tool_calls: int
    tool_errors: int
    tokens: int
    tool_counts: dict[str, int]


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            events.append(obj)
    return events


def metrics_from_events(events: list[dict[str, Any]]) -> RunMetrics:
    turns = sum(1 for e in events if e.get("type") == "turn_start")
    starts = [e for e in events if e.get("type") == "tool_execution_start"]
    ends = [e for e in events if e.get("type") == "tool_execution_end"]
    counts: dict[str, int] = {}
    for event in starts:
        name = str(event.get("toolName") or "?")
        counts[name] = counts.get(name, 0) + 1
    tokens = 0
    for event in events:
        usage = event.get("usage")
        if isinstance(usage, dict):
            tokens = max(tokens, int(usage.get("totalTokens") or 0))
        message = event.get("message")
        if isinstance(message, dict):
            usage = message.get("usage")
            if isinstance(usage, dict):
                tokens = max(tokens, int(usage.get("totalTokens") or 0))
    return RunMetrics(
        turns=turns,
        tool_calls=len(starts),
        tool_errors=sum(1 for e in ends if e.get("isError")),
        tokens=tokens,
        tool_counts=counts,
    )

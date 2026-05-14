"""In-memory feed for live UI (SSE). Trade notes + ingest events; not durable across restarts."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from typing import Any

_MAX = 200
_events: deque[dict[str, Any]] = deque(maxlen=_MAX)


def push_event(kind: str, payload: dict[str, Any] | None = None) -> None:
    row: dict[str, Any] = {
        "t": datetime.now(timezone.utc).isoformat(),
        "kind": kind,
    }
    if payload:
        row.update(payload)
    _events.append(row)


def recent_events(n: int = 30) -> list[dict[str, Any]]:
    return list(_events)[-n:]

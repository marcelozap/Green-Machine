"""Server-Sent Events live feed + quick trade notes."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool

from app.live_bus import push_event, recent_events
from app.schemas import LiveNoteBody

router = APIRouter(tags=["live"])

_REPO = Path(__file__).resolve().parents[3]


def _latest_bar() -> dict:
    db = _REPO / "data" / "greenmachine.db"
    if not db.exists():
        return {"spy": None, "vix": None, "as_of": None}
    import sqlite3

    con = sqlite3.connect(db)
    try:
        row = con.execute(
            "SELECT trade_date, close, vix_close FROM spy_daily ORDER BY trade_date DESC LIMIT 1",
        ).fetchone()
    finally:
        con.close()
    if not row:
        return {"spy": None, "vix": None, "as_of": None}
    return {"spy": row[1], "vix": row[2], "as_of": row[0]}


@router.get("/live/stream")
async def live_stream() -> StreamingResponse:
    async def gen():
        while True:
            snap = await run_in_threadpool(_latest_bar)
            payload = {"snapshot": snap, "events": recent_events(40)}
            yield f"data: {json.dumps(payload, default=str)}\n\n"
            await asyncio.sleep(2.5)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/live/note")
async def live_note(body: LiveNoteBody) -> dict[str, str]:
    push_event("note", {"text": body.text})
    return {"ok": "true"}


@router.get("/live/recent")
async def live_recent() -> dict:
    """JSON snapshot for clients that do not use SSE."""
    snap = await run_in_threadpool(_latest_bar)
    return {"snapshot": snap, "events": recent_events(40)}

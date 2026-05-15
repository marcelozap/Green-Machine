"""Persistent desk log — structured trade entries + notes."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Query
from starlette.concurrency import run_in_threadpool

from app.schemas import DeskLogItemOut, DeskNoteBody, DeskTradeBody

router = APIRouter(prefix="/desk", tags=["desk"])

_REPO = Path(__file__).resolve().parents[3]
_DB = _REPO / "data" / "greenmachine.db"


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(_DB)
    con.row_factory = sqlite3.Row
    return con


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    raw_tags = d.get("tags") or "[]"
    try:
        d["tags"] = json.loads(raw_tags)
    except Exception:
        d["tags"] = []
    return d


def _do_insert_trade(symbol: str, description: str, tags: list[str], session_date: str | None) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    sd = session_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sym = symbol.upper()
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO desk_log (ts, kind, symbol, description, tags, session_date) VALUES (?,?,?,?,?,?)",
            (ts, "trade", sym, description, json.dumps(tags), sd),
        )
        row_id = cur.lastrowid
    return {"id": row_id, "ts": ts, "kind": "trade", "symbol": sym,
            "description": description, "tags": tags, "session_date": sd, "text": None}


def _do_insert_note(text: str) -> dict:
    ts = datetime.now(timezone.utc).isoformat()
    sd = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _conn() as con:
        cur = con.execute(
            "INSERT INTO desk_log (ts, kind, text, session_date) VALUES (?,?,?,?)",
            (ts, "note", text, sd),
        )
        row_id = cur.lastrowid
    return {"id": row_id, "ts": ts, "kind": "note", "symbol": None,
            "description": None, "tags": [], "session_date": sd, "text": text}


def _do_recent(limit: int) -> list[dict]:
    if not _DB.exists():
        return []
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM desk_log ORDER BY ts DESC LIMIT ?", (limit,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _do_day(session_date: str) -> list[dict]:
    if not _DB.exists():
        return []
    with _conn() as con:
        rows = con.execute(
            "SELECT * FROM desk_log WHERE session_date=? ORDER BY ts", (session_date,)
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def _do_context_preview(limit: int = 20) -> dict:
    items = _do_recent(limit)
    lines: list[str] = []
    for item in reversed(items):
        ts = item.get("ts", "")[:16].replace("T", " ")
        if item["kind"] == "trade":
            tag_str = " ".join(f"[{t}]" for t in item.get("tags", []))
            sym = item.get("symbol") or ""
            desc = item.get("description") or ""
            lines.append(f"{ts}  TRADE  {sym}  {desc}  {tag_str}".rstrip())
        else:
            lines.append(f"{ts}  NOTE  {item.get('text') or ''}")
    return {"text": "\n".join(lines), "count": len(items)}


@router.post("/trade", response_model=DeskLogItemOut, status_code=201)
async def post_trade(body: DeskTradeBody) -> dict:
    return await run_in_threadpool(
        _do_insert_trade, body.symbol, body.description, body.tags, body.session_date
    )


@router.post("/note", response_model=DeskLogItemOut, status_code=201)
async def post_note(body: DeskNoteBody) -> dict:
    return await run_in_threadpool(_do_insert_note, body.text)


@router.get("/timeline", response_model=list[DeskLogItemOut])
async def get_timeline(limit: int = Query(default=40, ge=1, le=200)) -> list:
    return await run_in_threadpool(_do_recent, limit)


@router.get("/day/{session_date}", response_model=list[DeskLogItemOut])
async def get_day(session_date: str) -> list:
    return await run_in_threadpool(_do_day, session_date)


@router.get("/context-preview")
async def get_context_preview() -> dict:
    return await run_in_threadpool(_do_context_preview)

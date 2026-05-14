"""End-of-day CSV upload → background ingest (historian scripts)."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile

from app.live_bus import push_event

router = APIRouter(tags=["ingest"])
log = logging.getLogger(__name__)

_REPO = Path(__file__).resolve().parents[3]
_UPLOAD_DIR = _REPO / "data" / "uploads"
_MAX_BYTES = 80 * 1024 * 1024


def _run_ingest(kind: str, csv_path: str) -> None:
    script = (
        _REPO / "historian" / "scripts" / "import_tos_daily_csv.py"
        if kind == "tos_daily"
        else _REPO / "historian" / "scripts" / "ingest_options_sqlite.py"
    )
    try:
        r = subprocess.run(
            [sys.executable, str(script), csv_path],
            cwd=str(_REPO),
            check=True,
            capture_output=True,
            text=True,
            timeout=3600,
        )
        push_event(
            "ingest_done",
            {"ingest_kind": kind, "path": csv_path, "log": (r.stderr or "")[-2000:]},
        )
    except subprocess.CalledProcessError as e:
        log.exception("ingest failed")
        push_event(
            "ingest_error",
            {
                "ingest_kind": kind,
                "path": csv_path,
                "code": e.returncode,
                "stderr": (e.stderr or "")[-4000:],
                "stdout": (e.stdout or "")[-2000:],
            },
        )
    except Exception as e:  # noqa: BLE001
        log.exception("ingest failed")
        push_event("ingest_error", {"ingest_kind": kind, "path": csv_path, "error": str(e)})


@router.post("/ingest/eod")
async def ingest_eod(
    background_tasks: BackgroundTasks,
    kind: Literal["tos_daily", "options"] = Query(
        ...,
        description="tos_daily = Thinkorswim-style OHLCV CSV; options = normalized chain CSV",
    ),
    file: UploadFile = File(...),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file")
    raw = await file.read()
    if len(raw) > _MAX_BYTES:
        raise HTTPException(413, "File too large")
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in file.filename if c.isalnum() or c in "._-")[:120] or "upload.csv"
    dest = _UPLOAD_DIR / f"eod_{safe}"
    dest.write_bytes(raw)
    push_event("ingest_queued", {"ingest_kind": kind, "file": file.filename, "bytes": len(raw)})
    background_tasks.add_task(_run_ingest, kind, str(dest))
    return {"ok": True, "saved": str(dest), "kind": kind}

"""Parse realized_analysis.json rollup → session budget data for the cockpit rail."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _resolve_path(configured: str) -> Path:
    p = Path(configured)
    if p.is_absolute():
        return p
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / p


def load_session_budget(configured_path: str, daily_budget_usd: float) -> dict[str, Any]:
    path = _resolve_path(configured_path)
    if not path.exists():
        return {"available": False, "path_tried": str(path)}

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"available": False, "error": str(exc)}

    # Last session from the equity curve tail
    tail: list[dict] = data.get("daily_equity_curve_tail", [])
    if not tail:
        return {"available": False, "error": "daily_equity_curve_tail empty"}

    last = tail[-1]
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    last_date: str = last.get("session_date", "")
    last_pnl: float = float(last.get("net_pnl", 0))
    last_lots: int = int(last.get("lots", 0))
    cum_pnl: float = float(last.get("cum_pnl", 0))
    is_today = last_date == today_str

    # Headroom vs daily budget (only meaningful when last session is today)
    headroom_usd: float | None = None
    session_over_budget = False
    if is_today and last_pnl < 0:
        headroom_usd = daily_budget_usd - abs(last_pnl)
        session_over_budget = headroom_usd < 0

    # 0DTE concentration
    dte_buckets: list[dict] = data.get("by_dte_bucket", [])
    total_lots: int = sum(int(b.get("lots", 0)) for b in dte_buckets)
    zero_dte_row = next((b for b in dte_buckets if b.get("dte_bucket") == "0DTE"), None)
    zero_dte_lots = int(zero_dte_row.get("lots", 0)) if zero_dte_row else 0
    zero_dte_pnl = float(zero_dte_row.get("net_pnl", 0)) if zero_dte_row else 0.0
    zero_dte_pct = zero_dte_lots / total_lots if total_lots > 0 else 0.0

    # Recent 5 sessions for sparkline / tooltip
    recent = tail[-5:]

    return {
        "available": True,
        "last_session": {
            "date": last_date,
            "pnl": last_pnl,
            "lots": last_lots,
            "cum_pnl": cum_pnl,
            "is_today": is_today,
        },
        "total_realized_pnl": cum_pnl,
        "daily_budget_usd": daily_budget_usd,
        "headroom_usd": headroom_usd,
        "session_over_budget": session_over_budget,
        "zero_dte_pct": zero_dte_pct,
        "zero_dte_pnl": zero_dte_pnl,
        "recent_sessions": recent,
    }

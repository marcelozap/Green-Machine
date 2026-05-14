"""
Import a daily (or intraday-aggregated-to-daily) OHLCV CSV from Thinkorswim / Schwab
exports into local SQLite `spy_daily` for Green Machine backtests.

Thinkorswim does not expose a simple public "TOS API" for retail chain history.
Typical workflows:
  - Chart or grid export to CSV, then this script; or
  - Charles Schwab Market Data / Trader API (OAuth) for automation — not included here.

This script only needs the Python deps from requirements.txt (pandas).
"""

from __future__ import annotations

import argparse
import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "greenmachine.db"

# Normalized key -> possible header names (lowercase, spaces stripped for match)
_ALIASES: dict[str, tuple[str, ...]] = {
    "date": (
        "date",
        "time",
        "datetime",
        "dt",
        "bardate",
        "chart date",
        "last date",
    ),
    "open": ("open", "o", "first"),
    "high": ("high", "h", "max"),
    "low": ("low", "l", "min"),
    "close": ("close", "last", "c", "adj close", "adjclose", "underlying"),
    "volume": ("volume", "vol", "shares", "totalvolume"),
    "vix": ("vix", "vixclose", "vxn", "impvol", "impliedvol", "iv"),
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _pick_column(df: pd.DataFrame, aliases: tuple[str, ...]) -> str | None:
    norm_map = {_norm(c): c for c in df.columns}
    for a in aliases:
        key = _norm(a)
        if key in norm_map:
            return norm_map[key]
    return None


def _resolve_columns(df: pd.DataFrame, overrides: dict[str, str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, aliases in _ALIASES.items():
        if key in overrides and overrides[key]:
            c = overrides[key]
            if c not in df.columns:
                raise SystemExit(f"Column {c!r} not in CSV for --col-{key}")
            out[key] = c
        else:
            picked = _pick_column(df, aliases)
            if picked:
                out[key] = picked
    if "date" not in out:
        raise SystemExit(
            "Could not detect a date/time column. Set --col-date explicitly "
            f"(columns found: {list(df.columns)!r})",
        )
    if "close" not in out:
        raise SystemExit(
            "Could not detect a close/last column. Set --col-close explicitly.",
        )
    return out


def main() -> None:
    p = argparse.ArgumentParser(description="Import Thinkorswim-style daily CSV into SQLite spy_daily")
    p.add_argument("csv", help="Path to CSV exported from TOS / Schwab / similar")
    p.add_argument("--db", type=Path, default=DEFAULT_DB, help="SQLite database path")
    p.add_argument("--replace-symbol", default="SPY", help="Tag rows as this symbol (informational only)")
    p.add_argument("--col-date", dest="col_date", default="", help="Exact CSV header for date/time")
    p.add_argument("--col-open", dest="col_open", default="")
    p.add_argument("--col-high", dest="col_high", default="")
    p.add_argument("--col-low", dest="col_low", default="")
    p.add_argument("--col-close", dest="col_close", default="")
    p.add_argument("--col-volume", dest="col_volume", default="")
    p.add_argument("--col-vix", dest="col_vix", default="")
    args = p.parse_args()

    df = pd.read_csv(args.csv)
    df.columns = [str(c).strip() for c in df.columns]
    ov = {
        "date": args.col_date,
        "open": args.col_open,
        "high": args.col_high,
        "low": args.col_low,
        "close": args.col_close,
        "volume": args.col_volume,
        "vix": args.col_vix,
    }
    cm = _resolve_columns(df, ov)

    tcol = cm["date"]
    parsed = pd.to_datetime(df[tcol], utc=False, errors="coerce")
    if parsed.isna().all():
        raise SystemExit(f"Could not parse dates from column {tcol!r}")
    trade_date = parsed.dt.date.astype(str)

    close = pd.to_numeric(df[cm["close"]], errors="coerce")
    if cm.get("open") and cm.get("high") and cm.get("low"):
        o = pd.to_numeric(df[cm["open"]], errors="coerce")
        h = pd.to_numeric(df[cm["high"]], errors="coerce")
        l = pd.to_numeric(df[cm["low"]], errors="coerce")
    else:
        o = h = l = close
    vol = pd.to_numeric(df[cm["volume"]], errors="coerce") if cm.get("volume") else pd.Series([None] * len(df))
    vix = pd.to_numeric(df[cm["vix"]], errors="coerce") if cm.get("vix") else pd.Series([None] * len(df))

    out = pd.DataFrame(
        {
            "trade_date": trade_date,
            "open": o,
            "high": h,
            "low": l,
            "close": close,
            "volume": vol,
            "vix_close": vix,
        }
    )
    out = out.dropna(subset=["trade_date", "close"])
    out["rsi_14"] = None
    out["spy_return"] = out["close"].pct_change()
    out.loc[out.index[0], "spy_return"] = 0.0
    out["put_proxy_return"] = (-out["spy_return"].clip(lower=-0.2, upper=0.2) * 1.15).astype(float)

    args.db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(args.db)
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS spy_daily (
            trade_date TEXT PRIMARY KEY,
            open REAL, high REAL, low REAL, close REAL NOT NULL,
            volume INTEGER, vix_close REAL, rsi_14 REAL,
            spy_return REAL, put_proxy_return REAL
        );
        """
    )
    rows = []
    for _, row in out.iterrows():
        c = float(row["close"])
        o = float(row["open"]) if pd.notna(row["open"]) else c
        h = float(row["high"]) if pd.notna(row["high"]) else c
        l = float(row["low"]) if pd.notna(row["low"]) else c
        vol = int(row["volume"]) if pd.notna(row["volume"]) else None
        vx = float(row["vix_close"]) if pd.notna(row["vix_close"]) else None
        rows.append(
            (
                str(row["trade_date"]),
                o,
                h,
                l,
                c,
                vol,
                vx,
                None,
                float(row["spy_return"]),
                float(row["put_proxy_return"]),
            )
        )
    cur.executemany(
        """INSERT OR REPLACE INTO spy_daily
        (trade_date, open, high, low, close, volume, vix_close, rsi_14, spy_return, put_proxy_return)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        rows,
    )
    con.commit()
    con.close()
    print(f"Imported {len(rows)} rows into {args.db} (symbol context: {args.replace_symbol})")


if __name__ == "__main__":
    main()

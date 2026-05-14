"""
Bulk load normalized options CSV into local SQLite `spy_options_history`.

Same column contract as ingest_options.py (Postgres COPY path).
Chunked pandas read + batched executemany INSERT.

Expected CSV columns (header required):
  ts,underlying_price,strike,expiry,option_type,delta,gamma,theta,vega,iv,bid,ask,volume,open_interest
"""

from __future__ import annotations

import argparse
import math
import sqlite3
import sys
from pathlib import Path

import pandas as pd

_REPO = Path(__file__).resolve().parents[2]
_DEFAULT_DB = _REPO / "data" / "greenmachine.db"

COPY_COLUMNS = [
    "ts",
    "underlying_price",
    "strike",
    "expiry",
    "option_type",
    "delta",
    "gamma",
    "theta",
    "vega",
    "iv",
    "bid",
    "ask",
    "volume",
    "open_interest",
]

DDL = """
CREATE TABLE IF NOT EXISTS spy_options_history (
    ts TEXT NOT NULL,
    underlying_price REAL NOT NULL,
    strike REAL NOT NULL,
    expiry TEXT NOT NULL,
    option_type TEXT NOT NULL,
    delta REAL,
    gamma REAL,
    theta REAL,
    vega REAL,
    iv REAL,
    bid REAL,
    ask REAL,
    volume INTEGER,
    open_interest INTEGER
);
CREATE INDEX IF NOT EXISTS idx_opts_ts ON spy_options_history (ts);
"""


def _none_nan(v):
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except TypeError:
        pass
    if isinstance(v, float) and (math.isinf(v)):
        return None
    return v


def ingest_csv(path: Path, db: Path, chunksize: int, batch_rows: int) -> int:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.executescript(DDL)
    cur = con.cursor()
    ph = ",".join(["?"] * len(COPY_COLUMNS))
    sql = f"INSERT INTO spy_options_history ({','.join(COPY_COLUMNS)}) VALUES ({ph})"
    total = 0
    batch: list[tuple] = []

    def flush() -> None:
        nonlocal batch, total
        if not batch:
            return
        cur.executemany(sql, batch)
        con.commit()
        total += len(batch)
        print(f"loaded {total:,} rows", file=sys.stderr)
        batch = []

    for chunk in pd.read_csv(path, chunksize=chunksize):
        miss = [c for c in COPY_COLUMNS if c not in chunk.columns]
        if miss:
            raise SystemExit(f"CSV missing columns: {miss}")
        c = chunk[COPY_COLUMNS].copy()
        c["option_type"] = c["option_type"].astype(str).str.upper().str.strip().str[0:1]
        c["ts"] = pd.to_datetime(c["ts"], utc=True, errors="coerce").map(
            lambda x: x.isoformat() if pd.notna(x) else None,
        )
        c["expiry"] = pd.to_datetime(c["expiry"], errors="coerce").dt.strftime("%Y-%m-%d")
        c["volume"] = pd.to_numeric(c["volume"], errors="coerce").astype("Int64")
        for col in ("underlying_price", "strike", "delta", "gamma", "theta", "vega", "iv", "bid", "ask"):
            c[col] = pd.to_numeric(c[col], errors="coerce")
        c["open_interest"] = pd.to_numeric(c["open_interest"], errors="coerce").astype("Int64")

        for row in c.itertuples(index=False, name=None):
            batch.append(tuple(_none_nan(x) for x in row))
            if len(batch) >= batch_rows:
                flush()
    flush()
    con.close()
    return total


def main() -> None:
    p = argparse.ArgumentParser(description="GREEN MACHINE — options chain → SQLite")
    p.add_argument("csv", type=Path, help="Normalized options CSV")
    p.add_argument("--db", type=Path, default=_DEFAULT_DB, help="SQLite database path")
    p.add_argument("--chunksize", type=int, default=100_000)
    p.add_argument("--batch", type=int, default=10_000, help="Rows per INSERT batch")
    args = p.parse_args()
    n = ingest_csv(args.csv, args.db, args.chunksize, args.batch)
    print(f"done: {n:,} rows → {args.db}")


if __name__ == "__main__":
    main()

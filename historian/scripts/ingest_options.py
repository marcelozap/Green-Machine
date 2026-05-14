"""
Bulk load SPY options history into TimescaleDB.

Designed for throughput:
  - pandas read_csv in chunks (constant memory)
  - psycopg COPY FROM STDIN WITH (FORMAT csv) — fastest path into Postgres

Expected CSV columns (header required):
  ts,underlying_price,strike,expiry,option_type,delta,gamma,theta,vega,iv,bid,ask,volume,open_interest

ts: ISO-8601 or 'YYYY-MM-DD HH:MM:SS' (UTC recommended)
expiry: YYYY-MM-DD
option_type: C or P
"""

from __future__ import annotations

import argparse
import os
import sys
from io import StringIO

import pandas as pd
import psycopg
from psycopg import sql

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


def _dsn() -> str:
    return os.environ.get(
        "GM_DATABASE_DSN",
        "postgresql://green:green@localhost:5432/greenmachine",
    )


def ingest_csv(path: str, chunksize: int = 200_000) -> int:
    total = 0
    copy_sql = sql.SQL("COPY spy_options_history ({cols}) FROM STDIN WITH (FORMAT csv, NULL '')").format(
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in COPY_COLUMNS)
    )
    with psycopg.connect(_dsn()) as conn:
        conn.execute("SET synchronous_commit TO OFF")
        with conn.cursor() as cur:
            for chunk in pd.read_csv(path, chunksize=chunksize):
                missing = [c for c in COPY_COLUMNS if c not in chunk.columns]
                if missing:
                    raise SystemExit(f"CSV missing columns: {missing}")
                buf = StringIO()
                chunk[COPY_COLUMNS].to_csv(buf, index=False, header=False, na_rep="")
                buf.seek(0)
                with cur.copy(copy_sql) as copy:
                    while data := buf.read(8 * 1024 * 1024):
                        copy.write(data)
                total += len(chunk)
                print(f"loaded {total:,} rows", file=sys.stderr)
    return total


def main() -> None:
    p = argparse.ArgumentParser(description="GREEN MACHINE — Vault bulk ingest")
    p.add_argument("csv", help="Path to normalized options CSV")
    p.add_argument("--chunksize", type=int, default=200_000)
    args = p.parse_args()
    n = ingest_csv(args.csv, chunksize=args.chunksize)
    print(f"done: {n:,} rows")


if __name__ == "__main__":
    main()

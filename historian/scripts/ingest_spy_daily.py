"""
Bulk load `spy_daily` rows (OHLCV + optional vix / returns) for the Vault.

CSV columns (header required):
  trade_date,open,high,low,close,volume,vix_close,rsi_14,spy_return,put_proxy_return
"""

from __future__ import annotations

import argparse
import os
import sys
from io import StringIO

import pandas as pd
import psycopg
from psycopg import sql

COLS = [
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "vix_close",
    "rsi_14",
    "spy_return",
    "put_proxy_return",
]


def _dsn() -> str:
    return os.environ.get(
        "GM_DATABASE_DSN",
        "postgresql://green:green@localhost:5432/greenmachine",
    )


def ingest(path: str, chunksize: int = 50_000) -> int:
    total = 0
    copy_sql = sql.SQL("COPY spy_daily ({cols}) FROM STDIN WITH (FORMAT csv, NULL '')").format(
        cols=sql.SQL(", ").join(sql.Identifier(c) for c in COLS)
    )
    with psycopg.connect(_dsn()) as conn:
        conn.execute("SET synchronous_commit TO OFF")
        with conn.cursor() as cur:
            for chunk in pd.read_csv(path, chunksize=chunksize):
                miss = [c for c in COLS if c not in chunk.columns]
                if miss:
                    raise SystemExit(f"CSV missing columns: {miss}")
                buf = StringIO()
                chunk[COLS].to_csv(buf, index=False, header=False, na_rep="")
                buf.seek(0)
                with cur.copy(copy_sql) as copy:
                    while data := buf.read(8 * 1024 * 1024):
                        copy.write(data)
                total += len(chunk)
                print(f"loaded {total:,} rows", file=sys.stderr)
    return total


def main() -> None:
    p = argparse.ArgumentParser(description="GREEN MACHINE — spy_daily ingest")
    p.add_argument("csv")
    p.add_argument("--chunksize", type=int, default=50_000)
    args = p.parse_args()
    n = ingest(args.csv, chunksize=args.chunksize)
    print(f"done: {n:,} rows")


if __name__ == "__main__":
    main()

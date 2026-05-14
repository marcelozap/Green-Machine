"""
Insert demo `spy_daily` + `market_states` into local SQLite so the cockpit has
DB-backed series without Docker or external market APIs.

Synthetic random-walk data for UI/engine testing only — not for live trading.
Replace with your vendor CSV when you trust that data for decisions.
"""

from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = _REPO_ROOT / "data" / "greenmachine.db"


def _business_days(end: date, n: int) -> list[date]:
    out: list[date] = []
    d = end
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d -= timedelta(days=1)
    return list(reversed(out))


def main() -> None:
    p = argparse.ArgumentParser(description="Seed local SQLite with demo market series")
    p.add_argument("--days", type=int, default=900, help="Business days of history")
    p.add_argument("--force", action="store_true", help="Clear spy_daily / market_states first")
    args = p.parse_args()

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    rnd = random.Random(7)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS spy_daily (
            trade_date TEXT PRIMARY KEY,
            open REAL, high REAL, low REAL, close REAL NOT NULL,
            volume INTEGER, vix_close REAL, rsi_14 REAL,
            spy_return REAL, put_proxy_return REAL
        );
        CREATE TABLE IF NOT EXISTS market_states (
            trade_date TEXT PRIMARY KEY,
            vix_close REAL, spy_close REAL, rsi_14 REAL,
            macro_news_digest TEXT, trend_label TEXT, embedding TEXT
        );
        """
    )
    if args.force:
        cur.execute("DELETE FROM spy_daily")
        cur.execute("DELETE FROM market_states")

    days = _business_days(date.today(), args.days)
    close = 400.0
    vix = 16.0
    rsi = 50.0
    daily_rows: list[tuple] = []
    prev_c = close

    for d in days:
        shock = rnd.gauss(0, 0.008)
        close = max(50.0, close * (1.0 + shock))
        spy_ret = (close - prev_c) / prev_c if prev_c else 0.0
        prev_c = close
        vix = max(10.0, min(55.0, vix + rnd.gauss(0, 0.35)))
        rsi = max(5.0, min(95.0, rsi + rnd.gauss(0, 2.5)))
        o = close * (1.0 + rnd.gauss(0, 0.001))
        h = max(o, close) * (1.0 + abs(rnd.gauss(0, 0.002)))
        l = min(o, close) * (1.0 - abs(rnd.gauss(0, 0.002)))
        put_proxy = -spy_ret * rnd.uniform(0.9, 1.4) - abs(rnd.gauss(0, 0.002))
        vol = rnd.randint(40_000_000, 120_000_000)
        daily_rows.append(
            (
                d.isoformat(),
                float(o),
                float(h),
                float(l),
                float(close),
                vol,
                float(vix),
                float(rsi),
                float(spy_ret),
                float(put_proxy),
            )
        )

    cur.executemany(
        """INSERT OR REPLACE INTO spy_daily
        (trade_date, open, high, low, close, volume, vix_close, rsi_14, spy_return, put_proxy_return)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        daily_rows,
    )

    step = max(1, len(daily_rows) // 200)
    ms = [
        (
            daily_rows[i][0],
            daily_rows[i][6],
            daily_rows[i][4],
            daily_rows[i][7],
            "",
            "demo",
        )
        for i in range(0, len(daily_rows), step)
    ]
    cur.executemany(
        """INSERT OR REPLACE INTO market_states
        (trade_date, vix_close, spy_close, rsi_14, macro_news_digest, trend_label, embedding)
        VALUES (?,?,?,?,?,?,NULL)""",
        ms,
    )
    con.commit()
    con.close()
    print(f"Seeded {len(daily_rows)} spy_daily rows and {len(ms)} market_states into {DB_PATH}")


if __name__ == "__main__":
    main()

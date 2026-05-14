"""Create local tables when using SQLite (no Docker / no Postgres required)."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
_DATA_DIR = _BACKEND_ROOT / "data"

SQLITE_DDL = [
    """
    CREATE TABLE IF NOT EXISTS spy_daily (
        trade_date TEXT PRIMARY KEY,
        open REAL,
        high REAL,
        low REAL,
        close REAL NOT NULL,
        volume INTEGER,
        vix_close REAL,
        rsi_14 REAL,
        spy_return REAL,
        put_proxy_return REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS market_states (
        trade_date TEXT PRIMARY KEY,
        vix_close REAL,
        spy_close REAL,
        rsi_14 REAL,
        macro_news_digest TEXT,
        trend_label TEXT,
        embedding TEXT
    )
    """,
    """
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
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_spy_daily_td ON spy_daily (trade_date)",
    "CREATE INDEX IF NOT EXISTS idx_opts_ts ON spy_options_history (ts)",
]


def _is_sqlite(url: str) -> bool:
    return url.strip().lower().startswith("sqlite")


async def init_db_schema(engine: AsyncEngine) -> None:
    url = str(engine.url)
    if not _is_sqlite(url):
        return
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        for stmt in SQLITE_DDL:
            await conn.execute(text(stmt))

"""Load aggregated series from the Vault (PostgreSQL / Timescale)."""

from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def load_spy_daily(
    session: AsyncSession,
    *,
    start: date | None = None,
    end: date | None = None,
) -> pd.DataFrame:
    q = """
        SELECT trade_date AS date,
               close AS underlying_close,
               spy_return,
               put_proxy_return,
               vix_close AS vix
        FROM spy_daily
        WHERE (:start IS NULL OR trade_date >= :start)
          AND (:end IS NULL OR trade_date <= :end)
        ORDER BY trade_date
    """
    rows = await session.execute(
        text(q),
        {"start": start, "end": end},
    )
    cols = rows.keys()
    data = rows.fetchall()
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data, columns=cols)

"""Regime similarity using `market_states` (VIX / RSI geometry)."""

from __future__ import annotations

import re

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas import SimilarDay


def parse_vix_hint(prompt: str) -> float:
    m = re.search(r"vix\s*[:@]?\s*(\d{1,2}(?:\.\d+)?)", prompt, re.I)
    if m:
        return float(m.group(1))
    m2 = re.search(r"\b(\d{2})\b", prompt)
    if m2:
        v = float(m2.group(1))
        if 8 <= v <= 90:
            return v
    return 20.0


async def similar_days_from_db(
    session: AsyncSession,
    *,
    vix_anchor: float,
    limit: int = 8,
) -> list[SimilarDay]:
    q = text(
        """
        SELECT trade_date,
               vix_close,
               spy_close,
               rsi_14,
               trend_label,
               (
                   abs(COALESCE(vix_close, :v) - :v) * 3.0
                   + abs(COALESCE(rsi_14, 50.0) - 50.0) * 0.08
               ) AS dist
        FROM market_states
        WHERE vix_close IS NOT NULL
        ORDER BY dist ASC NULLS LAST
        LIMIT :lim
        """
    )
    try:
        res = await session.execute(q, {"v": vix_anchor, "lim": limit})
    except Exception:
        return []
    out: list[SimilarDay] = []
    for row in res.mappings():
        out.append(
            SimilarDay(
                trade_date=row["trade_date"],
                vix_close=row["vix_close"],
                spy_close=row["spy_close"],
                rsi_14=row["rsi_14"],
                trend_label=row["trend_label"],
                distance=float(row["dist"]),
            )
        )
    return out

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.schemas import Heartbeat, MarketSnapshot

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Heartbeat)
async def health() -> Heartbeat:
    return Heartbeat(status="ok", ts=datetime.now(timezone.utc))


@router.get("/health/ready", response_model=Heartbeat)
async def health_ready(session: AsyncSession = Depends(get_session)) -> Heartbeat:
    try:
        await session.execute(text("SELECT 1"))
        return Heartbeat(status="ok", ts=datetime.now(timezone.utc))
    except Exception:
        return Heartbeat(status="degraded", ts=datetime.now(timezone.utc))


@router.get("/market/snapshot", response_model=MarketSnapshot)
async def market_snapshot(session: AsyncSession = Depends(get_session)) -> MarketSnapshot:
    res = await session.execute(
        text("SELECT trade_date, close, vix_close FROM spy_daily ORDER BY trade_date DESC LIMIT 1"),
    )
    row = res.first()
    if not row or row[1] is None:
        return MarketSnapshot(spy=None, vix=None, as_of=str(row[0]) if row and row[0] is not None else None)
    td, close, vx = row[0], row[1], row[2]
    return MarketSnapshot(
        spy=float(close),
        vix=float(vx) if vx is not None else None,
        as_of=str(td) if td is not None else None,
    )

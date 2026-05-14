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
async def market_snapshot() -> MarketSnapshot:
    return MarketSnapshot(spy=582.12, vix=18.4)

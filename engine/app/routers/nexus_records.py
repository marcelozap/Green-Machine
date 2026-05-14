"""unified_nexus CRUD + State-Switcher (Nexus inside Green Machine)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.nexus.models import NexusDomain, UnifiedNexus
from app.nexus.nexus_logic import STATUS_NOMINAL, apply_switcher_to_payload, evaluate_market_boredom
from app.nexus.schemas import (
    NexusDomainEnum,
    StateSwitcherResponse,
    UnifiedNexusCreate,
    UnifiedNexusPatch,
    UnifiedNexusRead,
)

router = APIRouter(prefix="/nexus", tags=["nexus"])


def _to_domain(d: NexusDomainEnum) -> NexusDomain:
    return NexusDomain(d.value)


@router.post("/records", response_model=UnifiedNexusRead)
async def create_record(
    body: UnifiedNexusCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UnifiedNexus:
    domain = _to_domain(body.domain)
    mstatus, pivots = None, None
    if domain == NexusDomain.trading_signals:
        mstatus, pivots = apply_switcher_to_payload(
            body.volatility_score,
            body.signal_6_6,
            body.payload,
        )
    row = UnifiedNexus(
        domain=domain,
        title=body.title,
        payload=body.payload,
        volatility_score=body.volatility_score,
        signal_6_6=body.signal_6_6,
        market_boredom_status=mstatus,
        pivot_suggestions=pivots,
        notes=body.notes,
    )
    session.add(row)
    await session.commit()
    await session.refresh(row)
    return row


@router.get("/records", response_model=list[UnifiedNexusRead])
async def list_records(
    session: Annotated[AsyncSession, Depends(get_session)],
    domain: NexusDomainEnum | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> list[UnifiedNexus]:
    q = select(UnifiedNexus)
    if domain is not None:
        q = q.where(UnifiedNexus.domain == _to_domain(domain))
    q = q.order_by(UnifiedNexus.updated_at.desc()).limit(limit)
    res = await session.execute(q)
    return list(res.scalars().all())


@router.get("/records/{record_id}", response_model=UnifiedNexusRead)
async def get_record(
    record_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UnifiedNexus:
    row = await session.get(UnifiedNexus, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    return row


@router.patch("/records/{record_id}", response_model=UnifiedNexusRead)
async def patch_record(
    record_id: UUID,
    body: UnifiedNexusPatch,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UnifiedNexus:
    row = await session.get(UnifiedNexus, record_id)
    if not row:
        raise HTTPException(status_code=404, detail="Record not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(row, k, v)
    if row.domain == NexusDomain.trading_signals:
        mstatus, pivots = apply_switcher_to_payload(
            row.volatility_score,
            row.signal_6_6,
            row.payload,
        )
        row.market_boredom_status = mstatus
        row.pivot_suggestions = pivots
    await session.commit()
    await session.refresh(row)
    return row


@router.get("/state-switcher/evaluate", response_model=StateSwitcherResponse)
async def evaluate_state_switcher(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> StateSwitcherResponse:
    res = await session.execute(
        select(UnifiedNexus)
        .where(UnifiedNexus.domain == NexusDomain.trading_signals)
        .order_by(UnifiedNexus.updated_at.desc())
        .limit(1),
    )
    row = res.scalar_one_or_none()
    if not row:
        return StateSwitcherResponse(
            status=STATUS_NOMINAL,
            volatility_score=None,
            has_signal_6_6=False,
            reasons=["no_trading_snapshot"],
            suggested_blocks=[],
        )
    r = evaluate_market_boredom(
        volatility_score=row.volatility_score,
        signal_6_6_column=row.signal_6_6,
        payload=row.payload,
    )
    return StateSwitcherResponse(
        status=r.status,
        volatility_score=r.volatility_score,
        has_signal_6_6=r.has_signal_6_6,
        reasons=r.reasons,
        suggested_blocks=r.suggested_blocks,
    )

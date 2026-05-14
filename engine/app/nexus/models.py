"""SQLAlchemy models for unified_nexus — SQLite + Postgres compatible."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Enum as SAEnum, Float, String, Text, Uuid, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class NexusBase(DeclarativeBase):
    pass


class NexusDomain(str, enum.Enum):
    trading_signals = "trading_signals"
    work_tasks = "work_tasks"
    physical_state = "physical_state"
    creative_mode = "creative_mode"


class UnifiedNexus(NexusBase):
    __tablename__ = "unified_nexus"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain: Mapped[NexusDomain] = mapped_column(
        SAEnum(NexusDomain, native_enum=False, length=32),
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    volatility_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    signal_6_6: Mapped[bool] = mapped_column(default=False, nullable=False)

    market_boredom_status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pivot_suggestions: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class NexusDomainEnum(str, Enum):
    trading_signals = "trading_signals"
    work_tasks = "work_tasks"
    physical_state = "physical_state"
    creative_mode = "creative_mode"


class VoicePassRequest(BaseModel):
    passphrase: str = Field(..., min_length=1, max_length=512)


class VoicePassResponse(BaseModel):
    ok: bool = True
    clearance: str = "XIV"
    message: str = "Voice signature accepted."


class UnifiedNexusCreate(BaseModel):
    domain: NexusDomainEnum
    title: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    volatility_score: float | None = None
    signal_6_6: bool = False
    notes: str | None = None


class UnifiedNexusPatch(BaseModel):
    title: str | None = None
    payload: dict[str, Any] | None = None
    volatility_score: float | None = None
    signal_6_6: bool | None = None
    notes: str | None = None


class UnifiedNexusRead(BaseModel):
    id: UUID
    domain: NexusDomainEnum
    title: str
    payload: dict[str, Any]
    volatility_score: float | None
    signal_6_6: bool
    market_boredom_status: str | None
    pivot_suggestions: list[dict[str, Any]] | None = None
    notes: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StateSwitcherResponse(BaseModel):
    status: str
    volatility_score: float | None
    has_signal_6_6: bool
    reasons: list[str]
    suggested_blocks: list[dict[str, str]]

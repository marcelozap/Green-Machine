from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Heartbeat(BaseModel):
    service: str = "green-machine-api"
    status: Literal["ok", "degraded", "down"] = "ok"
    ts: datetime = Field(default_factory=_utcnow)


class MarketSnapshot(BaseModel):
    spy: float | None = None
    vix: float | None = None


class EntryRule(BaseModel):
    min_delta: float = -0.35
    max_delta: float = -0.05
    dte_min: int = 0
    dte_max: int = 7
    side: Literal["long", "short"] = "long"


class ExitRule(BaseModel):
    take_profit_pct: float | None = 0.5
    stop_loss_pct: float | None = 0.3


class BacktestConfig(BaseModel):
    entry: EntryRule = Field(default_factory=EntryRule)
    exit: ExitRule = Field(default_factory=ExitRule)
    max_contracts: int = 10
    start: date | None = None
    end: date | None = None


class BacktestResult(BaseModel):
    equity_curve: list[tuple[str, float]]
    sharpe: float | None = None
    sortino: float | None = None
    calmar: float | None = None
    max_drawdown: float
    total_return: float
    circuit_breaker_hit: bool = False
    notes: str = ""


class LLMBacktestRequest(BaseModel):
    """Payload from command bar / LLM orchestration layer."""

    prompt: str
    config: BacktestConfig | None = None

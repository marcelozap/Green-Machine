from datetime import date, datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Heartbeat(BaseModel):
    service: str = "green-machine-api"
    status: Literal["ok", "degraded", "down"] = "ok"
    ts: datetime = Field(default_factory=_utcnow)


class MarketSnapshot(BaseModel):
    spy: float | None = None
    vix: float | None = None
    as_of: str | None = Field(
        default=None,
        description="trade_date of the bar (YYYY-MM-DD) — last row in spy_daily after your EOD import.",
    )


class EntryRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    min_delta: float = -0.35
    max_delta: float = -0.05
    dte_min: int = 0
    dte_max: int = 7
    side: Literal["long", "short"] = "long"
    # Multiplier on put_proxy_return when optional column dte == 0 (0DTE emphasis)
    zero_dte_vol_boost: float = 1.35


class ExitRule(BaseModel):
    """TP/SL are applied within each contiguous in-position segment (mask True)."""

    model_config = ConfigDict(extra="ignore")

    take_profit_pct: float | None = Field(
        default=0.5,
        description="Take profit when segment cumulative PnL exceeds this times risk_unit_usd * max_contracts.",
    )
    stop_loss_pct: float | None = Field(
        default=0.3,
        description="Stop loss when segment cumulative PnL falls below negative this times risk_unit_usd * max_contracts.",
    )
    risk_unit_usd: float = Field(
        default=500.0,
        description="Scale for TP/SL thresholds in dollars per effective lot (see backtester).",
    )


class BacktestConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    entry: EntryRule = Field(default_factory=EntryRule)
    exit: ExitRule = Field(default_factory=ExitRule)
    max_contracts: int = 10
    start: date | None = None
    end: date | None = None


class SimilarDay(BaseModel):
    trade_date: date
    vix_close: float | None = None
    spy_close: float | None = None
    rsi_14: float | None = None
    trend_label: str | None = None
    distance: float


class BacktestResult(BaseModel):
    equity_curve: list[tuple[str, float]]
    sharpe: float | None = None
    sortino: float | None = None
    calmar: float | None = None
    max_drawdown: float
    total_return: float
    circuit_breaker_hit: bool = False
    notes: str = ""
    similar_days: list[SimilarDay] = Field(default_factory=list)
    llm_summary: str | None = None
    config_resolved: BacktestConfig | None = None
    bs_delta_mae: float | None = Field(
        default=None,
        description="Mean abs error vs Black–Scholes put delta when chain columns exist.",
    )


class LLMBacktestRequest(BaseModel):
    """Payload from command bar / LLM orchestration layer."""

    prompt: str
    config: BacktestConfig | None = None


class LiveNoteBody(BaseModel):
    """Quick desk note pushed to the live feed (e.g. after a trade)."""

    text: str = Field(..., min_length=1, max_length=800)


class DeskNoteBody(BaseModel):
    text: str = Field(..., min_length=1, max_length=800)


class DeskTradeBody(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    description: str = Field(..., min_length=1, max_length=800)
    tags: list[str] = Field(default_factory=list)
    session_date: str | None = Field(default=None, description="YYYY-MM-DD; defaults to UTC today.")


class DeskLogItemOut(BaseModel):
    id: int
    ts: str
    kind: str
    symbol: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    session_date: str | None = None
    text: str | None = None

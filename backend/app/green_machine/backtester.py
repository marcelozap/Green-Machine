"""
GREEN MACHINE — vectorized SPY put backtest skeleton.

Feeds full chain history when wired to the Vault; until then accepts
in-memory bars for API/UI integration tests.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import pandas as pd

from app.config import settings
from app.schemas import BacktestConfig, BacktestResult

try:
    import execution_core as _rust  # type: ignore
except ImportError:
    _rust = None


def _daily_rf() -> float:
    return (1.0 + settings.risk_free_annual) ** (1.0 / 252.0) - 1.0


def _sharpe(daily: np.ndarray, rf_daily: float) -> float | None:
    excess = daily - rf_daily
    std = float(np.std(excess, ddof=1)) if len(excess) > 1 else 0.0
    if std < 1e-12:
        return None
    return float(np.mean(excess) / std * math.sqrt(252.0))


def _sortino(daily: np.ndarray, rf_daily: float) -> float | None:
    excess = daily - rf_daily
    downside = excess[excess < 0]
    if len(downside) < 2:
        return None
    dstd = float(np.std(downside, ddof=1))
    if dstd < 1e-12:
        return None
    return float(np.mean(excess) / dstd * math.sqrt(252.0))


def _max_drawdown_equity(equity: np.ndarray) -> float:
    if len(equity) == 0:
        return 0.0
    peak = np.maximum.accumulate(equity)
    denom = np.where(np.abs(peak) > 1e-9, np.abs(peak), 1.0)
    dd = (equity - peak) / denom
    return float(np.min(dd))


def _calmar(total_return: float, max_dd: float, years: float) -> float | None:
    if max_dd >= -1e-9:
        return None
    cagr = (1.0 + total_return) ** (1.0 / years) - 1.0 if years > 0 else total_return
    return float(cagr / abs(max_dd))


@dataclass
class GreenMachineBacktester:
    """JSON-configurable put-focused backtester (vectorized core)."""

    config: BacktestConfig

    @classmethod
    def from_json(cls, raw: str | dict[str, Any]) -> GreenMachineBacktester:
        data = json.loads(raw) if isinstance(raw, str) else raw
        return cls(config=BacktestConfig.model_validate(data))

    def run(
        self,
        bars: pd.DataFrame | None = None,
        *,
        condition_fn: Callable[[pd.DataFrame], pd.Series] | None = None,
    ) -> BacktestResult:
        """
        bars: columns at minimum [date, spy_return, put_proxy_return, vix]
        put_proxy_return: stand-in for mark-to-market on selected puts until chain data is wired.
        """
        rf_daily = _daily_rf()
        if bars is None or bars.empty:
            rng = np.random.default_rng(42)
            n = 252 * 5
            dates = pd.date_range("2019-01-01", periods=n, freq="B")
            spy_r = rng.normal(0.0004, 0.012, n)
            put_r = rng.normal(-0.0002, 0.02, n) * 1.1
            vix = np.clip(15 + rng.normal(0, 2, n).cumsum() * 0.01, 10, 80)
            bars = pd.DataFrame(
                {
                    "date": dates,
                    "spy_return": spy_r,
                    "put_proxy_return": put_r,
                    "vix": vix,
                }
            )

        df = bars.copy()
        if condition_fn is not None:
            mask = condition_fn(df).astype(bool)
        else:
            mask = self._default_mask(df)

        mask_a = np.asarray(mask, dtype=bool)
        side = -1.0 if self.config.entry.side == "short" else 1.0
        w = min(self.config.max_contracts, 100)
        gross = df["put_proxy_return"].to_numpy(dtype=np.float64) * side * w
        slip = self._slippage(df["vix"].to_numpy(dtype=np.float64)) * np.abs(gross)
        net = np.where(mask_a, gross - slip, 0.0)
        if mask_a.any():
            net[0] -= settings.commission_per_contract * w * 2.0

        if _rust is not None:
            equity = np.asarray(_rust.cumulative_sum_py(net.tolist()), dtype=np.float64)
        else:
            equity = np.cumsum(net)

        daily_pnl = net
        sharpe = _sharpe(daily_pnl, rf_daily)
        sortino = _sortino(daily_pnl, rf_daily)
        mdd = _max_drawdown_equity(equity)
        notional = 1_000_000.0
        total_return = float(equity[-1] / notional) if len(equity) else 0.0
        years = max(len(df) / 252.0, 1e-6)
        calmar = _calmar(total_return, mdd, years)

        circuit = abs(mdd) >= settings.max_drawdown_circuit_breaker
        curve = [(d.isoformat(), float(e)) for d, e in zip(df["date"], equity, strict=False)]

        return BacktestResult(
            equity_curve=curve,
            sharpe=sharpe,
            sortino=sortino,
            calmar=calmar,
            max_drawdown=float(mdd),
            total_return=total_return,
            circuit_breaker_hit=circuit,
            notes="Demo path: replace put_proxy_return with Vault chain marks.",
        )

    def _default_mask(self, df: pd.DataFrame) -> pd.Series:
        return pd.Series(True, index=df.index)

    def _slippage(self, vix: np.ndarray) -> np.ndarray:
        half_spread = 0.0005 + np.clip(vix / 100.0, 0.0, 0.02) * 0.001
        return half_spread * 2.0

"""
GREEN MACHINE — vectorized SPY put backtest core.

Supports Vault daily bars, segment TP/SL, global drawdown circuit, optional 0DTE boost,
and Black–Scholes delta QA when options columns are present.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
import pandas as pd

from app.config import settings
from app.green_machine.black_scholes import delta_mae_vs_history
from app.schemas import BacktestConfig, BacktestResult, ExitRule

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


def _apply_segment_tp_sl(
    mask: np.ndarray,
    raw_edge: np.ndarray,
    exit_rule: ExitRule,
    contracts: int,
) -> np.ndarray:
    """Flatten the remainder of a segment once TP/SL thresholds are touched."""
    n = len(mask)
    out = np.zeros(n, dtype=np.float64)
    tp = exit_rule.take_profit_pct
    sl = exit_rule.stop_loss_pct
    risk = exit_rule.risk_unit_usd
    tp_level = float("inf") if tp is None else float(tp) * risk * contracts
    sl_level = float("inf") if sl is None else float(sl) * risk * contracts

    i = 0
    while i < n:
        if not mask[i]:
            i += 1
            continue
        cum = 0.0
        while i < n and mask[i]:
            cum += raw_edge[i]
            out[i] = raw_edge[i]
            if cum >= tp_level or cum <= -sl_level:
                i += 1
                while i < n and mask[i]:
                    out[i] = 0.0
                    i += 1
                break
            i += 1
    return out


def _apply_circuit(net: np.ndarray, threshold: float) -> tuple[np.ndarray, bool]:
    eq = np.cumsum(net)
    peak = np.maximum.accumulate(eq)
    dd = (eq - peak) / np.where(np.abs(peak) > 1e-9, np.abs(peak), 1.0)
    out = net.copy()
    idx = np.flatnonzero(dd <= -threshold)
    if len(idx):
        cut = int(idx[0])
        out[cut + 1 :] = 0.0
        return out, True
    return out, False


@dataclass
class GreenMachineBacktester:
    """JSON-configurable put-focused backtester (vectorized core + segment risk)."""

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
        rf_daily = _daily_rf()
        if bars is None or bars.empty:
            rng = np.random.default_rng(42)
            n = 252 * 5
            dates = pd.date_range("2019-01-01", periods=n, freq="B")
            spy_r = rng.normal(0.0004, 0.012, n)
            put_r = rng.normal(-0.0002, 0.02, n) * 1.1
            vix = np.clip(15 + rng.normal(0, 2, n).cumsum() * 0.01, 10, 80)
            dte = rng.integers(0, 6, n)
            bars = pd.DataFrame(
                {
                    "date": dates,
                    "spy_return": spy_r,
                    "put_proxy_return": put_r,
                    "vix": vix,
                    "dte": dte,
                }
            )

        df = bars.copy()
        mask = self._entry_mask(df)
        if condition_fn is not None:
            mask = mask & condition_fn(df).astype(bool)
        mask_a = np.asarray(mask, dtype=bool)

        put = df["put_proxy_return"].to_numpy(dtype=np.float64)
        if "dte" in df.columns:
            dte = df["dte"].to_numpy()
            z = self.config.entry.zero_dte_vol_boost
            put = np.where(dte == 0, put * z, put)

        side = -1.0 if self.config.entry.side == "short" else 1.0
        w = int(min(self.config.max_contracts, 500))
        gross = put * side * w
        slip = self._slippage(df["vix"].to_numpy(dtype=np.float64)) * np.abs(gross)
        raw_edge = gross - slip

        seg = _apply_segment_tp_sl(mask_a, raw_edge, self.config.exit, w)
        starts = mask_a & np.r_[True, ~mask_a[:-1]]
        comm = np.zeros(len(mask_a), dtype=np.float64)
        comm[starts] -= settings.commission_per_contract * w * 2.0
        net = seg + comm

        net, tripped = _apply_circuit(net, settings.max_drawdown_circuit_breaker)

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

        circuit = tripped
        curve = [(d.isoformat(), float(e)) for d, e in zip(df["date"], equity, strict=False)]

        bs_mae = None
        need_bs = {"underlying_price", "strike", "iv", "delta", "dte_days"}
        if need_bs.issubset(df.columns):
            tail = df.iloc[-4000:]
            bs_mae = delta_mae_vs_history(tail, settings.risk_free_annual)

        notes = (
            "Segment TP/SL + commission on opens; circuit breaker clips tail PnL. "
            "Populate `spy_daily` for production paths."
        )

        return BacktestResult(
            equity_curve=curve,
            sharpe=sharpe,
            sortino=sortino,
            calmar=calmar,
            max_drawdown=float(mdd),
            total_return=total_return,
            circuit_breaker_hit=circuit,
            notes=notes,
            bs_delta_mae=bs_mae,
        )

    def _entry_mask(self, df: pd.DataFrame) -> pd.Series:
        m = pd.Series(True, index=df.index)
        if "dte" in df.columns:
            d = df["dte"].to_numpy()
            m &= (d >= self.config.entry.dte_min) & (d <= self.config.entry.dte_max)
        return m

    def _slippage(self, vix: np.ndarray) -> np.ndarray:
        half_spread = 0.0005 + np.clip(vix / 100.0, 0.0, 0.02) * 0.001
        return half_spread * 2.0

"""Black–Scholes put delta for IV / greek sanity checks (European, q=0)."""

from __future__ import annotations

import math

import numpy as np
from pandas import DataFrame

_erf = np.vectorize(math.erf)


def _norm_cdf(x: np.ndarray) -> np.ndarray:
    xa = np.asarray(x, dtype=np.float64)
    return 0.5 * (1.0 + _erf(xa / math.sqrt(2.0)))


def put_delta(
    spot: np.ndarray,
    strike: np.ndarray,
    t_years: np.ndarray,
    vol: np.ndarray,
    rate: float,
) -> np.ndarray:
    eps = 1e-12
    t = np.maximum(np.asarray(t_years, dtype=np.float64), eps)
    v = np.maximum(np.asarray(vol, dtype=np.float64), eps)
    s = np.maximum(np.asarray(spot, dtype=np.float64), eps)
    k = np.maximum(np.asarray(strike, dtype=np.float64), eps)
    d1 = (np.log(s / k) + (rate + 0.5 * v * v) * t) / (v * np.sqrt(t))
    return _norm_cdf(d1) - 1.0


def delta_mae_vs_history(df: DataFrame, rate_annual: float) -> float | None:
    """
    Mean abs error between stored put delta and BS delta when columns exist.
    """
    required = {"underlying_price", "strike", "iv", "delta"}
    if not required.issubset(df.columns):
        return None
    sub = df
    if "option_type" in sub.columns:
        sub = sub[sub["option_type"].astype(str).str.upper().str.startswith("P")]
    if sub.empty:
        return None
    if "t_years" in sub.columns:
        t = sub["t_years"].to_numpy(dtype=np.float64)
    elif "dte_days" in sub.columns:
        t = np.maximum(sub["dte_days"].to_numpy(dtype=np.float64) / 365.0, 1.0 / 365.0)
    else:
        return None

    spot = sub["underlying_price"].to_numpy(dtype=np.float64)
    strike = sub["strike"].to_numpy(dtype=np.float64)
    vol = sub["iv"].to_numpy(dtype=np.float64)
    theo = put_delta(spot, strike, t, vol, rate_annual)
    stored = sub["delta"].to_numpy(dtype=np.float64)
    return float(np.mean(np.abs(theo - stored)))

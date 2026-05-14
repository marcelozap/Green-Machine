"""Keyword-driven config when LLM APIs are unavailable."""

from __future__ import annotations

from typing import Literal

import re

from app.schemas import BacktestConfig, EntryRule, ExitRule


def infer_config(prompt: str) -> tuple[BacktestConfig, str]:
    p = prompt.lower()
    side: Literal["long", "short"] = "long"
    if re.search(r"\bshort\b", p) or "short put" in p or "sell put" in p:
        side = "short"
    if "long put" in p or "buy put" in p:
        side = "long"

    dte_min, dte_max = 0, 7
    if re.search(r"\b0dte\b|0\s*dte|same[- ]day", p):
        dte_min, dte_max = 0, 0
    elif "weekly" in p or "weeklies" in p:
        dte_min, dte_max = 1, 7

    max_c = 10
    m = re.search(r"(\d{1,3})\s*(?:contracts|lots|size)", p)
    if m:
        max_c = max(1, min(500, int(m.group(1))))

    tp, sl = 0.5, 0.3
    if "tight" in p or "scalp" in p:
        tp, sl = 0.25, 0.15
    if "swing" in p or "wide" in p:
        tp, sl = 0.8, 0.5

    cfg = BacktestConfig(
        entry=EntryRule(
            side=side,
            dte_min=dte_min,
            dte_max=dte_max,
            zero_dte_vol_boost=1.5 if dte_max == 0 else 1.25,
        ),
        exit=ExitRule(take_profit_pct=tp, stop_loss_pct=sl),
        max_contracts=max_c,
    )
    note = (
        f"Heuristic parse: side={side}, dte=[{dte_min},{dte_max}], "
        f"contracts={max_c}, tp/sl scale=({tp},{sl})."
    )
    return cfg, note

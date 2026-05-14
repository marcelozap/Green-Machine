"""
State-Switcher: Market Boredom — XIV / Nexus (inside Green Machine).

If implied volatility regime is *quiet* (low `volatility_score`) and the proprietary
**6/6** checklist signal is *not* present, Nexus recommends pivoting attention toward
creative (music) or physical blocks instead of forcing tape reads.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.config import settings

STATUS_RECOMEND_PIVOT = "RECOMEND_PIVOT"
STATUS_NOMINAL = "NOMINAL"


@dataclass
class StateSwitcherResult:
    status: str
    volatility_score: float | None
    has_signal_6_6: bool
    reasons: list[str]
    suggested_blocks: list[dict[str, str]]


def _extract_six_of_six(payload: dict[str, Any] | None, column_flag: bool) -> bool:
    if column_flag:
        return True
    if not payload:
        return False
    if payload.get("signal_6_6") is True or payload.get("six_of_six") is True:
        return True
    checklist = payload.get("signal_checklist")
    if isinstance(checklist, list) and len(checklist) >= 6:
        return all(bool(x) for x in checklist[:6])
    return False


def _extract_volatility(row_vol: float | None, payload: dict[str, Any] | None) -> float | None:
    if row_vol is not None:
        return float(row_vol)
    if not payload:
        return None
    for key in ("volatility_score", "vix_norm", "iv_rank", "composite_vol"):
        v = payload.get(key)
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                continue
    return None


def evaluate_market_boredom(
    *,
    volatility_score: float | None,
    signal_6_6_column: bool,
    payload: dict[str, Any] | None,
) -> StateSwitcherResult:
    """
    Low vol: ``volatility_score < GM_NEXUS_VOLATILITY_LOW_BELOW`` (default 0.35), on a 0..1 scale.
    """
    reasons: list[str] = []
    vol = _extract_volatility(volatility_score, payload)
    has_6_6 = _extract_six_of_six(payload, signal_6_6_column)
    low = settings.nexus_volatility_low_below

    if vol is None:
        reasons.append("no_volatility_score")
        return StateSwitcherResult(
            status=STATUS_NOMINAL,
            volatility_score=None,
            has_signal_6_6=has_6_6,
            reasons=reasons,
            suggested_blocks=[],
        )

    if vol >= low:
        reasons.append("vol_not_boring")
    if has_6_6:
        reasons.append("six_of_six_present")

    boring = vol < low and not has_6_6
    if boring:
        blocks = [
            {
                "domain": "creative_mode",
                "hint": "XIV music block — Piano sketch or RC-505 loop session (25–45m).",
            },
            {
                "domain": "physical_state",
                "hint": "Gym / leg-rehab / trail micro-block — book before next cash session.",
            },
        ]
        return StateSwitcherResult(
            status=STATUS_RECOMEND_PIVOT,
            volatility_score=vol,
            has_signal_6_6=False,
            reasons=["low_volatility", "no_six_of_six"],
            suggested_blocks=blocks,
        )

    return StateSwitcherResult(
        status=STATUS_NOMINAL,
        volatility_score=vol,
        has_signal_6_6=has_6_6,
        reasons=reasons or ["watching_tape_warranted"],
        suggested_blocks=[],
    )


def apply_switcher_to_payload(
    volatility_score: float | None,
    signal_6_6_column: bool,
    payload: dict[str, Any] | None,
) -> tuple[str | None, list[dict[str, str]] | None]:
    r = evaluate_market_boredom(
        volatility_score=volatility_score,
        signal_6_6_column=signal_6_6_column,
        payload=payload,
    )
    if r.status == STATUS_RECOMEND_PIVOT:
        return r.status, r.suggested_blocks
    return STATUS_NOMINAL, None

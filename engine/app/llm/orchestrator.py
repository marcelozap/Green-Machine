"""LLM → structured `BacktestConfig` with safe JSON extraction."""

from __future__ import annotations

import json
import re
from typing import Any

import httpx

from app.config import settings
from app.llm.heuristic import infer_config
from app.schemas import BacktestConfig

_JSON_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.I)


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    m = _JSON_FENCE.search(text)
    if m:
        text = m.group(1).strip()
    return json.loads(text)


async def plan_backtest(prompt: str) -> tuple[BacktestConfig, str]:
    """
    Returns resolved config and a short rationale string.
    Falls back to heuristic routing when API keys are missing or the call fails.
    """
    sys = (
        "You are GREEN MACHINE trade-desk copilot. Output ONLY valid JSON matching this shape:\n"
        '{"entry":{"min_delta":number,"max_delta":number,"dte_min":int,"dte_max":int,'
        '"side":"long"|"short","zero_dte_vol_boost":number},'
        '"exit":{"take_profit_pct":number|null,"stop_loss_pct":number|null,"risk_unit_usd":number},'
        '"max_contracts":int}\n'
        "Interpret the user intent for SPY puts (0DTE / weeklies / long or short premium). "
        "Use conservative defaults if ambiguous."
    )
    user = f"Strategy request:\n{prompt.strip()}"

    if settings.openai_api_key and settings.llm_provider == "openai":
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                    json={
                        "model": settings.llm_model,
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"},
                        "messages": [
                            {"role": "system", "content": sys},
                            {"role": "user", "content": user},
                        ],
                    },
                )
                r.raise_for_status()
                content = r.json()["choices"][0]["message"]["content"] or "{}"
            data = _extract_json(content)
            cfg = BacktestConfig.model_validate(data)
            return cfg, "OpenAI structured JSON."
        except Exception as exc:  # noqa: BLE001
            cfg, note = infer_config(prompt)
            return cfg, f"Heuristic fallback (OpenAI error: {exc.__class__.__name__}). {note}"

    if settings.anthropic_api_key and settings.llm_provider == "anthropic":
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                r = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": settings.anthropic_api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": settings.anthropic_model,
                        "max_tokens": 1024,
                        "temperature": 0.1,
                        "system": sys,
                        "messages": [{"role": "user", "content": user}],
                    },
                )
                r.raise_for_status()
                parts = r.json()["content"]
                text = "".join(p.get("text", "") for p in parts if p.get("type") == "text")
            data = _extract_json(text)
            cfg = BacktestConfig.model_validate(data)
            return cfg, "Anthropic JSON extraction."
        except Exception as exc:  # noqa: BLE001
            cfg, note = infer_config(prompt)
            return cfg, f"Heuristic fallback (Anthropic error: {exc.__class__.__name__}). {note}"

    cfg, note = infer_config(prompt)
    return cfg, f"Heuristic routing (no LLM API key). {note}"

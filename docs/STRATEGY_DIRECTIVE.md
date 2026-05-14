# STRATEGY_DIRECTIVE.md — Green Machine ($10M AUM)

**Audience:** Marcelo (Head of Strategy) + all Cursor / Opus agents on Engine and Pilot.  
**Companion:** `docs/API_CONTRACT.md` (technical contract).

---

## Identity & objective

- **Role:** Senior quantitative software engineer operating a **$10M AUM** research and execution program.
- **Product:** **Green Machine** — high-fidelity backtesting and (future) execution for **SPY 0DTE / short-horizon put and call** scalping.
- **Data depth target:** Regime-aware history **1993 → present** (staged delivery; ingestion lives under `historian/`).

## Hardware split

| Machine | Repo paths | Responsibility |
|--------|------------|------------------|
| **PC (Engine)** | `engine/`, `historian/`, `data/` | FastAPI, Rust core, Timescale/SQLite, training & ingest |
| **MacBook (Pilot)** | `pilot/` | React/Vite Glass Cockpit; consume Engine HTTP (WebSocket target per API contract §B) |

## Non-negotiables

1. **Risk:** Institutional slippage and **market impact** assumptions for large clips; **daily and monthly** drawdown circuit breakers (monthly to be fully wired per roadmap).
2. **Performance:** Python **vectorized** (NumPy/Pandas); Rust path favors **SIMD**-friendly loops where applicable.
3. **Logic:** **Regime detection** — compare current conditions to stress templates (e.g. 2008, 2020) on substantive strategy proposals.
4. **UI:** High-contrast, **Bloomberg-style** minimalism; no retail fluff.

## Interaction rules (agents)

- **No junior code:** production-oriented, thread-safe where concurrent paths exist, scalable boundaries.
- **Concise:** prefer logic and diffs over essays.
- **Integrity flag:** if a proposed strategy shows **Max Drawdown > 12%** or **Sharpe < 2.0** (under stated assumptions), label **“High Risk / Unsuitable”** unless explicitly waived in writing with rationale.

## Repo map (enforced)

```
engine/       — FastAPI app, Python backtester, engine/rust_executioner (PyO3)
pilot/        — Vite/React dashboard
historian/    — SQL migrations, CSV ingest, seeds, future training jobs
docs/         — This file + API_CONTRACT.md
data/         — SQLite and future DB files (not secrets)
```

---

*Amend this file when fund mandate or risk limits change; bump version in commit message.*

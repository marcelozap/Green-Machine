# API_CONTRACT.md — Green Machine ($10M Fund)

**Version:** 1.0.0 (May 2026)  
**Status:** Mixed — **§A implemented in repo today**; **§B institutional target** (design north star; not all wired).

---

## §A — IMPLEMENTED (source of truth for Cursor on PC)

### Runtime

| Surface | URL / path |
|--------|------------|
| FastAPI app | `http://127.0.0.1:8000` (default `uvicorn app.main:app --port 8000`) |
| OpenAPI docs | `http://127.0.0.1:8000/docs` |
| React “Glass Cockpit” (Vite dev) | `http://127.0.0.1:5173` (proxies `/health`, `/backtest`, `/market` to port 8000 when `VITE_ENGINE_URL` unset) |
| Pilot on **Vercel** | Set **`VITE_ENGINE_URL`** to public **HTTPS** Engine base (tunnel); Engine must allow origin via **`GM_CORS_ORIGINS`** — see `docs/VERCEL_AND_ENGINE.txt`. |

**There is no WebSocket live feed in the codebase yet.** Pilot uses HTTP + polling patterns only.

### REST (current)

Base path is **not** `/api/v1`; routers are mounted at **root-relative** paths below.

#### Health & market shell

| Method | Path | Response (summary) |
|--------|------|---------------------|
| `GET` | `/health` | `Heartbeat` — liveness (no DB). |
| `GET` | `/health/ready` | `Heartbeat` — DB ping (`SELECT 1`). |
| `GET` | `/market/snapshot` | `MarketSnapshot` — placeholder SPY/VIX until wired to feed. |

#### Backtest / strategy

| Method | Path | Body | Response |
|--------|------|------|------------|
| `POST` | `/backtest/run` | `BacktestConfig` JSON | `BacktestResult` |
| `POST` | `/backtest/llm` | `LLMBacktestRequest` `{ "prompt": string, "config": BacktestConfig \| null }` | `BacktestResult` + `similar_days`, `llm_summary`, `config_resolved` when applicable |

#### `BacktestResult` (Pilot must parse)

- `equity_curve`: `[[iso_date, cumulative_pnl], ...]` (JSON: array of two-element arrays).
- `sharpe`, `sortino`, `calmar`: `number | null`
- `max_drawdown`, `total_return`, `circuit_breaker_hit`, `notes`
- `similar_days[]`: `{ trade_date, vix_close, spy_close, rsi_14, trend_label, distance }`
- `llm_summary`, `config_resolved`, `bs_delta_mae` (optional / nullable)

#### `BacktestConfig` (subset)

- `entry`: `min_delta`, `max_delta`, `dte_min`, `dte_max`, `side` (`long`|`short`), `zero_dte_vol_boost`
- `exit`: `take_profit_pct`, `stop_loss_pct`, `risk_unit_usd`
- `max_contracts`, `start`, `end` (dates)

### Data plane (current)

- **Default DB:** SQLite file `<repo>/data/greenmachine.db` (`GM_DATABASE_URL` overrides with `postgresql+asyncpg://...`).
- **Tables (SQLite auto-DDL on startup):** `spy_daily`, `market_states`, `spy_options_history` (Postgres/Timescale uses `historian/sql/*.sql` migrations separately).
- **Ingest / training scripts:** `historian/scripts/seed_sqlite_demo.py`, `historian/scripts/import_tos_daily_csv.py` (Thinkorswim-style CSV → `spy_daily`); **`historian/scripts/ingest_options_sqlite.py`** (full chain CSV → SQLite `spy_options_history`); Postgres bulk: `historian/scripts/ingest_options.py`, `ingest_spy_daily.py`.

### Risk / execution (current code behavior)

- **Slippage:** VIX-scaled spread model inside `GreenMachineBacktester` (not dollar impact for $10M clips).
- **Commission:** Per-contract constant (`GM_COMMISSION_PER_CONTRACT`, default institutional-ish).
- **Circuit breaker:** Global equity drawdown clip via `GM_MAX_DRAWDOWN_CIRCUIT_BREAKER` (default 0.5). **No separate monthly breaker** yet.
- **No:** Telegram/Discord bot, HMAC mobile auth, sub-ms heartbeat PING, or `>0.05%` slippage auto-reject in code.

---

## §B — INSTITUTIONAL TARGET (for Lead Architect / Opus design)

Use this section to **design forward**; do not assume it exists in git until implemented and referenced in §A.

### WebSocket (Engine → Pilot) — TARGET

- **Endpoint (target):** `wss://[PC_IP]:8080/v1/live` (port and path TBD; must not conflict with FastAPI default 8000 unless unified gateway).
- **Packet (target):** `TICK_UPDATE` with at least: `symbol`, `price`, optional second-order greeks / exposures (`vanna`, `charm`, `gamma_exposure`), `regime_match` (e.g. `2008_OCT_RECOVERY`).

### REST — TARGET extensions

- **Base (target):** `http://[PC_IP]:8000/api/v1` — requires API versioning router in FastAPI + reverse proxy discipline.
- **`GET /regimes/compare` (target):** query `current_vol`, `current_trend` → top **3** historical regime mirrors (ties into `market_states` / future `regime_labels`).

### Schema — TARGET (TimescaleDB on PC)

| Hypertable / table (target) | Role |
|------------------------------|------|
| `market_ticks` | Price, volume, bid–ask spread, microstructure |
| `option_greeks` | delta, gamma, theta, vega, iv (chain time series) |
| `regime_labels` | `start_date`, `regime_type`, `macro_context` |

### Safety — TARGET

- **Heartbeat:** e.g. 500ms PING / stale-data kill switch for live book.
- **Risk guard:** auto-reject or downsize when **expected slippage** for clip size exceeds policy (e.g. 5 bps for $10M-equivalent notional).
- **Mobile alerts:** Telegram/Discord; **HMAC** (or signed JWT) for webhook authenticity.

---

## §C — Handoff to “The Engine” (PC Cursor agent)

First implementation batch should: (1) freeze §A contract for the Pilot; (2) add `/api/v1` router **without** breaking existing paths (duplicate or 307); (3) spec WebSocket schema in OpenAPI sidecar or ADR before coding; (4) add **monthly** drawdown breaker next to daily; (5) document clip-size → impact curve for SPY options.

---

*This file is the shared brief between Head of Strategy (this thread) and Lead Architect (Opus). Update §A whenever ship code changes.*

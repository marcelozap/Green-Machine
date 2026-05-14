GREEN MACHINE — monorepo layout (two-machine workflow)
======================================================

REPOSITORY STRUCTURE
--------------------
  engine/       PC — FastAPI + Python backtester; Rust core in engine/rust_executioner/
  pilot/        MacBook — React/Vite Glass Cockpit (proxies API to Engine)
  historian/    PC — SQL migrations (historian/sql), ingest & seed scripts (historian/scripts)
  docs/         API_CONTRACT.md, STRATEGY_DIRECTIVE.md
  data/         Local SQLite (greenmachine.db) and future transaction DBs (*.db gitignored)

WHAT YOU NEED (minimal)
-----------------------
  1) Python 3.11+ from https://www.python.org/downloads/
  2) Node.js LTS from https://nodejs.org/ (for Pilot only)

The Engine uses SQLite by default at:
  data\greenmachine.db   (repository root)
No Postgres, Docker, or Timescale is required unless you choose them later.

LEGAL / MONEY REALITY
---------------------
  This software is a research and backtesting scaffold. It is NOT financial advice.
  Live options PnL depends on fills, borrow, margin, tax, and rules changes.
  If you "trust the data" for trading, still verify a sample of strikes/Greeks/IV
  against your broker or data vendor before sizing real risk.

QUICK START (Windows PowerShell)
--------------------------------
  From the repository root:

    .\run-windows.ps1

  That script will:
    - create engine\.venv if missing
    - pip install engine/requirements.txt
    - seed demo SQLite under data\
    - npm install in pilot/ if needed

  Then run two terminals:

    Terminal A (Engine):
      cd engine
      .\.venv\Scripts\Activate.ps1
      uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

    Terminal B (Pilot):
      cd pilot
      npm run dev

  Open http://127.0.0.1:5173 — use Ctrl+K to run a backtest.

  From MacBook: clone the same repo, work only under pilot/ unless you also run Engine locally.

THINKORSWIM (SCHWAB) USERS
---------------------------
  Thinkorswim is a front-end; automated market pulls for third-party apps go through
  Charles Schwab APIs (developer registration, OAuth). Green Machine does not embed
  Schwab OAuth — use CSV exports from TOS for the fastest path.

  Daily / chart style CSV (SPY or your underlying):
    cd <repo-root>
    engine\.venv\Scripts\python.exe historian\scripts\import_tos_daily_csv.py "C:\path\YourExport.csv"

  If headers are nonstandard:
    engine\.venv\Scripts\python.exe historian\scripts\import_tos_daily_csv.py export.csv --col-date Time --col-close LAST

YOUR REAL OPTION DATA
---------------------
  - Thinkorswim daily CSV: historian/scripts/import_tos_daily_csv.py
  - Full chain bulk load (Postgres): historian/scripts/ingest_options.py
  - Daily bulk load (Postgres): historian/scripts/ingest_spy_daily.py
  - Demo seed (SQLite): historian/scripts/seed_sqlite_demo.py

POSTGRES / TIMESCALE (optional, later)
--------------------------------------
  Set:
    GM_DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:5432/DBNAME
  Apply historian/sql/001_init_timescale.sql (and 002_*) on the server.
  docker-compose.yml mounts historian/sql for first-time container init.

LLM (optional)
--------------
  Set OPENAI_API_KEY or ANTHROPIC_API_KEY for structured strategy parsing; otherwise
  the stack uses built-in keyword heuristics.

DOCUMENTATION
--------------
  docs/API_CONTRACT.md       — REST + data contract (implemented vs target)
  docs/STRATEGY_DIRECTIVE.md — fund context and non-negotiables (see also .cursorrules)

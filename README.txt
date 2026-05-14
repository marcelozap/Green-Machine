GREEN MACHINE — run without Docker
====================================

WHAT YOU NEED (minimal)
-----------------------
  1) Python 3.11+ from https://www.python.org/downloads/
  2) Node.js LTS from https://nodejs.org/ (for the cockpit UI only)

The backend uses a SQLite file at:
  backend\data\greenmachine.db
No Postgres, Docker, or Timescale is required unless you choose to use them later.

LEGAL / MONEY REALITY
---------------------
  This software is a research and backtesting scaffold. It is NOT financial advice.
  Live options PnL depends on fills, borrow, margin, tax, and rules changes.
  If you "trust the data" for trading, still verify a sample of strikes/Greeks/IV
  against your broker or data vendor before sizing real risk.

QUICK START (Windows PowerShell)
--------------------------------
  From the project folder (where this file lives):

    .\run-windows.ps1

  That script will:
    - create backend\.venv if missing
    - pip install backend requirements
    - seed demo SQLite data (optional but recommended first run)
    - print commands to start API + UI in two terminals

  Manual equivalent:

    cd backend
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python scripts\seed_sqlite_demo.py
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

    cd ..\frontend
    npm install
    npm run dev

  Open http://127.0.0.1:5173 — use Ctrl+K to run a backtest.

YOUR REAL OPTION DATA
---------------------
  - Full chain history: use scripts\ingest_options.py against Postgres if you add it later.
  - Daily SPY + VIX for the Vault path: use scripts\ingest_spy_daily.py against Postgres,
    or load your own CSV into SQLite tables spy_daily / market_states (same columns as seed).

  With only SQLite, bulk COPY helpers are not wired; use DB Browser for SQLite, or
  extend a small importer script when you are ready.

POSTGRES / TIMESCALE (optional, later)
--------------------------------------
  Set environment variable:
    GM_DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:5432/DBNAME
  Apply sql\001_init_timescale.sql (and 002_*) on the server; keep docker-compose.yml
  only if you want containerized Postgres.

LLM (optional)
--------------
  Set OPENAI_API_KEY or ANTHROPIC_API_KEY for structured strategy parsing; otherwise
  the stack uses built-in keyword heuristics.

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

  Easiest “one live site” (UI + API together):

    cd pilot
    npm run build
    cd ..\engine
    .\.venv\Scripts\Activate.ps1
    uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

  Open http://127.0.0.1:8000 — the right column has LIVE DESK (SSE), trade notes, and
  end-of-day CSV upload (Thinkorswim daily or normalized options CSV).

  Phone (HTTPS tunnel + password): set GM_COCKPIT_PASSWORD (and optional GM_COCKPIT_USER, default ``green``)
  in engine/.env, run ``uvicorn`` with ``--host 0.0.0.0``, run cloudflared or ngrok to port 8000, open the
  tunnel URL on your phone, sign in when the browser asks. Details: docs/VERCEL_AND_ENGINE.txt
  Official installers: **docs/TUNNELS_PC.txt** — or clone the repo and run ``powershell -ExecutionPolicy Bypass -File tools/download.ps1`` to fetch ``cloudflared`` + ``flyctl`` into ``tools/`` (not stored on GitHub).

  Dev split (hot-reload UI): Engine on :8000, Pilot on :5173 (Vite proxies API, /live, /ingest, /nexus, /auth, /integrations).

  Docker (optional): from repo root run `docker compose up --build web` then open :8000.
  Mounts .\data into the container so SQLite and uploads persist.

  From MacBook: clone the same repo; use pilot/ with VITE_ENGINE_URL to your PC/tunnel, or
  build the static cockpit on the PC and browse port 8000 only.

COST-FREE "YESTERDAY'S TAPE" (no paid data feed)
-----------------------------------------------
  - **$0 data path:** keep using **SQLite** on disk; once per day (or whenever you like) import your
    Thinkorswim / Schwab **CSV export** via the cockpit upload or ``import_tos_daily_csv.py``. There is
    **no** subscription for "live ticks" in this stack.
  - **What "live" means here:** the header SPY/VIX and SSE feed read the **last row in spy_daily** — that is
    usually **through yesterday** after you upload, not streaming market data. No vendor meter running.
  - **Tunnel only when you want phone access:** start **cloudflared** or **ngrok free tier** when you need
    the site on your phone; stop it when you are done so nothing is exposed. Same for **GM_COCKPIT_PASSWORD**:
    optional gate when the tunnel is up.
  - **LLM charges:** leave ``OPENAI_API_KEY`` / ``ANTHROPIC_API_KEY`` unset to use **free** keyword heuristics
    for the command bar (no token billing).

THINKORSWIM (SCHWAB) USERS
---------------------------
  Thinkorswim is a front-end; automated market pulls for third-party apps go through
  Charles Schwab APIs (developer registration, OAuth). Green Machine does not embed
  Schwab OAuth — use CSV exports from TOS for the fastest path.

  Daily / chart style CSV (SPY or your underlying):
    cd <repo-root>
    engine\.venv\Scripts\python.exe historian\scripts\import_tos_daily_csv.py "C:\path\YourExport.csv"

  Nightly upload without opening the browser (Engine must be running, e.g. localhost or tunnel URL):
    engine\.venv\Scripts\python.exe historian\scripts\eod_upload_agent.py --file "C:\path\YourExport.csv"
    See historian\scripts\eod_upload_agent.py and historian\README.txt (Windows Task Scheduler).
    Your PC must be on (not sleeping) at that time: the script and API run locally unless you later host the Engine in the cloud.

  Mon–Fri 8:00 PM (example): edit ``historian\scripts\windows_task_eod_schedule.ps1``, then follow
    ``historian\scripts\EOD_TASK_SCHEDULER_WINDOWS.txt`` to register the task (market days only).

  If headers are nonstandard:
    engine\.venv\Scripts\python.exe historian\scripts\import_tos_daily_csv.py export.csv --col-date Time --col-close LAST

YOUR REAL OPTION DATA
---------------------
  - Thinkorswim daily CSV: historian/scripts/import_tos_daily_csv.py
  - Full chain bulk load (SQLite, no Docker): historian/scripts/ingest_options_sqlite.py
  - Full chain bulk load (Postgres): historian/scripts/ingest_options.py
  - Daily bulk load (Postgres): historian/scripts/ingest_spy_daily.py
  - Demo seed (SQLite): historian/scripts/seed_sqlite_demo.py

POSTGRES / TIMESCALE (optional, later)
--------------------------------------
  Set:
    GM_DATABASE_URL=postgresql+asyncpg://USER:PASS@HOST:5432/DBNAME
  Apply historian/sql/001_init_timescale.sql (and 002_*) on the server.
  docker-compose.yml mounts historian/sql for first-time container init.

NEXUS (XIV life domains — same Engine, port 8000)
-------------------------------------------------
  Nexus routes live on the same FastAPI app as Green Machine (no second process).
  Table unified_nexus is created automatically (SQLite or Postgres via GM_DATABASE_URL).
  Endpoints: POST /auth/voice-pass, /nexus/records, GET /nexus/state-switcher/evaluate,
  /integrations/google-calendar/status, /integrations/grocery-rehab/status.
  Env: XIV_VOICE_PASSPHRASE (or GM_XIV_VOICE_PASSPHRASE), GM_NEXUS_VOLATILITY_LOW_BELOW.
  Optional DDL mirror: historian/sql/nexus_001_unified_nexus.sql

CLOUD (always-on, PC can sleep)
-------------------------------
  Deploy the same Docker image to **Fly.io**: see **docs/HOSTING_FLY.txt** (``fly.toml`` at repo root,
  persistent volume for SQLite under ``/app/data``). Set ``GM_COCKPIT_PASSWORD`` as a fly secret so the
  public URL is not wide open. Fly CLI install: **docs/TUNNELS_PC.txt**

LLM (optional)
--------------
  Set OPENAI_API_KEY or ANTHROPIC_API_KEY for structured strategy parsing; otherwise
  the stack uses built-in keyword heuristics.

DOCUMENTATION
--------------
  docs/API_CONTRACT.md       — REST + data contract (implemented vs target)
  docs/STRATEGY_DIRECTIVE.md — fund context and non-negotiables (see also .cursorrules)
  docs/HOSTING_FLY.txt       — deploy Engine + cockpit to Fly.io (always-on, HTTPS)
  docs/TUNNELS_PC.txt        — Fly CLI, cloudflared, ngrok — official download links
  docs/GITHUB_PUSH.txt      — push this repo to GitHub (no binaries in git)

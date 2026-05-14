historian/ — data plane for Green Machine
=========================================

  sql/          Timescale/Postgres DDL (docker-compose init or manual apply)
  scripts/      Ingest, seed, vendor CSV

Scripts (run from repo root with engine venv)
-----------------------------------------------
  seed_sqlite_demo.py       Demo spy_daily + market_states → data/greenmachine.db
  import_tos_daily_csv.py   Thinkorswim-style daily OHLCV → spy_daily (SQLite)
  ingest_options_sqlite.py  Normalized options CSV → spy_options_history (SQLite)
  ingest_options.py         Same CSV → Postgres/Timescale (psycopg COPY)
  ingest_spy_daily.py       Daily bars CSV → Postgres spy_daily (psycopg COPY)
  eod_upload_agent.py       Scheduled agent: local file or URL → POST /ingest/eod on the Engine

Example:

  engine\.venv\Scripts\python.exe historian\scripts\ingest_options_sqlite.py C:\data\spy_options.csv

EOD agent (Task Scheduler / cron): see docstring in historian\scripts\eod_upload_agent.py -- --file,
--glob (newest match), or --url + --download-to; set GREEN_MACHINE_ENGINE and optional
GM_COCKPIT_USER / GM_COCKPIT_PASSWORD if the Engine uses the cockpit gate.

Windows Mon-Fri 8 PM: edit historian\scripts\windows_task_eod_schedule.ps1 then
historian\scripts\EOD_TASK_SCHEDULER_WINDOWS.txt

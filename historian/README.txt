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

Example:

  engine\.venv\Scripts\python.exe historian\scripts\ingest_options_sqlite.py C:\data\spy_options.csv

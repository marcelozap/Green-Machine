historian/ — data plane for Green Machine
=========================================

  sql/          Timescale/Postgres DDL (used by docker-compose init, or apply manually)
  scripts/      Bulk ingest, SQLite seed, Thinkorswim CSV import

Run scripts from repository root using the Engine venv, e.g.:

  engine\.venv\Scripts\python.exe historian\scripts\seed_sqlite_demo.py

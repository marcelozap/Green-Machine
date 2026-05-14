Agent reading order (Green Machine)
====================================

1. docs/STRATEGY_DIRECTIVE.md  — fund mandate, risk posture, interaction rules
2. docs/API_CONTRACT.md       — implemented REST + data contract vs institutional targets
3. .cursorrules (repo root)    — Cursor agent defaults; keep in sync with STRATEGY where they overlap

Financial ingestion code and SQL live under `historian/` (see `historian/README.txt`).  
Bulk options chain → local SQLite: `historian/scripts/ingest_options_sqlite.py`.

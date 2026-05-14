# engine/ — Green Machine PC backend

FastAPI entry: `app.main:app`

Run from this directory:

  python -m venv .venv
  .\.venv\Scripts\pip install -r requirements.txt
  .\.venv\Scripts\uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

Default SQLite DB path: `<repo-root>/data/greenmachine.db` (see `app/config.py`).

Rust core: `rust_executioner/` (maturin / PyO3 when wired).

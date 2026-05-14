"""
EOD upload agent -- download (optional) + POST CSV to Green Machine /ingest/eod.

Thinkorswim / Schwab does not give a simple unauthenticated nightly URL for retail exports.
Typical flows this script supports:

  1) Fixed path -- you save the same filename each day; Task Scheduler runs this script after export.
  2) Glob / newest file -- exports land in a folder; use --glob to pick latest by mtime.
  3) HTTP(S) URL -- only if you host the file (S3 presigned, Dropbox direct link, your own server).

Run from repo root with the Engine venv (has httpx):

  engine\\.venv\\Scripts\\python.exe historian\\scripts\\eod_upload_agent.py ^
    --file "C:\\Exports\\SPY_daily.csv" --engine http://127.0.0.1:8000 --kind tos_daily

  engine\\.venv\\Scripts\\python.exe historian\\scripts\\eod_upload_agent.py ^
    --glob "C:\\Exports\\SPY*.csv" --engine http://127.0.0.1:8000

  engine\\.venv\\Scripts\\python.exe historian\\scripts\\eod_upload_agent.py ^
    --url "https://your-bucket.s3.../spy_eod.csv" --download-to data\\agent_last.csv ^
    --engine https://your-tunnel.example.com --kind tos_daily

If the Engine uses HTTP Basic auth (GM_COCKPIT_PASSWORD), set the same credentials in the environment
before running (GM_COCKPIT_USER / GM_COCKPIT_PASSWORD) so this script can authenticate.
"""

from __future__ import annotations

import argparse
import base64
import glob
import os
import sys
from pathlib import Path

import httpx

_DEFAULT_ENGINE = "http://127.0.0.1:8000"


def _basic_headers() -> dict[str, str]:
    user = os.environ.get("GM_COCKPIT_USER", "green").strip()
    password = os.environ.get("GM_COCKPIT_PASSWORD", "").strip()
    if not password:
        return {}
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


def _resolve_file(path: str) -> Path:
    p = Path(path).expanduser().resolve()
    if not p.is_file():
        sys.exit(f"Not a file: {p}")
    return p


def _resolve_glob(pattern: str) -> Path:
    matches = sorted(glob.glob(pattern), key=lambda f: Path(f).stat().st_mtime, reverse=True)
    if not matches:
        sys.exit(f"No files matched glob: {pattern!r}")
    hit = Path(matches[0]).resolve()
    print(f"Using newest match: {hit}")
    return hit


def _download(url: str, dest: Path, headers: dict[str, str]) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120.0, follow_redirects=True, headers=headers) as client:
        r = client.get(url)
        r.raise_for_status()
        dest.write_bytes(r.content)
    print(f"Downloaded {len(r.content)} bytes -> {dest}")
    return dest


def _upload(csv_path: Path, engine: str, kind: str, headers: dict[str, str]) -> None:
    base = engine.rstrip("/")
    url = f"{base}/ingest/eod?kind={kind}"
    hdrs = {**headers}
    with httpx.Client(timeout=600.0, headers=hdrs) as client:
        with csv_path.open("rb") as f:
            files = {"file": (csv_path.name, f, "text/csv")}
            r = client.post(url, files=files)
    if not r.is_success:
        sys.exit(f"Upload failed HTTP {r.status_code}: {r.text[:2000]}")
    print("Upload OK:", r.text)


def main() -> None:
    parser = argparse.ArgumentParser(description="EOD CSV to Green Machine /ingest/eod")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--file", help="Path to local .csv")
    src.add_argument("--glob", dest="glob_pat", help="Glob pattern; newest file by mtime is uploaded")
    src.add_argument("--url", help="Download CSV from this URL, then upload (requires --download-to)")
    parser.add_argument(
        "--download-to",
        default="",
        help="Path to save URL download (required when --url is set)",
    )
    parser.add_argument(
        "--engine",
        default=os.environ.get("GREEN_MACHINE_ENGINE", _DEFAULT_ENGINE),
        help=f"Engine base URL (default {_DEFAULT_ENGINE} or env GREEN_MACHINE_ENGINE)",
    )
    parser.add_argument(
        "--kind",
        choices=("tos_daily", "options"),
        default="tos_daily",
        help="ingest/eod kind query param",
    )
    args = parser.parse_args()

    hdr = _basic_headers()
    if args.url:
        if not args.download_to:
            sys.exit("--download-to is required when using --url")
        csv_path = _download(args.url, Path(args.download_to).expanduser().resolve(), hdr)
    elif args.glob_pat:
        csv_path = _resolve_glob(args.glob_pat)
    else:
        csv_path = _resolve_file(args.file or "")

    if csv_path.suffix.lower() != ".csv":
        print("Warning: file does not end with .csv; upload may be rejected.", file=sys.stderr)

    _upload(csv_path, args.engine, args.kind, hdr)


if __name__ == "__main__":
    main()

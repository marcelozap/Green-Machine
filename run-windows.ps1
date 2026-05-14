# GREEN MACHINE — zero-Docker local run (Windows)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Engine = Join-Path $Root "engine"
$Pilot = Join-Path $Root "pilot"
$VenvPy = Join-Path $Engine ".venv\Scripts\python.exe"
$VenvPip = Join-Path $Engine ".venv\Scripts\pip.exe"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python is not on PATH. Install Python 3.11+ from python.org and re-run." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $VenvPy)) {
    Write-Host "Creating Python venv in engine\.venv ..."
    python -m venv (Join-Path $Engine ".venv")
}

Write-Host "Installing Python dependencies ..."
& $VenvPip install -r (Join-Path $Engine "requirements.txt")

Write-Host "Seeding demo SQLite under data\ (skip next time if you already have real data) ..."
Push-Location $Root
try {
    & $VenvPy "historian\scripts\seed_sqlite_demo.py"
} finally {
    Pop-Location
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "npm not found. Install Node.js LTS from nodejs.org for the UI." -ForegroundColor Yellow
} elseif (-not (Test-Path (Join-Path $Pilot "node_modules"))) {
    Write-Host "Installing pilot (frontend) dependencies ..."
    Push-Location $Pilot
    try { npm install } finally { Pop-Location }
}

Write-Host ""
Write-Host "=== Option A — one site (UI + API on port 8000) ===" -ForegroundColor Green
Write-Host "  cd `"$Pilot`""
Write-Host "  npm run build"
Write-Host "  cd `"$Engine`""
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Write-Host "  Open http://127.0.0.1:8000 — live desk + EOD upload in the right column."
Write-Host ""
Write-Host "=== Option B — dev (hot-reload UI, Vite proxy) ===" -ForegroundColor Green
Write-Host "Terminal A (Engine):"
Write-Host "  cd `"$Engine`""
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Write-Host "Terminal B (Pilot):"
Write-Host "  cd `"$Pilot`""
Write-Host "  npm run dev"
Write-Host "  Open http://127.0.0.1:5173"
Write-Host ""
Write-Host "=== Option C — Docker (same as Option A, no local Node after image build) ===" -ForegroundColor Green
Write-Host "  docker compose up --build web"
Write-Host "  Open http://127.0.0.1:8000"
Write-Host ""
Write-Host "Press Ctrl+K in the cockpit for the backtest command bar. Details: README.txt"

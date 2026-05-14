# GREEN MACHINE — zero-Docker local run (Windows)
$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Frontend = Join-Path $Root "frontend"
$VenvPy = Join-Path $Backend ".venv\Scripts\python.exe"
$VenvPip = Join-Path $Backend ".venv\Scripts\pip.exe"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python is not on PATH. Install Python 3.11+ from python.org and re-run." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $VenvPy)) {
    Write-Host "Creating Python venv in backend\.venv ..."
    python -m venv (Join-Path $Backend ".venv")
}

Write-Host "Installing Python dependencies ..."
& $VenvPip install -r (Join-Path $Backend "requirements.txt")

Write-Host "Seeding demo SQLite (skip next time if you already have real data) ..."
Push-Location $Backend
try {
    & $VenvPy "scripts\seed_sqlite_demo.py"
} finally {
    Pop-Location
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host "npm not found. Install Node.js LTS from nodejs.org for the UI." -ForegroundColor Yellow
} elseif (-not (Test-Path (Join-Path $Frontend "node_modules"))) {
    Write-Host "Installing frontend dependencies ..."
    Push-Location $Frontend
    try { npm install } finally { Pop-Location }
}

Write-Host ""
Write-Host "=== Next: run TWO terminals ===" -ForegroundColor Green
Write-Host "Terminal A (API):"
Write-Host "  cd `"$Backend`""
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Write-Host ""
Write-Host "Terminal B (UI):"
Write-Host "  cd `"$Frontend`""
Write-Host "  npm run dev"
Write-Host ""
Write-Host "Then open http://127.0.0.1:5173 and press Ctrl+K for the command bar."
Write-Host "Details: README.txt in this folder."

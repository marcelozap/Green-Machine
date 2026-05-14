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
Write-Host "=== Next: run TWO terminals ===" -ForegroundColor Green
Write-Host "Terminal A (Engine / API):"
Write-Host "  cd `"$Engine`""
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"
Write-Host ""
Write-Host "Terminal B (Pilot / UI):"
Write-Host "  cd `"$Pilot`""
Write-Host "  npm run dev"
Write-Host ""
Write-Host "Then open http://127.0.0.1:5173 and press Ctrl+K for the command bar."
Write-Host "Details: README.txt in this folder."

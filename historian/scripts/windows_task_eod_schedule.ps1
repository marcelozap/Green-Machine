# Green Machine — EOD CSV upload (Mon–Fri evening)
#
# 1) Edit the variables in the CONFIG block below (path to your export, optional engine URL / auth).
# 2) Test once from PowerShell:  .\windows_task_eod_schedule.ps1
# 3) Register Windows Task Scheduler to run this file Mon–Fri at 8:00 PM (see EOD_TASK_SCHEDULER_WINDOWS.txt).
#
# Your PC must be on and the Engine (uvicorn) running at that time.

$ErrorActionPreference = "Stop"

# ---------- CONFIG (edit these) ----------
# Use exactly ONE of: $CsvFile (fixed name each day) OR $Glob (newest matching file wins).
$CsvFile = "C:\Exports\SPY_daily.csv"
$Glob = $null
# $CsvFile = $null
# $Glob = "C:\Exports\SPY*.csv"

# Engine URL (tunnel or localhost). Override with env GREEN_MACHINE_ENGINE if you prefer.
$Engine = if ($env:GREEN_MACHINE_ENGINE) { $env:GREEN_MACHINE_ENGINE } else { "http://127.0.0.1:8000" }
$Kind = "tos_daily"
# For normalized options chain CSV use:  $Kind = "options"
# ---------- end CONFIG ----------

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Python = Join-Path $RepoRoot "engine\.venv\Scripts\python.exe"
$Agent = Join-Path $RepoRoot "historian\scripts\eod_upload_agent.py"

if (-not (Test-Path $Python)) {
    Write-Error "Missing venv Python: $Python  (run run-windows.ps1 or create engine\.venv)"
}
if (-not (Test-Path $Agent)) {
    Write-Error "Missing agent script: $Agent"
}

if (-not $Glob -and -not $CsvFile) {
    Write-Error "Edit CONFIG: set either `$CsvFile or `$Glob in windows_task_eod_schedule.ps1"
}
try {
    if ($Glob) {
        & $Python $Agent --glob $Glob --engine $Engine --kind $Kind
    } else {
        if (-not $CsvFile) {
            Write-Error "Set either `$CsvFile or `$Glob in CONFIG"
        }
        & $Python $Agent --file $CsvFile --engine $Engine --kind $Kind
    }
} finally {
    Pop-Location
}

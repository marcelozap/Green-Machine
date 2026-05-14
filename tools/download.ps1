# Download cloudflared + flyctl into ./tools/ (binaries are gitignored — do not commit them).
# Run from repo root:
#   powershell -ExecutionPolicy Bypass -File tools/download.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Tools = Join-Path $Root "tools"
New-Item -ItemType Directory -Force -Path $Tools | Out-Null

Write-Host "Downloading cloudflared (GitHub latest)..."
$cdUrl = "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
Invoke-WebRequest -Uri $cdUrl -OutFile (Join-Path $Tools "cloudflared.exe") -UseBasicParsing

Write-Host "Downloading flyctl (superfly/flyctl releases)..."
$rel = Invoke-RestMethod -Uri "https://api.github.com/repos/superfly/flyctl/releases/latest" -Headers @{ "User-Agent" = "GreenMachine-tools-download" }
$asset = $rel.assets | Where-Object { $_.name -match "Windows_x86_64\.zip$" } | Select-Object -First 1
if (-not $asset) {
    throw "No Windows_x86_64 zip in flyctl latest release"
}
$zip = Join-Path $Tools "flyctl.zip"
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $zip -UseBasicParsing
$ex = Join-Path $Tools "flyctl_extract"
if (Test-Path $ex) {
    Remove-Item $ex -Recurse -Force
}
Expand-Archive -Path $zip -DestinationPath $ex -Force
$exe = Get-ChildItem -Path $ex -Filter "*.exe" -Recurse | Select-Object -First 1
if (-not $exe) {
    throw "No exe in flyctl zip"
}
Copy-Item $exe.FullName (Join-Path $Tools "flyctl.exe") -Force
Remove-Item $zip -Force
Remove-Item $ex -Recurse -Force

Write-Host "Done. Binaries:"
Get-ChildItem $Tools -Filter "*.exe" | Format-Table Name, @{L = "MB"; E = { [math]::Round($_.Length / 1MB, 1) } }

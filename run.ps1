# CoBuilder — start the local dev server
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Test-Path "$Root\.env")) {
    Write-Host "Copy .env.example to .env and fill in your Azure Foundry endpoint." -ForegroundColor Yellow
    Copy-Item "$Root\.env.example" "$Root\.env"
}

if (-not (Test-Path "$Root\.venv")) {
    Write-Host "Creating virtual environment..."
    python -m venv "$Root\.venv"
}

& "$Root\.venv\Scripts\pip.exe" install -q -r "$Root\backend\requirements.txt"

Write-Host "Starting CoBuilder at http://127.0.0.1:8000" -ForegroundColor Green
Set-Location "$Root\backend"
& "$Root\.venv\Scripts\uvicorn.exe" app.main:app --reload --host 127.0.0.1 --port 8000

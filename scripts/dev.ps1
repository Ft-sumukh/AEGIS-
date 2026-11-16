# =============================================================================
# Aegis Development Startup Script for Windows PowerShell
# Starts backend and frontend development servers in separate processes.
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  AEGIS AI Operations Intelligence Platform" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Check if Docker is available
$dockerAvailable = (Get-Command docker -ErrorAction SilentlyContinue) -ne $null

if ($dockerAvailable) {
    Write-Host ">>> Docker detected. To start via Docker Compose, run:" -ForegroundColor Yellow
    Write-Host "    docker compose up --build" -ForegroundColor White
}

Write-Host "`n>>> Starting native development servers..." -ForegroundColor Cyan

# Start Backend API
Write-Host ">>> Launching Backend on http://localhost:8000..." -ForegroundColor Green
$backendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\backend'; .\.venv\Scripts\Activate.ps1; uvicorn app.main:app --reload --port 8000" -PassThru

# Start Frontend App
Write-Host ">>> Launching Frontend on http://localhost:3000..." -ForegroundColor Green
$frontendProcess = Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\..\frontend'; npm run dev" -PassThru

Write-Host "`n>>> Services started in separate terminal windows." -ForegroundColor Green
Write-Host "    Frontend:   http://localhost:3000" -ForegroundColor White
Write-Host "    Backend:    http://localhost:8000" -ForegroundColor White
Write-Host "    API Docs:   http://localhost:8000/docs" -ForegroundColor White

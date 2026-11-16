# =============================================================================
# Aegis Development Setup Script for Windows PowerShell
# =============================================================================

$ErrorActionPreference = "Stop"

Write-Host ">>> [Aegis] Initializing Development Environment..." -ForegroundColor Cyan

# 1. Environment file setup
if (-not (Test-Path ".env")) {
    Write-Host ">>> Creating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
} else {
    Write-Host ">>> .env already exists." -ForegroundColor Green
}

# 2. Backend virtual environment & dependencies
Write-Host ">>> Setting up Python backend..." -ForegroundColor Cyan
if (-not (Test-Path "backend\.venv")) {
    Write-Host ">>> Creating Python virtual environment in backend\.venv..." -ForegroundColor Yellow
    python -m venv "backend\.venv"
}

Write-Host ">>> Installing backend dependencies..." -ForegroundColor Yellow
& "backend\.venv\Scripts\pip.exe" install -e "backend\[dev]"

# 3. Frontend dependencies
Write-Host ">>> Installing frontend dependencies..." -ForegroundColor Cyan
Set-Location "frontend"
npm install
Set-Location ".."

Write-Host ">>> [Aegis] Setup complete! Run .\scripts\dev.ps1 to start services." -ForegroundColor Green

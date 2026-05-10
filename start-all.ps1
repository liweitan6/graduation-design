# DL Fuzzing System - Startup Script (PowerShell)
# Usage: Right-click -> Run with PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DL Fuzzing System - Starting All" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# Conda initialization path
$CondaInit = "C:\Users\gjj\anaconda3\Scripts\activate.bat"
$CondaEnv  = "dl_fuzz_env"

# 0. Ensure Docker containers are running
Write-Host "[0/3] Checking Docker containers..." -ForegroundColor Yellow
$running = docker ps --format "{{.Names}}" 2>$null
$stopped = docker ps -a --filter "status=exited" --format "{{.Names}}" 2>$null
if ($running -match "fuzzing_mysql") {
    Write-Host "      Docker containers already running." -ForegroundColor Green
} elseif ($stopped -match "fuzzing_mysql") {
    Write-Host "      Resuming stopped Docker containers..." -ForegroundColor Yellow
    docker-compose -f "$ProjectRoot\docker-compose.yml" start
    Write-Host "      Waiting for containers to become ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 15
} else {
    Write-Host "      Creating Docker containers..." -ForegroundColor Yellow
    docker-compose -f "$ProjectRoot\docker-compose.yml" up -d
    Write-Host "      Waiting for containers to become healthy..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
}

# 1. Start Python Data Service
Write-Host "[1/3] Starting Python Data Service (port 5000)..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k", "title [Python API - 5000] && call `"$CondaInit`" && conda activate $CondaEnv && cd /d `"$ProjectRoot`" && python scripts/data_service.py"

Start-Sleep -Seconds 8

# 2. Start Java Backend
Write-Host "[2/3] Starting Java Backend (port 8080)..." -ForegroundColor Yellow
Start-Process cmd -ArgumentList "/k", "title [Java API - 8080] && call `"$CondaInit`" && conda activate $CondaEnv && cd /d `"$ProjectRoot\backend`" && mvn spring-boot:run"

Start-Sleep -Seconds 15

# 3. Start Vue Frontend (auto npm install if needed)
Write-Host "[3/3] Starting Vue Frontend (port 5173)..." -ForegroundColor Yellow
if (-not (Test-Path "$ProjectRoot\frontend\node_modules")) {
    Write-Host "      node_modules not found, running npm install..." -ForegroundColor Yellow
    Start-Process -Wait -NoNewWindow -FilePath "cmd" -ArgumentList "/c", "call `"$CondaInit`" && conda activate $CondaEnv && cd /d `"$ProjectRoot\frontend`" && npm install"
}
Start-Process cmd -ArgumentList "/k", "title [Vue Frontend - 5173] && call `"$CondaInit`" && conda activate $CondaEnv && cd /d `"$ProjectRoot\frontend`" && npm run dev"

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All services started!" -ForegroundColor Green
Write-Host "  - Docker:      MySQL(3306) Milvus(19530) MinIO(9000) Attu(8000)" -ForegroundColor White
Write-Host "  - Python API:  http://localhost:5000" -ForegroundColor White
Write-Host "  - Java API:    http://localhost:8080" -ForegroundColor White
Write-Host "  - Frontend:    http://localhost:5173" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green

Start-Sleep -Seconds 5
Start-Process "http://localhost:5173"

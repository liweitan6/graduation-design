# DL Fuzzing System - Stop All Services (PowerShell)
# Usage: Right-click -> Run with PowerShell

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DL Fuzzing System - Stopping All" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

function Stop-ServiceOnPort {
    param([int]$Port, [string]$Name)
    Write-Host "      Stopping $Name (port $Port)..." -ForegroundColor Yellow
    $procIds = Get-NetTCPConnection -LocalPort $Port -ErrorAction SilentlyContinue |
               Select-Object -ExpandProperty OwningProcess -Unique
    if ($procIds) {
        foreach ($p in $procIds) {
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
        Write-Host "      $Name stopped." -ForegroundColor Green
    } else {
        Write-Host "      $Name not running." -ForegroundColor Gray
    }
}

# 1. Stop Python Data Service (port 5000)
Write-Host "[1/4] Stopping Python Data Service..." -ForegroundColor Yellow
Stop-ServiceOnPort -Port 5000 -Name "Python API"

# 2. Stop Java Backend (port 8080)
Write-Host "[2/4] Stopping Java Backend..." -ForegroundColor Yellow
Stop-ServiceOnPort -Port 8080 -Name "Java Backend"

# 3. Stop Vue Frontend (port 5173)
Write-Host "[3/4] Stopping Vue Frontend..." -ForegroundColor Yellow
Stop-ServiceOnPort -Port 5173 -Name "Vue Frontend"

# 4. Stop Docker containers
Write-Host "[4/4] Stopping Docker containers..." -ForegroundColor Yellow
$running = docker ps --format "{{.Names}}" 2>$null
if ($running -match "fuzzing_") {
    docker-compose -f "$ProjectRoot\docker-compose.yml" stop
    Write-Host "      Docker containers stopped." -ForegroundColor Green
} else {
    Write-Host "      Docker containers not running." -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  All services stopped!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

#Requires -Version 5.1
<#
.SYNOPSIS
    Reliable Docker Desktop restart for this project.
.DESCRIPTION
    Handles the known issues with Docker Desktop + WSL2:
    1. Zombie "Docker Desktop.exe" processes that block startup
    2. Missing "docker-desktop" WSL distribution after updates
    3. Engine stuck in ping loop (500 errors)
.EXAMPLE
    .\scripts\restart-docker.ps1
    .\scripts\restart-docker.ps1 -SkipBuild
    .\scripts\restart-docker.ps1 -WaitSeconds 120
#>
param(
    [int]$WaitSeconds = 90,
    [switch]$SkipBuild
)

$ErrorActionPreference = "SilentlyContinue"
$DockerDesktopExe = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
$WslVhdx = "$env:LOCALAPPDATA\Docker\wsl\main\ext4.vhdx"

function Write-Step($step, $msg) {
    Write-Host "`n[$step] $msg" -ForegroundColor Cyan
}

# ── Step 1: Stop Docker Desktop gracefully ──
Write-Step 1 "Stopping Docker Desktop processes..."
Get-Process -Name "com.docker.backend", "com.docker.build", "docker-sandbox" -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue |
    Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

# ── Step 2: Check for zombie processes ──
Write-Step 2 "Checking for zombie processes..."
$zombies = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
if ($zombies) {
    Write-Host "  Found $($zombies.Count) unkillable Docker Desktop process(es)." -ForegroundColor Yellow
    Write-Host "  Attempting taskkill..." -ForegroundColor Yellow
    taskkill /F /IM "Docker Desktop.exe" /T 2>$null | Out-Null
    Start-Sleep -Seconds 3
    $zombies = Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue
    if ($zombies) {
        Write-Host ""
        Write-Host "  *** REBOOT REQUIRED ***" -ForegroundColor Red
        Write-Host "  Zombie Docker Desktop processes cannot be killed." -ForegroundColor Red
        Write-Host "  Reboot your machine, then re-run this script." -ForegroundColor Red
        Write-Host ""
        exit 1
    }
}
Write-Host "  All Docker processes stopped." -ForegroundColor Green

# ── Step 3: Shutdown WSL ──
Write-Step 3 "Shutting down WSL..."
wsl --shutdown 2>$null
Start-Sleep -Seconds 3

# ── Step 4: Fix docker-desktop WSL distro if missing ──
Write-Step 4 "Checking docker-desktop WSL distribution..."
$distros = wsl -l -q 2>$null
$hasDockerDesktop = $distros | Where-Object { $_ -match "docker-desktop" }

if (-not $hasDockerDesktop) {
    if (Test-Path $WslVhdx) {
        Write-Host "  docker-desktop distro missing. Re-importing from VHDX..." -ForegroundColor Yellow
        wsl --import-in-place docker-desktop $WslVhdx 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Successfully re-imported docker-desktop." -ForegroundColor Green
        } else {
            Write-Host "  Failed to import. Docker Desktop will recreate it on startup." -ForegroundColor Yellow
        }
    } else {
        Write-Host "  No VHDX found. Docker Desktop will create a fresh distro on startup." -ForegroundColor Yellow
    }
} else {
    Write-Host "  docker-desktop distro present." -ForegroundColor Green
}

# ── Step 5: Start Docker Desktop ──
Write-Step 5 "Starting Docker Desktop..."
if (-not (Test-Path $DockerDesktopExe)) {
    Write-Host "  Docker Desktop not found at: $DockerDesktopExe" -ForegroundColor Red
    exit 1
}
Start-Process $DockerDesktopExe

# ── Step 6: Wait for engine ──
Write-Step 6 "Waiting up to ${WaitSeconds}s for Docker engine..."
$elapsed = 0
$ready = $false
while ($elapsed -lt $WaitSeconds) {
    Start-Sleep -Seconds 5
    $elapsed += 5
    $result = docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        $ready = $true
        break
    }
    # Show progress every 15s
    if ($elapsed % 15 -eq 0) {
        Write-Host "  Still waiting... (${elapsed}s)" -ForegroundColor DarkGray
    }
}

if (-not $ready) {
    Write-Host ""
    Write-Host "  Docker engine did not respond after ${WaitSeconds}s." -ForegroundColor Red
    Write-Host "  Check Docker Desktop UI for error dialogs." -ForegroundColor Red
    Write-Host "  If stuck, reboot and re-run this script." -ForegroundColor Red
    exit 1
}

Write-Host "  Docker engine is ready! (took ${elapsed}s)" -ForegroundColor Green

# ── Step 7: Show running containers ──
Write-Step 7 "Current containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1

# ── Step 8: Optionally rebuild and start project containers ──
if (-not $SkipBuild) {
    Write-Step 8 "Starting project containers..."
    Push-Location $PSScriptRoot\..
    docker compose up -d --build aegis-api aegis-worker aegis-ui 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "`n  Project containers started." -ForegroundColor Green
        # Wait for postgres to be healthy before running migration
        Write-Host "  Waiting for postgres..." -ForegroundColor DarkGray
        Start-Sleep -Seconds 10
        docker exec aegis-securityhardening-aegis-api-1 alembic upgrade head 2>&1
        Write-Host "  Database migrations applied." -ForegroundColor Green
    } else {
        Write-Host "  Failed to start project containers." -ForegroundColor Red
    }
    Pop-Location
} else {
    Write-Host "`n  Skipping build (-SkipBuild). Run manually:" -ForegroundColor DarkGray
    Write-Host "  docker compose up -d --build aegis-api aegis-worker aegis-ui" -ForegroundColor DarkGray
}

Write-Host "`nDone!" -ForegroundColor Green

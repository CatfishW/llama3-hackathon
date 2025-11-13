#!/usr/bin/env powershell
<#
.SYNOPSIS
Voice Chat Debug Build and Run Script
Starts SST broker, TTS broker, and FastAPI backend with debug logging

.DESCRIPTION
This script starts all three services needed for voice chat + LLM integration:
1. SST Broker (Whisper.cpp) on port 9082
2. TTS Broker (Kokoro) on port 8080
3. FastAPI Backend on port 8000

All services are configured for debug logging.

.EXAMPLE
./debug_build.ps1
#>

param(
    [switch]$NoBrokers,  # Skip broker startup (if already running)
    [switch]$BackendOnly, # Only start backend
    [int]$SSTPort = 9082,
    [int]$TTSPort = 8080,
    [int]$BackendPort = 8000
)

$ErrorActionPreference = "Stop"
$DebugPreference = "Continue"

# Colors for output
$Green = "`e[32m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Red = "`e[31m"
$Reset = "`e[0m"

function Write-Header {
    param([string]$Message)
    Write-Host "`n$Blue===================================================$Reset" -ForegroundColor Blue
    Write-Host "$Blue$Message$Reset" -ForegroundColor Blue
    Write-Host "$Blue===================================================$Reset`n" -ForegroundColor Blue
}

function Write-Step {
    param([string]$Message)
    Write-Host "$Green✓$Reset $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "$Yellow⚠$Reset $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "$Red✗$Reset $Message" -ForegroundColor Red
}

function Test-Service {
    param([string]$Url, [string]$Name)
    
    try {
        $response = Invoke-WebRequest -Uri $Url -TimeoutSec 2 -ErrorAction Stop
        Write-Step "$Name is responding (${Url})"
        return $true
    }
    catch {
        Write-Warn "$Name is not responding (${Url})"
        return $false
    }
}

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Join-Path $ScriptDir "..\..\.."

Write-Header "Voice Chat Debug Build & Run"

# Check Python installation
Write-Host "Checking prerequisites..."
$Python = (Get-Command python -ErrorAction SilentlyContinue)
if (-not $Python) {
    Write-Error "Python not found. Please install Python 3.10+"
    exit 1
}
Write-Step "Python: $($Python.Source)"

# Show configuration
Write-Host "`nConfiguration:"
Write-Host "  SST Broker Port: $SSTPort"
Write-Host "  TTS Broker Port: $TTSPort"
Write-Host "  Backend Port: $BackendPort`n"

# ============================================================================
# Start SST Broker (unless disabled)
# ============================================================================

if (-not $NoBrokers -and -not $BackendOnly) {
    Write-Header "Starting SST Broker (Whisper.cpp)"
    Write-Host "Location: SST/publicip_server_whisper_sst.py"
    Write-Host "Command: python publicip_server_whisper_sst.py --port $SSTPort --log-level DEBUG`n"
    
    Push-Location "$ProjectRoot/SST"
    
    # Start in a new window or background job
    $sstJob = Start-Process -FilePath python `
        -ArgumentList @("publicip_server_whisper_sst.py", "--port", $SSTPort, "--log-level", "DEBUG") `
        -PassThru `
        -NoNewWindow
    
    Write-Step "SST Broker started (PID: $($sstJob.Id))"
    Start-Sleep -Seconds 2
    
    Pop-Location
}

# ============================================================================
# Start TTS Broker (unless disabled)
# ============================================================================

if (-not $NoBrokers -and -not $BackendOnly) {
    Write-Header "Starting TTS Broker (Kokoro)"
    Write-Host "Location: TTS/publicip_server_kokoro_tts.py"
    Write-Host "Command: python publicip_server_kokoro_tts.py --port $TTSPort --log-level DEBUG`n"
    
    Push-Location "$ProjectRoot/TTS"
    
    $ttsJob = Start-Process -FilePath python `
        -ArgumentList @("publicip_server_kokoro_tts.py", "--port", $TTSPort, "--log-level", "DEBUG") `
        -PassThru `
        -NoNewWindow
    
    Write-Step "TTS Broker started (PID: $($ttsJob.Id))"
    Start-Sleep -Seconds 2
    
    Pop-Location
}

# ============================================================================
# Start FastAPI Backend
# ============================================================================

Write-Header "Starting FastAPI Backend"
Write-Host "Location: Hackathon/prompt-portal/backend"
Write-Host "Command: uvicorn app.main:app --host 0.0.0.0 --port $BackendPort --reload --log-level debug`n"

Push-Location "$ProjectRoot/Hackathon/prompt-portal/backend"

# Load debug environment variables
if (Test-Path ".env.debug") {
    Write-Step "Loading debug environment variables from .env.debug"
    Get-Content .env.debug | Where-Object { $_ -and -not $_.StartsWith('#') } | ForEach-Object {
        $key, $value = $_ -split '=', 2
        [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim())
    }
}

# Run backend with debug logging
Write-Step "Starting backend server..."
Write-Host "$Green================================================================$Reset"
Write-Host "$Green Backend Server is Running                                   $Reset"
Write-Host "$Green Open: http://localhost:$BackendPort/docs (API docs)        $Reset"
Write-Host "$Green Open: http://localhost:$BackendPort/redoc (ReDoc)          $Reset"
Write-Host "$Green================================================================$Reset`n"

python -m uvicorn app.main:app `
    --host 0.0.0.0 `
    --port $BackendPort `
    --reload `
    --log-level debug

Pop-Location

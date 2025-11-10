# Quick fix deployment script for SSE mode maze game issue
# PowerShell version for Windows

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Maze Game SSE Mode Fix - Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running in backend directory
if (-not (Test-Path "app/main.py")) {
    Write-Host "❌ Error: Must run from backend directory" -ForegroundColor Red
    Write-Host "   cd to: prompt-portal\backend" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Running in backend directory" -ForegroundColor Green
Write-Host ""

# Check .env configuration
Write-Host "Checking configuration..." -ForegroundColor Cyan
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    
    # Parse LLM_COMM_MODE
    if ($envContent -match 'LLM_COMM_MODE\s*=\s*["\']?([^"\'\r\n]+)') {
        $commMode = $matches[1].Trim()
        if ($commMode -ne "sse" -and $commMode -ne "SSE") {
            Write-Host "⚠️  Warning: LLM_COMM_MODE is not set to 'sse'" -ForegroundColor Yellow
            Write-Host "   Current value: $commMode" -ForegroundColor Yellow
            Write-Host "   This fix is specifically for SSE mode" -ForegroundColor Yellow
            $continue = Read-Host "   Continue anyway? (y/n)"
            if ($continue -ne "y" -and $continue -ne "Y") {
                exit 1
            }
        } else {
            Write-Host "✅ LLM_COMM_MODE=sse" -ForegroundColor Green
        }
    }
    
    # Parse LLM_SERVER_URL
    if ($envContent -match 'LLM_SERVER_URL\s*=\s*["\']?([^"\'\r\n]+)') {
        $serverUrl = $matches[1].Trim()
        Write-Host "✅ LLM_SERVER_URL=$serverUrl" -ForegroundColor Green
        
        # Test connectivity
        Write-Host ""
        Write-Host "Testing llama.cpp server connectivity..." -ForegroundColor Cyan
        try {
            $response = Invoke-WebRequest -Uri "$serverUrl/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop
            Write-Host "✅ llama.cpp server is reachable" -ForegroundColor Green
        } catch {
            Write-Host "⚠️  Warning: Cannot reach llama.cpp server at $serverUrl" -ForegroundColor Yellow
            Write-Host "   Make sure:" -ForegroundColor Yellow
            Write-Host "   1. SSH tunnel is active: ssh -R 8080:127.0.0.1:8080 root@vpn.agaii.org -N" -ForegroundColor Yellow
            Write-Host "   2. llama-server is running on the 4090 machine" -ForegroundColor Yellow
            $continue = Read-Host "   Continue anyway? (y/n)"
            if ($continue -ne "y" -and $continue -ne "Y") {
                exit 1
            }
        }
    } else {
        Write-Host "⚠️  Warning: LLM_SERVER_URL not set" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️  Warning: .env file not found" -ForegroundColor Yellow
    Write-Host "   Make sure configuration is set via environment variables" -ForegroundColor Yellow
}

Write-Host ""

# Find running backend processes
Write-Host "Checking for running backend processes..." -ForegroundColor Cyan
$backendProcesses = Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*uvicorn*app.main:app*"
}

if ($backendProcesses) {
    Write-Host "Found running backend process(es): $($backendProcesses.Id -join ', ')" -ForegroundColor Yellow
    $stop = Read-Host "Stop existing backend? (y/n)"
    if ($stop -eq "y" -or $stop -eq "Y") {
        Write-Host "Stopping backend processes..." -ForegroundColor Yellow
        $backendProcesses | Stop-Process -Force
        Start-Sleep -Seconds 2
        Write-Host "✅ Backend stopped" -ForegroundColor Green
    }
} else {
    Write-Host "No running backend found" -ForegroundColor Gray
}

Write-Host ""

# Start backend
Write-Host "Starting backend with SSE mode fix..." -ForegroundColor Cyan
Write-Host "Command: uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload" -ForegroundColor Gray
Write-Host ""
Write-Host "📝 Watch for these log messages:" -ForegroundColor Cyan
Write-Host "   - 'UnifiedLLMService initialized in SSE mode'" -ForegroundColor Gray
Write-Host "   - '[SSE MODE] Auto-generating hint for publish_state'" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Yellow
Write-Host ""
Start-Sleep -Seconds 2

# Start with reload for development
& uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload

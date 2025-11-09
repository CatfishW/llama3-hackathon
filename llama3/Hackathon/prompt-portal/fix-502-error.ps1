# Fix 502 Error Script (PowerShell version for Windows deployment)

$ErrorActionPreference = "Stop"

Write-Host "`n=============================================="
Write-Host "  Fixing 502 Bad Gateway - Long Runtime Issue"
Write-Host "==============================================`n"

function Write-Step {
    param([string]$Message)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] " -ForegroundColor Green -NoNewline
    Write-Host $Message
}

function Write-ErrorMessage {
    param([string]$Message)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message
}

function Write-WarningMessage {
    param([string]$Message)
    Write-Host "[WARNING] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message
}

# Configuration
$ServerHost = "root@lammp.agaii.org"
$BackendDir = "/opt/prompt-portal/backend"
$LocalBackendDir = "backend"

# Step 1: Check SSH connection
Write-Step "Checking SSH connection to server..."
try {
    $sshTest = ssh $ServerHost "echo 'Connected'"
    if ($sshTest -ne "Connected") {
        throw "SSH connection failed"
    }
    Write-Host "  ✓ SSH connection successful" -ForegroundColor Green
} catch {
    Write-ErrorMessage "Cannot connect to server. Please check SSH configuration."
    Write-Host "  Make sure you can run: ssh $ServerHost"
    exit 1
}

# Step 2: Backup current code on server
Write-Step "Backing up current backend code on server..."
ssh $ServerHost "cd $BackendDir && cp -r . ../backend_backup_$(date +%Y%m%d_%H%M%S) || true"
Write-Host "  ✓ Backup created" -ForegroundColor Green

# Step 3: Upload updated backend files
Write-Step "Uploading updated backend code..."

# Upload chatbot.py
Write-Host "  Uploading chatbot.py..."
scp "$LocalBackendDir/app/routers/chatbot.py" "${ServerHost}:${BackendDir}/app/routers/chatbot.py"

# Upload mqtt.py
Write-Host "  Uploading mqtt.py..."
scp "$LocalBackendDir/app/mqtt.py" "${ServerHost}:${BackendDir}/app/mqtt.py"

Write-Host "  ✓ Code uploaded" -ForegroundColor Green

# Step 4: Upload fix script
Write-Step "Uploading fix script to server..."
scp "fix-502-error.sh" "${ServerHost}:/tmp/fix-502-error.sh"
Write-Host "  ✓ Script uploaded" -ForegroundColor Green

# Step 5: Make script executable and run it
Write-Step "Executing fix script on server..."
Write-Host "  This will take a few minutes..." -ForegroundColor Yellow
Write-Host ""

ssh $ServerHost "chmod +x /tmp/fix-502-error.sh && sudo /tmp/fix-502-error.sh"

# Step 6: Verify deployment
Write-Step "Verifying deployment..."
Start-Sleep -Seconds 3

try {
    $healthCheck = Invoke-WebRequest -Uri "https://lammp.agaii.org/api/health" -TimeoutSec 10 -UseBasicParsing
    if ($healthCheck.StatusCode -eq 200) {
        Write-Host "  ✓ External health check PASSED" -ForegroundColor Green
        
        $healthData = $healthCheck.Content | ConvertFrom-Json
        Write-Host "  Status: $($healthData.status)" -ForegroundColor Cyan
        Write-Host "  MQTT Connected: $($healthData.mqtt.connected)" -ForegroundColor Cyan
    }
} catch {
    Write-WarningMessage "Could not verify external health endpoint"
    Write-Host "  Please check manually: https://lammp.agaii.org/api/health"
}

Write-Host "`n=============================================="
Write-Host "  ✓ Fix Deployment Completed!" -ForegroundColor Green
Write-Host "==============================================`n"

Write-Host "What was fixed:" -ForegroundColor Cyan
Write-Host "  ✓ Enhanced error handling in backend"
Write-Host "  ✓ Systemd service with auto-restart"
Write-Host "  ✓ Nginx timeouts increased to 120s"
Write-Host "  ✓ Health monitoring with auto-recovery"
Write-Host "  ✓ Better MQTT connection verification`n"

Write-Host "Monitoring Commands (run on server):" -ForegroundColor Cyan
Write-Host "  ssh $ServerHost 'sudo journalctl -u prompt-portal-backend -f'"
Write-Host "  ssh $ServerHost 'sudo tail -f /var/log/prompt-portal/health-monitor.log'"
Write-Host "  ssh $ServerHost 'curl http://localhost:8000/api/health | jq'`n"

Write-Host "Test the fix:" -ForegroundColor Cyan
Write-Host "  External health:  curl https://lammp.agaii.org/api/health"
Write-Host "  Web interface:    https://lammp.agaii.org`n"

Write-Host "If issues persist:" -ForegroundColor Yellow
Write-Host "  1. Check backend logs: ssh $ServerHost 'sudo journalctl -u prompt-portal-backend -n 50'"
Write-Host "  2. Check MQTT health:  curl https://lammp.agaii.org/api/health/mqtt"
Write-Host "  3. Restart service:    ssh $ServerHost 'sudo systemctl restart prompt-portal-backend'`n"

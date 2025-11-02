# Restart Backend to Fix 405 Method Not Allowed for Driving Game Endpoints
# The routes are defined correctly but the server needs to be restarted

Write-Host "======================================" -ForegroundColor Cyan
Write-Host "Restarting Backend for Driving Endpoints Fix" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Find Python processes running the backend
Write-Host "[1/3] Finding backend Python processes..." -ForegroundColor Yellow
$backendProcesses = Get-Process python -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -like "*prompt-portal*backend*"
}

if ($backendProcesses) {
    Write-Host "Found $($backendProcesses.Count) backend process(es):" -ForegroundColor Green
    $backendProcesses | ForEach-Object {
        Write-Host "  - PID: $($_.Id), Path: $($_.Path)" -ForegroundColor Gray
    }
    
    Write-Host "`n[2/3] Stopping backend processes..." -ForegroundColor Yellow
    $backendProcesses | Stop-Process -Force
    Write-Host "Backend processes stopped." -ForegroundColor Green
    Start-Sleep -Seconds 2
} else {
    Write-Host "No backend processes found. May not be running or running under different name." -ForegroundColor Yellow
}

Write-Host "`n[3/3] Starting backend with updated code..." -ForegroundColor Yellow
Write-Host ""
Write-Host "To start the backend, run ONE of these commands:" -ForegroundColor Cyan
Write-Host ""
Write-Host "Option 1 (Recommended):" -ForegroundColor Green
Write-Host "  cd Hackathon\prompt-portal\backend" -ForegroundColor White
Write-Host "  python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000" -ForegroundColor White
Write-Host ""
Write-Host "Option 2 (If using deploy script):" -ForegroundColor Green  
Write-Host "  cd Hackathon\prompt-portal" -ForegroundColor White
Write-Host "  .\deploy.sh restart-backend" -ForegroundColor White
Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "What Was Fixed:" -ForegroundColor Yellow
Write-Host "  ✓ Added /api/driving/leaderboard (GET) endpoint" -ForegroundColor Green
Write-Host "  ✓ Added /api/driving/stats (GET) endpoint" -ForegroundColor Green
Write-Host "  ✓ These are properly separated from maze game" -ForegroundColor Green
Write-Host ""
Write-Host "After restart, test at:" -ForegroundColor Yellow
Write-Host "  https://lammp.agaii.org/api/driving/leaderboard" -ForegroundColor White
Write-Host "  https://lammp.agaii.org/api/driving/stats" -ForegroundColor White
Write-Host "======================================" -ForegroundColor Cyan


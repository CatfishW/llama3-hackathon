# Complete fix for https://lammp.agaii.org deployment
# This script fixes both backend CORS and frontend configuration

Write-Host "🔧 Fixing deployment for https://lammp.agaii.org..." -ForegroundColor Cyan
Write-Host ""

$ROOT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ROOT_DIR

# Step 1: Fix Backend CORS
Write-Host "📡 Step 1: Configuring backend CORS..." -ForegroundColor Yellow
Set-Location backend

if (-not (Test-Path .env)) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item .env.example .env
}

# Backup existing .env
Write-Host "Backing up current .env..."
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item .env ".env.backup.$timestamp"

# Set comprehensive CORS origins
$CORS_ORIGINS = "https://lammp.agaii.org,http://lammp.agaii.org,https://lammp.agaii.org/api,http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:5173,http://127.0.0.1:5173"

Write-Host "Updating CORS_ORIGINS..."
$envContent = Get-Content .env -Raw
if ($envContent -match 'CORS_ORIGINS=') {
    $envContent = $envContent -replace 'CORS_ORIGINS=.*', "CORS_ORIGINS=$CORS_ORIGINS"
} else {
    $envContent += "`nCORS_ORIGINS=$CORS_ORIGINS"
}
Set-Content .env $envContent

Write-Host "✓ Backend CORS configured" -ForegroundColor Green
Write-Host ""

# Step 2: Fix Frontend Configuration
Write-Host "🎨 Step 2: Configuring frontend API endpoints..." -ForegroundColor Yellow
Set-Location ..\frontend

# Create production environment files
@"
VITE_API_BASE=https://lammp.agaii.org/api
VITE_WS_BASE=wss://lammp.agaii.org/api
"@ | Set-Content .env.production

@"
VITE_API_BASE=https://lammp.agaii.org/api
VITE_WS_BASE=wss://lammp.agaii.org/api
"@ | Set-Content .env.local

Write-Host "✓ Frontend environment configured" -ForegroundColor Green
Write-Host ""

# Step 3: Rebuild Frontend
Write-Host "🏗️  Step 3: Rebuilding frontend..." -ForegroundColor Yellow
npm run build

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Frontend built successfully" -ForegroundColor Green
} else {
    Write-Host "❌ Frontend build failed" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 4: Restart Backend
Write-Host "🔄 Step 4: Restarting backend..." -ForegroundColor Yellow
Set-Location ..\backend

# Stop existing backend
if (Test-Path backend.pid) {
    $PID = Get-Content backend.pid -ErrorAction SilentlyContinue
    if ($PID) {
        Stop-Process -Id $PID -Force -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
    }
    Remove-Item backend.pid -ErrorAction SilentlyContinue
}

# Kill any process on port 3000
Get-NetTCPConnection -LocalPort 3000 -ErrorAction SilentlyContinue | 
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 1

# Start backend
Write-Host "Starting backend on port 3000..."
$process = Start-Process -FilePath "uvicorn" -ArgumentList "app.main:app", "--host", "0.0.0.0", "--port", "3000" -PassThru -WindowStyle Hidden
$process.Id | Set-Content backend.pid

# Wait for backend to be ready
Start-Sleep -Seconds 3

# Check if backend is running
if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
    Write-Host "✓ Backend started (PID: $($process.Id))" -ForegroundColor Green
} else {
    Write-Host "❌ Backend failed to start" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Step 5: Verify Configuration
Write-Host "✅ Step 5: Verifying configuration..." -ForegroundColor Yellow
Set-Location $ROOT_DIR

Write-Host ""
Write-Host "Backend CORS Origins:"
Get-Content backend\.env | Select-String "CORS_ORIGINS=" | ForEach-Object { 
    $_ -replace 'CORS_ORIGINS=', '  ' 
} | Write-Host

Write-Host ""
Write-Host "Frontend API Base:"
Write-Host "  VITE_API_BASE=https://lammp.agaii.org/api"
Write-Host "  VITE_WS_BASE=wss://lammp.agaii.org/api"
Write-Host ""

Write-Host "Backend Status:"
try {
    $response = Invoke-WebRequest -Uri "http://127.0.0.1:3000/docs" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
    Write-Host "  ✓ Backend is responding at http://127.0.0.1:3000" -ForegroundColor Green
} catch {
    Write-Host "  ⚠️  Backend health check failed" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "✅ Deployment Fix Complete!" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Your application should now be accessible at:"
Write-Host "  🌐 https://lammp.agaii.org/" -ForegroundColor Cyan
Write-Host "  🔗 API: https://lammp.agaii.org/api" -ForegroundColor Cyan
Write-Host "  📚 API Docs: https://lammp.agaii.org/api/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Open https://lammp.agaii.org/ in your browser"
Write-Host "2. Clear browser cache (Ctrl+Shift+Delete)"
Write-Host "3. Try logging in"
Write-Host ""
Write-Host "If issues persist:"
Write-Host "  - Check browser console (F12) for errors"
Write-Host "  - Verify the backend is accessible"
Write-Host "  - Check that Nginx is properly configured on the server"
Write-Host ""
Write-Host "Press any key to continue..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

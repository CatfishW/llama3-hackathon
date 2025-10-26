# Deploy WebSocket Fix to Server
# This PowerShell script uploads and runs the fix on your server

$ErrorActionPreference = "Stop"

Write-Host "🚀 Deploying WebSocket Fix to lammp.agaii.org" -ForegroundColor Green
Write-Host ""

# Configuration
$SERVER = "root@lammp.agaii.org"
$LOCAL_FIX_SCRIPT = "fix-websocket.sh"
$REMOTE_PATH = "~/prompt-portal/"

# Check if SSH is available
try {
    ssh -V 2>&1 | Out-Null
} catch {
    Write-Host "❌ SSH not found. Please install OpenSSH or use WSL." -ForegroundColor Red
    Write-Host ""
    Write-Host "To install OpenSSH on Windows:" -ForegroundColor Yellow
    Write-Host "  Settings > Apps > Optional Features > Add OpenSSH Client" -ForegroundColor Yellow
    exit 1
}

# Check if the fix script exists
if (-not (Test-Path $LOCAL_FIX_SCRIPT)) {
    Write-Host "❌ Fix script not found: $LOCAL_FIX_SCRIPT" -ForegroundColor Red
    Write-Host "Make sure you're in the prompt-portal directory" -ForegroundColor Yellow
    exit 1
}

Write-Host "📤 Uploading fix script to server..." -ForegroundColor Cyan
try {
    scp "$LOCAL_FIX_SCRIPT" "${SERVER}:${REMOTE_PATH}"
    Write-Host "✓ Upload successful" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to upload script" -ForegroundColor Red
    Write-Host "Make sure you can SSH to the server: ssh $SERVER" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "🔧 Running fix script on server..." -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""

# Run the fix script on the server
ssh "$SERVER" "cd $REMOTE_PATH && chmod +x $LOCAL_FIX_SCRIPT && bash $LOCAL_FIX_SCRIPT"

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Gray
Write-Host ""
Write-Host "✅ WebSocket fix deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "  1. Clear your browser cache (Ctrl+Shift+R)" -ForegroundColor White
Write-Host "  2. Reload https://lammp.agaii.org" -ForegroundColor White
Write-Host "  3. Check browser console for WebSocket connection status" -ForegroundColor White
Write-Host ""
Write-Host "To verify the fix worked:" -ForegroundColor Yellow
Write-Host "  • Open DevTools (F12) → Console" -ForegroundColor White
Write-Host "  • Should NOT see: 'WebSocket connection to wss://... failed'" -ForegroundColor White
Write-Host "  • Should see: WebSocket connection established" -ForegroundColor White
Write-Host ""
Write-Host "To check server logs:" -ForegroundColor Yellow
Write-Host "  ssh $SERVER" -ForegroundColor Cyan
Write-Host "  sudo tail -f /var/log/nginx/error.log" -ForegroundColor Cyan
Write-Host ""

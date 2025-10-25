# PowerShell script to deploy the routing fix to the server
# Run this from your local machine

param(
    [string]$ServerIP = "your.server.ip.here",
    [string]$ServerUser = "root",
    [string]$ServerPath = "/root/prompt-portal"
)

Write-Host "🚀 Deploying Routing Fix to Prompt Portal" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""

# Check if plink is available (PuTTY)
$hasPlink = Get-Command plink -ErrorAction SilentlyContinue
$hasPscp = Get-Command pscp -ErrorAction SilentlyContinue

if (-not $hasPlink -or -not $hasPscp) {
    Write-Host "⚠️  PuTTY tools (plink/pscp) not found in PATH" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please install PuTTY or use one of these alternatives:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "OPTION 1: Manual Copy via Git" -ForegroundColor Cyan
    Write-Host "  1. Commit and push the changes:" -ForegroundColor White
    Write-Host "     git add ." -ForegroundColor Gray
    Write-Host "     git commit -m 'Fix routing issues'" -ForegroundColor Gray
    Write-Host "     git push" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  2. On the server, pull the changes:" -ForegroundColor White
    Write-Host "     cd $ServerPath" -ForegroundColor Gray
    Write-Host "     git pull" -ForegroundColor Gray
    Write-Host "     chmod +x fix-routing-complete.sh" -ForegroundColor Gray
    Write-Host "     bash fix-routing-complete.sh" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "OPTION 2: Use SCP (if you have Git Bash or WSL)" -ForegroundColor Cyan
    Write-Host "  In Git Bash or WSL, run:" -ForegroundColor White
    Write-Host "  scp fix-routing-complete.sh ${ServerUser}@${ServerIP}:${ServerPath}/" -ForegroundColor Gray
    Write-Host "  ssh ${ServerUser}@${ServerIP}" -ForegroundColor Gray
    Write-Host "  cd $ServerPath" -ForegroundColor Gray
    Write-Host "  chmod +x fix-routing-complete.sh" -ForegroundColor Gray
    Write-Host "  bash fix-routing-complete.sh" -ForegroundColor Gray
    Write-Host ""
    
    Write-Host "OPTION 3: Copy-Paste the fix script" -ForegroundColor Cyan
    Write-Host "  1. Open fix-routing-complete.sh in an editor" -ForegroundColor White
    Write-Host "  2. Copy all contents" -ForegroundColor White
    Write-Host "  3. SSH to server: ssh ${ServerUser}@${ServerIP}" -ForegroundColor Gray
    Write-Host "  4. Create file: nano $ServerPath/fix-routing-complete.sh" -ForegroundColor Gray
    Write-Host "  5. Paste contents, save (Ctrl+O, Enter, Ctrl+X)" -ForegroundColor Gray
    Write-Host "  6. Make executable: chmod +x fix-routing-complete.sh" -ForegroundColor Gray
    Write-Host "  7. Run: bash fix-routing-complete.sh" -ForegroundColor Gray
    Write-Host ""
    
    exit
}

# Verify server details
if ($ServerIP -eq "your.server.ip.here") {
    Write-Host "❌ Error: Please set the server IP address" -ForegroundColor Red
    Write-Host ""
    Write-Host "Usage:" -ForegroundColor Yellow
    Write-Host "  .\deploy-routing-fix.ps1 -ServerIP '1.2.3.4' -ServerUser 'root' -ServerPath '/root/prompt-portal'" -ForegroundColor Gray
    Write-Host ""
    exit
}

Write-Host "Server: $ServerUser@$ServerIP" -ForegroundColor Cyan
Write-Host "Path: $ServerPath" -ForegroundColor Cyan
Write-Host ""

# Get the current directory
$currentDir = Get-Location
$fixScript = Join-Path $currentDir "Hackathon\prompt-portal\fix-routing-complete.sh"

if (-not (Test-Path $fixScript)) {
    Write-Host "❌ Error: fix-routing-complete.sh not found at: $fixScript" -ForegroundColor Red
    exit
}

Write-Host "📤 Uploading fix script to server..." -ForegroundColor Yellow
pscp -batch $fixScript "${ServerUser}@${ServerIP}:${ServerPath}/fix-routing-complete.sh"

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to upload file" -ForegroundColor Red
    exit
}

Write-Host "✅ File uploaded successfully" -ForegroundColor Green
Write-Host ""
Write-Host "🔧 Running fix script on server..." -ForegroundColor Yellow

plink -batch "${ServerUser}@${ServerIP}" "cd $ServerPath && chmod +x fix-routing-complete.sh && bash fix-routing-complete.sh"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ Fix applied successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Clear browser cache (Ctrl+Shift+R)" -ForegroundColor White
    Write-Host "  2. Visit https://lammp.agaii.org" -ForegroundColor White
    Write-Host "  3. Check browser console - URLs should be /api/... not /api/api/..." -ForegroundColor White
} else {
    Write-Host ""
    Write-Host "❌ Fix script encountered errors" -ForegroundColor Red
    Write-Host "Please check the output above for details" -ForegroundColor Yellow
}

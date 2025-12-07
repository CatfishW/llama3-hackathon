#!/usr/bin/env powershell
<#
.SYNOPSIS
Voice Chat Configuration Verification Script
Tests connectivity and configuration for SST and TTS services

.DESCRIPTION
Verifies that the backend can reach the SST and TTS services at:
- SST: http://173.61.35.162:25567
- TTS: http://173.61.35.162:25566
#>

$ErrorActionPreference = "Continue"

# Colors
$Green = "`e[32m"
$Red = "`e[31m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Reset = "`e[0m"

function Write-Status {
    param([string]$Message, [bool]$Success)
    if ($Success) {
        Write-Host "$Green✓$Reset $Message" -ForegroundColor Green
    } else {
        Write-Host "$Red✗$Reset $Message" -ForegroundColor Red
    }
}

function Test-Service {
    param([string]$Url, [string]$Name)
    
    Write-Host "`nTesting $Name..."
    Write-Host "URL: $Url"
    
    try {
        $response = Invoke-WebRequest -Uri "$Url/healthz" -TimeoutSec 5 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Status "$Name is responding at $Url" $true
            
            $content = $response.Content | ConvertFrom-Json
            Write-Host "Response:" -ForegroundColor Cyan
            Write-Host ($content | ConvertTo-Json -Depth 3)
            return $true
        }
    } catch {
        Write-Status "$Name is not responding at $Url" $false
        Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Yellow
        return $false
    }
}

Write-Host "`n$Blue========================================$Reset"
Write-Host "$Blue Voice Chat Configuration Verification $Reset"
Write-Host "$Blue========================================$Reset`n"

# Test SST
$sstUrl = "http://173.61.35.162:25567"
$sstHealthy = Test-Service -Url $sstUrl -Name "SST Service (Whisper.cpp)"

# Test TTS
$ttsUrl = "http://173.61.35.162:25566"
$ttsHealthy = Test-Service -Url $ttsUrl -Name "TTS Service (Kokoro)"

# Summary
Write-Host "`n$Blue========================================$Reset"
Write-Host "$Blue Configuration Summary$Reset"
Write-Host "$Blue========================================$Reset`n"

Write-Host "SST (Speech-to-Text):"
Write-Host "  URL:    $sstUrl"
Write-Host "  Status: $(if ($sstHealthy) { 'Connected' } else { 'Not Connected' })" -ForegroundColor $(if ($sstHealthy) { 'Green' } else { 'Red' })

Write-Host "`nTTS (Text-to-Speech):"
Write-Host "  URL:    $ttsUrl"
Write-Host "  Status: $(if ($ttsHealthy) { 'Connected' } else { 'Not Connected' })" -ForegroundColor $(if ($ttsHealthy) { 'Green' } else { 'Red' })

Write-Host "`nBackend Configuration (.env.debug):"
Write-Host "  SST_BROKER_URL=http://173.61.35.162:25567"
Write-Host "  TTS_BROKER_URL=http://173.61.35.162:25566"

# Overall status
Write-Host "`n$Blue========================================$Reset"
if ($sstHealthy -and $ttsHealthy) {
    Write-Host "$Green✓ All services are configured and responding$Reset" -ForegroundColor Green
    Write-Host "Ready to run voice chat pipeline!`n" -ForegroundColor Green
} elseif ($sstHealthy -or $ttsHealthy) {
    Write-Host "$Yellow⚠ Some services are unavailable$Reset" -ForegroundColor Yellow
    Write-Host "Check network connectivity to 173.61.35.162`n" -ForegroundColor Yellow
} else {
    Write-Host "$Red✗ Services are not responding$Reset" -ForegroundColor Red
    Write-Host "1. Check that SST and TTS servers are running`n2. Verify network connectivity to 173.61.35.162:25567 and 173.61.35.162:25566`n3. Check firewall rules`n" -ForegroundColor Red
}

Write-Host "$Blue========================================$Reset`n"

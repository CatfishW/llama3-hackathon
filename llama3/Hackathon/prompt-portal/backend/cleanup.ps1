# Database Cleanup Scripts for LAM Prompt Portal
# PowerShell version

param(
    [Parameter(Mandatory=$true, Position=0)]
    [ValidateSet("stats", "reset", "clean-all", "clean-test", "clean-old", "clean-messages", "clean-friendships")]
    [string]$Action,
    
    [Parameter(Position=1)]
    [int]$Days = 30,
    
    [Parameter()]
    [string]$Status
)

# Change to script directory
Set-Location -Path $PSScriptRoot

Write-Host "🗄️  LAM Prompt Portal Database Cleanup" -ForegroundColor Cyan
Write-Host "=====================================" -ForegroundColor Cyan

switch ($Action) {
    "stats" {
        Write-Host "📊 Showing database statistics..." -ForegroundColor Green
        python clean_database.py --action stats
    }
    "reset" {
        Write-Host "🔄 Quick development reset..." -ForegroundColor Yellow
        python quick_reset.py
    }
    "clean-all" {
        Write-Host "⚠️  WARNING: This will delete ALL data!" -ForegroundColor Red
        python clean_database.py --action clean-all
    }
    "clean-test" {
        Write-Host "🧪 Cleaning test data..." -ForegroundColor Green
        python clean_database.py --action clean-test
    }
    "clean-old" {
        Write-Host "🕒 Cleaning data older than $Days days..." -ForegroundColor Green
        python clean_database.py --action clean-old --days $Days
    }
    "clean-messages" {
        Write-Host "💬 Cleaning messages..." -ForegroundColor Green
        if ($Days -ne 30) {
            python clean_database.py --action clean-messages --days $Days
        } else {
            python clean_database.py --action clean-messages
        }
    }
    "clean-friendships" {
        Write-Host "👥 Cleaning friendships..." -ForegroundColor Green
        if ($Status) {
            python clean_database.py --action clean-friendships --status $Status
        } else {
            python clean_database.py --action clean-friendships
        }
    }
}

Write-Host "`nScript completed!" -ForegroundColor Cyan

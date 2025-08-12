@echo off
REM Database Cleanup Scripts for LAM Prompt Portal
REM 
REM Usage:
REM   cleanup.bat stats          - Show database statistics
REM   cleanup.bat reset          - Quick reset (development)
REM   cleanup.bat clean-all      - Delete all data (DESTRUCTIVE!)
REM   cleanup.bat clean-test     - Delete test data only
REM   cleanup.bat clean-old [days] - Delete old data (default 30 days)

cd /d "%~dp0"

if "%1"=="stats" (
    echo 📊 Showing database statistics...
    python clean_database.py --action stats
    goto end
)

if "%1"=="reset" (
    echo 🔄 Quick development reset...
    python quick_reset.py
    goto end
)

if "%1"=="clean-all" (
    echo ⚠️  WARNING: This will delete ALL data!
    python clean_database.py --action clean-all
    goto end
)

if "%1"=="clean-test" (
    echo 🧪 Cleaning test data...
    python clean_database.py --action clean-test
    goto end
)

if "%1"=="clean-old" (
    set days=30
    if not "%2"=="" set days=%2
    echo 🕒 Cleaning data older than %days% days...
    python clean_database.py --action clean-old --days %days%
    goto end
)

if "%1"=="clean-messages" (
    echo 💬 Cleaning messages...
    python clean_database.py --action clean-messages
    goto end
)

if "%1"=="clean-friendships" (
    echo 👥 Cleaning friendships...
    python clean_database.py --action clean-friendships
    goto end
)

echo.
echo 🗄️  LAM Prompt Portal Database Cleanup
echo =====================================
echo.
echo Available commands:
echo   cleanup.bat stats          - Show database statistics
echo   cleanup.bat reset          - Quick reset (development)
echo   cleanup.bat clean-all      - Delete all data (DESTRUCTIVE!)
echo   cleanup.bat clean-test     - Delete test data only
echo   cleanup.bat clean-old [days] - Delete old data (default 30 days)
echo   cleanup.bat clean-messages - Delete all messages
echo   cleanup.bat clean-friendships - Delete all friendships
echo.
echo Examples:
echo   cleanup.bat stats
echo   cleanup.bat reset
echo   cleanup.bat clean-old 7
echo   cleanup.bat clean-test
echo.

:end
pause

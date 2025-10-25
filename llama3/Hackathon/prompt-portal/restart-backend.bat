@echo off
REM Restart backend server

echo 🔄 Restarting backend server...
echo.

cd /d "%~dp0backend"

REM Stop existing backend
echo Stopping existing backend...
if exist backend.pid (
    set /p BACKEND_PID=<backend.pid
    taskkill /PID %BACKEND_PID% /F >nul 2>&1
    del backend.pid
)

REM Also kill by port
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000') do taskkill /PID %%a /F >nul 2>&1

echo.
echo Starting backend on port 3000...
start /B uvicorn app.main:app --host 0.0.0.0 --port 3000 > nul 2>&1

REM Wait a moment for the process to start
timeout /t 2 /nobreak >nul

REM Try to get the PID (this is approximate on Windows)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do (
    echo %%a > backend.pid
    echo ✓ Backend started with PID: %%a
    goto :found
)

:found
echo.
echo ✓ Backend is running on http://127.0.0.1:3000
echo ✓ API docs at http://127.0.0.1:3000/docs
echo.
echo Testing backend health...
timeout /t 2 /nobreak >nul

curl -s http://127.0.0.1:3000/docs >nul 2>&1
if %errorlevel% == 0 (
    echo ✓ Backend is healthy!
) else (
    echo ⚠️  Backend might still be starting up...
    echo    Wait a few seconds and check http://127.0.0.1:3000/docs
)

echo.
pause

@echo off
REM ============================================================================
REM Llama.cpp Web Server Deployment Script (Windows)
REM ============================================================================
REM
REM Usage:
REM   deploy.bat [install|start|stop|restart|logs|status]
REM
REM Examples:
REM   deploy.bat install          # First-time installation
REM   deploy.bat start            # Start the service
REM   deploy.bat stop             # Stop the service
REM   deploy.bat restart          # Restart the service
REM   deploy.bat logs             # Show logs
REM   deploy.bat status           # Check status
REM

setlocal enabledelayedexpansion

REM Configuration
set "SERVICE_NAME=LlamaCppWebServer"
set "INSTALL_DIR=%CD%\..\llamacppWeb"
set "VENV_DIR=%INSTALL_DIR%\venv"
set "PYTHON_EXEC=%VENV_DIR%\Scripts\python.exe"
set "PIP_EXEC=%VENV_DIR%\Scripts\pip.exe"

REM Colors for output
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

REM ============================================================================
REM Functions
REM ============================================================================

:log_info
echo [INFO] %1
exit /b

:log_success
echo [SUCCESS] %1
exit /b

:log_error
echo [ERROR] %1
exit /b

:log_warning
echo [WARNING] %1
exit /b

REM Check if running as admin
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] This script must be run as Administrator
    echo Please run Command Prompt as Administrator and try again
    pause
    exit /b 1
)

REM ============================================================================
REM Commands
REM ============================================================================

if "%1"=="" goto help
if /i "%1"=="install" goto install
if /i "%1"=="start" goto start_service
if /i "%1"=="stop" goto stop_service
if /i "%1"=="restart" goto restart_service
if /i "%1"=="logs" goto show_logs
if /i "%1"=="status" goto show_status
if /i "%1"=="help" goto help

echo Unknown command: %1
goto help

REM ============================================================================
REM Install Command
REM ============================================================================

:install
echo [INFO] Starting installation...

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.8+ from https://www.python.org/
    pause
    exit /b 1
)

echo [INFO] Creating virtual environment...
if exist "%VENV_DIR%" (
    echo [WARNING] Virtual environment already exists
) else (
    python -m venv "%VENV_DIR%"
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

echo [INFO] Installing Python dependencies...
call "%PIP_EXEC%" install --upgrade pip
if %errorlevel% neq 0 (
    echo [ERROR] Failed to upgrade pip
    pause
    exit /b 1
)

call "%PIP_EXEC%" install -r "%INSTALL_DIR%\requirements.txt"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [INFO] Creating batch runner script...
call :create_runner_script

echo [INFO] Registering Windows service...
call :register_service

echo [SUCCESS] Installation complete!
echo [INFO] To start the server, run: deploy.bat start
pause
exit /b 0

REM ============================================================================
REM Start Service Command
REM ============================================================================

:start_service
echo [INFO] Starting service...

if exist "%INSTALL_DIR%\run.bat" (
    start "Llama.cpp Web Server" cmd /k "%INSTALL_DIR%\run.bat"
    timeout /t 2 /nobreak
    echo [SUCCESS] Service started
    echo Open http://localhost:5000 in your browser
) else (
    echo [ERROR] run.bat not found. Please run 'deploy.bat install' first
)

pause
exit /b 0

REM ============================================================================
REM Stop Service Command
REM ============================================================================

:stop_service
echo [INFO] Stopping service...
taskkill /FI "WINDOWTITLE eq Llama.cpp Web Server*" /T /F
echo [SUCCESS] Service stopped
pause
exit /b 0

REM ============================================================================
REM Restart Service Command
REM ============================================================================

:restart_service
echo [INFO] Restarting service...
call :stop_service
timeout /t 2 /nobreak
call :start_service
exit /b 0

REM ============================================================================
REM Show Logs Command
REM ============================================================================

:show_logs
echo [INFO] Logs are displayed in the server window
echo [INFO] Check %INSTALL_DIR%\logs\ for log files
pause
exit /b 0

REM ============================================================================
REM Show Status Command
REM ============================================================================

:show_status
echo [INFO] Checking service status...
tasklist /FI "WINDOWTITLE eq Llama.cpp Web Server*" 2>NUL | find /I "python.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    echo [SUCCESS] Service is running
) else (
    echo [WARNING] Service is not running
)
pause
exit /b 0

REM ============================================================================
REM Help Command
REM ============================================================================

:help
cls
echo.
echo ============================================================================
echo Llama.cpp Web Server Deployment Script (Windows)
echo ============================================================================
echo.
echo Usage: deploy.bat [COMMAND]
echo.
echo Commands:
echo   install     Install and setup the service
echo   start       Start the service
echo   stop        Stop the service
echo   restart     Restart the service
echo   logs        Show service logs
echo   status      Show service status
echo   help        Show this help message
echo.
echo Examples:
echo   deploy.bat install
echo   deploy.bat start
echo   deploy.bat restart
echo.
echo ============================================================================
echo.
pause
exit /b 0

REM ============================================================================
REM Helper Functions
REM ============================================================================

:create_runner_script
set "RUN_SCRIPT=%INSTALL_DIR%\run.bat"

if exist "%RUN_SCRIPT%" (
    goto :eof
)

(
    echo @echo off
    echo setlocal enabledelayedexpansion
    echo.
    echo set "VENV_DIR=%VENV_DIR%"
    echo set "INSTALL_DIR=%INSTALL_DIR%"
    echo.
    echo REM Activate virtual environment
    echo call "!VENV_DIR!\Scripts\activate.bat"
    echo.
    echo REM Set environment variables
    echo set "FLASK_ENV=production"
    echo set "FLASK_DEBUG=False"
    echo set "HOST=0.0.0.0"
    echo set "PORT=5000"
    echo set "MQTT_BROKER=47.89.252.2"
    echo set "MQTT_PORT=1883"
    echo.
    echo REM Change to install directory
    echo cd /d "!INSTALL_DIR!"
    echo.
    echo REM Start the server
    echo echo [INFO] Starting Llama.cpp Web Server...
    echo echo [INFO] Open http://localhost:5000 in your browser
    echo echo [INFO] Press Ctrl+C to stop the server
    echo python app.py
    echo.
    echo pause
) > "%RUN_SCRIPT%"

exit /b 0

:register_service
REM This creates a scheduled task instead of a Windows service
REM for easier management in Windows

set "TASK_NAME=LlamaCppWebServer"
set "TASK_SCRIPT=%INSTALL_DIR%\run.bat"

REM Check if task already exists
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [WARNING] Scheduled task already exists
) else (
    echo [INFO] Creating scheduled task...
    schtasks /create /tn "%TASK_NAME%" /tr "%TASK_SCRIPT%" /sc onstart /rl highest /f
    if %errorlevel% equ 0 (
        echo [SUCCESS] Scheduled task created
    ) else (
        echo [WARNING] Failed to create scheduled task
    )
)

exit /b 0

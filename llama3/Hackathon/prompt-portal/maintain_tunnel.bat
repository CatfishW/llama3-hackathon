@echo off
REM LLM Server Reverse SSH Tunnel Maintainer (Windows version)
REM This script establishes and maintains a reverse SSH tunnel from your LLM server
REM (Machine A with GPU) to your web server (Machine B with public IP)

SETLOCAL EnableDelayedExpansion

REM ============================================================================
REM CONFIGURATION - Edit these values for your setup
REM ============================================================================

SET REMOTE_USER=lobin
SET REMOTE_HOST=vpn.agaii.org
SET REMOTE_PORT=8080
SET LOCAL_PORT=8080

SET KEEPALIVE_INTERVAL=30
SET KEEPALIVE_MAX=3
SET RECONNECT_DELAY=5

REM ============================================================================

echo ╔════════════════════════════════════════════════════════════╗
echo ║       LLM Server Reverse SSH Tunnel Maintainer            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Check if configuration is default
if "%REMOTE_HOST%"=="your-server-ip" (
    echo [ERROR] Please edit this script and update the CONFIGURATION section!
    echo [INFO] Set REMOTE_USER and REMOTE_HOST to match your web server
    pause
    exit /b 1
)

REM Check if SSH is available
where ssh >nul 2>nul
if errorlevel 1 (
    echo [ERROR] SSH is not available. Please install OpenSSH or use Git Bash.
    echo [INFO] Windows 10/11: Settings ^> Apps ^> Optional Features ^> Add OpenSSH Client
    pause
    exit /b 1
)

REM Check if local LLM server is running
echo [INFO] Checking local LLM server on port %LOCAL_PORT%...
curl -s --max-time 2 http://localhost:%LOCAL_PORT%/health >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Local LLM server not responding on port %LOCAL_PORT%
    echo [WARNING] Make sure llama.cpp server is running before starting tunnel
    set /p CONTINUE="Continue anyway? (y/N): "
    if /i not "!CONTINUE!"=="y" exit /b 1
) else (
    echo [SUCCESS] Local LLM server is running on port %LOCAL_PORT%
)

echo.
echo [INFO] Configuration:
echo   Remote Server: %REMOTE_USER%@%REMOTE_HOST%
echo   Remote Port:   %REMOTE_PORT% (localhost on Machine B)
echo   Local Port:    %LOCAL_PORT% (llama.cpp server)
echo   Keepalive:     %KEEPALIVE_INTERVAL%s interval, %KEEPALIVE_MAX% max failures
echo   Reconnect:     %RECONNECT_DELAY%s delay
echo.

echo [SUCCESS] Tunnel starting...
echo.
echo [INFO] What's happening:
echo   • Your LLM server (localhost:%LOCAL_PORT%) is now accessible on Machine B
echo   • Machine B can connect to http://localhost:%REMOTE_PORT%
echo   • This connection is encrypted and secure
echo.
echo [INFO] To verify on Machine B:
echo   ssh %REMOTE_USER%@%REMOTE_HOST%
echo   curl http://localhost:%REMOTE_PORT%/health
echo.
echo [WARNING] Keep this window open! Closing it will stop the tunnel.
echo.

:TUNNEL_LOOP
SET /a ATTEMPT+=1
echo [INFO] Starting tunnel (attempt #%ATTEMPT%) at %TIME%...
echo [INFO] Forwarding: %REMOTE_HOST%:%REMOTE_PORT% -^> localhost:%LOCAL_PORT%
echo.

REM Start SSH tunnel
ssh -R %REMOTE_PORT%:localhost:%LOCAL_PORT% ^
    -o ServerAliveInterval=%KEEPALIVE_INTERVAL% ^
    -o ServerAliveCountMax=%KEEPALIVE_MAX% ^
    -o ExitOnForwardFailure=yes ^
    -o StrictHostKeyChecking=no ^
    -N ^
    %REMOTE_USER%@%REMOTE_HOST%

SET EXIT_CODE=%ERRORLEVEL%

if %EXIT_CODE%==0 (
    echo [INFO] Tunnel stopped gracefully
    goto :END
)

echo [WARNING] Tunnel disconnected at %TIME% (exit code: %EXIT_CODE%)
echo [INFO] Reconnecting in %RECONNECT_DELAY% seconds...
timeout /t %RECONNECT_DELAY% /nobreak >nul
goto :TUNNEL_LOOP

:END
echo [INFO] Tunnel stopped
pause

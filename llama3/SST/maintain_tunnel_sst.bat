@echo off
REM Whisper.cpp SST Server Reverse SSH Tunnel Maintainer (Windows version)
REM This script establishes and maintains a reverse SSH tunnel from your SST server
REM (Machine A with private IP) to your web server (Machine B with public IP)
REM Enables remote speech-to-text inference on port 8082

SETLOCAL EnableDelayedExpansion

REM ============================================================================
REM CONFIGURATION - Edit these values for your setup
REM ============================================================================

SET REMOTE_USER=lobin
SET REMOTE_HOST=vpn.agaii.org
SET REMOTE_PORT=8082
SET LOCAL_PORT=8082

SET KEEPALIVE_INTERVAL=30
SET KEEPALIVE_MAX=3
SET RECONNECT_DELAY=5

REM ============================================================================

echo ╔════════════════════════════════════════════════════════════╗
echo ║      Whisper.cpp SST Reverse SSH Tunnel Maintainer        ║
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

REM Check if local SST server is running
echo [INFO] Checking local Whisper.cpp SST server on port %LOCAL_PORT%...
curl -s --max-time 2 http://127.0.0.1:%LOCAL_PORT%/ >nul 2>nul
if errorlevel 1 (
    echo [WARNING] Local SST server not responding on port %LOCAL_PORT%
    echo [WARNING] Make sure whisper.cpp server is running before starting tunnel
    set /p CONTINUE="Continue anyway? (y/N): "
    if /i not "!CONTINUE!"=="y" exit /b 1
) else (
    echo [SUCCESS] Local Whisper.cpp SST server is running on port %LOCAL_PORT%
)

echo.
echo [INFO] Configuration:
echo   Remote Server: %REMOTE_USER%@%REMOTE_HOST%
echo   Remote Port:   %REMOTE_PORT% (127.0.0.1 on Machine B)
echo   Local Port:    %LOCAL_PORT% (whisper.cpp SST server)
echo   Keepalive:     %KEEPALIVE_INTERVAL%s interval, %KEEPALIVE_MAX% max failures
echo   Reconnect:     %RECONNECT_DELAY%s delay
echo.

echo [SUCCESS] Tunnel starting...
echo.
echo [INFO] What's happening:
echo   • Your SST server (127.0.0.1:%LOCAL_PORT%) is now accessible on Machine B
echo   • Machine B can connect to http://127.0.0.1:%REMOTE_PORT%
echo   • Speech-to-text inference is available remotely on port %REMOTE_PORT%
echo   • This connection is encrypted and secure
echo.
echo [INFO] To verify on Machine B:
echo   ssh %REMOTE_USER%@%REMOTE_HOST%
echo   curl http://127.0.0.1:%REMOTE_PORT%/
echo.
echo [INFO] To use remote SST service:
echo   curl 127.0.0.1:%REMOTE_PORT%/inference \
echo     -H "Content-Type: multipart/form-data" \
echo     -F file="@audio.wav" \
echo     -F temperature="0.0" \
echo     -F response_format="json"
echo.
echo [WARNING] Keep this window open! Closing it will stop the tunnel.
echo.

:TUNNEL_LOOP
SET /a ATTEMPT+=1
echo [INFO] Starting tunnel (attempt #%ATTEMPT%) at %TIME%...
echo [INFO] Forwarding: %REMOTE_HOST%:%REMOTE_PORT% -^> 127.0.0.1:%LOCAL_PORT%
echo.

REM Start SSH tunnel
ssh -R %REMOTE_PORT%:127.0.0.1:%LOCAL_PORT% ^
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

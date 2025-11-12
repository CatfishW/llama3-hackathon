@echo off
setlocal EnableDelayedExpansion

echo ====================================
echo Llama Server Auto-Restart Script
echo ====================================
echo.
echo This script will keep llama-server running.
echo If it crashes or exits, it will automatically restart.
echo Press Ctrl+C to stop this script permanently.
echo.
echo ====================================

set "SERVER_PATH=D:/llama.cpp/build/bin/Debug/llama-server"
set "MODEL_PATH=Qwen3-Coder-30B-A3B-Instruct-1M-UD-Q3_K_XL.gguf"
@REM set "MODEL_PATH=gpt-oss-20b-F16.gguf"
@REM set "MODEL_PATH=Qwen3-Coder-30B-A3B-Instruct-1M-UD-TQ1_0.gguf"
set "HOST=0.0.0.0"
set "PORT=8080"
set "CONTEXT_SIZE=18312"
set "GPU_LAYERS=80"
set "THREADS=6"
set "PARALLEL=2"


:restart_loop
echo.
echo [%date% %time%] Starting llama-server...
echo.

"%SERVER_PATH%" -m "%MODEL_PATH%" --host %HOST% --port %PORT% -c %CONTEXT_SIZE% -ngl %GPU_LAYERS% -t %THREADS% --parallel %PARALLEL% --flash-attn on

set EXIT_CODE=%ERRORLEVEL%

echo.
echo [%date% %time%] llama-server exited with code: %EXIT_CODE%
echo.

if %EXIT_CODE% EQU 0 (
    echo Server stopped normally.
) else (
    echo Server crashed or encountered an error!
)

echo Waiting 3 seconds before restarting...
timeout /t 3 /nobreak >nul

goto restart_loop

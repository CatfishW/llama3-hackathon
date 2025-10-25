@echo off
REM Quick Setup Script for LLM Integration (Windows)

echo =========================================
echo Prompt Portal LLM Integration Setup
echo =========================================
echo.

REM Check if we're in the right directory
if not exist "backend\requirements.txt" (
    echo Error: Must run from prompt-portal directory
    echo Current directory: %CD%
    exit /b 1
)

REM Install backend dependencies
echo Installing backend dependencies...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install dependencies
    exit /b 1
)
echo Dependencies installed
echo.

REM Setup environment file
if not exist ".env" (
    echo Creating .env file from template...
    copy .env.example .env
    echo Created .env file
    echo Please edit backend\.env and set your LLM_SERVER_URL
) else (
    echo .env file already exists
)
echo.

REM Check if LLM server is configured
echo Checking LLM configuration...
findstr /C:"LLM_SERVER_URL=http://localhost:8080" .env >nul 2>&1
if %errorlevel% equ 0 (
    echo Using default LLM_SERVER_URL (http://localhost:8080^)
    echo Edit backend\.env if your server is on a different URL
)
echo.

REM Test LLM server connectivity
echo Testing LLM server connectivity...
curl -s --max-time 2 "http://localhost:8080/health" >nul 2>&1
if %errorlevel% equ 0 (
    echo LLM server is accessible at http://localhost:8080
) else (
    echo Cannot connect to LLM server at http://localhost:8080
    echo.
    echo To start a local llama.cpp server:
    echo   llama-server -m .\your-model.gguf --port 8080
    echo.
    echo Or use the MQTT deployment script:
    echo   cd ..\..
    echo   python llamacpp_mqtt_deploy.py --projects prompt_portal
)
echo.

echo =========================================
echo Setup Complete!
echo =========================================
echo.
echo Next steps:
echo 1. Make sure your LLM server is running
echo 2. Start the backend:
echo    cd backend
echo    python run_server.py
echo.
echo 3. Test the API:
echo    curl http://localhost:8000/api/llm/health
echo.
echo 4. See LLM_INTEGRATION_GUIDE.md for usage examples
echo.

cd ..
pause

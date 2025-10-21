@echo off
echo ====================================
echo Blood Racing Game - Client Launcher
echo ====================================
echo.

REM Check if PyQt5 is installed
python -c "import PyQt5" 2>nul
if errorlevel 1 (
    echo PyQt5 is not installed. Installing now...
    pip install -r requirements_client.txt
    if errorlevel 1 (
        echo Failed to install requirements!
        pause
        exit /b 1
    )
)

echo Starting Racing Game Client...
echo.
echo Make sure the MQTT server is running first!
echo.

python racing_game_client.py

if errorlevel 1 (
    echo.
    echo Client exited with error!
    pause
)

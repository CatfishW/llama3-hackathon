@echo off
REM Fix script for frontend build issues with TAB completion

echo 🔧 Fixing frontend build issues for TAB completion...

REM Navigate to frontend directory
cd Hackathon\prompt-portal\frontend

REM Check if node_modules exists
if not exist "node_modules" (
    echo 📦 Installing dependencies...
    npm install
)

REM Check if MQTT is properly installed
npm list mqtt >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing MQTT dependency...
    npm install mqtt@^5.3.4
)

REM Check if MQTT types are installed
npm list @types/mqtt >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing MQTT types...
    npm install @types/mqtt@^2.5.5 --save-dev
)

REM Check if terser is installed
npm list terser >nul 2>&1
if errorlevel 1 (
    echo 📦 Installing terser...
    npm install terser@^5.19.0 --save-dev
)

REM Try to build
echo 🏗️ Attempting to build frontend...
npm run build
if errorlevel 1 (
    echo ❌ Build failed, trying alternative approach...
    
    REM Try building with different options
    echo 🔄 Trying build with --force...
    npm run build -- --force
    
    REM If still failing, try clearing cache
    if errorlevel 1 (
        echo 🧹 Clearing npm cache and retrying...
        npm cache clean --force
        rmdir /s /q node_modules
        del package-lock.json
        npm install
        npm run build
    )
)

echo 🎉 Frontend build fix completed!
pause

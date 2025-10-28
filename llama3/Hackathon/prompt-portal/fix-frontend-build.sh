#!/bin/bash
# Fix script for frontend build issues with TAB completion

echo "🔧 Fixing frontend build issues for TAB completion..."

# Navigate to frontend directory
cd Hackathon/prompt-portal/frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Check if MQTT is properly installed
if ! npm list mqtt > /dev/null 2>&1; then
    echo "📦 Installing MQTT dependency..."
    npm install mqtt@^5.3.4
fi

# Check if MQTT types are installed
if ! npm list @types/mqtt > /dev/null 2>&1; then
    echo "📦 Installing MQTT types..."
    npm install @types/mqtt@^2.5.5 --save-dev
fi

# Check if terser is installed
if ! npm list terser > /dev/null 2>&1; then
    echo "📦 Installing terser..."
    npm install terser@^5.19.0 --save-dev
fi

# Try to build
echo "🏗️ Attempting to build frontend..."
if npm run build; then
    echo "✅ Frontend build successful!"
else
    echo "❌ Build failed, trying alternative approach..."
    
    # Try building with different options
    echo "🔄 Trying build with --force..."
    npm run build -- --force
    
    # If still failing, try clearing cache
    if [ $? -ne 0 ]; then
        echo "🧹 Clearing npm cache and retrying..."
        npm cache clean --force
        rm -rf node_modules package-lock.json
        npm install
        npm run build
    fi
fi

echo "🎉 Frontend build fix completed!"

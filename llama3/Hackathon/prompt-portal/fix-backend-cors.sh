#!/bin/bash

# Quick fix for backend CORS to allow domain access

echo "🔧 Fixing backend CORS configuration..."

cd "$(dirname "$0")/backend"

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Backup existing .env
echo "Backing up current .env..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Set comprehensive CORS origins
CORS_ORIGINS="https://lammp.agaii.org,http://lammp.agaii.org,http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:5173,http://127.0.0.1:5173"

echo "Updating CORS_ORIGINS in .env..."
if grep -q "CORS_ORIGINS" .env; then
    # Update existing line (works on both Linux and macOS)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sed -i '' "s|CORS_ORIGINS=.*|CORS_ORIGINS=${CORS_ORIGINS}|" .env
    else
        sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=${CORS_ORIGINS}|" .env
    fi
else
    # Add new line
    echo "CORS_ORIGINS=${CORS_ORIGINS}" >> .env
fi

echo "✓ CORS configuration updated!"
echo ""
echo "CORS now allows:"
echo "  - https://lammp.agaii.org"
echo "  - http://lammp.agaii.org"
echo "  - http://localhost:3000"
echo "  - http://127.0.0.1:3000"
echo "  - http://localhost:3001"
echo "  - http://127.0.0.1:3001"
echo "  - http://localhost:5173"
echo "  - http://127.0.0.1:5173"
echo ""
echo "⚠️  You need to restart the backend for changes to take effect:"
echo "    kill \$(cat backend.pid) 2>/dev/null"
echo "    cd backend && nohup uvicorn app.main:app --host 0.0.0.0 --port 3000 > /dev/null 2>&1 &"
echo "    echo \$! > backend.pid"

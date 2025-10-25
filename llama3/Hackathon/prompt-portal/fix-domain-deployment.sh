#!/bin/bash

# Complete fix for https://lammp.agaii.org deployment
# This script fixes both backend CORS and frontend configuration

set -e

echo "🔧 Fixing deployment for https://lammp.agaii.org..."
echo ""

ROOT_DIR="$(dirname "$0")"
cd "$ROOT_DIR"

# Step 1: Fix Backend CORS
echo "📡 Step 1: Configuring backend CORS..."
cd backend

if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# Backup existing .env
echo "Backing up current .env..."
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Set comprehensive CORS origins including the domain
CORS_ORIGINS="https://lammp.agaii.org,http://lammp.agaii.org,https://lammp.agaii.org/api,http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:5173,http://127.0.0.1:5173"

echo "Updating CORS_ORIGINS..."
if grep -q "CORS_ORIGINS" .env; then
    sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=${CORS_ORIGINS}|" .env
else
    echo "CORS_ORIGINS=${CORS_ORIGINS}" >> .env
fi

echo "✓ Backend CORS configured"
echo ""

# Step 2: Fix Frontend Configuration
echo "🎨 Step 2: Configuring frontend API endpoints..."
cd ../frontend

# Create production environment file
cat > .env.production << 'EOF'
VITE_API_BASE=https://lammp.agaii.org/api
VITE_WS_BASE=wss://lammp.agaii.org/api
EOF

cat > .env.local << 'EOF'
VITE_API_BASE=https://lammp.agaii.org/api
VITE_WS_BASE=wss://lammp.agaii.org/api
EOF

echo "✓ Frontend environment configured"
echo ""

# Step 3: Rebuild Frontend
echo "🏗️  Step 3: Rebuilding frontend..."
npm run build

if [ $? -eq 0 ]; then
    echo "✓ Frontend built successfully"
else
    echo "❌ Frontend build failed"
    exit 1
fi
echo ""

# Step 4: Restart Backend
echo "🔄 Step 4: Restarting backend..."
cd ../backend

# Stop existing backend
if [ -f backend.pid ]; then
    PID=$(cat backend.pid 2>/dev/null || echo "")
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null || true
        sleep 2
    fi
    rm -f backend.pid
fi

# Kill any process on port 3000
pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
if command -v lsof >/dev/null 2>&1; then
    lsof -ti:3000 | xargs -r kill -9 2>/dev/null || true
fi
if command -v fuser >/dev/null 2>&1; then
    fuser -k 3000/tcp 2>/dev/null || true
fi

sleep 1

# Start backend
echo "Starting backend on port 3000..."
nohup uvicorn app.main:app --host 0.0.0.0 --port 3000 > /dev/null 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > backend.pid

# Wait for backend to be ready
sleep 3

# Check if backend is running
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo "✓ Backend started (PID: $BACKEND_PID)"
else
    echo "❌ Backend failed to start"
    exit 1
fi
echo ""

# Step 5: Reload Nginx
echo "🌐 Step 5: Reloading Nginx..."
if command -v nginx &> /dev/null; then
    sudo nginx -t && sudo systemctl reload nginx
    echo "✓ Nginx reloaded"
else
    echo "⚠️  Nginx not found - skipping reload"
fi
echo ""

# Step 6: Verify Configuration
echo "✅ Step 6: Verifying configuration..."
cd "$ROOT_DIR"

echo ""
echo "Backend CORS Origins:"
grep "CORS_ORIGINS=" backend/.env | sed 's/CORS_ORIGINS=/  /'
echo ""

echo "Frontend API Base:"
echo "  VITE_API_BASE=https://lammp.agaii.org/api"
echo "  VITE_WS_BASE=wss://lammp.agaii.org/api"
echo ""

echo "Backend Status:"
if curl -s --max-time 2 "http://127.0.0.1:3000/docs" > /dev/null; then
    echo "  ✓ Backend is responding at http://127.0.0.1:3000"
else
    echo "  ⚠️  Backend health check failed"
fi
echo ""

echo "=================================="
echo "✅ Deployment Fix Complete!"
echo "=================================="
echo ""
echo "Your application should now be accessible at:"
echo "  🌐 https://lammp.agaii.org/"
echo "  🔗 API: https://lammp.agaii.org/api"
echo "  📚 API Docs: https://lammp.agaii.org/api/docs"
echo ""
echo "Next steps:"
echo "1. Open https://lammp.agaii.org/ in your browser"
echo "2. Clear browser cache (Ctrl+Shift+Delete)"
echo "3. Try logging in"
echo ""
echo "If issues persist:"
echo "  - Check browser console (F12) for errors"
echo "  - Verify Nginx config: sudo nginx -t"
echo "  - Check backend logs: cd backend && tail -f *.log"

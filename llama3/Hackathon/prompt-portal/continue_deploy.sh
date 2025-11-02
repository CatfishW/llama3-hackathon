#!/bin/bash

# Continue deployment from where it stopped
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "🔄 Continuing deployment..."

# Configuration
BACKEND_PORT=3000
FRONTEND_PORT=3001
DOMAIN_NAME="lammp.agaii.org"
USE_DOMAIN=true
USE_HTTPS=true
SETUP_NGINX=true

# Directories
ROOT_DIR=$(pwd)
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
SERVER_IP="127.0.0.1"

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Kill any existing processes
kill_port() {
    local port="$1"
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti:"$port" | xargs -r kill -9 2>/dev/null || true
    fi
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "${port}/tcp" 2>/dev/null || true
    fi
}

stop_backend() {
    print_step "Stopping any existing backend..."
    if [ -f "$BACKEND_DIR/backend.pid" ]; then
        PID=$(cat "$BACKEND_DIR/backend.pid" 2>/dev/null || echo "")
        if [ -n "$PID" ]; then kill "$PID" 2>/dev/null || true; fi
        rm -f "$BACKEND_DIR/backend.pid" 2>/dev/null || true
    fi
    pkill -f "uvicorn .*app\.main:app" 2>/dev/null || true
    kill_port "$BACKEND_PORT"
}

stop_frontend() {
    print_step "Stopping any existing frontend..."
    if [ -f "$FRONTEND_DIR/frontend.pid" ]; then
        PID=$(cat "$FRONTEND_DIR/frontend.pid" 2>/dev/null || echo "")
        if [ -n "$PID" ]; then kill "$PID" 2>/dev/null || true; fi
        rm -f "$FRONTEND_DIR/frontend.pid" 2>/dev/null || true
    fi
    pkill -f "vite.*preview" 2>/dev/null || true
    kill_port "$FRONTEND_PORT"
}

# Try building again with visible output
print_step "Building frontend (showing output)..."
cd "$FRONTEND_DIR"

npm run build || {
    print_error "Build failed! See error above."
    exit 1
}

print_step "Starting services in background..."

# Clean up existing processes
stop_backend
stop_frontend
sleep 1

# Start backend
cd "$BACKEND_DIR"
print_step "Starting backend on port $BACKEND_PORT..."
nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT > backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > backend.pid

# Wait for backend to be ready
print_step "Waiting for backend to start..."
for i in $(seq 1 20); do
    if curl -s --max-time 1 "http://127.0.0.1:$BACKEND_PORT/docs" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Backend is ready!${NC}"
        break
    fi
    sleep 0.5
done

# Verify backend is running
if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
    print_error "Backend failed to start. Check backend.log for details."
    cat "$BACKEND_DIR/backend.log" | tail -20
    exit 1
fi

# Start frontend
cd "$FRONTEND_DIR"
print_step "Starting frontend on port $FRONTEND_PORT..."
nohup npm run preview -- --host 0.0.0.0 --port $FRONTEND_PORT > frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > frontend.pid

sleep 3

# Check service status
BACKEND_OK=0
FRONTEND_OK=0
if ps -p $BACKEND_PID > /dev/null 2>&1; then BACKEND_OK=1; fi
if ps -p $FRONTEND_PID > /dev/null 2>&1; then FRONTEND_OK=1; fi

echo ""
echo "=================================="
echo -e "${GREEN}DEPLOYMENT STATUS${NC}"
echo "=================================="

if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend is running (PID: $BACKEND_PID)${NC}"
    echo -e "  Log: $BACKEND_DIR/backend.log"
else
    echo -e "${RED}✗ Backend failed to start${NC}"
    echo -e "  Check: $BACKEND_DIR/backend.log"
fi

if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend is running (PID: $FRONTEND_PID)${NC}"
    echo -e "  Log: $FRONTEND_DIR/frontend.log"
else
    echo -e "${RED}✗ Frontend failed to start${NC}"
    echo -e "  Check: $FRONTEND_DIR/frontend.log"
fi

echo ""
echo -e "${GREEN}Access URLs:${NC}"
echo -e "🌐 Website: ${GREEN}https://$DOMAIN_NAME${NC}"
echo -e "🔗 API: ${GREEN}https://$DOMAIN_NAME/api${NC}"
echo -e "📚 API Docs: ${GREEN}https://$DOMAIN_NAME/api/docs${NC}"

echo ""
echo -e "${GREEN}Service Management:${NC}"
echo "  kill \$(cat backend/backend.pid)    # Stop backend"
echo "  kill \$(cat frontend/frontend.pid)  # Stop frontend"
echo "  tail -f backend/backend.log         # View backend logs"
echo "  tail -f frontend/frontend.log       # View frontend logs"

if [ "$BACKEND_OK" -eq 1 ] && [ "$FRONTEND_OK" -eq 1 ]; then
    echo ""
    echo -e "${GREEN}✓ Deployment completed successfully! 🎉${NC}"
    exit 0
else
    echo ""
    echo -e "${YELLOW}⚠ Deployment completed with issues${NC}"
    exit 1
fi


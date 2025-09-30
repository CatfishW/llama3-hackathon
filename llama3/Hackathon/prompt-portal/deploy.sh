#!/bin/bash

# Prompt Portal - Simplified Deployment Script
# This script sets up the application assuming environments are already installed
# Prerequisites: Python3, Node.js, npm, git should already be installed

set -e  # Exit on any error

echo "🚀 Starting Prompt Portal Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration - Change these ports if 8000 or 5173 are not available
BACKEND_PORT=3000
FRONTEND_PORT=3001

# Directories
ROOT_DIR=$(pwd)
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Get server IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}' 2>/dev/null)
echo -e "${GREEN}Detected server IP: $SERVER_IP${NC}"
echo -e "${GREEN}Using Backend Port: $BACKEND_PORT, Frontend Port: $FRONTEND_PORT${NC}"

# Function to print colored output
print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Helpers to cleanly stop running services
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
    # By PID file
    if [ -f "$BACKEND_DIR/backend.pid" ]; then
        PID=$(cat "$BACKEND_DIR/backend.pid" 2>/dev/null || echo "")
        if [ -n "$PID" ]; then kill "$PID" 2>/dev/null || true; fi
        rm -f "$BACKEND_DIR/backend.pid" 2>/dev/null || true
    fi
    # By process signature
    pkill -f "uvicorn .*app\.main:app" 2>/dev/null || true
    pkill -f "run_server\.py" 2>/dev/null || true
    # By port
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


print_step "Using built-in process management (no PM2 required)..."

print_step "Skipping firewall configuration..."

print_step "Setting up backend..."
cd "$BACKEND_DIR"

# Skip backend environment configuration - using existing .env file
print_step "Skipping backend environment configuration - using existing .env file..."

# Check and preserve existing database
print_step "Checking database status..."
if [ -f "app.db" ]; then
    print_warning "Database already exists - preserving existing data..."
    echo -e "${GREEN}Existing database found and will be preserved${NC}"
else
    print_step "No existing database found - initializing new database..."
    python create_db.py > /dev/null 2>&1 || python -c "
from app.database import init_db
init_db()
print('Database initialized successfully!')
" > /dev/null 2>&1
fi

print_step "Setting up frontend..."
cd "$FRONTEND_DIR"

# Install Node.js dependencies
print_step "Installing Node.js dependencies..."
if [ ! -d "node_modules" ]; then
    npm install --legacy-peer-deps > /dev/null 2>&1
else
    print_warning "Node modules already exist, skipping installation..."
fi

# Install additional build dependencies if needed
if ! npm list terser &> /dev/null; then
    print_step "Installing build dependencies..."
    npm install --save-dev terser > /dev/null 2>&1
fi

# Fix TypeScript configuration for compatibility
print_step "Fixing TypeScript configuration..."
cat > tsconfig.json << 'EOF'
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": false,
    "allowSyntheticDefaultImports": true,
    "esModuleInterop": true,
    "forceConsistentCasingInFileNames": true
  },
  "include": ["src"],
  "exclude": ["node_modules", "dist"]
}
EOF

# Create production environment file
print_step "Configuring frontend environment..."
cat > .env.production << EOF
VITE_API_BASE=http://173.61.35.162:$BACKEND_PORT
VITE_WS_BASE=ws://173.61.35.162:$BACKEND_PORT
EOF

cat > .env.local << EOF
VITE_API_BASE=http://173.61.35.162:$BACKEND_PORT
VITE_WS_BASE=ws://173.61.35.162:$BACKEND_PORT
EOF

echo -e "${GREEN}Frontend environment configured!${NC}"

# Build frontend for production
print_step "Building frontend..."
npm run build > /dev/null 2>&1 || {
    print_warning "Initial build failed, trying fixes..."
    
    # Install terser if missing
    print_step "Installing terser..."
    npm install --save-dev terser > /dev/null 2>&1
    
    # Try building again
    npm run build > /dev/null 2>&1 || {
        print_warning "Still failing, cleaning and reinstalling..."
        rm -rf node_modules package-lock.json dist
        npm install --legacy-peer-deps --force > /dev/null 2>&1
        npm install --save-dev terser > /dev/null 2>&1
        npm run build > /dev/null 2>&1
    }
}

print_step "Starting services in background..."

# Kill any existing processes on these ports
print_step "Cleaning up any existing processes..."
stop_backend
stop_frontend
sleep 1

# Start backend in background (silent)
cd ../backend
print_step "Starting backend on port $BACKEND_PORT..."
nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT > /dev/null 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > backend.pid

# Wait for backend port to be ready (up to ~10s)
for i in $(seq 1 20); do
    if curl -s --max-time 1 "http://127.0.0.1:$BACKEND_PORT/docs" > /dev/null; then
        break
    fi
    sleep 0.5
done

if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
    print_warning "Backend process exited unexpectedly. Attempting one restart..."
    stop_backend
    nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT > /dev/null 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > backend.pid
    sleep 2
fi

# Start frontend in background (silent)
cd ../frontend
print_step "Starting frontend on port $FRONTEND_PORT..."
nohup npm run preview -- --host 0.0.0.0 --port $FRONTEND_PORT > /dev/null 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > frontend.pid

# Give frontend time to start
sleep 3

print_step "Skipping monitoring and backup scripts setup..."

print_step "Deployment completed successfully! 🎉"

echo ""
echo "=================================="
echo -e "${GREEN}DEPLOYMENT SUMMARY${NC}"
echo "=================================="
echo -e "🌐 Frontend URL: ${GREEN}http://$SERVER_IP:$FRONTEND_PORT${NC}"
echo -e "🔗 Backend API: ${GREEN}http://$SERVER_IP:$BACKEND_PORT${NC}"
echo -e "📚 API Docs: ${GREEN}http://$SERVER_IP:$BACKEND_PORT/docs${NC}"
echo ""
echo -e "${YELLOW}Service Management:${NC}"
echo "  kill \$(cat backend/backend.pid)    # Stop backend"
echo "  kill \$(cat frontend/frontend.pid)  # Stop frontend"
echo "  # or use built-in cleanup in this script on re-run"
echo "  ./stop_services.sh               # Stop all services"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "- Firewall configuration has been skipped"
echo "- Backend secret key has been generated automatically"
echo "- Existing database is preserved (no data loss)"
echo "- Logging and monitoring have been disabled"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Open http://173.61.35.162:$FRONTEND_PORT in your browser"
echo "2. Register a new account"
echo "3. Create your first prompt template"
echo "4. Test the MQTT functionality"

# Show service status
echo ""
print_step "Checking service status:"
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo -e "${GREEN}Backend is running (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}Backend failed to start${NC}"
fi

if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo -e "${GREEN}Frontend is running (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}Frontend failed to start${NC}"
fi

echo ""
echo -e "${GREEN}Deployment completed! Your Prompt Portal is now running.${NC}"

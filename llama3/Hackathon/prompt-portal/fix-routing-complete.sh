#!/bin/bash

# Complete fix for the 405 Method Not Allowed errors
# This script fixes both the Nginx routing and rebuilds the frontend

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "🔧 Complete Fix for Prompt Portal Routing Issues"
echo "================================================="
echo ""

DOMAIN_NAME="lammp.agaii.org"
BACKEND_PORT=3000
FRONTEND_PORT=3001
ROOT_DIR="/root/prompt-portal"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Step 1: Update environment files
echo -e "${BLUE}[1/4]${NC} Updating frontend environment configuration..."
cd "$FRONTEND_DIR"

cat > .env.production << EOF
VITE_API_BASE=https://$DOMAIN_NAME
VITE_WS_BASE=wss://$DOMAIN_NAME
EOF

cat > .env.local << EOF
VITE_API_BASE=https://$DOMAIN_NAME
VITE_WS_BASE=wss://$DOMAIN_NAME
EOF

echo -e "${GREEN}✓ Environment files updated${NC}"

# Step 2: Update Nginx configuration
echo -e "${BLUE}[2/4]${NC} Updating Nginx configuration..."

cat > /tmp/nginx_${DOMAIN_NAME}.conf << 'NGINXCONF'
server {
    listen 80;
    listen [::]:80;
    server_name lammp.agaii.org;

    # Serve frontend static files
    location / {
        root /root/prompt-portal/frontend/dist;
        try_files $uri $uri/ /index.html;
        index index.html;
        
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    }

    # Proxy API requests to backend - KEEP /api prefix!
    location /api/ {
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
            add_header Access-Control-Max-Age 3600;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        
        # No rewrite - pass /api prefix through to backend
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    }

    # WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
NGINXCONF

# Backup and install
if [ -f "/etc/nginx/sites-available/${DOMAIN_NAME}" ]; then
    sudo cp "/etc/nginx/sites-available/${DOMAIN_NAME}" "/etc/nginx/sites-available/${DOMAIN_NAME}.backup.$(date +%Y%m%d_%H%M%S)"
fi

sudo mv /tmp/nginx_${DOMAIN_NAME}.conf /etc/nginx/sites-available/${DOMAIN_NAME}
sudo ln -sf /etc/nginx/sites-available/${DOMAIN_NAME} /etc/nginx/sites-enabled/

# Test and reload nginx
if sudo nginx -t > /dev/null 2>&1; then
    sudo systemctl reload nginx
    echo -e "${GREEN}✓ Nginx configuration updated and reloaded${NC}"
else
    echo -e "${RED}✗ Nginx configuration test failed!${NC}"
    exit 1
fi

# Step 3: Rebuild frontend
echo -e "${BLUE}[3/4]${NC} Rebuilding frontend with new configuration..."
cd "$FRONTEND_DIR"

npm run build > /dev/null 2>&1 || {
    echo -e "${YELLOW}Build failed, trying with fresh install...${NC}"
    npm install --legacy-peer-deps > /dev/null 2>&1
    npm run build > /dev/null 2>&1
}

echo -e "${GREEN}✓ Frontend rebuilt successfully${NC}"

# Step 4: Restart frontend service
echo -e "${BLUE}[4/4]${NC} Restarting frontend service..."

# Stop existing frontend
if [ -f "$FRONTEND_DIR/frontend.pid" ]; then
    PID=$(cat "$FRONTEND_DIR/frontend.pid" 2>/dev/null || echo "")
    if [ -n "$PID" ]; then
        kill "$PID" 2>/dev/null || true
    fi
    rm -f "$FRONTEND_DIR/frontend.pid"
fi

# Kill any process on frontend port
lsof -ti:${FRONTEND_PORT} | xargs -r kill -9 2>/dev/null || true
fuser -k ${FRONTEND_PORT}/tcp 2>/dev/null || true

# Start frontend
nohup npm run preview -- --host 0.0.0.0 --port $FRONTEND_PORT > /dev/null 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > frontend.pid

sleep 2

if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Frontend service restarted (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}✗ Frontend failed to start${NC}"
    exit 1
fi

echo ""
echo "════════════════════════════════════════════════════"
echo -e "${GREEN}✓ Fix completed successfully!${NC}"
echo "════════════════════════════════════════════════════"
echo ""
echo -e "${GREEN}What was fixed:${NC}"
echo "1. ❌ Old: https://lammp.agaii.org/api + /api/templates = /api/api/templates (404)"
echo "2. ✅ New: https://lammp.agaii.org + /api/templates = /api/templates (works!)"
echo ""
echo "3. ❌ Old: Nginx stripped /api prefix before proxying to backend"
echo "4. ✅ New: Nginx keeps /api prefix when proxying to backend"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Clear your browser cache (Ctrl+Shift+R on the page)"
echo "2. Visit: https://${DOMAIN_NAME}"
echo "3. Try logging in or registering"
echo ""
echo -e "${BLUE}Testing the fix:${NC}"
echo "Open browser console and check that requests go to:"
echo "  https://lammp.agaii.org/api/auth/login"
echo "  https://lammp.agaii.org/api/templates"
echo "(NOT /api/api/...)"
echo ""
echo -e "${GREEN}Services Status:${NC}"
echo "  Backend: http://127.0.0.1:$BACKEND_PORT (internal)"
echo "  Frontend: Running on port $FRONTEND_PORT"
echo "  Public URL: https://$DOMAIN_NAME"

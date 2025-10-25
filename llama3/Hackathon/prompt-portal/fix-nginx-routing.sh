#!/bin/bash

# Fix Nginx routing for Prompt Portal
# This script fixes the double /api/api/ issue by updating the Nginx configuration

set -e

echo "🔧 Fixing Nginx routing configuration..."

DOMAIN_NAME="lammp.agaii.org"
BACKEND_PORT=3000
FRONTEND_DIR="/root/prompt-portal/frontend"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if Nginx is installed
if ! command -v nginx &> /dev/null; then
    echo -e "${RED}Nginx is not installed!${NC}"
    exit 1
fi

echo -e "${GREEN}Creating new Nginx configuration...${NC}"

# Create the correct Nginx configuration
cat > /tmp/nginx_${DOMAIN_NAME}.conf << 'EOF'
server {
    listen 80;
    listen [::]:80;
    server_name lammp.agaii.org;

    # Serve frontend static files
    location / {
        root /root/prompt-portal/frontend/dist;
        try_files $uri $uri/ /index.html;
        index index.html;
        
        # Add CORS headers for frontend
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    }

    # Proxy API requests to backend (DO NOT strip /api prefix!)
    location /api/ {
        # Handle OPTIONS preflight requests
        if ($request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
            add_header Access-Control-Max-Age 3600;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        
        # Pass through to backend with /api prefix intact (no rewrite!)
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Add CORS headers
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
EOF

# Backup existing configuration
if [ -f "/etc/nginx/sites-available/${DOMAIN_NAME}" ]; then
    echo -e "${YELLOW}Backing up existing configuration...${NC}"
    sudo cp "/etc/nginx/sites-available/${DOMAIN_NAME}" "/etc/nginx/sites-available/${DOMAIN_NAME}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Install new configuration
echo -e "${GREEN}Installing new Nginx configuration...${NC}"
sudo mv /tmp/nginx_${DOMAIN_NAME}.conf /etc/nginx/sites-available/${DOMAIN_NAME}

# Enable the site
sudo ln -sf /etc/nginx/sites-available/${DOMAIN_NAME} /etc/nginx/sites-enabled/

# Test configuration
echo -e "${GREEN}Testing Nginx configuration...${NC}"
if sudo nginx -t; then
    echo -e "${GREEN}✓ Configuration test passed${NC}"
    
    # Reload Nginx
    echo -e "${GREEN}Reloading Nginx...${NC}"
    sudo systemctl reload nginx
    
    echo -e "${GREEN}✓ Nginx configuration updated successfully!${NC}"
    echo ""
    echo "The routing issue has been fixed. The application should now work correctly."
    echo "Frontend URLs like https://lammp.agaii.org/api/templates will now correctly"
    echo "proxy to the backend at http://127.0.0.1:3000/api/templates"
else
    echo -e "${RED}✗ Configuration test failed!${NC}"
    echo "Restoring backup..."
    if [ -f "/etc/nginx/sites-available/${DOMAIN_NAME}.backup.$(date +%Y%m%d)_"* ]; then
        sudo cp "/etc/nginx/sites-available/${DOMAIN_NAME}.backup."* "/etc/nginx/sites-available/${DOMAIN_NAME}"
    fi
    exit 1
fi

echo ""
echo "════════════════════════════════════════"
echo -e "${GREEN}Next Steps:${NC}"
echo "════════════════════════════════════════"
echo "1. Rebuild and restart the frontend:"
echo "   cd ~/prompt-portal/frontend"
echo "   npm run build"
echo "   kill \$(cat frontend.pid)"
echo "   nohup npm run preview -- --host 0.0.0.0 --port 3001 > /dev/null 2>&1 &"
echo "   echo \$! > frontend.pid"
echo ""
echo "2. Clear browser cache or hard refresh (Ctrl+Shift+R)"
echo ""
echo "3. Test the application at https://lammp.agaii.org"
echo ""
echo -e "${YELLOW}If you still see SSL errors, make sure certbot/SSL is configured:${NC}"
echo "   sudo certbot --nginx -d lammp.agaii.org"

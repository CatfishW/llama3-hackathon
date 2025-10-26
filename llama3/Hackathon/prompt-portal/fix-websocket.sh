#!/bin/bash

# Fix WebSocket Connection Issues for Prompt Portal
# This script fixes the WebSocket routing for /api/mqtt/ws/hints/* endpoints

set -e

echo "🔧 Fixing WebSocket configuration for lammp.agaii.org..."

DOMAIN_NAME="lammp.agaii.org"
NGINX_CONFIG="/etc/nginx/sites-available/${DOMAIN_NAME}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if running on the server (Linux)
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo -e "${RED}This script must be run on the Linux server, not locally!${NC}"
    echo "Please SSH to your server first:"
    echo "  ssh root@lammp.agaii.org"
    echo "Then run this script from there."
    exit 1
fi

# Check if Nginx is installed
if ! command -v nginx &> /dev/null; then
    echo -e "${RED}Nginx is not installed!${NC}"
    exit 1
fi

# Detect backend port
echo -e "${YELLOW}Detecting backend port...${NC}"
BACKEND_PORT=8000
if netstat -tlnp 2>/dev/null | grep -q ":3000.*uvicorn"; then
    BACKEND_PORT=3000
    echo -e "${GREEN}Found backend running on port 3000${NC}"
elif netstat -tlnp 2>/dev/null | grep -q ":8000.*uvicorn"; then
    BACKEND_PORT=8000
    echo -e "${GREEN}Found backend running on port 8000${NC}"
else
    echo -e "${YELLOW}Backend not detected. Assuming port 8000${NC}"
fi

# Backup existing configuration
if [ -f "$NGINX_CONFIG" ]; then
    echo -e "${YELLOW}Backing up existing configuration...${NC}"
    sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
fi

echo -e "${GREEN}Creating updated Nginx configuration with WebSocket support...${NC}"

# Create the corrected Nginx configuration
sudo tee $NGINX_CONFIG > /dev/null << EOF
# WebSocket upgrade headers
map \$http_upgrade \$connection_upgrade {
    default upgrade;
    '' close;
}

# Redirect www to non-www
server {
    listen 80;
    listen [::]:80;
    server_name www.$DOMAIN_NAME;
    return 301 https://\$scheme://$DOMAIN_NAME\$request_uri;
}

# Main server block
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN_NAME;

    # Serve frontend static files
    location / {
        root /root/prompt-portal/frontend/dist;
        try_files \$uri \$uri/ /index.html;
        index index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # WebSocket support for MQTT hints (MUST come before /api/ block!)
    # This handles paths like /api/mqtt/ws/hints/session-xyz
    location ~ ^/api/mqtt/ws/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket specific timeouts - very long for persistent connections
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
        
        # Add CORS headers
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Upgrade, Connection" always;
    }

    # WebSocket support for user messages (/ws/token)
    location ~ ^/ws/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
    }

    # Proxy API requests to backend
    # This handles all other /api/* requests (non-WebSocket)
    location /api/ {
        # Handle OPTIONS preflight requests
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
            add_header Access-Control-Max-Age 3600;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        
        # Pass through to backend with /api prefix intact
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts for slow API operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Add CORS headers
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
}

# HTTPS configuration (if SSL is already set up)
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN_NAME;

    # SSL certificate paths (update these if different)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Serve frontend static files
    location / {
        root /root/prompt-portal/frontend/dist;
        try_files \$uri \$uri/ /index.html;
        index index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # WebSocket support for MQTT hints (MUST come before /api/ block!)
    location ~ ^/api/mqtt/ws/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket specific timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
        
        # Add CORS headers
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Upgrade, Connection" always;
    }

    # WebSocket support for user messages
    location ~ ^/ws/ {
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
    }

    # Proxy API requests to backend
    location /api/ {
        # Handle OPTIONS preflight requests
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
            add_header Access-Control-Max-Age 3600;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        
        # Pass through to backend
        proxy_pass http://127.0.0.1:${BACKEND_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Add CORS headers
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
}
EOF

# Enable the site
sudo ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/

# Test configuration
echo -e "${GREEN}Testing Nginx configuration...${NC}"
if sudo nginx -t; then
    echo -e "${GREEN}✓ Configuration test passed${NC}"
    
    # Reload Nginx
    echo -e "${GREEN}Reloading Nginx...${NC}"
    sudo systemctl reload nginx
    
    echo -e "${GREEN}✓ Nginx configuration updated successfully!${NC}"
    echo ""
    echo "════════════════════════════════════════════════════════"
    echo -e "${GREEN}WebSocket Fix Applied Successfully!${NC}"
    echo "════════════════════════════════════════════════════════"
    echo ""
    echo "What was fixed:"
    echo "  • WebSocket location blocks now come BEFORE /api/ block"
    echo "  • Proper WebSocket upgrade headers configured"
    echo "  • Extended timeouts for persistent connections (1 hour)"
    echo "  • Backend port set to ${BACKEND_PORT}"
    echo ""
    echo "WebSocket endpoints that should now work:"
    echo "  • wss://lammp.agaii.org/api/mqtt/ws/hints/session-*"
    echo "  • wss://lammp.agaii.org/ws/token"
    echo ""
    echo "Next steps:"
    echo "  1. Clear browser cache (Ctrl+Shift+R)"
    echo "  2. Test the WebSocket connection"
    echo "  3. Check browser console for any remaining errors"
    echo ""
    echo "To verify backend is running:"
    echo "  netstat -tlnp | grep ${BACKEND_PORT}"
    echo ""
else
    echo -e "${RED}✗ Configuration test failed!${NC}"
    echo "Restoring backup..."
    LATEST_BACKUP=$(ls -t ${NGINX_CONFIG}.backup.* 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        sudo cp "$LATEST_BACKUP" "$NGINX_CONFIG"
        echo -e "${YELLOW}Backup restored${NC}"
    fi
    exit 1
fi

# Show Nginx error log location
echo -e "${YELLOW}If issues persist, check logs:${NC}"
echo "  sudo tail -f /var/log/nginx/error.log"
echo "  sudo tail -f /var/log/nginx/access.log"


#!/bin/bash
set -e

echo "🔧 Fixing WebSocket Configuration for Maze Game"
echo ""

DOMAIN_NAME="lammp.agaii.org"
NGINX_CONFIG="/etc/nginx/sites-available/${DOMAIN_NAME}"

# Detect backend port
BACKEND_PORT=8000
if netstat -tlnp 2>/dev/null | grep -q ':3000.*uvicorn'; then
    BACKEND_PORT=3000
    echo "✓ Backend detected on port 3000"
elif netstat -tlnp 2>/dev/null | grep -q ':8000.*python'; then
    BACKEND_PORT=8000
    echo "✓ Backend detected on port 8000"
else
    echo "⚠ Backend not detected, defaulting to port 8000"
fi

# Backup existing config
echo "📦 Backing up current nginx configuration..."
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

# Create new configuration with proper WebSocket support
echo "📝 Creating new nginx configuration with WebSocket support..."
sudo tee $NGINX_CONFIG > /dev/null << EOFNGINX
# WebSocket upgrade map - CRITICAL for WebSocket connections
map \$http_upgrade \$connection_upgrade {
    default upgrade;
    '' close;
}

# HTTP server - redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN_NAME;
    return 301 https://\$host\$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN_NAME;

    # SSL certificate (managed by Certbot)
    ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

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

    # CRITICAL: WebSocket for MQTT hints MUST come BEFORE /api/ block!
    # This handles: wss://lammp.agaii.org/api/mqtt/ws/hints/session-xyz
    location ~ ^/api/mqtt/ws/ {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket specific timeouts - 1 hour for persistent connections
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
        
        # Disable buffering for real-time data
        proxy_buffering off;
        
        # CORS headers
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With, Upgrade, Connection" always;
    }

    # WebSocket for user messages
    location ~ ^/ws/ {
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
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
        proxy_buffering off;
    }

    # General API proxy (non-WebSocket)
    location /api/ {
        # Handle OPTIONS preflight
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
            add_header Access-Control-Max-Age 3600;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        
        # Proxy to backend
        proxy_pass http://127.0.0.1:$BACKEND_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Standard timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # CORS headers
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
EOFNGINX

echo "✅ Configuration file created"
echo ""

# Test nginx configuration
echo "🧪 Testing nginx configuration..."
if sudo nginx -t; then
    echo "✅ Configuration test passed"
    echo ""
    
    # Reload nginx
    echo "🔄 Reloading nginx..."
    sudo systemctl reload nginx
    
    echo "✅ Nginx reloaded successfully!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ WebSocket Fix Applied Successfully!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Backend Port: $BACKEND_PORT"
    echo "WebSocket Endpoint: wss://$DOMAIN_NAME/api/mqtt/ws/hints/*"
    echo ""
    echo "Next steps:"
    echo "  1. Clear your browser cache (Ctrl+Shift+R)"
    echo "  2. Reload https://$DOMAIN_NAME"
    echo "  3. Try the maze game - WebSocket should now connect!"
    echo ""
    echo "To verify:"
    echo "  • Open DevTools (F12) → Console"
    echo "  • Should NOT see: 'WebSocket connection failed'"
    echo "  • Network tab → Filter by WS → Should see status 101"
    echo ""
else
    echo "❌ Configuration test failed!"
    echo ""
    echo "Restoring backup..."
    LATEST_BACKUP=$(ls -t ${NGINX_CONFIG}.backup.* 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        sudo cp "$LATEST_BACKUP" "$NGINX_CONFIG"
        echo "✅ Backup restored"
    fi
    exit 1
fi

echo "To check logs if issues persist:"
echo "  sudo tail -f /var/log/nginx/error.log"
echo "  sudo tail -f /var/log/nginx/access.log | grep ws"

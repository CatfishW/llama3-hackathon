# Quick WebSocket Fix - Upload and Apply on Server
# This script will SSH to the server and fix the nginx configuration immediately

$ErrorActionPreference = "Stop"

$SERVER = "root@lammp.agaii.org"
$DOMAIN = "lammp.agaii.org"

Write-Host "🔧 Fixing WebSocket Configuration on $DOMAIN" -ForegroundColor Cyan
Write-Host ""

# Create the fix script inline
$INLINE_FIX = @'
#!/bin/bash
set -e

DOMAIN_NAME="lammp.agaii.org"
NGINX_CONFIG="/etc/nginx/sites-available/${DOMAIN_NAME}"

# Detect backend port
BACKEND_PORT=8000
if netstat -tlnp 2>/dev/null | grep -q ":3000.*uvicorn"; then
    BACKEND_PORT=3000
elif netstat -tlnp 2>/dev/null | grep -q ":8000.*python"; then
    BACKEND_PORT=8000
fi

echo "Detected backend on port: $BACKEND_PORT"

# Backup existing config
sudo cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"

# Check if certbot SSL exists
SSL_EXISTS=false
if [ -d "/etc/letsencrypt/live/$DOMAIN_NAME" ]; then
    SSL_EXISTS=true
fi

# Create new configuration with WebSocket support
sudo tee $NGINX_CONFIG > /dev/null << 'EOFNGINX'
# WebSocket upgrade map
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}

# HTTP server - redirect to HTTPS if SSL exists
server {
    listen 80;
    listen [::]:80;
    server_name lammp.agaii.org;

PLACEHOLDER_REDIRECT

    # Serve frontend static files
    location / {
        root /root/prompt-portal/frontend/dist;
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    # CRITICAL: WebSocket location MUST come BEFORE /api/
    location ~ ^/api/mqtt/ws/ {
        proxy_pass http://127.0.0.1:BACKEND_PORT_PLACEHOLDER;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
        proxy_buffering off;
    }

    location ~ ^/ws/ {
        proxy_pass http://127.0.0.1:BACKEND_PORT_PLACEHOLDER;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
        proxy_buffering off;
    }

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
        proxy_pass http://127.0.0.1:BACKEND_PORT_PLACEHOLDER;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

PLACEHOLDER_HTTPS_BLOCK
EOFNGINX

# Now replace placeholders
if [ "$SSL_EXISTS" = true ]; then
    # Remove HTTP redirect placeholder and add HTTPS block
    sudo sed -i '/PLACEHOLDER_REDIRECT/d' "$NGINX_CONFIG"
    sudo sed -i 's/PLACEHOLDER_HTTPS_BLOCK//' "$NGINX_CONFIG"
    
    # Add HTTPS server block
    sudo tee -a $NGINX_CONFIG > /dev/null << 'EOFHTTPS'
# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name lammp.agaii.org;

    ssl_certificate /etc/letsencrypt/live/lammp.agaii.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lammp.agaii.org/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        root /root/prompt-portal/frontend/dist;
        try_files $uri $uri/ /index.html;
        index index.html;
    }

    # CRITICAL: WebSocket MUST come BEFORE /api/
    location ~ ^/api/mqtt/ws/ {
        proxy_pass http://127.0.0.1:BACKEND_PORT_PLACEHOLDER;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
        proxy_buffering off;
    }

    location ~ ^/ws/ {
        proxy_pass http://127.0.0.1:BACKEND_PORT_PLACEHOLDER;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
        proxy_buffering off;
    }

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
        proxy_pass http://127.0.0.1:BACKEND_PORT_PLACEHOLDER;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOFHTTPS
else
    # Remove both placeholders for HTTP-only
    sudo sed -i '/PLACEHOLDER_REDIRECT/d' "$NGINX_CONFIG"
    sudo sed -i '/PLACEHOLDER_HTTPS_BLOCK/d' "$NGINX_CONFIG"
fi

# Replace backend port placeholder
sudo sed -i "s/BACKEND_PORT_PLACEHOLDER/$BACKEND_PORT/g" "$NGINX_CONFIG"

# Test configuration
echo "Testing nginx configuration..."
if sudo nginx -t; then
    echo "✓ Configuration test passed"
    sudo systemctl reload nginx
    echo "✓ Nginx reloaded successfully"
    echo ""
    echo "WebSocket fix applied! Backend on port: $BACKEND_PORT"
    echo "Please clear browser cache and test: wss://lammp.agaii.org/api/mqtt/ws/hints/test"
else
    echo "✗ Configuration test failed!"
    echo "Restoring backup..."
    LATEST_BACKUP=$(ls -t ${NGINX_CONFIG}.backup.* 2>/dev/null | head -1)
    if [ -n "$LATEST_BACKUP" ]; then
        sudo cp "$LATEST_BACKUP" "$NGINX_CONFIG"
        echo "Backup restored"
    fi
    exit 1
fi
'@

Write-Host "📤 Connecting to server and applying fix..." -ForegroundColor Yellow

# Execute the fix directly via SSH
$INLINE_FIX | ssh $SERVER "bash -s"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✅ WebSocket fix applied successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Clear browser cache (Ctrl+Shift+R)" -ForegroundColor White
    Write-Host "  2. Reload https://lammp.agaii.org" -ForegroundColor White
    Write-Host "  3. Try the maze game - WebSocket should now connect" -ForegroundColor White
    Write-Host ""
    Write-Host "To verify on server:" -ForegroundColor Cyan
    Write-Host "  ssh $SERVER" -ForegroundColor Gray
    Write-Host "  sudo tail -f /var/log/nginx/error.log" -ForegroundColor Gray
} else {
    Write-Host ""
    Write-Host "❌ Fix failed! Check the output above for errors." -ForegroundColor Red
    exit 1
}

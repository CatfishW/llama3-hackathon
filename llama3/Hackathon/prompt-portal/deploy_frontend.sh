#!/bin/bash

# Configuration
REMOTE_USER="lobin"
REMOTE_HOST="vpn.agaii.org"
REMOTE_WWW_ROOT="/www/wwwroot/lammp.agaii.org"
NGINX_CONF="/www/server/panel/vhost/nginx/lammp.agaii.org.conf"
LEGACY_CONF="/etc/nginx/sites-available/lammp.agaii.org"
SUDO_PASS="Clb1997521"

echo "🚀 Starting frontend deployment..."
export PATH="/usr/bin:$PATH"

# 1. Build frontend locally
echo "📦 Building frontend..."
cd frontend
npm install --legacy-peer-deps
npm run build
if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi
cd ..

# 2. Package build files
echo "tgz-ing build files..."
tar -czf dist.tar.gz -C frontend/dist .

# 3. Transfer to remote
echo "📤 Transferring to remote..."
scp dist.tar.gz ${REMOTE_USER}@${REMOTE_HOST}:/tmp/dist.tar.gz

# 4. Deploy on remote
echo "🔧 Deploying on remote server..."
ssh ${REMOTE_USER}@${REMOTE_HOST} << EOF
    # Use sudo password
    echo "${SUDO_PASS}" | sudo -S ls > /dev/null

    # Create wwwroot if it doesn't exist
    sudo mkdir -p ${REMOTE_WWW_ROOT}
    
    # Clean old files
    sudo rm -rf ${REMOTE_WWW_ROOT}/*
    
    # Extract new files
    sudo tar -xzf /tmp/dist.tar.gz -C ${REMOTE_WWW_ROOT}
    sudo rm /tmp/dist.tar.gz
    
    # Set permissions
    sudo chown -R www:www ${REMOTE_WWW_ROOT}
    
    # Remove softlinks if any
    sudo rm -f /etc/nginx/sites-enabled/lammp.agaii.org
    
    # Migrate/Update Nginx Configuration
    echo "Updating Nginx configuration..."
    
    cat << 'NGINXEOF' | sudo tee ${NGINX_CONF} > /dev/null
# Combined and Migrated Nginx Config
map \$http_upgrade \$connection_upgrade {
    default upgrade;
    '' close;
}

# HTTPS
server {
    listen 443 ssl;
    server_name lammp.agaii.org;

    # SSL Certs (Managed by BT Panel)
    ssl_certificate     /www/server/panel/vhost/cert/lammp.agaii.org/fullchain.pem;
    ssl_certificate_key /www/server/panel/vhost/cert/lammp.agaii.org/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_session_timeout 10m;

    # Frontend Static Files
    location / {
        root ${REMOTE_WWW_ROOT};
        try_files \$uri \$uri/ /index.html;
        index index.html;
        
        # Security/CORS
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    }

    # ACME validation
    location ^~ /.well-known/acme-challenge/ {
        root ${REMOTE_WWW_ROOT};
        default_type text/plain;
    }

    # General WebSocket support (Messages, etc.)
    location /ws/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection \$connection_upgrade;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
    }

    # Proxy API requests to backend
    location /api/ {
        if (\$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
            add_header Access-Control-Max-Age 3600;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_connect_timeout 300s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        proxy_buffering off;
        proxy_request_buffering off;
    }

    # Proxy uploads to backend
    location /uploads/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    access_log /www/wwwlogs/lammp.agaii.org_ssl.log;
    error_log  /www/wwwlogs/lammp.agaii.org_ssl.error.log;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name lammp.agaii.org;

    location ^~ /.well-known/acme-challenge/ {
        root ${REMOTE_WWW_ROOT};
        default_type text/plain;
    }

    location / { return 301 https://\$host\$request_uri; }

    access_log /www/wwwlogs/lammp.agaii.org.log;
    error_log  /www/wwwlogs/lammp.agaii.org.error.log;
}
NGINXEOF

    # Test and reload Nginx
    echo "Reloading Nginx..."
    sudo nginx -t && sudo systemctl reload nginx
EOF

# 5. Cleanup local
rm dist.tar.gz

echo "✅ Deployment complete!"

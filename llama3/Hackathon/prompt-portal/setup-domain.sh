#!/bin/bash

# Prompt Portal - Domain Setup Script
# Sets up lammp.agaii.org domain with SSL

set -e  # Exit on any error

echo "🌐 Setting up domain lammp.agaii.org for Prompt Portal..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN_NAME="lammp.agaii.org"
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}' 2>/dev/null)

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

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please don't run this script as root"
    exit 1
fi

print_info "Detected server IP: $SERVER_IP"
print_info "Domain: $DOMAIN_NAME"

# Verify Nginx is installed
if ! command -v nginx &> /dev/null; then
    print_error "Nginx is not installed. Please run deploy-production.sh first."
    exit 1
fi

# Verify Certbot is installed
if ! command -v certbot &> /dev/null; then
    print_step "Installing Certbot..."
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
fi

print_step "Updating backend environment for domain..."
cd backend

# Backup existing .env
if [ -f .env ]; then
    cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
fi

# Update CORS origins to include the domain
if [ -f .env ]; then
    # Check if domain is already in CORS_ORIGINS
    if ! grep -q "$DOMAIN_NAME" .env; then
        print_step "Adding domain to CORS origins..."
        sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=https://${DOMAIN_NAME},http://${DOMAIN_NAME},https://www.${DOMAIN_NAME},http://www.${DOMAIN_NAME},http://${SERVER_IP}:3001,http://${SERVER_IP}:8000,http://localhost:5173|" .env
    else
        print_info "Domain already in CORS origins"
    fi
else
    print_error ".env file not found. Please run deploy.sh first."
    exit 1
fi

print_step "Updating frontend environment for domain..."
cd ../frontend

# Create production environment file
cat > .env.production << EOF
VITE_API_BASE=https://$DOMAIN_NAME/api
VITE_WS_BASE=wss://$DOMAIN_NAME/api
EOF

# Also update .env.local for consistency
cat > .env.local << EOF
VITE_API_BASE=https://$DOMAIN_NAME/api
VITE_WS_BASE=wss://$DOMAIN_NAME/api
EOF

echo -e "${GREEN}Frontend environment configured for $DOMAIN_NAME!${NC}"

print_step "Rebuilding frontend with domain configuration..."
npm run build > /dev/null 2>&1 || {
    print_warning "Build failed, trying with clean install..."
    rm -rf node_modules package-lock.json dist
    npm install --legacy-peer-deps > /dev/null 2>&1
    npm run build > /dev/null 2>&1
}

print_step "Configuring Nginx for domain..."

# Create Nginx configuration for the domain
NGINX_CONFIG="/etc/nginx/sites-available/$DOMAIN_NAME"
sudo tee $NGINX_CONFIG > /dev/null << EOF
# Redirect www to non-www
server {
    listen 80;
    listen [::]:80;
    server_name www.$DOMAIN_NAME;
    return 301 https://$DOMAIN_NAME\$request_uri;
}

# Main server block
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN_NAME $SERVER_IP;

    # Serve frontend static files
    location / {
        root $(pwd)/dist;
        try_files \$uri \$uri/ /index.html;
        index index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # Increase timeouts for slow operations
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support for MQTT
    location /api/mqtt/ws/ {
        proxy_pass http://127.0.0.1:8000/api/mqtt/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket specific timeouts
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
EOF

# Enable the site
sudo ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
print_step "Testing Nginx configuration..."
sudo nginx -t || {
    print_error "Nginx configuration test failed!"
    exit 1
}

# Reload Nginx
print_step "Reloading Nginx..."
sudo systemctl reload nginx

print_step "Checking DNS configuration..."
DNS_IP=$(dig +short $DOMAIN_NAME @8.8.8.8 | tail -n1)
if [ -z "$DNS_IP" ]; then
    print_warning "DNS not configured yet for $DOMAIN_NAME"
    echo ""
    echo "=========================================="
    echo -e "${YELLOW}DNS CONFIGURATION REQUIRED${NC}"
    echo "=========================================="
    echo ""
    echo "Please configure your DNS with the following A record:"
    echo ""
    echo "  Type: A"
    echo "  Name: lammp (or @)"
    echo "  Value: $SERVER_IP"
    echo "  TTL: 3600 (or Auto)"
    echo ""
    echo "After DNS propagates (can take a few minutes to 48 hours),"
    echo "run this command to set up SSL:"
    echo ""
    echo "  sudo certbot --nginx -d $DOMAIN_NAME"
    echo ""
elif [ "$DNS_IP" != "$SERVER_IP" ]; then
    print_warning "DNS points to $DNS_IP but server IP is $SERVER_IP"
    echo "Please update your DNS A record to point to $SERVER_IP"
else
    print_info "DNS correctly configured!"
    
    # Attempt SSL setup
    print_step "Setting up SSL certificate with Let's Encrypt..."
    echo ""
    print_info "This will request a free SSL certificate from Let's Encrypt"
    
    read -p "Proceed with SSL setup? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Try to get SSL certificate
        sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@agaii.org --redirect || {
            print_warning "SSL setup failed. You can run this manually later:"
            echo "sudo certbot --nginx -d $DOMAIN_NAME"
        }
    else
        print_info "Skipping SSL setup. You can run it later with:"
        echo "sudo certbot --nginx -d $DOMAIN_NAME"
    fi
fi

# Restart backend to pick up new CORS settings
print_step "Restarting backend service..."
cd ../backend
if command -v pm2 &> /dev/null; then
    pm2 restart prompt-portal-backend > /dev/null 2>&1 || {
        print_warning "PM2 restart failed, trying manual restart..."
        pkill -f "uvicorn.*app\.main:app" > /dev/null 2>&1
        sleep 2
        nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
        echo $! > backend.pid
    }
else
    print_warning "PM2 not found, restarting manually..."
    pkill -f "uvicorn.*app\.main:app" > /dev/null 2>&1
    sleep 2
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
    echo $! > backend.pid
fi

# Wait for backend to start
sleep 3

# Test backend health
if curl -s --max-time 5 "http://127.0.0.1:8000/docs" > /dev/null; then
    print_info "Backend is healthy!"
else
    print_warning "Backend health check failed. Check backend/backend.log"
fi

print_step "Domain setup completed! 🎉"

echo ""
echo "=========================================="
echo -e "${GREEN}DOMAIN SETUP SUMMARY${NC}"
echo "=========================================="
echo ""
echo -e "🌐 Domain: ${GREEN}$DOMAIN_NAME${NC}"
echo -e "🖥️  Server IP: ${GREEN}$SERVER_IP${NC}"
echo ""

if [ "$DNS_IP" == "$SERVER_IP" ]; then
    echo -e "✅ DNS is correctly configured"
    echo ""
    echo -e "🔗 Website: ${GREEN}https://$DOMAIN_NAME${NC}"
    echo -e "🔗 API: ${GREEN}https://$DOMAIN_NAME/api${NC}"
    echo -e "📚 API Docs: ${GREEN}https://$DOMAIN_NAME/api/docs${NC}"
else
    echo -e "⚠️  DNS not configured yet"
    echo ""
    echo -e "🔗 Website: ${YELLOW}http://$SERVER_IP:3001${NC} (temporary)"
    echo -e "🔗 API: ${YELLOW}http://$SERVER_IP:8000${NC} (temporary)"
fi

echo ""
echo -e "${YELLOW}Next steps:${NC}"
if [ -z "$DNS_IP" ] || [ "$DNS_IP" != "$SERVER_IP" ]; then
    echo "1. Configure DNS A record to point to $SERVER_IP"
    echo "2. Wait for DNS propagation (use: dig $DOMAIN_NAME)"
    echo "3. Run: sudo certbot --nginx -d $DOMAIN_NAME"
else
    echo "1. Your site should be accessible at https://$DOMAIN_NAME"
    echo "2. Test all features including login, templates, and MQTT"
    echo "3. Monitor logs with: pm2 logs prompt-portal-backend"
fi

echo ""
echo -e "${GREEN}Configuration files updated:${NC}"
echo "  - backend/.env (CORS origins)"
echo "  - frontend/.env.production (API endpoints)"
echo "  - /etc/nginx/sites-available/$DOMAIN_NAME"
echo ""

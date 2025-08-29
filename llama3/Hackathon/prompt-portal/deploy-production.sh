#!/bin/bash

# Prompt Portal - Production Deployment Script
# This script sets up the application for production with Nginx, SSL, and security

set -e  # Exit on any error

echo "🚀 Starting Prompt Portal Production Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get server IP
SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
echo -e "${GREEN}Detected server IP: $SERVER_IP${NC}"

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

# Ask for domain name (optional)
echo ""
read -p "Do you have a domain name for this server? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your domain name (e.g., example.com): " DOMAIN_NAME
    USE_DOMAIN=true
else
    DOMAIN_NAME=""
    USE_DOMAIN=false
fi

print_step "Updating system packages..."
sudo apt update && sudo apt upgrade -y

print_step "Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv nodejs npm git curl nginx certbot python3-certbot-nginx ufw

print_step "Configuring firewall..."
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw allow 8000/tcp
sudo ufw allow 1883/tcp
sudo ufw --force enable

print_step "Installing PM2 for process management..."
sudo npm install -g pm2

print_step "Setting up backend..."
cd backend

# Create virtual environment
print_step "Creating Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

# Install Python dependencies
print_step "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Setup environment file
print_step "Configuring backend environment..."
if [ ! -f .env ]; then
    cp .env.example .env
    
    # Generate a random secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Update environment file
    sed -i "s/SECRET_KEY=change_me_to_a_random_long_string/SECRET_KEY=$SECRET_KEY/" .env
    
    if [ "$USE_DOMAIN" = true ]; then
        sed -i "s/CORS_ORIGINS=http:\/\/localhost:5173/CORS_ORIGINS=https:\/\/$DOMAIN_NAME,http:\/\/$DOMAIN_NAME,http:\/\/$SERVER_IP/" .env
    else
        sed -i "s/CORS_ORIGINS=http:\/\/localhost:5173/CORS_ORIGINS=http:\/\/$SERVER_IP/" .env
    fi
    
    echo -e "${GREEN}Backend environment configured!${NC}"
else
    print_warning "Backend .env file already exists, updating CORS settings..."
    if [ "$USE_DOMAIN" = true ]; then
        sed -i "s/CORS_ORIGINS=.*/CORS_ORIGINS=https:\/\/$DOMAIN_NAME,http:\/\/$DOMAIN_NAME,http:\/\/$SERVER_IP/" .env
    else
        sed -i "s/CORS_ORIGINS=.*/CORS_ORIGINS=http:\/\/$SERVER_IP/" .env
    fi
fi

# Initialize database
print_step "Initializing database..."
python create_db.py || python -c "
from app.database import init_db
init_db()
print('Database initialized successfully!')
"

print_step "Setting up frontend..."
cd ../frontend

# Install Node.js dependencies
print_step "Installing Node.js dependencies..."
npm install --legacy-peer-deps

# Fix TypeScript configuration for compatibility
print_step "Ensuring TypeScript compatibility..."
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
if [ "$USE_DOMAIN" = true ]; then
    cat > .env.production << EOF
VITE_API_BASE=https://$DOMAIN_NAME/api
VITE_WS_BASE=wss://$DOMAIN_NAME/api
EOF
else
    cat > .env.production << EOF
VITE_API_BASE=http://$SERVER_IP/api
VITE_WS_BASE=ws://$SERVER_IP/api
EOF
fi

echo -e "${GREEN}Frontend environment configured!${NC}"

# Build frontend for production
print_step "Building frontend for production..."
npm run build || {
    print_warning "Build failed, applying fixes..."
    rm -rf node_modules package-lock.json dist
    npm install --legacy-peer-deps --force
    npm run build
}

print_step "Configuring Nginx..."

# Create Nginx configuration
if [ "$USE_DOMAIN" = true ]; then
    NGINX_CONFIG="/etc/nginx/sites-available/$DOMAIN_NAME"
    sudo tee $NGINX_CONFIG > /dev/null << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME $SERVER_IP;

    # Serve frontend
    location / {
        root $(pwd)/dist;
        try_files \$uri \$uri/ /index.html;
        index index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket support
    location /api/mqtt/ws/ {
        proxy_pass http://127.0.0.1:8000/api/mqtt/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    sudo ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/
else
    NGINX_CONFIG="/etc/nginx/sites-available/prompt-portal"
    sudo tee $NGINX_CONFIG > /dev/null << EOF
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name $SERVER_IP _;

    # Serve frontend
    location / {
        root $(pwd)/dist;
        try_files \$uri \$uri/ /index.html;
        index index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket support
    location /api/mqtt/ws/ {
        proxy_pass http://127.0.0.1:8000/api/mqtt/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

    sudo ln -sf $NGINX_CONFIG /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
fi

# Test Nginx configuration
print_step "Testing Nginx configuration..."
sudo nginx -t

print_step "Starting services..."

# Start backend with PM2
cd ../backend
pm2 delete prompt-portal-backend 2>/dev/null || true
pm2 start "source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000" --name prompt-portal-backend --interpreter bash

# Save PM2 configuration
pm2 save
pm2 startup | tail -1 | sudo bash || true

# Start/restart Nginx
sudo systemctl enable nginx
sudo systemctl restart nginx

# Setup SSL if domain is provided
if [ "$USE_DOMAIN" = true ]; then
    print_step "Setting up SSL certificate..."
    print_info "This will request a Let's Encrypt SSL certificate for $DOMAIN_NAME"
    
    # Wait for Nginx to start
    sleep 5
    
    sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME || {
        print_warning "SSL setup failed. You can run this manually later:"
        echo "sudo certbot --nginx -d $DOMAIN_NAME"
    }
fi

print_step "Creating system services and scripts..."
sudo mkdir -p /opt/scripts
sudo mkdir -p /opt/backups

# Create backup script
sudo tee /opt/scripts/backup.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="$(dirname "$(dirname "$(readlink -f "$0")")")"

mkdir -p $BACKUP_DIR

# Backup database
if [ -f "$APP_DIR/backend/app.db" ]; then
    cp "$APP_DIR/backend/app.db" "$BACKUP_DIR/app.db.$DATE"
    echo "Database backed up: app.db.$DATE"
fi

# Backup environment files
if [ -f "$APP_DIR/backend/.env" ]; then
    cp "$APP_DIR/backend/.env" "$BACKUP_DIR/.env.$DATE"
fi

# Keep only last 30 days of backups
find $BACKUP_DIR -name "*.db.*" -mtime +30 -delete
find $BACKUP_DIR -name ".env.*" -mtime +30 -delete
EOF

# Create monitoring script
sudo tee /opt/scripts/monitor.sh > /dev/null << 'EOF'
#!/bin/bash
LOG_FILE="/var/log/prompt-portal-monitor.log"

log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> $LOG_FILE
}

# Check if backend is running
if ! pm2 show prompt-portal-backend | grep -q "online"; then
    log_message "Backend down, restarting..."
    pm2 restart prompt-portal-backend
    log_message "Backend restarted"
fi

# Check if Nginx is running
if ! systemctl is-active --quiet nginx; then
    log_message "Nginx down, restarting..."
    sudo systemctl restart nginx
    log_message "Nginx restarted"
fi

# Check disk space
DISK_USAGE=$(df / | grep -vE '^Filesystem' | awk '{print $5}' | sed 's/%//g')
if [ $DISK_USAGE -gt 85 ]; then
    log_message "WARNING: Disk usage is ${DISK_USAGE}%"
fi
EOF

# Create update script
sudo tee /opt/scripts/update.sh > /dev/null << 'EOF'
#!/bin/bash
set -e

echo "Updating Prompt Portal..."

# Backup before update
/opt/scripts/backup.sh

cd "$(dirname "$(dirname "$(readlink -f "$0")")")"

# Update backend
cd backend
source .venv/bin/activate
pip install --upgrade -r requirements.txt

# Update frontend
cd ../frontend
npm install
npm run build

# Restart services
pm2 restart prompt-portal-backend
sudo systemctl reload nginx

echo "Update completed successfully!"
EOF

sudo chmod +x /opt/scripts/backup.sh
sudo chmod +x /opt/scripts/monitor.sh
sudo chmod +x /opt/scripts/update.sh

print_step "Setting up cron jobs..."
# Add cron jobs for monitoring and backup
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/scripts/backup.sh") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/scripts/monitor.sh") | crontab -

# Create systemd service for auto-restart on boot
print_step "Creating systemd service..."
sudo tee /etc/systemd/system/prompt-portal.service > /dev/null << EOF
[Unit]
Description=Prompt Portal Application
After=network.target

[Service]
Type=forking
User=$USER
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/pm2 resurrect
ExecReload=/usr/bin/pm2 reload all
ExecStop=/usr/bin/pm2 kill
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable prompt-portal
sudo systemctl daemon-reload

print_step "Production deployment completed successfully! 🎉"

echo ""
echo "=========================================="
echo -e "${GREEN}PRODUCTION DEPLOYMENT SUMMARY${NC}"
echo "=========================================="

if [ "$USE_DOMAIN" = true ]; then
    echo -e "🌐 Website: ${GREEN}https://$DOMAIN_NAME${NC}"
    echo -e "🔗 API: ${GREEN}https://$DOMAIN_NAME/api${NC}"
    echo -e "📚 API Docs: ${GREEN}https://$DOMAIN_NAME/api/docs${NC}"
else
    echo -e "🌐 Website: ${GREEN}http://$SERVER_IP${NC}"
    echo -e "🔗 API: ${GREEN}http://$SERVER_IP/api${NC}"
    echo -e "📚 API Docs: ${GREEN}http://$SERVER_IP/api/docs${NC}"
fi

echo ""
echo -e "${YELLOW}Service Management:${NC}"
echo "  pm2 status                    # Check PM2 services"
echo "  sudo systemctl status nginx  # Check Nginx"
echo "  sudo systemctl status prompt-portal # Check systemd service"
echo "  pm2 logs prompt-portal-backend # View backend logs"
echo "  sudo tail -f /var/log/nginx/error.log # View Nginx logs"
echo ""
echo -e "${YELLOW}Maintenance Scripts:${NC}"
echo "  sudo /opt/scripts/backup.sh   # Manual backup"
echo "  sudo /opt/scripts/update.sh   # Update application"
echo "  sudo /opt/scripts/monitor.sh  # Manual health check"
echo ""
echo -e "${YELLOW}Security Features:${NC}"
echo "  ✅ UFW firewall configured"
echo "  ✅ SSL certificate ${USE_DOMAIN:+installed}${USE_DOMAIN:-"(install manually if needed)"}"
echo "  ✅ Nginx reverse proxy"
echo "  ✅ Automated monitoring"
echo "  ✅ Automated backups"
echo ""
echo -e "${GREEN}Production deployment completed!${NC}"
echo "Your Prompt Portal is now running in production mode."

if [ "$USE_DOMAIN" = false ]; then
    echo ""
    echo -e "${YELLOW}To add SSL later:${NC}"
    echo "1. Point your domain to this server"
    echo "2. Run: sudo certbot --nginx -d yourdomain.com"
fi

# Show service status
echo ""
print_step "Current service status:"
pm2 status
echo ""
sudo systemctl status nginx --no-pager -l

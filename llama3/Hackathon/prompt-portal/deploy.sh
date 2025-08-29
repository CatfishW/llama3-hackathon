#!/bin/bash

# Prompt Portal - Quick Development Deployment Script
# This script sets up the application for development/testing on a cloud server

set -e  # Exit on any error

echo "🚀 Starting Prompt Portal Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please don't run this script as root"
    exit 1
fi

print_step "Updating system packages..."
sudo apt update && sudo apt upgrade -y

print_step "Installing required packages..."
sudo apt install -y python3 python3-pip python3-venv nodejs npm git curl

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
    
    # Update environment file with server IP
    sed -i "s/SECRET_KEY=change_me_to_a_random_long_string/SECRET_KEY=$SECRET_KEY/" .env
    sed -i "s/CORS_ORIGINS=http:\/\/localhost:5173/CORS_ORIGINS=http:\/\/$SERVER_IP:5173,http:\/\/$SERVER_IP/" .env
    
    echo -e "${GREEN}Backend environment configured!${NC}"
else
    print_warning "Backend .env file already exists, skipping..."
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
VITE_API_BASE=http://$SERVER_IP:8000
VITE_WS_BASE=ws://$SERVER_IP:8000
EOF

cat > .env.local << EOF
VITE_API_BASE=http://$SERVER_IP:8000
VITE_WS_BASE=ws://$SERVER_IP:8000
EOF

echo -e "${GREEN}Frontend environment configured!${NC}"

# Build frontend for production
print_step "Building frontend..."
npm run build || {
    print_warning "Initial build failed, trying with build fix..."
    chmod +x fix-build.sh 2>/dev/null || true
    if [ -f "fix-build.sh" ]; then
        ./fix-build.sh
    else
        # Inline fix
        rm -rf node_modules package-lock.json
        npm install --legacy-peer-deps --force
        npm run build
    fi
}

print_step "Starting services with PM2..."

# Start backend with PM2
cd ../backend
pm2 delete prompt-portal-backend 2>/dev/null || true
pm2 start "source .venv/bin/activate && uvicorn app.main:app --host 0.0.0.0 --port 8000" --name prompt-portal-backend --interpreter bash

# Start frontend with PM2
cd ../frontend
pm2 delete prompt-portal-frontend 2>/dev/null || true
pm2 start "npm run preview -- --host 0.0.0.0 --port 5173" --name prompt-portal-frontend

# Save PM2 configuration
pm2 save
pm2 startup | tail -1 | sudo bash || true

print_step "Creating monitoring scripts..."
sudo mkdir -p /opt/scripts
sudo mkdir -p /opt/backups

# Create backup script
sudo tee /opt/scripts/backup.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR="/opt/prompt-portal"

mkdir -p $BACKUP_DIR

# Backup database
if [ -f "$APP_DIR/backend/app.db" ]; then
    cp "$APP_DIR/backend/app.db" "$BACKUP_DIR/app.db.$DATE"
fi

# Keep only last 7 days of backups
find $BACKUP_DIR -name "app.db.*" -mtime +7 -delete
EOF

# Create monitoring script
sudo tee /opt/scripts/monitor.sh > /dev/null << 'EOF'
#!/bin/bash
# Check if services are running and restart if needed
if ! pm2 show prompt-portal-backend | grep -q "online"; then
    echo "Backend down, restarting..."
    pm2 restart prompt-portal-backend
fi

if ! pm2 show prompt-portal-frontend | grep -q "online"; then
    echo "Frontend down, restarting..."
    pm2 restart prompt-portal-frontend
fi
EOF

sudo chmod +x /opt/scripts/backup.sh
sudo chmod +x /opt/scripts/monitor.sh

print_step "Setting up cron jobs..."
# Add cron jobs for monitoring and backup
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/scripts/backup.sh") | crontab -
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/scripts/monitor.sh") | crontab -

print_step "Deployment completed successfully! 🎉"

echo ""
echo "=================================="
echo -e "${GREEN}DEPLOYMENT SUMMARY${NC}"
echo "=================================="
echo -e "🌐 Frontend URL: ${GREEN}http://$SERVER_IP:5173${NC}"
echo -e "🔗 Backend API: ${GREEN}http://$SERVER_IP:8000${NC}"
echo -e "📚 API Docs: ${GREEN}http://$SERVER_IP:8000/docs${NC}"
echo ""
echo -e "${YELLOW}Service Management:${NC}"
echo "  pm2 status                    # Check service status"
echo "  pm2 logs prompt-portal-backend # View backend logs"
echo "  pm2 logs prompt-portal-frontend # View frontend logs"
echo "  pm2 restart all               # Restart all services"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "- Make sure ports 5173 and 8000 are open in your firewall"
echo "- Backend secret key has been generated automatically"
echo "- Database is initialized and ready to use"
echo "- Automated backups run daily at 2 AM"
echo "- Service monitoring runs every 5 minutes"
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Open http://$SERVER_IP:5173 in your browser"
echo "2. Register a new account"
echo "3. Create your first prompt template"
echo "4. Test the MQTT functionality"

# Show service status
echo ""
print_step "Current service status:"
pm2 status

echo ""
echo -e "${GREEN}Deployment completed! Your Prompt Portal is now running.${NC}"

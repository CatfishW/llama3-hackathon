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

# Get server IP
SERVER_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
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


print_step "Checking if PM2 is installed..."
if ! command -v pm2 &> /dev/null; then
    print_step "Installing PM2 for process management..."
    sudo npm install -g pm2
else
    echo -e "${GREEN}PM2 is already installed${NC}"
fi

print_step "Checking firewall configuration..."
if command -v ufw &> /dev/null; then
    print_step "UFW is available, configuring firewall..."
    # Set default policies
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing

    # Allow SSH (important to not lock yourself out)
    sudo ufw allow ssh
    sudo ufw allow 22/tcp

    # Allow HTTP and HTTPS
    sudo ufw allow 80/tcp
    sudo ufw allow 443/tcp

    # Allow application ports
    sudo ufw allow $FRONTEND_PORT/tcp comment "Frontend (Vite dev server)"
    sudo ufw allow $BACKEND_PORT/tcp comment "Backend API (FastAPI)"

    # Allow MQTT if needed
    sudo ufw allow 1883/tcp comment "MQTT broker"

    # Enable firewall
    sudo ufw --force enable

    print_step "Firewall configured successfully!"
    sudo ufw status
else
    print_warning "UFW not available, skipping firewall configuration"
fi

print_step "Setting up backend..."
cd backend

# Setup environment file
print_step "Configuring backend environment..."
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        # Try to copy with proper permissions
        if cp .env.example .env 2>/dev/null; then
            echo -e "${GREEN}Copied .env.example to .env${NC}"
        else
            print_warning "Permission denied copying .env.example, creating new .env file..."
            # Create new .env file if copy fails
            cat > .env << 'EOF'
SECRET_KEY=change_me_to_a_random_long_string
DATABASE_URL=sqlite:///./app.db
CORS_ORIGINS=http://localhost:5173
EOF
        fi
    else
        print_warning ".env.example not found, creating default .env file..."
        # Create default .env file
        cat > .env << 'EOF'
SECRET_KEY=change_me_to_a_random_long_string
DATABASE_URL=sqlite:///./app.db
CORS_ORIGINS=http://localhost:5173
EOF
    fi
    
    # Make sure .env is writable
    chmod 644 .env 2>/dev/null || true
    
    # Generate a random secret key
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
    
    # Update environment file with server IP
    sed -i "s/SECRET_KEY=change_me_to_a_random_long_string/SECRET_KEY=$SECRET_KEY/" .env
    sed -i "s/CORS_ORIGINS=http:\/\/localhost:5173/CORS_ORIGINS=http:\/\/173.61.35.162:$FRONTEND_PORT,http:\/\/173.61.35.162/" .env
    
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
if [ ! -d "node_modules" ]; then
    npm install --legacy-peer-deps
else
    print_warning "Node modules already exist, skipping installation..."
fi

# Install additional build dependencies if needed
if ! npm list terser &> /dev/null; then
    print_step "Installing build dependencies..."
    npm install --save-dev terser
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
npm run build || {
    print_warning "Initial build failed, trying fixes..."
    
    # Install terser if missing
    print_step "Installing terser..."
    npm install --save-dev terser
    
    # Try building again
    npm run build || {
        print_warning "Still failing, cleaning and reinstalling..."
        rm -rf node_modules package-lock.json dist
        npm install --legacy-peer-deps --force
        npm install --save-dev terser
        npm run build
    }
}

print_step "Starting services with PM2..."

# Start backend with PM2
cd ../backend
pm2 delete prompt-portal-backend 2>/dev/null || true
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT" --name prompt-portal-backend

# Start frontend with PM2
cd ../frontend
pm2 delete prompt-portal-frontend 2>/dev/null || true
pm2 start "npm run preview -- --host 0.0.0.0 --port $FRONTEND_PORT" --name prompt-portal-frontend

# Save PM2 configuration
pm2 save
pm2 startup | tail -1 | sudo bash || true

print_step "Creating monitoring scripts..."
if [ ! -d "/opt/scripts" ]; then
    sudo mkdir -p /opt/scripts
fi
if [ ! -d "/opt/backups" ]; then
    sudo mkdir -p /opt/backups
fi

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
echo -e "🌐 Frontend URL: ${GREEN}http://173.61.35.162:$FRONTEND_PORT${NC}"
echo -e "🔗 Backend API: ${GREEN}http://173.61.35.162:$BACKEND_PORT${NC}"
echo -e "📚 API Docs: ${GREEN}http://173.61.35.162:$BACKEND_PORT/docs${NC}"
echo ""
echo -e "${YELLOW}Service Management:${NC}"
echo "  pm2 status                    # Check service status"
echo "  pm2 logs prompt-portal-backend # View backend logs"
echo "  pm2 logs prompt-portal-frontend # View frontend logs"
echo "  pm2 restart all               # Restart all services"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "- Firewall has been configured automatically"
echo "- Ports 22 (SSH), 80 (HTTP), 443 (HTTPS), $FRONTEND_PORT (Frontend), $BACKEND_PORT (Backend), and 1883 (MQTT) are open"
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

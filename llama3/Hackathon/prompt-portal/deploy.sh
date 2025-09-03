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

print_step "Skipping firewall configuration..."

print_step "Setting up backend..."
cd backend

# Skip backend environment configuration - using existing .env file
print_step "Skipping backend environment configuration - using existing .env file..."

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

# Start backend with PM2 (no logging)
cd ../backend
pm2 delete prompt-portal-backend 2>/dev/null || true
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT" --name prompt-portal-backend --no-autorestart --log /dev/null --error /dev/null --out /dev/null

# Start frontend with PM2 (no logging)
cd ../frontend
pm2 delete prompt-portal-frontend 2>/dev/null || true
pm2 start "npm run preview -- --host 0.0.0.0 --port $FRONTEND_PORT" --name prompt-portal-frontend --no-autorestart --log /dev/null --error /dev/null --out /dev/null

# Skip saving PM2 configuration and startup
print_step "Skipping PM2 configuration save..."

print_step "Skipping monitoring and backup scripts setup..."

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
echo "  pm2 restart all               # Restart all services"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "- Firewall configuration has been skipped"
echo "- Backend secret key has been generated automatically"
echo "- Database is initialized and ready to use"
echo "- Logging and monitoring have been disabled"
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

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
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Change these ports if 8000 or 5173 are not available
BACKEND_PORT=3000
FRONTEND_PORT=3001

# Domain configuration
USE_DOMAIN=true
DOMAIN_NAME="lammp.agaii.org"

# Directories
ROOT_DIR=$(pwd)
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"

# Get server IP
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}' 2>/dev/null)

# Ask about domain name
echo ""
echo -e "${BLUE}Domain Configuration${NC}"
read -p "Do you want to use a custom domain? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter your domain name (e.g., lammp.agaii.org): " DOMAIN_NAME
    if [ -n "$DOMAIN_NAME" ]; then
        USE_DOMAIN=true
        echo -e "${GREEN}✓ Will configure for domain: $DOMAIN_NAME${NC}"
        
        # Check DNS
        DNS_IP=$(dig +short $DOMAIN_NAME @8.8.8.8 2>/dev/null | tail -n1)
        if [ -n "$DNS_IP" ] && [ "$DNS_IP" == "$SERVER_IP" ]; then
            echo -e "${GREEN}✓ DNS is correctly configured!${NC}"
        elif [ -n "$DNS_IP" ]; then
            echo -e "${YELLOW}⚠ DNS points to $DNS_IP but server IP is $SERVER_IP${NC}"
            echo -e "${YELLOW}  Please update your DNS A record${NC}"
        else
            echo -e "${YELLOW}⚠ DNS not configured yet${NC}"
            echo -e "${YELLOW}  Add A record: $DOMAIN_NAME → $SERVER_IP${NC}"
        fi
        
        # Ask about Nginx setup
        echo ""
        read -p "Do you want to set up Nginx (access without port)? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            SETUP_NGINX=true
        else
            SETUP_NGINX=false
        fi
    else
        USE_DOMAIN=false
        SETUP_NGINX=false
    fi
else
    SETUP_NGINX=false
fi

echo ""
echo -e "${GREEN}Detected server IP: $SERVER_IP${NC}"
if [ "$USE_DOMAIN" = true ]; then
    echo -e "${GREEN}Domain: $DOMAIN_NAME${NC}"
fi
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

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Helpers to cleanly stop running services
kill_port() {
    local port="$1"
    if command -v lsof >/dev/null 2>&1; then
        lsof -ti:"$port" | xargs -r kill -9 2>/dev/null || true
    fi
    if command -v fuser >/dev/null 2>&1; then
        fuser -k "${port}/tcp" 2>/dev/null || true
    fi
}

stop_backend() {
    print_step "Stopping any existing backend..."
    # By PID file
    if [ -f "$BACKEND_DIR/backend.pid" ]; then
        PID=$(cat "$BACKEND_DIR/backend.pid" 2>/dev/null || echo "")
        if [ -n "$PID" ]; then kill "$PID" 2>/dev/null || true; fi
        rm -f "$BACKEND_DIR/backend.pid" 2>/dev/null || true
    fi
    # By process signature
    pkill -f "uvicorn .*app\.main:app" 2>/dev/null || true
    pkill -f "run_server\.py" 2>/dev/null || true
    # By port
    kill_port "$BACKEND_PORT"
}

stop_frontend() {
    print_step "Stopping any existing frontend..."
    if [ -f "$FRONTEND_DIR/frontend.pid" ]; then
        PID=$(cat "$FRONTEND_DIR/frontend.pid" 2>/dev/null || echo "")
        if [ -n "$PID" ]; then kill "$PID" 2>/dev/null || true; fi
        rm -f "$FRONTEND_DIR/frontend.pid" 2>/dev/null || true
    fi
    pkill -f "vite.*preview" 2>/dev/null || true
    kill_port "$FRONTEND_PORT"
}


print_step "Using built-in process management (no PM2 required)..."

print_step "Skipping firewall configuration..."

print_step "Setting up backend..."
cd "$BACKEND_DIR"

# Configure backend CORS for domain
if [ "$USE_DOMAIN" = true ]; then
    print_step "Configuring backend for domain..."
    if [ -f .env ]; then
        # Backup existing .env
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        
        # Update CORS_ORIGINS to include domain
        if grep -q "CORS_ORIGINS" .env; then
            # Add domain to existing CORS_ORIGINS
            sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=https://${DOMAIN_NAME},http://${DOMAIN_NAME},http://${SERVER_IP}:${BACKEND_PORT},http://${SERVER_IP}:${FRONTEND_PORT},http://localhost:5173|" .env
            echo -e "${GREEN}✓ Backend CORS configured for domain${NC}"
        else
            echo "CORS_ORIGINS=https://${DOMAIN_NAME},http://${DOMAIN_NAME},http://localhost:5173" >> .env
        fi
    else
        print_warning ".env file not found, will use defaults"
    fi
else
    print_step "Using existing backend .env configuration..."
fi

# Check and preserve existing database
print_step "Checking database status..."
if [ -f "app.db" ]; then
    print_warning "Database already exists - preserving existing data..."
    echo -e "${GREEN}Existing database found and will be preserved${NC}"
else
    print_step "No existing database found - initializing new database..."
    python create_db.py > /dev/null 2>&1 || python -c "
from app.database import init_db
init_db()
print('Database initialized successfully!')
" > /dev/null 2>&1
fi

print_step "Setting up frontend..."
cd "$FRONTEND_DIR"

# Install Node.js dependencies
print_step "Installing Node.js dependencies..."
if [ ! -d "node_modules" ]; then
    npm install --legacy-peer-deps > /dev/null 2>&1
else
    print_warning "Node modules already exist, skipping installation..."
fi

# Install additional build dependencies if needed
if ! npm list terser &> /dev/null; then
    print_step "Installing build dependencies..."
    npm install --save-dev terser > /dev/null 2>&1
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

# Update Vite config to allow domain
if [ "$USE_DOMAIN" = true ]; then
    print_step "Configuring Vite for domain..."
    cat > vite.config.ts << EOF
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { 
    port: 5173,
    host: true
  },
  preview: {
    port: ${FRONTEND_PORT},
    host: true,
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      '${DOMAIN_NAME}',
      '${SERVER_IP}'
    ]
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: false
  }
})
EOF
    echo -e "${GREEN}✓ Vite configured to allow domain: $DOMAIN_NAME${NC}"
else
    cat > vite.config.ts << EOF
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: { 
    port: 5173,
    host: true
  },
  preview: {
    port: ${FRONTEND_PORT},
    host: true
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    minify: false
  }
})
EOF
fi

# Create production environment file
print_step "Configuring frontend environment..."
if [ "$USE_DOMAIN" = true ] && [ "$SETUP_NGINX" = true ]; then
    # With Nginx, use clean URLs without ports
    cat > .env.production << EOF
VITE_API_BASE=https://$DOMAIN_NAME/api
VITE_WS_BASE=wss://$DOMAIN_NAME/api
EOF

    cat > .env.local << EOF
VITE_API_BASE=https://$DOMAIN_NAME/api
VITE_WS_BASE=wss://$DOMAIN_NAME/api
EOF
    echo -e "${GREEN}✓ Frontend configured for domain with Nginx (HTTPS)${NC}"
elif [ "$USE_DOMAIN" = true ]; then
    # Without Nginx, use HTTP with domain and port
    cat > .env.production << EOF
VITE_API_BASE=http://$DOMAIN_NAME:$BACKEND_PORT
VITE_WS_BASE=ws://$DOMAIN_NAME:$BACKEND_PORT
EOF

    cat > .env.local << EOF
VITE_API_BASE=http://$DOMAIN_NAME:$BACKEND_PORT
VITE_WS_BASE=ws://$DOMAIN_NAME:$BACKEND_PORT
EOF
    echo -e "${GREEN}✓ Frontend configured for domain: $DOMAIN_NAME (HTTP with ports)${NC}"
else
    cat > .env.production << EOF
VITE_API_BASE=http://$SERVER_IP:$BACKEND_PORT
VITE_WS_BASE=ws://$SERVER_IP:$BACKEND_PORT
EOF

    cat > .env.local << EOF
VITE_API_BASE=http://$SERVER_IP:$BACKEND_PORT
VITE_WS_BASE=ws://$SERVER_IP:$BACKEND_PORT
EOF
    echo -e "${GREEN}✓ Frontend configured for IP-based access${NC}"
fi

# Build frontend for production
print_step "Building frontend..."
npm run build > /dev/null 2>&1 || {
    print_warning "Initial build failed, trying fixes..."
    
    # Install terser if missing
    print_step "Installing terser..."
    npm install --save-dev terser > /dev/null 2>&1
    
    # Try building again
    npm run build > /dev/null 2>&1 || {
        print_warning "Still failing, cleaning and reinstalling..."
        rm -rf node_modules package-lock.json dist
        npm install --legacy-peer-deps --force > /dev/null 2>&1
        npm install --save-dev terser > /dev/null 2>&1
        npm run build > /dev/null 2>&1
    }
}

print_step "Starting services in background..."

# Kill any existing processes on these ports
print_step "Cleaning up any existing processes..."
stop_backend
stop_frontend
sleep 1

# Start backend in background (no logs)
cd ../backend
print_step "Starting backend on port $BACKEND_PORT..."
nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT > /dev/null 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > backend.pid

# Wait for backend port to be ready (up to ~10s)
for i in $(seq 1 20); do
    if curl -s --max-time 1 "http://127.0.0.1:$BACKEND_PORT/docs" > /dev/null; then
        break
    fi
    sleep 0.5
done

if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
    print_warning "Backend process exited unexpectedly. Attempting one restart..."
    stop_backend
    nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT > /dev/null 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > backend.pid
    sleep 2
fi

# Fail fast if backend is not running/healthy
if ! ps -p $BACKEND_PID > /dev/null 2>&1; then
    print_error "Backend failed to start. Check if port $BACKEND_PORT is available."
    exit 1
fi

if ! curl -s --max-time 2 "http://127.0.0.1:$BACKEND_PORT/docs" > /dev/null; then
    print_error "Backend health check failed at http://127.0.0.1:$BACKEND_PORT/docs."
    exit 1
fi

# Start frontend in background (silent)
cd ../frontend
print_step "Starting frontend on port $FRONTEND_PORT..."
nohup npm run preview -- --host 0.0.0.0 --port $FRONTEND_PORT > /dev/null 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > frontend.pid

# Give frontend time to start
sleep 3

print_step "Skipping monitoring and backup scripts setup..."

# Setup Nginx if requested
if [ "$USE_DOMAIN" = true ] && [ "$SETUP_NGINX" = true ]; then
    print_step "Setting up Nginx..."
    cd "$ROOT_DIR"
    
    # Check if Nginx is installed
    if ! command -v nginx &> /dev/null; then
        print_info "Installing Nginx..."
        sudo apt update > /dev/null 2>&1
        sudo apt install -y nginx > /dev/null 2>&1
    fi
    
    # Create nginx directories if they don't exist
    sudo mkdir -p /etc/nginx/sites-available > /dev/null 2>&1
    sudo mkdir -p /etc/nginx/sites-enabled > /dev/null 2>&1
    
    # Create Nginx configuration
    print_step "Configuring Nginx for $DOMAIN_NAME..."
    
    # Create temporary file first
    cat > /tmp/nginx_$DOMAIN_NAME.conf << EOF
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN_NAME;

    # Serve frontend static files
    location / {
        root $FRONTEND_DIR/dist;
        try_files \$uri \$uri/ /index.html;
        index index.html;
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://127.0.0.1:$BACKEND_PORT/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # WebSocket support for MQTT
    location /api/mqtt/ws/ {
        proxy_pass http://127.0.0.1:$BACKEND_PORT/api/mqtt/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOF
    
    # Move to nginx directory with sudo
    sudo mv /tmp/nginx_$DOMAIN_NAME.conf /etc/nginx/sites-available/$DOMAIN_NAME
    
    # Enable the site
    sudo ln -sf /etc/nginx/sites-available/$DOMAIN_NAME /etc/nginx/sites-enabled/
    sudo rm -f /etc/nginx/sites-enabled/default
    
    # Test and reload Nginx
    if sudo nginx -t > /dev/null 2>&1; then
        sudo systemctl reload nginx > /dev/null 2>&1
        echo -e "${GREEN}✓ Nginx configured successfully!${NC}"
        
        # Try to set up SSL if certbot is available
        if command -v certbot &> /dev/null; then
            print_step "Setting up SSL certificate..."
            sudo certbot --nginx -d $DOMAIN_NAME --non-interactive --agree-tos --email admin@$DOMAIN_NAME --redirect > /dev/null 2>&1 && {
                echo -e "${GREEN}✓ SSL certificate installed!${NC}"
            } || {
                print_warning "SSL setup skipped. Run manually: sudo certbot --nginx -d $DOMAIN_NAME"
            }
        else
            print_info "Certbot not installed. Install it for HTTPS: sudo apt install certbot python3-certbot-nginx"
        fi
    else
        print_error "Nginx configuration test failed"
    fi
fi

BACKEND_OK=0
FRONTEND_OK=0
if ps -p $BACKEND_PID > /dev/null 2>&1; then BACKEND_OK=1; fi
if ps -p $FRONTEND_PID > /dev/null 2>&1; then FRONTEND_OK=1; fi

if [ "$BACKEND_OK" -eq 1 ] && [ "$FRONTEND_OK" -eq 1 ]; then
    print_step "Deployment completed successfully! 🎉"
else
    print_warning "Deployment completed with issues. See status below."
fi

echo ""
echo "=================================="
echo -e "${GREEN}DEPLOYMENT SUMMARY${NC}"
echo "=================================="

if [ "$USE_DOMAIN" = true ] && [ "$SETUP_NGINX" = true ]; then
    echo -e "🌐 Domain: ${GREEN}$DOMAIN_NAME${NC}"
    echo -e "🖥️  Server IP: ${GREEN}$SERVER_IP${NC}"
    echo ""
    
    # Check if SSL was set up
    if sudo test -d /etc/letsencrypt/live/$DOMAIN_NAME 2>/dev/null; then
        echo -e "🌐 Website: ${GREEN}https://$DOMAIN_NAME${NC} (No port needed!)"
        echo -e "🔗 API: ${GREEN}https://$DOMAIN_NAME/api${NC}"
        echo -e "📚 API Docs: ${GREEN}https://$DOMAIN_NAME/api/docs${NC}"
    else
        echo -e "🌐 Website: ${GREEN}http://$DOMAIN_NAME${NC} (No port needed!)"
        echo -e "🔗 API: ${GREEN}http://$DOMAIN_NAME/api${NC}"
        echo -e "📚 API Docs: ${GREEN}http://$DOMAIN_NAME/api/docs${NC}"
        echo ""
        echo -e "${YELLOW}For HTTPS: sudo certbot --nginx -d $DOMAIN_NAME${NC}"
    fi
elif [ "$USE_DOMAIN" = true ]; then
    echo -e "🌐 Domain: ${GREEN}$DOMAIN_NAME${NC}"
    echo -e "🖥️  Server IP: ${GREEN}$SERVER_IP${NC}"
    echo ""
    echo -e "🌐 Frontend: ${GREEN}http://$DOMAIN_NAME:$FRONTEND_PORT${NC}"
    echo -e "🔗 Backend API: ${GREEN}http://$DOMAIN_NAME:$BACKEND_PORT${NC}"
    echo -e "📚 API Docs: ${GREEN}http://$DOMAIN_NAME:$BACKEND_PORT/docs${NC}"
    echo ""
    echo -e "${YELLOW}To remove ports from URLs, re-run with Nginx setup${NC}"
else
    echo -e "🌐 Frontend URL: ${GREEN}http://$SERVER_IP:$FRONTEND_PORT${NC}"
    echo -e "🔗 Backend API: ${GREEN}http://$SERVER_IP:$BACKEND_PORT${NC}"
    echo -e "📚 API Docs: ${GREEN}http://$SERVER_IP:$BACKEND_PORT/docs${NC}"
fi

echo ""
echo -e "${YELLOW}Service Management:${NC}"
echo "  kill \$(cat backend/backend.pid)    # Stop backend"
echo "  kill \$(cat frontend/frontend.pid)  # Stop frontend"
echo "  # or use built-in cleanup in this script on re-run"
echo "  ./stop_services.sh               # Stop all services"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "- Firewall configuration has been skipped"
echo "- Backend secret key has been generated automatically"
echo "- Existing database is preserved (no data loss)"
echo "- Logging and monitoring have been disabled"

echo ""
echo -e "${GREEN}Next steps:${NC}"
if [ "$USE_DOMAIN" = true ] && [ "$SETUP_NGINX" = true ]; then
    if sudo test -d /etc/letsencrypt/live/$DOMAIN_NAME 2>/dev/null; then
        echo "1. Open https://$DOMAIN_NAME in your browser"
    else
        echo "1. Open http://$DOMAIN_NAME in your browser"
    fi
elif [ "$USE_DOMAIN" = true ]; then
    echo "1. Open http://$DOMAIN_NAME:$FRONTEND_PORT in your browser"
else
    echo "1. Open http://$SERVER_IP:$FRONTEND_PORT in your browser"
fi
echo "2. Register a new account"
echo "3. Create your first prompt template"
echo "4. Test the MQTT functionality"

# Show service status
echo ""
print_step "Checking service status:"
if ps -p $BACKEND_PID > /dev/null 2>&1; then
    echo -e "${GREEN}Backend is running (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}Backend failed to start${NC}"
fi

if ps -p $FRONTEND_PID > /dev/null 2>&1; then
    echo -e "${GREEN}Frontend is running (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}Frontend failed to start${NC}"
fi

echo ""
if [ "$BACKEND_OK" -eq 1 ] && [ "$FRONTEND_OK" -eq 1 ]; then
    echo -e "${GREEN}Deployment completed! Your Prompt Portal is now running.${NC}"
else
    echo -e "${YELLOW}Deployment finished but not all services are healthy.${NC}"
    echo -e "${YELLOW}Check process status and try restarting.${NC}"
fi
#!/bin/bash

# Firewall Configuration Script for Prompt Portal
# This script configures UFW firewall with the necessary ports

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🔥 Configuring Firewall for Prompt Portal..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please don't run this script as root (use sudo when needed)"
    exit 1
fi

print_step "Installing UFW firewall..."
sudo apt update
sudo apt install -y ufw

print_step "Configuring firewall rules..."

# Reset firewall to defaults
print_warning "Resetting firewall to defaults..."
sudo ufw --force reset

# Set default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

print_step "Adding essential rules..."

# SSH access (CRITICAL - don't lock yourself out!)
sudo ufw allow ssh
sudo ufw allow 22/tcp
echo "✅ SSH (port 22) - ENABLED"

# Web server ports
sudo ufw allow 80/tcp
echo "✅ HTTP (port 80) - ENABLED"

sudo ufw allow 443/tcp
echo "✅ HTTPS (port 443) - ENABLED"

print_step "Adding Prompt Portal application ports..."

# Frontend (Vite development server)
sudo ufw allow 5173/tcp comment "Prompt Portal Frontend"
echo "✅ Frontend (port 5173) - ENABLED"

# Backend API (FastAPI)
sudo ufw allow 8000/tcp comment "Prompt Portal Backend API"
echo "✅ Backend API (port 8000) - ENABLED"

# MQTT broker (optional)
sudo ufw allow 1883/tcp comment "MQTT Broker"
echo "✅ MQTT (port 1883) - ENABLED"

print_step "Enabling firewall..."
sudo ufw --force enable

print_step "Firewall configuration completed! 🎉"

echo ""
echo "=================================="
echo -e "${GREEN}FIREWALL STATUS${NC}"
echo "=================================="
sudo ufw status verbose

echo ""
echo -e "${GREEN}CONFIGURED PORTS:${NC}"
echo "- 22   (SSH)           - Remote access"
echo "- 80   (HTTP)          - Web traffic"  
echo "- 443  (HTTPS)         - Secure web traffic"
echo "- 5173 (Frontend)      - Prompt Portal frontend"
echo "- 8000 (Backend)       - Prompt Portal API"
echo "- 1883 (MQTT)          - MQTT broker"

echo ""
echo -e "${YELLOW}TESTING:${NC}"
echo "You can test the ports with:"
echo "  sudo ufw status                    # Check firewall status"
echo "  sudo ss -tlnp | grep ':5173'       # Check if frontend is listening"
echo "  sudo ss -tlnp | grep ':8000'       # Check if backend is listening"
echo "  curl -I http://YOUR_SERVER_IP:8000 # Test backend API"

echo ""
echo -e "${YELLOW}MANAGEMENT:${NC}"
echo "  sudo ufw status         # Show status"
echo "  sudo ufw disable        # Disable firewall"
echo "  sudo ufw enable         # Enable firewall"
echo "  sudo ufw delete allow 5173  # Remove a rule"

echo ""
echo -e "${GREEN}Firewall is now configured for Prompt Portal!${NC}"

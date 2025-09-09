#!/bin/bash

# MQTT Broker Setup Script for Prompt Portal
# This script installs and configures Mosquitto MQTT broker

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

echo "🔧 Setting up MQTT Broker (Mosquitto) for Prompt Portal..."

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_error "Please don't run this script as root"
    exit 1
fi

print_step "Installing Mosquitto MQTT broker..."
sudo apt update
sudo apt install -y mosquitto mosquitto-clients

print_step "Configuring Mosquitto..."

# Create configuration file
sudo tee /etc/mosquitto/conf.d/prompt-portal.conf > /dev/null << 'EOF'
# Prompt Portal MQTT Configuration

# Listen on all interfaces
listener 1883 0.0.0.0

# Allow anonymous connections (for development)
# For production, consider setting up authentication
allow_anonymous true

# Persistence
persistence true
persistence_location /var/lib/mosquitto/

# Logging disabled for security - no logs stored on server

# Maximum connections
max_connections 1000

# Message limits
message_size_limit 8192
EOF

print_step "Starting and enabling Mosquitto service..."
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto

# Wait for service to start
sleep 2

print_step "Testing MQTT broker..."
if mosquitto_pub -h localhost -t test/connection -m "test" 2>/dev/null; then
    echo -e "${GREEN}✅ MQTT broker is working correctly!${NC}"
else
    print_error "❌ MQTT broker test failed"
    sudo systemctl status mosquitto
    exit 1
fi

print_step "Setting up MQTT authentication (optional)..."
read -p "Do you want to set up MQTT authentication? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    read -p "Enter MQTT username: " mqtt_user
    read -s -p "Enter MQTT password: " mqtt_pass
    echo
    
    # Create password file
    sudo mosquitto_passwd -c /etc/mosquitto/passwd $mqtt_user << EOF
$mqtt_pass
EOF
    
    # Update configuration to require authentication
    sudo tee /etc/mosquitto/conf.d/prompt-portal.conf > /dev/null << 'EOF'
# Prompt Portal MQTT Configuration

# Listen on all interfaces
listener 1883 0.0.0.0

# Require authentication
allow_anonymous false
password_file /etc/mosquitto/passwd

# Persistence
persistence true
persistence_location /var/lib/mosquitto/

# Logging
# Logging disabled for security - no logs stored on server

# Maximum connections
max_connections 1000

# Message limits
message_size_limit 8192
EOF
    
    sudo systemctl restart mosquitto
    sleep 2
    
    print_step "Testing authenticated connection..."
    if mosquitto_pub -h localhost -t test/auth -m "auth_test" -u $mqtt_user -P $mqtt_pass 2>/dev/null; then
        echo -e "${GREEN}✅ MQTT authentication is working!${NC}"
        
        print_warning "Update your backend .env file with MQTT credentials:"
        echo "MQTT_USERNAME=$mqtt_user"
        echo "MQTT_PASSWORD=$mqtt_pass"
    else
        print_error "❌ MQTT authentication test failed"
        exit 1
    fi
fi

print_step "Creating MQTT monitoring script (NO LOGGING)..."
sudo tee /opt/scripts/mqtt-monitor.sh > /dev/null << 'EOF'
#!/bin/bash

# Check if Mosquitto is running (no logging for security)
if ! systemctl is-active --quiet mosquitto; then
    sudo systemctl restart mosquitto
fi

# Test MQTT connection without logging
if ! mosquitto_pub -h localhost -t health/check -m "$(date)" 2>/dev/null; then
    sudo systemctl restart mosquitto
fi
EOF

sudo chmod +x /opt/scripts/mqtt-monitor.sh

print_step "Adding MQTT monitoring to cron..."
(crontab -l 2>/dev/null; echo "*/2 * * * * /opt/scripts/mqtt-monitor.sh") | crontab -

print_step "Setting up firewall rule for MQTT..."
sudo ufw allow 1883/tcp

print_step "MQTT broker setup completed! 🎉"

echo ""
echo "=================================="
echo -e "${GREEN}MQTT SETUP SUMMARY${NC}"
echo "=================================="
echo -e "📡 MQTT Broker: ${GREEN}Mosquitto${NC}"
echo -e "🔌 Port: ${GREEN}1883${NC}"
echo -e "🌐 Access: ${GREEN}All interfaces (0.0.0.0)${NC}"
echo -e "🔐 Authentication: ${GREEN}$([ -f /etc/mosquitto/passwd ] && echo "Enabled" || echo "Disabled")${NC}"
echo ""
echo -e "${YELLOW}Testing Commands:${NC}"
echo "  # Subscribe to test topic:"
echo "  mosquitto_sub -h localhost -t 'test/+'"
echo ""
echo "  # Publish test message:"
echo "  mosquitto_pub -h localhost -t 'test/hello' -m 'Hello MQTT'"
echo ""
echo "  # Monitor maze topics:"
echo "  mosquitto_sub -h localhost -t 'maze/+'"
echo ""
echo -e "${YELLOW}Service Management:${NC}"
echo "  sudo systemctl status mosquitto   # Check status"
echo "  sudo systemctl restart mosquitto  # Restart broker"
echo "  systemctl status mosquitto           # Check status"
echo "  # Note: Logging has been disabled for security"
echo ""
echo -e "${YELLOW}Configuration:${NC}"
echo "  Config file: /etc/mosquitto/conf.d/prompt-portal.conf"
echo "  # Note: Log files have been disabled for security"
echo "  Data directory: /var/lib/mosquitto/"
echo ""

if [ -f /etc/mosquitto/passwd ]; then
    echo -e "${YELLOW}Important:${NC}"
    echo "Don't forget to update your backend .env file with MQTT credentials!"
    echo ""
fi

echo -e "${GREEN}MQTT broker is ready for your Prompt Portal application!${NC}"

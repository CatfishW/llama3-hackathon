#!/bin/bash

# ============================================================================
# Llama.cpp Web Server Deployment Script (Linux/Ubuntu)
# ============================================================================
#
# Usage:
#   sudo ./deploy.sh [install|start|stop|restart|logs|status]
#
# Examples:
#   sudo ./deploy.sh install          # First-time installation
#   sudo ./deploy.sh start            # Start the service
#   sudo ./deploy.sh stop             # Stop the service
#   sudo ./deploy.sh restart          # Restart the service
#   sudo ./deploy.sh logs             # View service logs
#   sudo ./deploy.sh status           # Check service status
#

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="llamacpp-web"
SERVICE_USER="llamacpp"
SERVICE_GROUP="llamacpp"
INSTALL_DIR="/opt/llamacpp-web"
VENV_DIR="${INSTALL_DIR}/venv"
LOG_DIR="/var/log/llamacpp-web"
PID_FILE="/var/run/${SERVICE_NAME}.pid"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

install_dependencies() {
    log_info "Installing system dependencies..."
    
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        git \
        curl \
        nginx \
        supervisor
    
    log_success "System dependencies installed"
}

create_user() {
    log_info "Creating service user..."
    
    if id "$SERVICE_USER" &>/dev/null; then
        log_warning "User $SERVICE_USER already exists"
    else
        useradd -m -s /bin/bash -d /home/$SERVICE_USER $SERVICE_USER
        log_success "Created user $SERVICE_USER"
    fi
}

setup_directories() {
    log_info "Setting up directories..."
    
    mkdir -p $INSTALL_DIR
    mkdir -p $LOG_DIR
    
    cp -r $SCRIPT_DIR/llamacppWeb/* $INSTALL_DIR/
    
    chown -R $SERVICE_USER:$SERVICE_GROUP $INSTALL_DIR
    chown -R $SERVICE_USER:$SERVICE_GROUP $LOG_DIR
    
    chmod -R 755 $INSTALL_DIR
    chmod -R 755 $LOG_DIR
    
    log_success "Directories set up"
}

setup_venv() {
    log_info "Setting up Python virtual environment..."
    
    cd $INSTALL_DIR
    
    python3 -m venv $VENV_DIR
    
    source $VENV_DIR/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    
    log_success "Virtual environment set up"
}

create_systemd_service() {
    log_info "Creating systemd service..."
    
    cat > /etc/systemd/system/${SERVICE_NAME}.service << 'EOF'
[Unit]
Description=Llama.cpp Web Chat Server
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=llamacpp
Group=llamacpp
WorkingDirectory=/opt/llamacpp-web
Environment="PATH=/opt/llamacpp-web/venv/bin"
Environment="FLASK_ENV=production"
Environment="FLASK_DEBUG=False"
Environment="HOST=0.0.0.0"
Environment="PORT=5000"
Environment="MQTT_BROKER=47.89.252.2"
Environment="MQTT_PORT=1883"

ExecStart=/opt/llamacpp-web/venv/bin/python /opt/llamacpp-web/app.py
Restart=on-failure
RestartSec=10
StandardOutput=append:/var/log/llamacpp-web/app.log
StandardError=append:/var/log/llamacpp-web/error.log
SyslogIdentifier=llamacpp-web

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    log_success "Systemd service created"
}

create_nginx_config() {
    log_info "Creating Nginx configuration..."
    
    cat > /etc/nginx/sites-available/${SERVICE_NAME} << 'EOF'
upstream llamacpp_web {
    server 127.0.0.1:5000;
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    server_name _;

    # SSL certificates (update paths as needed)
    ssl_certificate /etc/ssl/certs/llama-cert.crt;
    ssl_certificate_key /etc/ssl/private/llama-key.key;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logging
    access_log /var/log/nginx/llamacpp_web_access.log;
    error_log /var/log/nginx/llamacpp_web_error.log;

    # Client body size
    client_max_body_size 50M;

    # Root location
    location / {
        proxy_pass http://llamacpp_web;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # Static files
    location /static {
        alias /opt/llamacpp-web/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # API endpoints
    location /api {
        proxy_pass http://llamacpp_web;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # Socket.io
    location /socket.io {
        proxy_pass http://llamacpp_web/socket.io;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

    ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/
    
    # Test Nginx config
    nginx -t
    
    log_success "Nginx configuration created"
}

enable_service() {
    log_info "Enabling service..."
    systemctl enable ${SERVICE_NAME}
    log_success "Service enabled"
}

start_service() {
    log_info "Starting service..."
    systemctl start ${SERVICE_NAME}
    sleep 2
    
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        log_success "Service started successfully"
    else
        log_error "Failed to start service"
        systemctl status ${SERVICE_NAME}
        exit 1
    fi
}

stop_service() {
    log_info "Stopping service..."
    systemctl stop ${SERVICE_NAME}
    log_success "Service stopped"
}

restart_service() {
    log_info "Restarting service..."
    systemctl restart ${SERVICE_NAME}
    sleep 2
    
    if systemctl is-active --quiet ${SERVICE_NAME}; then
        log_success "Service restarted successfully"
    else
        log_error "Failed to restart service"
        exit 1
    fi
}

show_logs() {
    journalctl -u ${SERVICE_NAME} -f
}

show_status() {
    systemctl status ${SERVICE_NAME}
}

show_help() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    install     Install and setup the service
    start       Start the service
    stop        Stop the service
    restart     Restart the service
    logs        Show service logs
    status      Show service status
    help        Show this help message

Examples:
    sudo $0 install
    sudo $0 start
    sudo $0 logs -f

EOF
}

# ============================================================================
# Main
# ============================================================================

case "${1:-help}" in
    install)
        check_root
        log_info "Starting installation..."
        install_dependencies
        create_user
        setup_directories
        setup_venv
        create_systemd_service
        create_nginx_config
        enable_service
        log_success "Installation complete!"
        log_info "To start the service, run: sudo $0 start"
        ;;
    start)
        check_root
        start_service
        ;;
    stop)
        check_root
        stop_service
        ;;
    restart)
        check_root
        restart_service
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    help|*)
        show_help
        ;;
esac

exit 0

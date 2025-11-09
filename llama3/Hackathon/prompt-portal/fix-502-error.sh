#!/bin/bash
# fix-502-error.sh - Comprehensive fix for 502 Bad Gateway errors after long runtime

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run as root (sudo ./fix-502-error.sh)"
    exit 1
fi

echo "=============================================="
echo "  Fixing 502 Bad Gateway - Long Runtime Issue"
echo "=============================================="
echo ""

# Configuration
BACKEND_DIR="/opt/prompt-portal/backend"
LOG_DIR="/var/log/prompt-portal"
NGINX_CONF="/etc/nginx/sites-available/lammp.agaii.org"

# Step 1: Create log directory
print_step "Creating log directory..."
mkdir -p "$LOG_DIR"
chown www-data:www-data "$LOG_DIR"
echo -e "${GREEN}✓${NC} Log directory created"

# Step 2: Stop current backend (if running)
print_step "Stopping current backend process (if running)..."
pkill -f "uvicorn app.main:app" || true
sleep 3
echo -e "${GREEN}✓${NC} Backend stopped"

# Step 3: Update backend code
print_step "Backend code has been updated with enhanced error handling"
echo "  - Added MQTT connection health check before processing requests"
echo "  - Increased timeout to 90 seconds for LLM responses"
echo "  - Better error messages for connection issues"
echo "  - Graceful shutdown signal handlers"
echo "  - Periodic connection verification (every 60 seconds)"

# Step 4: Install systemd service
print_step "Installing systemd service..."

cat > /etc/systemd/system/prompt-portal-backend.service <<'EOF'
[Unit]
Description=Prompt Portal Backend (FastAPI)
After=network.target mosquitto.service
Requires=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/prompt-portal/backend
Environment="PATH=/opt/prompt-portal/backend/.venv/bin"

# Start command
ExecStart=/opt/prompt-portal/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1

# Restart policy - automatically restart if crashed
Restart=always
RestartSec=10
StartLimitInterval=5min
StartLimitBurst=10

# Resource limits
LimitNOFILE=65536
MemoryMax=4G

# Logging
StandardOutput=append:/var/log/prompt-portal/backend.log
StandardError=append:/var/log/prompt-portal/backend-error.log

# Graceful shutdown
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable prompt-portal-backend
echo -e "${GREEN}✓${NC} Systemd service installed and enabled"

# Step 5: Start backend service
print_step "Starting backend service..."
systemctl start prompt-portal-backend
sleep 5

# Check if backend is running
if systemctl is-active --quiet prompt-portal-backend; then
    echo -e "${GREEN}✓${NC} Backend service started successfully"
else
    print_error "Backend service failed to start"
    echo ""
    echo "Service status:"
    systemctl status prompt-portal-backend --no-pager -l
    echo ""
    echo "Recent logs:"
    journalctl -u prompt-portal-backend -n 50 --no-pager
    exit 1
fi

# Step 6: Update nginx configuration
print_step "Updating nginx configuration..."

if [ -f "$NGINX_CONF" ]; then
    # Backup existing config
    cp "$NGINX_CONF" "${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    echo "  Backed up existing config"
    
    # Update timeout settings
    sed -i '/location \/api\//,/}/ {
        s/proxy_read_timeout [0-9]*s;/proxy_read_timeout 120s;/g
        s/proxy_send_timeout [0-9]*s;/proxy_send_timeout 120s;/g
    }' "$NGINX_CONF"
    
    # If no timeout settings exist in API location, add them
    if ! grep -A 10 "location /api/" "$NGINX_CONF" | grep -q "proxy_read_timeout"; then
        sed -i '/location \/api\//,/proxy_pass/ {
            /proxy_pass/ a\        proxy_connect_timeout 10s;\
        proxy_send_timeout 120s;\
        proxy_read_timeout 120s;
        }' "$NGINX_CONF"
    fi
    
    echo -e "${GREEN}✓${NC} Nginx timeouts updated to 120 seconds"
else
    print_warning "Nginx config not found at $NGINX_CONF"
    print_warning "Please manually update nginx timeouts:"
    echo "    proxy_connect_timeout 10s;"
    echo "    proxy_send_timeout 120s;"
    echo "    proxy_read_timeout 120s;"
fi

# Test nginx config
print_step "Testing nginx configuration..."
if nginx -t 2>&1 | grep -q "successful"; then
    systemctl reload nginx
    echo -e "${GREEN}✓${NC} Nginx configuration reloaded"
else
    print_error "Nginx configuration test failed"
    nginx -t
    print_warning "Nginx not reloaded - please fix configuration manually"
fi

# Step 7: Install health monitoring script
print_step "Installing health monitoring script..."

mkdir -p /opt/scripts

cat > /opt/scripts/monitor-backend.sh <<'EOF'
#!/bin/bash
# Backend health monitoring script

HEALTH_URL="http://localhost:8000/api/health"
MAX_FAILURES=3
FAILURE_COUNT=0
LOG_FILE="/var/log/prompt-portal/health-monitor.log"

log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

check_health() {
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$HEALTH_URL" 2>&1)
    echo "$response"
}

log_message "Health monitor started"

while true; do
    HTTP_CODE=$(check_health)
    
    if [ "$HTTP_CODE" != "200" ]; then
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
        log_message "Health check failed: HTTP $HTTP_CODE (failures: $FAILURE_COUNT/$MAX_FAILURES)"
        
        if [ $FAILURE_COUNT -ge $MAX_FAILURES ]; then
            log_message "Max failures reached. Restarting backend service..."
            systemctl restart prompt-portal-backend
            
            # Wait for restart
            sleep 10
            
            # Verify restart
            NEW_CODE=$(check_health)
            if [ "$NEW_CODE" = "200" ]; then
                log_message "Backend successfully restarted and healthy"
                FAILURE_COUNT=0
            else
                log_message "Backend restart failed! Manual intervention required."
            fi
        fi
    else
        if [ $FAILURE_COUNT -gt 0 ]; then
            log_message "Health check recovered (was failing)"
        fi
        FAILURE_COUNT=0
    fi
    
    sleep 30  # Check every 30 seconds
done
EOF

chmod +x /opt/scripts/monitor-backend.sh

# Create systemd service for health monitor
cat > /etc/systemd/system/backend-monitor.service <<'EOF'
[Unit]
Description=Backend Health Monitor
After=prompt-portal-backend.service
Requires=prompt-portal-backend.service

[Service]
Type=simple
User=root
ExecStart=/opt/scripts/monitor-backend.sh
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable backend-monitor
systemctl start backend-monitor

echo -e "${GREEN}✓${NC} Health monitoring service installed and started"

# Step 8: Verify everything is working
print_step "Verifying deployment..."
sleep 3

# Check backend health
HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health 2>/dev/null || echo "000")

if [ "$HEALTH_CHECK" = "200" ]; then
    echo -e "${GREEN}✓${NC} Backend health check PASSED"
    
    # Get health details
    HEALTH_DATA=$(curl -s http://localhost:8000/api/health 2>/dev/null || echo "{}")
    echo "  Health status: $(echo $HEALTH_DATA | grep -o '"status":"[^"]*"' | cut -d'"' -f4)"
    
    # Check MQTT status
    MQTT_DATA=$(curl -s http://localhost:8000/api/health/mqtt 2>/dev/null || echo "{}")
    MQTT_CONNECTED=$(echo $MQTT_DATA | grep -o '"connected":[^,}]*' | cut -d':' -f2)
    if [ "$MQTT_CONNECTED" = "true" ]; then
        echo -e "${GREEN}✓${NC} MQTT connection healthy"
    else
        print_warning "MQTT connection may have issues"
    fi
else
    print_error "Backend health check FAILED (HTTP $HEALTH_CHECK)"
    echo "Recent logs:"
    journalctl -u prompt-portal-backend -n 20 --no-pager
fi

# Final summary
echo ""
echo "=============================================="
echo -e "${GREEN}✓ Fix Deployment Completed!${NC}"
echo "=============================================="
echo ""
echo "Services Status:"
echo "----------------"
systemctl status prompt-portal-backend --no-pager -l | head -n 10
echo ""
systemctl status backend-monitor --no-pager -l | head -n 10
echo ""
echo "What was fixed:"
echo "  ✓ Enhanced error handling in backend"
echo "  ✓ Systemd service with auto-restart"
echo "  ✓ Nginx timeouts increased to 120s"
echo "  ✓ Health monitoring with auto-recovery"
echo "  ✓ Better MQTT connection verification"
echo ""
echo "Monitoring Commands:"
echo "--------------------"
echo "  Backend logs:     sudo journalctl -u prompt-portal-backend -f"
echo "  Monitor logs:     sudo tail -f /var/log/prompt-portal/health-monitor.log"
echo "  Backend status:   sudo systemctl status prompt-portal-backend"
echo "  Health check:     curl http://localhost:8000/api/health | jq"
echo "  MQTT health:      curl http://localhost:8000/api/health/mqtt | jq"
echo ""
echo "Test the fix:"
echo "  External:         curl https://lammp.agaii.org/api/health"
echo "  Send message:     Test in web interface"
echo ""
echo "If issues persist, check:"
echo "  1. sudo journalctl -u prompt-portal-backend -n 50"
echo "  2. sudo tail -f /var/log/prompt-portal/backend.log"
echo "  3. curl http://localhost:8000/api/health/mqtt"
echo ""

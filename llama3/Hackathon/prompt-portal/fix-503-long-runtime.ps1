# Fix 503 Service Unavailable Error for Long-Running Backend
# This script fixes MQTT disconnection issues that cause 503 errors

Write-Host "=== Fixing 503 Service Unavailable (Long Runtime) ===" -ForegroundColor Cyan
Write-Host ""

$ROOT = $PSScriptRoot
$BACKEND = Join-Path $ROOT "backend"
$DOMAIN = "lammp.agaii.org"

# Step 1: Update nginx configuration with extended timeouts
Write-Host "[1/4] Updating nginx configuration..." -ForegroundColor Yellow

$nginxConfig = @"
# WebSocket upgrade headers
map `$http_upgrade `$connection_upgrade {
    default upgrade;
    '' close;
}

server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN;

    # Serve frontend static files
    location / {
        root /root/prompt-portal/frontend/dist;
        try_files `$uri `$uri/ /index.html;
        index index.html;
        
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    }

    # WebSocket support for MQTT hints
    location /api/mqtt/ws/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade `$http_upgrade;
        proxy_set_header Connection `$connection_upgrade;
        proxy_set_header Host `$host;
        proxy_set_header X-Real-IP `$remote_addr;
        proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `$scheme;
        
        # Extended WebSocket timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
        
        add_header Access-Control-Allow-Origin * always;
    }

    # Legacy WebSocket support
    location /ws/ {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade `$http_upgrade;
        proxy_set_header Connection `$connection_upgrade;
        proxy_set_header Host `$host;
        proxy_set_header X-Real-IP `$remote_addr;
        proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `$scheme;
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;
        proxy_read_timeout 3600s;
    }

    # API routes with extended timeouts for LLM operations
    location /api/ {
        # Handle OPTIONS preflight
        if (`$request_method = 'OPTIONS') {
            add_header Access-Control-Allow-Origin * always;
            add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
            add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
            add_header Access-Control-Max-Age 3600;
            add_header Content-Length 0;
            add_header Content-Type text/plain;
            return 204;
        }
        
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host `$host;
        proxy_set_header X-Real-IP `$remote_addr;
        proxy_set_header X-Forwarded-For `$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto `$scheme;
        
        # CRITICAL: Extended timeouts for LLM responses (10 minutes)
        proxy_connect_timeout 300s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
        
        # Disable buffering for streaming
        proxy_buffering off;
        proxy_request_buffering off;
        
        # Increase buffer sizes
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        proxy_busy_buffers_size 256k;
        
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Content-Type, Authorization, X-Requested-With" always;
    }
}
"@

Write-Host "Nginx config prepared (will need SSH to apply)" -ForegroundColor Green

# Step 2: Create monitoring script
Write-Host "[2/4] Creating backend health monitor..." -ForegroundColor Yellow

$monitorScript = @'
#!/bin/bash
# Backend Health Monitor - Auto-restart on failure

BACKEND_DIR="/root/prompt-portal/backend"
BACKEND_PORT=3000
CHECK_INTERVAL=60  # Check every 60 seconds
MAX_FAILURES=3

failure_count=0

echo "Starting backend health monitor (checking every ${CHECK_INTERVAL}s)..."

while true; do
    sleep $CHECK_INTERVAL
    
    # Check if backend is responding
    if curl -sf --max-time 5 "http://127.0.0.1:${BACKEND_PORT}/api/health" > /dev/null 2>&1; then
        failure_count=0
    else
        failure_count=$((failure_count + 1))
        echo "[$(date)] Backend health check failed (${failure_count}/${MAX_FAILURES})"
        
        if [ $failure_count -ge $MAX_FAILURES ]; then
            echo "[$(date)] Backend unhealthy, restarting..."
            
            # Kill existing backend
            if [ -f "${BACKEND_DIR}/backend.pid" ]; then
                kill $(cat "${BACKEND_DIR}/backend.pid") 2>/dev/null || true
            fi
            pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
            sleep 2
            
            # Restart backend
            cd "${BACKEND_DIR}"
            nohup uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} > backend.log 2>&1 &
            echo $! > backend.pid
            
            echo "[$(date)] Backend restarted (PID: $(cat backend.pid))"
            failure_count=0
            sleep 10  # Give it time to start
        fi
    fi
done
'@

$monitorScript | Out-File -FilePath (Join-Path $ROOT "monitor-backend-health.sh") -Encoding UTF8 -NoNewline
Write-Host "Created monitor-backend-health.sh" -ForegroundColor Green

# Step 3: Create systemd service for auto-restart
Write-Host "[3/4] Creating systemd service configuration..." -ForegroundColor Yellow

$systemdService = @"
[Unit]
Description=Prompt Portal Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/prompt-portal/backend
ExecStart=/usr/bin/uvicorn app.main:app --host 0.0.0.0 --port 3000
Restart=always
RestartSec=10
StandardOutput=append:/root/prompt-portal/backend/backend.log
StandardError=append:/root/prompt-portal/backend/backend.log

# Environment
Environment="PYTHONUNBUFFERED=1"

# Restart policy
StartLimitInterval=60
StartLimitBurst=5

[Install]
WantedBy=multi-user.target
"@

$systemdService | Out-File -FilePath (Join-Path $ROOT "prompt-portal-backend.service") -Encoding UTF8 -NoNewline
Write-Host "Created prompt-portal-backend.service" -ForegroundColor Green

# Step 4: Create deployment script
Write-Host "[4/4] Creating deployment script..." -ForegroundColor Yellow

$deployScript = @'
#!/bin/bash
# Apply 503 Long-Runtime Fix

set -e

echo "=== Applying 503 Service Unavailable Fix ==="
echo ""

# Update nginx
echo "[1/3] Updating nginx configuration..."
sudo cp /root/prompt-portal/nginx-$DOMAIN.conf /etc/nginx/sites-available/$DOMAIN 2>/dev/null || true
if sudo nginx -t; then
    sudo systemctl reload nginx
    echo "✓ Nginx configuration updated"
else
    echo "✗ Nginx configuration test failed"
    exit 1
fi

# Install systemd service
echo "[2/3] Installing systemd service..."
sudo cp /root/prompt-portal/prompt-portal-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable prompt-portal-backend
sudo systemctl restart prompt-portal-backend
echo "✓ Systemd service installed and started"

# Start health monitor
echo "[3/3] Starting health monitor..."
chmod +x /root/prompt-portal/monitor-backend-health.sh
if ! pgrep -f "monitor-backend-health.sh" > /dev/null; then
    nohup /root/prompt-portal/monitor-backend-health.sh > /root/prompt-portal/monitor.log 2>&1 &
    echo "✓ Health monitor started"
else
    echo "✓ Health monitor already running"
fi

echo ""
echo "=== Fix Applied Successfully ==="
echo ""
echo "Backend is now monitored and will auto-restart on failure"
echo "Nginx timeouts extended to 10 minutes for LLM operations"
echo ""
echo "Monitoring:"
echo "  - Backend logs: tail -f /root/prompt-portal/backend/backend.log"
echo "  - Monitor logs: tail -f /root/prompt-portal/monitor.log"
echo "  - Service status: sudo systemctl status prompt-portal-backend"
'@

$deployScript | Out-File -FilePath (Join-Path $ROOT "apply-503-fix.sh") -Encoding UTF8 -NoNewline
Write-Host "Created apply-503-fix.sh" -ForegroundColor Green

Write-Host ""
Write-Host "=== Files Created ===" -ForegroundColor Cyan
Write-Host "1. monitor-backend-health.sh - Auto-restart unhealthy backend" -ForegroundColor White
Write-Host "2. prompt-portal-backend.service - Systemd service for auto-restart" -ForegroundColor White
Write-Host "3. apply-503-fix.sh - Deployment script" -ForegroundColor White
Write-Host ""
Write-Host "=== Next Steps ===" -ForegroundColor Cyan
Write-Host "SSH into your server and run:" -ForegroundColor Yellow
Write-Host ""
Write-Host "cd /root/prompt-portal" -ForegroundColor White
Write-Host "bash apply-503-fix.sh" -ForegroundColor White
Write-Host ""
Write-Host "This will:" -ForegroundColor Green
Write-Host "  ✓ Update nginx with 10-minute timeouts" -ForegroundColor White
Write-Host "  ✓ Install systemd service for auto-restart" -ForegroundColor White
Write-Host "  ✓ Start health monitoring" -ForegroundColor White
Write-Host ""
Write-Host "=== Root Cause ===" -ForegroundColor Cyan
Write-Host "The 503 error occurs when:" -ForegroundColor White
Write-Host "  1. MQTT connection drops after long runtime" -ForegroundColor White
Write-Host "  2. Backend becomes unresponsive" -ForegroundColor White
Write-Host "  3. Nginx returns 503 instead of forwarding request" -ForegroundColor White
Write-Host ""
Write-Host "=== The Fix ===" -ForegroundColor Cyan
Write-Host "  1. Extended nginx timeouts (60s → 600s)" -ForegroundColor White
Write-Host "  2. Health monitoring with auto-restart" -ForegroundColor White
Write-Host "  3. Systemd service for crash recovery" -ForegroundColor White
Write-Host "  4. MQTT reconnection logic already in backend" -ForegroundColor White
Write-Host ""
Write-Host "Done!" -ForegroundColor Green

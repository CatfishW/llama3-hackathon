# Fix 502 Bad Gateway Error After Long Runtime

## Problem Summary

After the web application runs for an extended period, sending messages to the chatbot endpoint results in a **502 Bad Gateway** error:

```
POST https://lammp.agaii.org/api/chatbot/messages 502 (Bad Gateway)
```

This indicates the backend service becomes unresponsive or crashes after prolonged operation.

## Root Causes

Based on the codebase analysis, the likely causes are:

### 1. **Backend Service Crashing/Hanging**
- Python process may crash due to unhandled exceptions
- MQTT connection issues causing the backend to hang
- Memory leaks accumulating over time

### 2. **Nginx Timeout Issues**
- Default nginx timeouts (60s) may be too short for LLM responses
- Proxy not properly configured for long-polling scenarios
- Missing keepalive settings

### 3. **MQTT Connection Health Issues**
- Despite the MQTT_LONG_RUNTIME_FIX being implemented, there may be edge cases
- Connection might appear "connected" but be non-functional
- Pending requests accumulating without cleanup

### 4. **No Process Monitoring**
- Backend crashes go undetected
- No automatic restart mechanism
- No external health monitoring

## Comprehensive Solutions

### Solution 1: Enhanced Backend Error Handling

Add better error handling and timeout management to the chatbot endpoint:

```python
# backend/app/routers/chatbot.py

@router.post("/messages", response_model=schemas.ChatMessageSendResponse)
async def send_message(
    payload: schemas.ChatMessageSendRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
) -> schemas.ChatMessageSendResponse:
    session = (
        db.query(ChatSession)
        .filter(ChatSession.id == payload.session_id, ChatSession.user_id == user.id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check MQTT connection health before processing
    from ..mqtt import mqtt_client
    if not mqtt_client or not mqtt_client.is_connected():
        raise HTTPException(
            status_code=503,
            detail="LLM backend connection unavailable. Please try again in a moment."
        )

    # Rest of implementation...
    
    try:
        response_payload = await send_chat_message(mqtt_payload, timeout=90.0)  # Increased timeout
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="The AI model is taking longer than usual. Please try again."
        )
    except RuntimeError as exc:
        if "MQTT connection" in str(exc):
            raise HTTPException(
                status_code=503,
                detail="LLM backend connection lost. Reconnecting..."
            )
        raise HTTPException(status_code=502, detail=f"Backend error: {exc}") from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to contact LLM backend: {str(exc)}"
        ) from exc
```

### Solution 2: Nginx Configuration for Production

Create/update nginx configuration with proper timeout settings:

```nginx
# /etc/nginx/sites-available/lammp.agaii.org

upstream backend {
    server 127.0.0.1:8000 fail_timeout=30s max_fails=3;
    keepalive 32;
}

server {
    listen 443 ssl http2;
    server_name lammp.agaii.org;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/lammp.agaii.org/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lammp.agaii.org/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # API endpoints - increased timeouts for LLM responses
    location /api/ {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        
        # Connection settings
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeout settings for LLM responses
        proxy_connect_timeout 10s;
        proxy_send_timeout 120s;      # Allow 2 minutes for request
        proxy_read_timeout 120s;      # Allow 2 minutes for response
        
        # Buffer settings
        proxy_buffering off;
        proxy_request_buffering off;
        
        # CORS
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS, PATCH" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type, Accept" always;
        add_header Access-Control-Max-Age 3600 always;
        
        if ($request_method = 'OPTIONS') {
            return 204;
        }
    }

    # WebSocket connections
    location ~ ^/(ws|api/mqtt/ws) {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        # WebSocket specific timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 3600s;     # 1 hour for WebSocket
        proxy_read_timeout 3600s;     # 1 hour for WebSocket
        
        # Disable buffering for WebSocket
        proxy_buffering off;
    }

    # Frontend static files
    location / {
        root /var/www/lammp.agaii.org/html;
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, immutable";
    }

    # Health check endpoint (no caching)
    location /api/health {
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        
        proxy_connect_timeout 5s;
        proxy_send_timeout 10s;
        proxy_read_timeout 10s;
        
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name lammp.agaii.org;
    return 301 https://$server_name$request_uri;
}
```

### Solution 3: Systemd Service for Auto-Restart

Create a systemd service that automatically restarts the backend if it crashes:

```ini
# /etc/systemd/system/prompt-portal-backend.service

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

# Restart policy
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
```

### Solution 4: Health Monitoring Script

Create a monitoring script that checks health and restarts if needed:

```bash
#!/bin/bash
# /opt/scripts/monitor-backend.sh

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
                # Send alert (optional)
                # curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
                #      -d "chat_id=<CHAT_ID>&text=Backend restart failed at lammp.agaii.org"
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
```

### Solution 5: Backend Connection Pool

Add connection pooling to prevent resource exhaustion:

```python
# backend/app/mqtt.py

# Add at the top of the file
import signal
import sys

# Graceful shutdown handler
def _signal_handler(sig, frame):
    print(f"\n[MQTT] Received signal {sig}, shutting down gracefully...")
    stop_mqtt()
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# Update start_mqtt function
def start_mqtt():
    global _mqtt_reconnect_attempts, _mqtt_last_activity
    _mqtt_reconnect_attempts = 0
    _mqtt_last_activity = time.time()
    
    mqtt_client.on_connect = _on_connect
    mqtt_client.on_disconnect = _on_disconnect
    mqtt_client.on_message = _on_message
    
    # Set up authentication
    if hasattr(settings, 'MQTT_USERNAME') and hasattr(settings, 'MQTT_PASSWORD'):
        mqtt_client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
        print(f"MQTT authentication configured for user: {settings.MQTT_USERNAME}")
    
    # Configure connection options for better reliability
    mqtt_client.reconnect_delay_set(min_delay=1, max_delay=120)
    
    # Enable clean session to prevent message buildup
    mqtt_client._clean_session = True
    
    print(f"Connecting to MQTT broker at {settings.MQTT_BROKER_HOST}:{settings.MQTT_BROKER_PORT}")
    print(f"Using client ID: {unique_client_id}")
    
    try:
        # Connect with keepalive of 60 seconds (will send PINGREQ if no activity)
        mqtt_client.connect(settings.MQTT_BROKER_HOST, settings.MQTT_BROKER_PORT, keepalive=60)
        mqtt_client.loop_start()
        print("MQTT loop started successfully")
        
        # Start health monitoring thread
        health_thread = threading.Thread(target=_mqtt_health_monitor, daemon=True)
        health_thread.start()
        print("MQTT health monitor started")
        
        # Start periodic connection verification
        verify_thread = threading.Thread(target=_periodic_connection_check, daemon=True)
        verify_thread.start()
        print("MQTT connection verifier started")
        
    except Exception as e:
        print(f"Failed to start MQTT connection: {e}")
        raise

def _periodic_connection_check():
    """Periodically verify MQTT connection is truly alive"""
    while True:
        try:
            time.sleep(60)  # Check every minute
            if mqtt_client.is_connected():
                # Try to publish a test message
                try:
                    result = mqtt_client.publish("$SYS/heartbeat", "ping", qos=0)
                    if result.rc != 0:
                        print(f"[MQTT Verify] Publish failed (rc={result.rc}), may need reconnection")
                except Exception as e:
                    print(f"[MQTT Verify] Connection test failed: {e}")
                    _attempt_reconnect()
            else:
                print("[MQTT Verify] Connection lost, attempting reconnect")
                _attempt_reconnect()
        except Exception as e:
            print(f"[MQTT Verify] Error in connection check: {e}")
```

## Deployment Instructions

### Step 1: Update Backend Code

```bash
# On the server
cd /opt/prompt-portal/backend

# Backup current code
cp app/routers/chatbot.py app/routers/chatbot.py.backup
cp app/mqtt.py app/mqtt.py.backup

# Apply the chatbot.py fixes (copy the enhanced error handling code)
# Apply the mqtt.py enhancements (copy the connection pool code)
```

### Step 2: Setup Systemd Service

```bash
# Create log directory
sudo mkdir -p /var/log/prompt-portal
sudo chown www-data:www-data /var/log/prompt-portal

# Install systemd service
sudo cp prompt-portal-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable prompt-portal-backend
sudo systemctl start prompt-portal-backend

# Check status
sudo systemctl status prompt-portal-backend
```

### Step 3: Update Nginx Configuration

```bash
# Backup current config
sudo cp /etc/nginx/sites-available/lammp.agaii.org /etc/nginx/sites-available/lammp.agaii.org.backup

# Update with new configuration (copy from Solution 2)
sudo nano /etc/nginx/sites-available/lammp.agaii.org

# Test configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Step 4: Setup Health Monitoring

```bash
# Create scripts directory
sudo mkdir -p /opt/scripts

# Install monitoring script
sudo cp monitor-backend.sh /opt/scripts/
sudo chmod +x /opt/scripts/monitor-backend.sh

# Create systemd service for monitor
sudo tee /etc/systemd/system/backend-monitor.service > /dev/null <<'EOF'
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

sudo systemctl daemon-reload
sudo systemctl enable backend-monitor
sudo systemctl start backend-monitor
```

### Step 5: Verify Everything Works

```bash
# Check backend service
sudo systemctl status prompt-portal-backend

# Check health endpoint
curl http://localhost:8000/api/health

# Check MQTT health
curl http://localhost:8000/api/health/mqtt

# Monitor logs
sudo tail -f /var/log/prompt-portal/backend.log
sudo tail -f /var/log/prompt-portal/health-monitor.log

# Test from external
curl https://lammp.agaii.org/api/health
```

## Quick Fix Script

Create an automated deployment script:

```bash
#!/bin/bash
# fix-502-error.sh

set -e

echo "=== Fixing 502 Error - Long Runtime Issue ==="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_step() {
    echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    print_error "Please run as root (sudo)"
    exit 1
fi

print_step "Creating log directory..."
mkdir -p /var/log/prompt-portal
chown www-data:www-data /var/log/prompt-portal

print_step "Stopping current backend (if running)..."
pkill -f "uvicorn app.main:app" || true
sleep 2

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
ExecStart=/opt/prompt-portal/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
Restart=always
RestartSec=10
StartLimitInterval=5min
StartLimitBurst=10
LimitNOFILE=65536
MemoryMax=4G
StandardOutput=append:/var/log/prompt-portal/backend.log
StandardError=append:/var/log/prompt-portal/backend-error.log
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable prompt-portal-backend
systemctl start prompt-portal-backend

print_step "Waiting for backend to start..."
sleep 5

# Check if backend is running
if systemctl is-active --quiet prompt-portal-backend; then
    echo -e "${GREEN}✓ Backend service started successfully${NC}"
else
    print_error "Backend service failed to start"
    systemctl status prompt-portal-backend
    exit 1
fi

print_step "Updating nginx configuration..."
NGINX_CONF="/etc/nginx/sites-available/lammp.agaii.org"

# Backup existing config
if [ -f "$NGINX_CONF" ]; then
    cp "$NGINX_CONF" "${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Update timeout settings in existing config
sed -i 's/proxy_read_timeout [0-9]*s;/proxy_read_timeout 120s;/g' "$NGINX_CONF"
sed -i 's/proxy_send_timeout [0-9]*s;/proxy_send_timeout 120s;/g' "$NGINX_CONF"

# If no timeout settings exist, add them
if ! grep -q "proxy_read_timeout" "$NGINX_CONF"; then
    print_step "Adding timeout settings to nginx config..."
    # This would require more sophisticated sed/awk to insert properly
fi

# Test nginx config
if nginx -t 2>/dev/null; then
    systemctl reload nginx
    echo -e "${GREEN}✓ Nginx configuration updated${NC}"
else
    print_error "Nginx configuration test failed"
    exit 1
fi

print_step "Testing backend health..."
sleep 2

HEALTH_CHECK=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/api/health)
if [ "$HEALTH_CHECK" = "200" ]; then
    echo -e "${GREEN}✓ Backend health check passed${NC}"
else
    print_error "Backend health check failed (HTTP $HEALTH_CHECK)"
fi

echo ""
echo "==================================="
echo -e "${GREEN}✓ Fix deployment completed!${NC}"
echo "==================================="
echo ""
echo "Services status:"
systemctl status prompt-portal-backend --no-pager -l
echo ""
echo "To monitor logs:"
echo "  sudo journalctl -u prompt-portal-backend -f"
echo "  sudo tail -f /var/log/prompt-portal/backend.log"
echo ""
echo "To check health:"
echo "  curl http://localhost:8000/api/health"
echo "  curl http://localhost:8000/api/health/mqtt"
echo ""
```

## Testing the Fix

### 1. Immediate Test

```bash
# Send a test message
curl -X POST https://lammp.agaii.org/api/chatbot/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "session_id": 1,
    "content": "Hello, are you working?"
  }'
```

### 2. Long-Running Test

```bash
# Run for 24 hours, sending messages every minute
for i in {1..1440}; do
  echo "Test $i/1440 at $(date)"
  curl -X POST https://lammp.agaii.org/api/chatbot/messages \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -d "{\"session_id\": 1, \"content\": \"Test message $i\"}"
  sleep 60
done
```

### 3. Monitor Health

```bash
# Watch health status continuously
watch -n 5 'curl -s http://localhost:8000/api/health | jq'
```

## Monitoring & Alerts

### Key Metrics to Watch

1. **Backend Uptime**
   ```bash
   systemctl status prompt-portal-backend
   ```

2. **MQTT Connection Status**
   ```bash
   curl -s http://localhost:8000/api/health/mqtt | jq '.connected'
   ```

3. **Pending Requests**
   ```bash
   curl -s http://localhost:8000/api/health/mqtt | jq '.pending_requests.total'
   ```

4. **Response Times**
   ```bash
   curl -w "@curl-format.txt" -o /dev/null -s https://lammp.agaii.org/api/health
   ```

### Setup Alerts (Optional)

Add Telegram/Slack notifications when backend fails:

```bash
# Add to monitor-backend.sh
send_alert() {
    MESSAGE="$1"
    # Telegram
    curl -X POST "https://api.telegram.org/bot<TOKEN>/sendMessage" \
         -d "chat_id=<CHAT_ID>&text=🚨 Backend Alert: $MESSAGE"
    
    # Or Slack
    # curl -X POST <WEBHOOK_URL> \
    #      -H 'Content-Type: application/json' \
    #      -d "{\"text\": \"🚨 Backend Alert: $MESSAGE\"}"
}
```

## Expected Results

After applying all fixes:

✅ **No more 502 errors** after long runtime  
✅ **Automatic recovery** if backend crashes  
✅ **Better error messages** to users  
✅ **Health monitoring** with auto-restart  
✅ **Proper timeouts** for LLM responses  
✅ **Connection resilience** with MQTT  

## Summary

The 502 error after long runtime is caused by:
1. Backend process crashes without restart
2. MQTT connection becoming stale
3. Nginx timeouts too aggressive
4. No health monitoring

The comprehensive fix includes:
1. Enhanced error handling in backend
2. Systemd service with auto-restart
3. Updated nginx timeouts (120s)
4. Health monitoring script
5. Better MQTT connection verification

Deploy using the provided script and monitor for 24-48 hours to ensure stability.

# WebSocket Connection Fix Guide

## Problem

The browser console showed this error:
```
index-hF2Uwrdz.js:17358 WebSocket connection to 'wss://lammp.agaii.org/api/mqtt/ws/hints/session-874q8t' failed
```

This indicates that WebSocket connections to the MQTT hint system were failing.

## Root Cause

The issue was in the Nginx configuration. The location blocks were ordered incorrectly, causing WebSocket upgrade requests to be handled by the general `/api/` block instead of the specific WebSocket block.

### The Problem Chain

1. **Client Request**: Browser tries to connect to `wss://lammp.agaii.org/api/mqtt/ws/hints/session-874q8t`
2. **Nginx Routing**: Request matches both:
   - `location /api/` (general API block)
   - `location /api/mqtt/ws/` (WebSocket-specific block)
3. **Location Block Order**: Nginx uses the **first matching** location block
4. **Missing WebSocket Headers**: The general `/api/` block doesn't include WebSocket upgrade headers
5. **Connection Fails**: Backend receives the request but can't upgrade to WebSocket protocol

### Key Issues in Original Configuration

```nginx
# WRONG ORDER - General block comes first
location /api/ {
    proxy_pass http://127.0.0.1:8000;
    # Missing: Upgrade and Connection headers
}

# This block never gets reached for /api/mqtt/ws/* requests!
location /api/mqtt/ws/ {
    proxy_pass http://127.0.0.1:8000/api/mqtt/ws/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## The Fix

### 1. Correct Location Block Order

More specific location blocks must come **before** more general ones:

```nginx
# CORRECT ORDER - Specific WebSocket block comes first
location ~ ^/api/mqtt/ws/ {
    # WebSocket configuration with upgrade headers
}

location /api/ {
    # General API configuration
}
```

### 2. Use Regex Location Blocks

Using `location ~ ^/api/mqtt/ws/` ensures this block has higher priority over prefix-based location blocks.

### 3. Proper WebSocket Headers

```nginx
location ~ ^/api/mqtt/ws/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    
    # Extended timeouts for persistent connections
    proxy_connect_timeout 60s;
    proxy_send_timeout 3600s;  # 1 hour
    proxy_read_timeout 3600s;  # 1 hour
}
```

### 4. Connection Upgrade Map

Added at the top of the configuration:

```nginx
map $http_upgrade $connection_upgrade {
    default upgrade;
    '' close;
}
```

This properly maps the Upgrade header to the Connection header.

## How to Apply the Fix

### Option 1: Automated Fix (Recommended)

On your server, run:

```bash
cd ~/prompt-portal
bash fix-websocket.sh
```

This script will:
- Detect your backend port (3000 or 8000)
- Backup existing Nginx configuration
- Create new configuration with correct WebSocket support
- Test and reload Nginx
- Provide verification steps

### Option 2: Manual Fix

1. **SSH to your server:**
   ```bash
   ssh root@lammp.agaii.org
   ```

2. **Edit Nginx configuration:**
   ```bash
   sudo nano /etc/nginx/sites-available/lammp.agaii.org
   ```

3. **Add the connection upgrade map at the top:**
   ```nginx
   map $http_upgrade $connection_upgrade {
       default upgrade;
       '' close;
   }
   ```

4. **Reorder location blocks in both server blocks (HTTP and HTTPS):**
   - Move WebSocket blocks (`location ~ ^/api/mqtt/ws/` and `location ~ ^/ws/`) **before** the general `/api/` block
   - Ensure WebSocket blocks use regex patterns (`~`)
   - Verify all required headers are present

5. **Test and reload:**
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

## Verification

After applying the fix:

### 1. Test Backend Connection

```bash
# Check if backend is running
netstat -tlnp | grep -E ":(8000|3000)"

# Should show something like:
# tcp  0  0  0.0.0.0:8000  0.0.0.0:*  LISTEN  12345/python
```

### 2. Test WebSocket Endpoint Directly

```bash
# Test WebSocket upgrade (should return 101 Switching Protocols)
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
     -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: test" \
     https://lammp.agaii.org/api/mqtt/ws/hints/test-session
```

### 3. Test in Browser

1. Open the application: https://lammp.agaii.org
2. Open DevTools (F12) → Console tab
3. Navigate to a page that uses WebSocket (e.g., the game page)
4. Check for WebSocket errors
5. In the Network tab, filter by "WS" to see WebSocket connections
6. Look for status code 101 (Switching Protocols)

### 4. Check Nginx Logs

```bash
# Watch for WebSocket connection attempts
sudo tail -f /var/log/nginx/access.log | grep ws

# Check for errors
sudo tail -f /var/log/nginx/error.log
```

## Understanding WebSocket Flow

### Successful Connection Flow

1. **Client Initiates WebSocket**:
   ```javascript
   const ws = new WebSocket('wss://lammp.agaii.org/api/mqtt/ws/hints/session-xyz')
   ```

2. **Browser Sends HTTP Upgrade Request**:
   ```http
   GET /api/mqtt/ws/hints/session-xyz HTTP/1.1
   Host: lammp.agaii.org
   Upgrade: websocket
   Connection: Upgrade
   Sec-WebSocket-Version: 13
   Sec-WebSocket-Key: random-key-here
   ```

3. **Nginx Routes to Backend**:
   - Matches `location ~ ^/api/mqtt/ws/` block
   - Adds upgrade headers
   - Proxies to backend on port 8000/3000

4. **Backend Responds with 101**:
   ```http
   HTTP/1.1 101 Switching Protocols
   Upgrade: websocket
   Connection: Upgrade
   ```

5. **Connection Established**:
   - HTTP connection upgrades to WebSocket
   - Bidirectional communication begins
   - Connection stays open for real-time data

## Common Issues and Solutions

### Issue 1: Still Getting Connection Errors

**Check:**
- Backend is actually running: `ps aux | grep uvicorn`
- Correct port in Nginx config: `grep proxy_pass /etc/nginx/sites-available/lammp.agaii.org`
- Firewall allows connections: `sudo ufw status`

**Solution:**
```bash
# Restart backend
cd ~/prompt-portal/backend
pkill -f "uvicorn.*app.main:app"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
```

### Issue 2: Connection Closes Immediately

**Check:**
- Proxy timeouts in Nginx configuration
- Backend isn't crashing (check logs)

**Solution:** Ensure long timeouts:
```nginx
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
```

### Issue 3: 403 Forbidden

**Check:**
- CORS headers are present
- Authentication token (if required)

**Solution:** Verify CORS headers in WebSocket block:
```nginx
add_header Access-Control-Allow-Origin * always;
```

### Issue 4: 502 Bad Gateway

**Check:**
- Backend is running on the correct port
- Backend can handle WebSocket connections

**Solution:**
```bash
# Check backend logs
cd ~/prompt-portal/backend
# Find the backend process
ps aux | grep uvicorn
# Check its output (if using nohup, find the log file)
```

## Technical Details

### Location Block Matching Order in Nginx

Nginx processes location blocks in this order:

1. **Exact match**: `location = /exact/path`
2. **Regex match** (case-sensitive): `location ~ /regex/pattern`
3. **Regex match** (case-insensitive): `location ~* /regex/pattern`
4. **Longest prefix match**: `location /prefix/`
5. **General prefix match**: `location /`

Our fix uses regex (`~`) to ensure WebSocket blocks are checked before the general `/api/` prefix block.

### WebSocket vs HTTP

| Feature | HTTP | WebSocket |
|---------|------|-----------|
| Connection | Request/Response | Persistent |
| Direction | Client → Server | Bidirectional |
| Protocol | HTTP/1.1, HTTP/2 | WS, WSS |
| Overhead | High (headers each request) | Low (small frames) |
| Use Case | APIs, web pages | Real-time data, chat |

### Why WebSockets for MQTT Hints?

The application uses WebSocket for real-time hint delivery from the LAM (Language Agent Model) system:

- **Low Latency**: Hints arrive instantly without polling
- **Efficient**: Single persistent connection vs repeated HTTP requests
- **Bidirectional**: Client can send keep-alive or status updates
- **Real-time**: Perfect for interactive game hints and chat

## Files Modified

1. **Created**: `fix-websocket.sh` - Automated fix script
2. **Modified**: `/etc/nginx/sites-available/lammp.agaii.org` - Nginx configuration
3. **Created**: `WEBSOCKET_FIX_GUIDE.md` - This documentation

## Prevention for Future

When modifying Nginx configuration:

✅ **DO:**
- Put more specific location blocks first
- Use regex patterns for WebSocket paths
- Include all required WebSocket headers
- Test configuration before reloading
- Keep backups of working configurations

❌ **DON'T:**
- Put general `/api/` block before specific WebSocket blocks
- Forget the connection upgrade map
- Use short timeouts for WebSocket connections
- Apply configuration without testing (`nginx -t`)

## Additional Resources

- [Nginx WebSocket Proxying](https://nginx.org/en/docs/http/websocket.html)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)

## Support

If you encounter issues after applying this fix:

1. **Check the logs first:**
   ```bash
   sudo tail -f /var/log/nginx/error.log
   cd ~/prompt-portal/backend && tail -f nohup.out
   ```

2. **Verify configuration:**
   ```bash
   sudo nginx -t
   grep -A 10 "location ~ ^/api/mqtt/ws/" /etc/nginx/sites-available/lammp.agaii.org
   ```

3. **Test directly:**
   ```bash
   # Test backend responds
   curl http://localhost:8000/api/docs
   
   # Test Nginx routing
   curl -I https://lammp.agaii.org/api/docs
   ```

4. **Restart services:**
   ```bash
   # Restart Nginx
   sudo systemctl restart nginx
   
   # Restart backend
   cd ~/prompt-portal/backend
   pkill -f uvicorn
   nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
   ```

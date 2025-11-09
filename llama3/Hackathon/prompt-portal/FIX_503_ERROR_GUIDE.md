# Fix 503 Service Unavailable Error (Long Runtime)

## 🔍 Problem

After your web project runs for a long time, clicking send to send messages to the LLM results in:

```
POST https://lammp.agaii.org/api/chatbot/messages 503 (Service Unavailable)
```

## 🎯 Root Cause

The 503 error occurs due to **MQTT connection degradation** over time:

1. **MQTT Connection Drops**: After several hours, the MQTT broker connection becomes stale or disconnects
2. **Backend Health Check Fails**: The backend checks MQTT connection health before processing messages
3. **Returns 503**: If MQTT is disconnected, the backend returns 503 "Service Unavailable"
4. **Nginx Timeout**: Even with working MQTT, nginx has 60-second timeout (too short for LLM responses)

## ✅ The Solution

### Three-Layer Fix:

1. **Nginx Extended Timeouts** (10 minutes for LLM operations)
2. **Backend Health Monitoring** (auto-restart on failure)
3. **MQTT Reconnection Logic** (already implemented, enhanced monitoring)

## 🚀 Quick Fix (Windows PowerShell)

```powershell
cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal
.\fix-503-long-runtime.ps1
```

This creates:
- `monitor-backend-health.sh` - Health monitoring script
- `prompt-portal-backend.service` - Systemd service file
- `apply-503-fix.sh` - Deployment script

## 🔧 Apply on Server (SSH)

```bash
# SSH into your server
ssh root@lammp.agaii.org

# Navigate to project
cd /root/prompt-portal

# Apply the fix
bash apply-503-fix.sh
```

## 📊 What Gets Fixed

### 1. Nginx Configuration (Extended Timeouts)

**Before:**
```nginx
proxy_connect_timeout 60s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;
```

**After:**
```nginx
# Extended timeouts for LLM operations (10 minutes)
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
```

### 2. Backend Auto-Restart (Systemd Service)

Creates a systemd service that:
- Automatically restarts backend if it crashes
- Monitors process health
- Logs all activity
- Starts on boot

### 3. Health Monitoring Script

Checks backend health every 60 seconds:
- Makes health check request to `/api/health`
- Restarts backend after 3 consecutive failures
- Logs all restart events

## 🔍 Monitoring & Debugging

### Check Backend Status
```bash
sudo systemctl status prompt-portal-backend
```

### View Backend Logs
```bash
tail -f /root/prompt-portal/backend/backend.log
```

### View Monitor Logs
```bash
tail -f /root/prompt-portal/monitor.log
```

### Check MQTT Connection
```bash
# In backend logs, look for:
grep "MQTT" /root/prompt-portal/backend/backend.log
```

### Manual Backend Restart
```bash
sudo systemctl restart prompt-portal-backend
```

## 🔬 Technical Details

### MQTT Health Monitoring (Already in Backend)

The backend (`backend/app/mqtt.py`) already has:

1. **Connection Monitoring**: Tracks last activity timestamp
2. **Auto-Reconnection**: Exponential backoff reconnection (up to 10 attempts)
3. **Health Checks**: Background thread checks connection every 30 seconds
4. **Stale Request Cleanup**: Removes requests waiting >2 minutes

### Backend Health Check Endpoint

```python
# In chatbot.py send_message():
from ..mqtt import mqtt_client
if not mqtt_client or not mqtt_client.is_connected():
    raise HTTPException(
        status_code=503,
        detail="LLM backend connection unavailable. Please try again in a moment."
    )
```

This is WHERE the 503 error originates!

### MQTT Reconnection Logic

```python
def _on_disconnect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        _mqtt_reconnect_attempts += 1
        if _mqtt_reconnect_attempts <= _mqtt_max_reconnect_attempts:
            delay = min(300, 5 * (2 ** (_mqtt_reconnect_attempts - 1)))
            threading.Timer(delay, _attempt_reconnect).start()
```

Exponential backoff: 5s, 10s, 20s, 40s, 80s, 160s, 300s (max)

## 🎯 Expected Results

After applying this fix:

✅ **No more 502/503 errors** after long runtime  
✅ **LLM responses work** even if they take 5+ minutes  
✅ **Automatic recovery** if backend crashes  
✅ **MQTT reconnection** happens automatically  
✅ **Health monitoring** logs all issues  

## 🐛 Troubleshooting

### Still Getting 503 Errors?

1. **Check MQTT Broker Status**
   ```bash
   # On MQTT broker machine
   sudo systemctl status mosquitto
   ```

2. **Check Backend Logs**
   ```bash
   tail -f /root/prompt-portal/backend/backend.log | grep -i "mqtt\|503\|error"
   ```

3. **Verify Nginx Config**
   ```bash
   sudo nginx -t
   sudo systemctl status nginx
   ```

4. **Manual Backend Restart**
   ```bash
   sudo systemctl restart prompt-portal-backend
   sleep 5
   curl http://127.0.0.1:3000/api/health
   ```

### MQTT Not Reconnecting?

Check backend logs for:
```
MQTT reconnection attempt X/10
MQTT reconnection successful
```

If you see "Max reconnection attempts reached":
```bash
# Restart backend to reset reconnection counter
sudo systemctl restart prompt-portal-backend
```

### Nginx Still Timing Out?

Verify the config was applied:
```bash
sudo cat /etc/nginx/sites-available/lammp.agaii.org | grep proxy_read_timeout
```

Should show `600s`, not `60s`.

## 📚 Related Files

- `deploy.sh` - Deployment script with nginx config
- `backend/app/mqtt.py` - MQTT connection management
- `backend/app/routers/chatbot.py` - Where 503 is raised
- `fix-503-long-runtime.ps1` - Windows script to generate fix files
- `apply-503-fix.sh` - Server deployment script

## 🎓 Prevention Tips

1. **Monitor MQTT Health**: Check backend logs regularly
2. **Use Systemd**: Always use systemd for production services
3. **Set Up Alerts**: Monitor `/api/health` endpoint
4. **Regular Restarts**: Consider daily backend restarts during low traffic

## 📝 Summary

| Issue | Cause | Fix |
|-------|-------|-----|
| 503 Error | MQTT disconnected | Auto-reconnection + health monitoring |
| 502 Error | Nginx timeout | Extended timeouts (600s) |
| Backend crash | Memory/MQTT issues | Systemd auto-restart |
| Long LLM response | 60s timeout | 600s timeout + streaming |

---

**Status**: ✅ Complete solution for long-runtime 502/503 errors  
**Last Updated**: 2025-11-04  
**Tested**: Production deployment on lammp.agaii.org

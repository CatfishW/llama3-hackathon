# Quick Fix Guide - 502 Bad Gateway Error

## Problem
After running for a long time, the web application returns:
```
POST https://lammp.agaii.org/api/chatbot/messages 502 (Bad Gateway)
```

## Quick Fix (Use PowerShell Script)

### On Windows (Local Development Machine):

```powershell
cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal
.\fix-502-error.ps1
```

This script will:
1. ✓ Upload updated backend code to server
2. ✓ Install systemd service with auto-restart
3. ✓ Update nginx timeouts to 120 seconds
4. ✓ Setup health monitoring
5. ✓ Verify deployment

**Total time: ~3-5 minutes**

---

## Manual Fix (If Script Fails)

### Step 1: Upload Code Changes
```powershell
# Upload updated backend files
scp backend/app/routers/chatbot.py root@lammp.agaii.org:/opt/prompt-portal/backend/app/routers/
scp backend/app/mqtt.py root@lammp.agaii.org:/opt/prompt-portal/backend/app/
```

### Step 2: Deploy on Server
```bash
# SSH into server
ssh root@lammp.agaii.org

# Run the fix script
cd /tmp
# Upload fix-502-error.sh first, then:
chmod +x fix-502-error.sh
sudo ./fix-502-error.sh
```

### Step 3: Verify
```bash
# Check backend status
sudo systemctl status prompt-portal-backend

# Check health
curl http://localhost:8000/api/health
curl https://lammp.agaii.org/api/health

# Watch logs
sudo journalctl -u prompt-portal-backend -f
```

---

## What Was Fixed

### 1. Backend Enhancements
- ✅ Check MQTT connection before processing requests
- ✅ Increased timeout to 90 seconds (was 45s)
- ✅ Better error messages for users
- ✅ Graceful shutdown handlers
- ✅ Periodic connection verification every 60 seconds

### 2. Process Management
- ✅ Systemd service with auto-restart on crash
- ✅ Resource limits (4GB memory, 65K file descriptors)
- ✅ Automatic logs to `/var/log/prompt-portal/`

### 3. Nginx Configuration
- ✅ Increased timeouts to 120 seconds (was 60s)
- ✅ Better proxy settings for long-running requests
- ✅ Proper buffer configuration

### 4. Health Monitoring
- ✅ Automatic health checks every 30 seconds
- ✅ Auto-restart after 3 consecutive failures
- ✅ Logs to `/var/log/prompt-portal/health-monitor.log`

---

## Monitoring Commands

### Check Service Status
```bash
# Backend service
sudo systemctl status prompt-portal-backend

# Health monitor
sudo systemctl status backend-monitor
```

### View Logs
```bash
# Backend logs (live)
sudo journalctl -u prompt-portal-backend -f

# Health monitor logs
sudo tail -f /var/log/prompt-portal/health-monitor.log

# Backend application logs
sudo tail -f /var/log/prompt-portal/backend.log
```

### Check Health Endpoints
```bash
# Local (on server)
curl http://localhost:8000/api/health | jq
curl http://localhost:8000/api/health/mqtt | jq

# External
curl https://lammp.agaii.org/api/health | jq
```

### Manual Restart (if needed)
```bash
# Restart backend
sudo systemctl restart prompt-portal-backend

# Restart health monitor
sudo systemctl restart backend-monitor

# Restart nginx
sudo systemctl restart nginx
```

---

## Troubleshooting

### Issue: Backend Still Returns 502

**Check 1: Is backend running?**
```bash
sudo systemctl status prompt-portal-backend
```

**Check 2: Is MQTT connected?**
```bash
curl http://localhost:8000/api/health/mqtt | jq '.connected'
```

**Check 3: Check recent logs**
```bash
sudo journalctl -u prompt-portal-backend -n 50
```

**Solution:**
```bash
# Restart everything
sudo systemctl restart mosquitto
sudo systemctl restart prompt-portal-backend
sudo systemctl restart nginx
```

### Issue: Backend Keeps Crashing

**Check logs:**
```bash
sudo journalctl -u prompt-portal-backend -n 100 | grep -i error
sudo tail -f /var/log/prompt-portal/backend-error.log
```

**Common causes:**
- MQTT broker down: `sudo systemctl status mosquitto`
- Out of memory: `free -h` (should have > 1GB available)
- Database locked: Check for `app.db-wal` files

**Solution:**
```bash
# Check MQTT
sudo systemctl restart mosquitto
sleep 5

# Clear database locks (if needed)
cd /opt/prompt-portal/backend
rm -f app.db-wal app.db-shm

# Restart backend
sudo systemctl restart prompt-portal-backend
```

### Issue: Nginx Returns 504 (Gateway Timeout)

This means nginx timeout is still too short.

**Fix nginx config:**
```bash
sudo nano /etc/nginx/sites-available/lammp.agaii.org

# Find "location /api/" section and ensure:
proxy_connect_timeout 10s;
proxy_send_timeout 120s;
proxy_read_timeout 120s;

# Save and test
sudo nginx -t
sudo systemctl reload nginx
```

### Issue: MQTT Connection Not Working

**Check MQTT broker:**
```bash
sudo systemctl status mosquitto
mosquitto_pub -h localhost -t test -m "hello"
```

**Check MQTT health:**
```bash
curl http://localhost:8000/api/health/mqtt | jq
```

**Solution:**
```bash
# Restart MQTT broker
sudo systemctl restart mosquitto
sleep 5

# Restart backend (will reconnect)
sudo systemctl restart prompt-portal-backend
```

---

## Testing the Fix

### 1. Quick Test
```bash
# From your local machine
curl https://lammp.agaii.org/api/health
```

Expected: HTTP 200 with `"status": "healthy"`

### 2. Send Test Message

Open https://lammp.agaii.org in your browser and send a chat message.

Expected: Response within 10-30 seconds (no 502 error)

### 3. Long-Running Test

```bash
# Run overnight to test stability
for i in {1..1000}; do
  echo "Test $i at $(date)"
  curl -X POST https://lammp.agaii.org/api/chatbot/messages \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"session_id": 1, "content": "Test '$i'"}' \
    | jq '.assistant_message.content' || echo "FAILED"
  sleep 60
done
```

---

## Rollback (If Needed)

If something goes wrong:

```bash
# SSH to server
ssh root@lammp.agaii.org

# Stop new services
sudo systemctl stop prompt-portal-backend
sudo systemctl stop backend-monitor

# Restore old code (if backup exists)
cd /opt/prompt-portal
mv backend backend_new
mv backend_backup_* backend

# Start old way
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## Success Indicators

After deployment, you should see:

✅ **Backend service running:**
```bash
$ sudo systemctl status prompt-portal-backend
● prompt-portal-backend.service - Prompt Portal Backend (FastAPI)
   Active: active (running) since ...
```

✅ **Health endpoint returns healthy:**
```bash
$ curl http://localhost:8000/api/health | jq '.status'
"healthy"
```

✅ **MQTT connected:**
```bash
$ curl http://localhost:8000/api/health/mqtt | jq '.connected'
true
```

✅ **No 502 errors in browser console**

✅ **Chat messages work consistently**

---

## Support

If issues persist after following this guide:

1. **Collect logs:**
   ```bash
   sudo journalctl -u prompt-portal-backend -n 200 > backend-logs.txt
   sudo cat /var/log/prompt-portal/health-monitor.log > monitor-logs.txt
   curl http://localhost:8000/api/health/mqtt > mqtt-health.json
   ```

2. **Check system resources:**
   ```bash
   free -h
   df -h
   top -b -n 1 | head -n 20
   ```

3. **Verify all services:**
   ```bash
   sudo systemctl status mosquitto
   sudo systemctl status prompt-portal-backend
   sudo systemctl status nginx
   ```

4. **Review documentation:**
   - `FIX_502_ERROR_LONG_RUNTIME.md` - Full detailed guide
   - `MQTT_LONG_RUNTIME_FIX.md` - MQTT connection fixes
   - Backend logs for specific error messages

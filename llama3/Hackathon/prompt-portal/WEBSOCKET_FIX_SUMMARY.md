# WebSocket Fix - Quick Summary

## Problem
```
WebSocket connection to 'wss://lammp.agaii.org/api/mqtt/ws/hints/session-874q8t' failed
```

## Cause
Nginx location blocks were in the wrong order. The general `/api/` block was catching WebSocket requests before the specific WebSocket block, so upgrade headers weren't being added.

## Solution
Reorder Nginx configuration to put specific WebSocket location blocks BEFORE general API block.

## Fix It Now

### From Windows (Your Machine)
```powershell
cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal
.\deploy-websocket-fix.ps1
```

### From Linux Server
```bash
ssh root@lammp.agaii.org
cd ~/prompt-portal
bash fix-websocket.sh
```

## What Gets Fixed

**Before (Broken):**
```nginx
location /api/ {                      # ← Catches ALL /api/* requests
    proxy_pass http://127.0.0.1:8000;
    # Missing WebSocket headers!
}

location /api/mqtt/ws/ {              # ← Never reached!
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

**After (Fixed):**
```nginx
location ~ ^/api/mqtt/ws/ {           # ← Checked FIRST (regex = higher priority)
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection $connection_upgrade;
    proxy_read_timeout 3600s;         # 1 hour timeout
}

location /api/ {                      # ← Checked second
    proxy_pass http://127.0.0.1:8000;
}
```

## Verify It Works

1. **Clear browser cache**: `Ctrl + Shift + R`
2. **Open DevTools**: `F12` → Console tab
3. **Check for errors**: Should NOT see WebSocket connection failures
4. **Network tab**: Filter by `WS`, look for status `101 Switching Protocols`

## What Changed

### Files Created
- ✅ `fix-websocket.sh` - Automated fix script for Linux server
- ✅ `deploy-websocket-fix.ps1` - Deploy script for Windows
- ✅ `WEBSOCKET_FIX_GUIDE.md` - Detailed documentation
- ✅ `WEBSOCKET_FIX_SUMMARY.md` - This file

### Files Modified
- ✅ `/etc/nginx/sites-available/lammp.agaii.org` - Nginx config on server

## Technical Details

### Why Order Matters
Nginx processes locations in this priority:
1. Exact match (`=`)
2. Regex match (`~` or `~*`) ← We use this
3. Longest prefix
4. General prefix ← The `/api/` block

By using `location ~ ^/api/mqtt/ws/`, we ensure WebSocket paths are matched before the general `/api/` prefix.

### Why WebSocket Needs Special Headers
HTTP → WebSocket upgrade requires:
```
Upgrade: websocket
Connection: Upgrade
```

Without these headers, the connection stays HTTP and can't upgrade to WebSocket protocol.

### Why Long Timeouts
WebSocket connections are **persistent** (stay open), unlike HTTP (open, request, close). 

Default timeouts (60s) would close the connection. We use:
- `proxy_read_timeout 3600s` (1 hour)
- `proxy_send_timeout 3600s` (1 hour)

## Troubleshooting

### Still seeing errors?

**Check backend is running:**
```bash
ssh root@lammp.agaii.org
netstat -tlnp | grep -E ":(8000|3000)"
```

**Check Nginx logs:**
```bash
sudo tail -f /var/log/nginx/error.log
```

**Restart services:**
```bash
# Restart Nginx
sudo systemctl restart nginx

# Restart backend
cd ~/prompt-portal/backend
pkill -f uvicorn
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > /dev/null 2>&1 &
```

**Check Nginx config:**
```bash
sudo nginx -t
cat /etc/nginx/sites-available/lammp.agaii.org | grep -A 10 "location ~ ^/api/mqtt/ws/"
```

## Need Help?

See the full guide: `WEBSOCKET_FIX_GUIDE.md`

Or check:
- Nginx docs: https://nginx.org/en/docs/http/websocket.html
- FastAPI WebSocket: https://fastapi.tiangolo.com/advanced/websockets/

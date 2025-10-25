# Quick Fix for https://lammp.agaii.org Login Issues

## Problem
- Frontend works at https://lammp.agaii.org/
- Login fails due to backend API connection issues
- CORS or configuration problems

## Quick Solution

### Option 1: Automated Fix (Recommended)

**On Windows:**
```powershell
cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal
.\fix-domain-deployment.ps1
```

**On Linux Server:**
```bash
cd /path/to/prompt-portal
chmod +x fix-domain-deployment.sh
./fix-domain-deployment.sh
```

This script will:
1. ✅ Configure backend CORS to allow https://lammp.agaii.org
2. ✅ Update frontend to use https://lammp.agaii.org/api
3. ✅ Rebuild frontend with correct configuration
4. ✅ Restart backend to apply changes
5. ✅ Reload Nginx (if on Linux server)

### Option 2: Manual Fix

If automated script doesn't work, follow these manual steps:

#### Step 1: Fix Backend CORS

Edit `backend/.env` and add/update:
```
CORS_ORIGINS=https://lammp.agaii.org,http://lammp.agaii.org,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173
```

#### Step 2: Configure Frontend

Create `frontend/.env.production`:
```
VITE_API_BASE=https://lammp.agaii.org/api
VITE_WS_BASE=wss://lammp.agaii.org/api
```

Create `frontend/.env.local`:
```
VITE_API_BASE=https://lammp.agaii.org/api
VITE_WS_BASE=wss://lammp.agaii.org/api
```

#### Step 3: Rebuild Frontend

```bash
cd frontend
npm run build
```

#### Step 4: Restart Backend

**Windows:**
```powershell
cd backend
Get-Process | Where-Object {$_.Path -like "*uvicorn*"} | Stop-Process -Force
Start-Process uvicorn -ArgumentList "app.main:app","--host","0.0.0.0","--port","3000" -WindowStyle Hidden
```

**Linux:**
```bash
cd backend
kill $(cat backend.pid) 2>/dev/null
nohup uvicorn app.main:app --host 0.0.0.0 --port 3000 > /dev/null 2>&1 &
echo $! > backend.pid
```

#### Step 5: Reload Nginx (Linux Server Only)

```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Verification Steps

1. **Check Backend is Running:**
   ```bash
   curl http://127.0.0.1:3000/docs
   ```
   Should return HTML content.

2. **Check CORS Headers:**
   ```bash
   curl -H "Origin: https://lammp.agaii.org" -I http://127.0.0.1:3000/docs
   ```
   Should include `Access-Control-Allow-Origin: https://lammp.agaii.org`

3. **Test API Through Nginx:**
   ```bash
   curl https://lammp.agaii.org/api/docs
   ```
   Should return backend API documentation.

4. **Test Login:**
   - Open https://lammp.agaii.org/ in browser
   - Open DevTools (F12) → Network tab
   - Try to login
   - Check for successful API calls to `/api/auth/login`

## Common Issues & Solutions

### Issue 1: "Network Error" in browser
**Cause:** Frontend can't reach backend
**Solution:** 
- Verify backend is running on port 3000
- Check Nginx is properly proxying `/api/` to backend
- Verify SSL certificate is valid

### Issue 2: CORS errors in browser console
**Cause:** Backend not configured to allow domain
**Solution:**
- Update `backend/.env` with correct CORS_ORIGINS
- Restart backend completely
- Clear browser cache

### Issue 3: 404 errors on API calls
**Cause:** Nginx not properly configured
**Solution:**
Check Nginx config has:
```nginx
location /api/ {
    proxy_pass http://127.0.0.1:3000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### Issue 4: Mixed content warnings (HTTP/HTTPS)
**Cause:** Frontend trying to access HTTP backend from HTTPS page
**Solution:**
- Ensure frontend .env files use `https://` for API_BASE
- Make sure Nginx SSL is properly configured

### Issue 5: WebSocket connection fails
**Cause:** WebSocket proxy not configured
**Solution:**
Ensure Nginx has WebSocket config:
```nginx
location /api/mqtt/ws/ {
    proxy_pass http://127.0.0.1:3000/api/mqtt/ws/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
}
```

## File Locations Reference

- Backend config: `backend/.env`
- Frontend config: `frontend/.env.production`, `frontend/.env.local`
- Nginx config: `/etc/nginx/sites-available/lammp.agaii.org` (Linux)
- Backend PID: `backend/backend.pid`
- Frontend build: `frontend/dist/`

## Support Commands

**Check what's running on port 3000:**
```bash
# Linux
lsof -i :3000

# Windows
netstat -ano | findstr :3000
```

**View backend logs (if logging enabled):**
```bash
cd backend
tail -f *.log
```

**View Nginx logs:**
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

**Test DNS resolution:**
```bash
nslookup lammp.agaii.org
```

## Expected Configuration

After running the fix, you should have:

**Backend CORS allows:**
- https://lammp.agaii.org ✓
- http://lammp.agaii.org ✓
- http://localhost:3000 ✓
- http://127.0.0.1:3000 ✓

**Frontend points to:**
- API Base: https://lammp.agaii.org/api ✓
- WebSocket: wss://lammp.agaii.org/api ✓

**Nginx proxies:**
- / → Frontend static files ✓
- /api/ → Backend at 127.0.0.1:3000 ✓
- /api/mqtt/ws/ → WebSocket endpoint ✓

## Still Having Issues?

1. Clear browser cache completely (Ctrl+Shift+Delete)
2. Try in incognito/private browsing mode
3. Check browser console (F12) for specific error messages
4. Verify your server's firewall allows ports 80, 443, and 3000
5. Ensure DNS is correctly pointing to your server
6. Test backend directly: `curl http://YOUR_SERVER_IP:3000/docs`

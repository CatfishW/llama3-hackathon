# 🔧 Routing Fix - Quick Reference

## Problem
- URLs showing: `https://lammp.agaii.org/api/api/templates` (double `/api`)
- Getting 405 Method Not Allowed errors
- Login and API requests failing

## Root Cause
1. Frontend base URL included `/api`: `VITE_API_BASE=https://lammp.agaii.org/api`
2. Frontend routes also have `/api`: `/api/templates`
3. Result: `/api` + `/api/templates` = `/api/api/templates` ❌

## Solution
Remove `/api` from the base URL, keep it only in routes:
- Base: `https://lammp.agaii.org`
- Route: `/api/templates`
- Result: `https://lammp.agaii.org/api/templates` ✅

## Fix Options

### OPTION 1: Automated (Recommended) ⚡
```bash
# On your server:
cd /root/prompt-portal
wget https://raw.githubusercontent.com/[your-repo]/fix-routing-complete.sh
chmod +x fix-routing-complete.sh
bash fix-routing-complete.sh
```

Or if you have the file locally:
```powershell
# From your Windows machine:
.\deploy-routing-fix.ps1 -ServerIP "your.ip" -ServerUser "root"
```

### OPTION 2: Via Git 📦
```bash
# On your local machine:
git add .
git commit -m "Fix routing configuration"
git push

# On your server:
cd /root/prompt-portal
git pull
chmod +x fix-routing-complete.sh
bash fix-routing-complete.sh
```

### OPTION 3: Manual Steps 🔧

#### Step 1: Fix Frontend Environment
```bash
cd /root/prompt-portal/frontend

# Update .env.production
cat > .env.production << EOF
VITE_API_BASE=https://lammp.agaii.org
VITE_WS_BASE=wss://lammp.agaii.org
EOF

# Update .env.local
cat > .env.local << EOF
VITE_API_BASE=https://lammp.agaii.org
VITE_WS_BASE=wss://lammp.agaii.org
EOF
```

#### Step 2: Fix Nginx Configuration
```bash
sudo nano /etc/nginx/sites-available/lammp.agaii.org
```

**Find and change:**
```nginx
# OLD:
location /api {
    rewrite ^/api/(.*) /$1 break;
    proxy_pass http://127.0.0.1:3000;
}

# NEW:
location /api/ {
    proxy_pass http://127.0.0.1:3000;
}
```

**Test and reload:**
```bash
sudo nginx -t
sudo systemctl reload nginx
```

#### Step 3: Rebuild Frontend
```bash
cd /root/prompt-portal/frontend
npm run build
```

#### Step 4: Restart Frontend Service
```bash
kill $(cat frontend.pid)
nohup npm run preview -- --host 0.0.0.0 --port 3001 > /dev/null 2>&1 &
echo $! > frontend.pid
```

## Verification ✅

1. **Clear browser cache**: `Ctrl + Shift + R`
2. **Open DevTools**: F12 → Network tab
3. **Try to login**
4. **Check URLs in Network tab**:
   - ✅ Should see: `https://lammp.agaii.org/api/auth/login`
   - ❌ Should NOT see: `https://lammp.agaii.org/api/api/...`

## Files Created
- ✅ `fix-routing-complete.sh` - Full automated fix
- ✅ `fix-nginx-routing.sh` - Nginx-only fix
- ✅ `quick-fix.sh` - Quick frontend-only fix
- ✅ `deploy-routing-fix.ps1` - Windows deployment script
- ✅ `ROUTING_FIX_GUIDE.md` - Detailed explanation
- ✅ `deploy.sh` - Updated for future deployments

## Files Modified
- ✅ `frontend/.env.production`
- ✅ `frontend/.env.local`
- ✅ `deploy.sh` (for future deployments)

## Troubleshooting

### Still seeing `/api/api/` in URLs?
- Hard refresh: `Ctrl + Shift + F5`
- Clear all browser data for the site
- Try incognito/private window

### 502 Bad Gateway?
- Check backend is running: `curl http://localhost:3000/api/docs`
- Check backend logs
- Restart backend if needed

### 404 Not Found?
- Check Nginx configuration: `sudo nginx -t`
- Check Nginx is running: `sudo systemctl status nginx`
- Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`

### Frontend not loading?
- Check frontend is running: `ps aux | grep vite`
- Check frontend.pid exists: `cat /root/prompt-portal/frontend/frontend.pid`
- Check dist folder: `ls -la /root/prompt-portal/frontend/dist/`

## Quick Commands

```bash
# Check all services
ps aux | grep -E "uvicorn|vite|nginx"

# Restart backend
cd /root/prompt-portal/backend
kill $(cat backend.pid)
nohup uvicorn app.main:app --host 0.0.0.0 --port 3000 > /dev/null 2>&1 &
echo $! > backend.pid

# Restart frontend
cd /root/prompt-portal/frontend
kill $(cat frontend.pid)
nohup npm run preview -- --host 0.0.0.0 --port 3001 > /dev/null 2>&1 &
echo $! > frontend.pid

# Check Nginx
sudo nginx -t
sudo systemctl status nginx
sudo systemctl reload nginx

# View logs
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

## Success Indicators

✅ URLs in browser console show single `/api/`: `https://lammp.agaii.org/api/...`  
✅ Login works without errors  
✅ Templates load correctly  
✅ No 405 Method Not Allowed errors  
✅ No 404 Not Found errors  

## Need Help?

Check the detailed guide: `ROUTING_FIX_GUIDE.md`

Or contact support with:
- Browser console errors (F12)
- Network tab screenshots
- Nginx error logs: `sudo tail -50 /var/log/nginx/error.log`

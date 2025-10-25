# Fix for 405 Method Not Allowed Errors

## Problem Summary

The console showed these errors:
```
GET https://lammp.agaii.org/api/api/templates 405 (Method Not Allowed)
POST https://lammp.agaii.org/api/api/login 405 (Method Not Allowed)
```

Notice the **double `/api/api/`** in the URLs? This is the root cause.

## Root Cause Analysis

### The Problem Chain

1. **Frontend API Client (`api.ts`)**
   - All API routes are defined with `/api/` prefix
   - Example: `api.get('/api/templates')`
   - This is correct and standard

2. **Frontend Environment (`.env.production`)**
   - Was set to: `VITE_API_BASE=https://lammp.agaii.org/api`
   - This added `/api` to the base URL

3. **Axios Request Construction**
   - Base URL: `https://lammp.agaii.org/api`
   - Route: `/api/templates`
   - **Result**: `https://lammp.agaii.org/api/api/templates` ❌

4. **Nginx Configuration**
   - Was stripping the `/api` prefix with `rewrite ^/api/(.*) /$1 break;`
   - Would have turned `/api/templates` into `/templates`
   - But received `/api/api/templates` which it didn't handle properly

5. **Backend Routes**
   - All routers are defined with `/api` prefix
   - Example: `router = APIRouter(prefix="/api/auth")`
   - Backend expects routes like `/api/auth/login`

## The Fix

### What Was Changed

#### 1. Frontend Environment Files
**Before:**
```bash
VITE_API_BASE=https://lammp.agaii.org/api
VITE_WS_BASE=wss://lammp.agaii.org/api
```

**After:**
```bash
VITE_API_BASE=https://lammp.agaii.org
VITE_WS_BASE=wss://lammp.agaii.org
```

#### 2. Nginx Configuration
**Before:**
```nginx
location /api {
    rewrite ^/api/(.*) /$1 break;
    proxy_pass http://127.0.0.1:3000;
    # ...
}
```

**After:**
```nginx
location /api/ {
    # No rewrite! Pass through with /api prefix
    proxy_pass http://127.0.0.1:3000;
    # ...
}
```

### Request Flow (After Fix)

1. **Frontend makes request**: `/api/templates`
2. **Axios constructs full URL**: 
   - Base: `https://lammp.agaii.org`
   - Route: `/api/templates`
   - **Full URL**: `https://lammp.agaii.org/api/templates` ✅

3. **Nginx receives**: `https://lammp.agaii.org/api/templates`
4. **Nginx proxies to**: `http://127.0.0.1:3000/api/templates`
5. **Backend receives**: `/api/templates` (matches the router prefix)
6. **Backend router**: `APIRouter(prefix="/api/templates")` handles it ✅

## How to Apply the Fix

### Option 1: Complete Automated Fix (Recommended)

Run this script on your server:
```bash
cd ~/prompt-portal
bash fix-routing-complete.sh
```

This will:
- Update environment files
- Fix Nginx configuration
- Rebuild frontend
- Restart frontend service

### Option 2: Manual Steps

1. **Update environment files:**
```bash
cd ~/prompt-portal/frontend

cat > .env.production << EOF
VITE_API_BASE=https://lammp.agaii.org
VITE_WS_BASE=wss://lammp.agaii.org
EOF

cat > .env.local << EOF
VITE_API_BASE=https://lammp.agaii.org
VITE_WS_BASE=wss://lammp.agaii.org
EOF
```

2. **Update Nginx configuration:**
```bash
sudo nano /etc/nginx/sites-available/lammp.agaii.org
```

Find the `location /api` block and change:
- `location /api` → `location /api/`
- Remove the `rewrite ^/api/(.*) /$1 break;` line

3. **Test and reload Nginx:**
```bash
sudo nginx -t
sudo systemctl reload nginx
```

4. **Rebuild frontend:**
```bash
cd ~/prompt-portal/frontend
npm run build
```

5. **Restart frontend service:**
```bash
kill $(cat frontend.pid)
nohup npm run preview -- --host 0.0.0.0 --port 3001 > /dev/null 2>&1 &
echo $! > frontend.pid
```

## Verification

After applying the fix:

1. **Clear browser cache**: Press `Ctrl+Shift+R` on the page
2. **Open browser DevTools**: F12 → Console tab
3. **Try to login or register**
4. **Check the Network tab**: URLs should now be:
   - ✅ `https://lammp.agaii.org/api/auth/login`
   - ✅ `https://lammp.agaii.org/api/templates`
   - ❌ NOT `https://lammp.agaii.org/api/api/...`

## Files Modified

1. `frontend/.env.production` - Removed `/api` from base URL
2. `frontend/.env.local` - Removed `/api` from base URL
3. `/etc/nginx/sites-available/lammp.agaii.org` - Removed rewrite rule
4. `deploy.sh` - Updated for future deployments
5. Created `fix-routing-complete.sh` - Automated fix script
6. Created `fix-nginx-routing.sh` - Nginx-only fix script

## Prevention for Future Deployments

The `deploy.sh` script has been updated to prevent this issue in future deployments. The fix ensures:
- Frontend `VITE_API_BASE` doesn't include `/api` suffix
- Nginx passes through the `/api` prefix without modification
- Backend continues to use `/api` prefix in all routers

## Additional Notes

### Why This Happened
This is a common issue when migrating from direct access (app communicates directly with backend) to proxied access (Nginx sits between frontend and backend). The `/api` prefix was being added at multiple layers.

### Alternative Approaches Considered

1. **Remove `/api` from all frontend routes** - Would break development mode
2. **Remove `/api` from backend routers** - Large refactor, affects all code
3. **Keep double `/api` and make backend handle it** - Messy and non-standard
4. **Fix the configuration** ✅ - Clean, maintains standards

## Troubleshooting

If you still see issues after applying the fix:

1. **Hard refresh the browser**: `Ctrl+Shift+F5`
2. **Check Nginx is running**: `sudo systemctl status nginx`
3. **Check backend is running**: `curl http://localhost:3000/api/docs`
4. **Check Nginx logs**: `sudo tail -f /var/log/nginx/error.log`
5. **Check frontend is serving**: `ls -la /root/prompt-portal/frontend/dist/`

## Support

If you encounter any issues:
1. Check the Nginx error logs: `sudo tail -f /var/log/nginx/error.log`
2. Check backend logs: Look at the uvicorn output
3. Verify environment files are correct: `cat ~/prompt-portal/frontend/.env.production`
4. Test backend directly: `curl https://lammp.agaii.org/api/docs`

# Backend API Fix for Domain Access

## Problem
When accessing https://lammp.agaii.org/login, the backend API fails because CORS is not configured to allow requests from the domain.

## Quick Fix (Recommended)

### For Windows:
1. Run the CORS fix script:
   ```cmd
   cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal
   fix-backend-cors.bat
   ```

2. Restart the backend:
   ```cmd
   restart-backend.bat
   ```

### For Linux/Mac:
1. Run the CORS fix script:
   ```bash
   cd /path/to/prompt-portal
   chmod +x fix-backend-cors.sh
   ./fix-backend-cors.sh
   ```

2. Restart the backend:
   ```bash
   kill $(cat backend/backend.pid) 2>/dev/null
   cd backend
   nohup uvicorn app.main:app --host 0.0.0.0 --port 3000 > /dev/null 2>&1 &
   echo $! > backend.pid
   ```

## What the Fix Does

The script updates the `backend/.env` file to include these CORS origins:
- https://lammp.agaii.org (HTTPS - for production with SSL)
- http://lammp.agaii.org (HTTP - fallback)
- http://localhost:3000 (Backend local access)
- http://127.0.0.1:3000 (Backend local access)
- http://localhost:3001 (Frontend local access)
- http://127.0.0.1:3001 (Frontend local access)
- http://localhost:5173 (Vite dev server)
- http://127.0.0.1:5173 (Vite dev server)

## Manual Fix (Alternative)

If the scripts don't work, manually edit `backend/.env`:

1. Open `backend/.env` in a text editor
2. Find or add the line:
   ```
   CORS_ORIGINS=https://lammp.agaii.org,http://lammp.agaii.org,http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001,http://localhost:5173,http://127.0.0.1:5173
   ```
3. Save the file
4. Restart the backend server

## Verification

After applying the fix:

1. Check if backend is running:
   ```cmd
   curl http://127.0.0.1:3000/docs
   ```

2. Check CORS headers from your domain:
   ```cmd
   curl -H "Origin: https://lammp.agaii.org" -I http://127.0.0.1:3000/docs
   ```
   Should include: `Access-Control-Allow-Origin: https://lammp.agaii.org`

3. Test login from the website:
   - Go to https://lammp.agaii.org/login
   - Open browser DevTools (F12) → Network tab
   - Try to login
   - Check for CORS errors (should be gone)

## Nginx Configuration (If Using)

Make sure your Nginx config at `/etc/nginx/sites-available/lammp.agaii.org` has:

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:3000/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Reload Nginx after any changes:
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Common Issues

### Issue 1: Backend not accessible from domain
**Solution**: Check if backend is running and port 3000 is open
```cmd
netstat -an | findstr :3000
```

### Issue 2: CORS errors persist
**Solution**: 
1. Verify `.env` was updated correctly
2. Restart backend completely (not just reload)
3. Clear browser cache
4. Check browser console for exact error

### Issue 3: SSL certificate issues
**Solution**: Make sure SSL is properly set up:
```bash
sudo certbot --nginx -d lammp.agaii.org
```

## Testing the API Directly

Test backend endpoints directly:

1. Health check:
   ```cmd
   curl http://127.0.0.1:3000/docs
   ```

2. Login endpoint:
   ```cmd
   curl -X POST http://127.0.0.1:3000/auth/login -H "Content-Type: application/json" -d "{\"username\":\"test\",\"password\":\"test123\"}"
   ```

3. From domain (if Nginx configured):
   ```cmd
   curl https://lammp.agaii.org/api/docs
   ```

## Support

If issues persist:
1. Check backend logs: `cd backend && tail -f logs/*.log` (if logging enabled)
2. Check Nginx logs: `sudo tail -f /var/log/nginx/error.log`
3. Verify domain DNS: `nslookup lammp.agaii.org`
4. Check firewall: Ensure ports 80, 443, and 3000 are open

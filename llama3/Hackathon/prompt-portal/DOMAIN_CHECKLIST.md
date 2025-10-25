# Domain Configuration Checklist - lammp.agaii.org

Use this checklist to ensure proper domain configuration for Prompt Portal.

## ✅ Pre-Deployment

- [ ] Server with public IP address
- [ ] SSH/terminal access to server
- [ ] Root/sudo privileges
- [ ] Prompt Portal deployed (ran `deploy.sh` or `deploy-production.sh`)
- [ ] Access to DNS management for `agaii.org` domain

## ✅ DNS Configuration

- [ ] Added A record to DNS provider:
  - **Type:** A
  - **Name:** lammp
  - **Value:** [YOUR_SERVER_IP]
  - **TTL:** 3600 or Auto

- [ ] Verified DNS propagation:
  ```bash
  dig lammp.agaii.org
  # Should return your server IP
  ```

- [ ] Optional: Added www subdomain:
  - **Type:** CNAME
  - **Name:** www.lammp
  - **Value:** lammp.agaii.org

## ✅ Backend Configuration

- [ ] Updated `backend/.env` with domain in CORS_ORIGINS:
  ```env
  CORS_ORIGINS=https://lammp.agaii.org,http://lammp.agaii.org,http://localhost:5173
  ```

- [ ] Backend environment includes:
  - [ ] SECRET_KEY (generated and secure)
  - [ ] DATABASE_URL configured
  - [ ] MQTT broker settings configured

- [ ] Database initialized (app.db exists)

## ✅ Frontend Configuration

- [ ] Created `frontend/.env.production`:
  ```env
  VITE_API_BASE=https://lammp.agaii.org/api
  VITE_WS_BASE=wss://lammp.agaii.org/api
  ```

- [ ] Created `frontend/.env.local` (same as above)

- [ ] Frontend build successful:
  ```bash
  cd frontend
  npm run build
  # Dist folder created with no errors
  ```

## ✅ Nginx Configuration

- [ ] Nginx installed: `nginx -v`

- [ ] Configuration file created at:
  `/etc/nginx/sites-available/lammp.agaii.org`

- [ ] Symlink created:
  ```bash
  ls -l /etc/nginx/sites-enabled/lammp.agaii.org
  ```

- [ ] Configuration includes:
  - [ ] Frontend static file serving
  - [ ] API reverse proxy to port 8000
  - [ ] WebSocket proxy configuration
  - [ ] Security headers

- [ ] Nginx configuration test passed:
  ```bash
  sudo nginx -t
  ```

- [ ] Nginx reloaded/restarted:
  ```bash
  sudo systemctl status nginx
  # Should show "active (running)"
  ```

## ✅ SSL Certificate

- [ ] Certbot installed: `certbot --version`

- [ ] DNS pointing to correct IP (required for SSL)

- [ ] SSL certificate obtained:
  ```bash
  sudo certbot --nginx -d lammp.agaii.org
  ```

- [ ] Certificate verified:
  ```bash
  sudo certbot certificates
  # Should show lammp.agaii.org certificate
  ```

- [ ] Auto-renewal configured:
  ```bash
  sudo certbot renew --dry-run
  # Should succeed
  ```

## ✅ Firewall Configuration

- [ ] Firewall allows HTTP (port 80):
  ```bash
  sudo ufw status | grep 80
  ```

- [ ] Firewall allows HTTPS (port 443):
  ```bash
  sudo ufw status | grep 443
  ```

- [ ] Firewall allows SSH (port 22):
  ```bash
  sudo ufw status | grep 22
  ```

- [ ] Backend port accessible internally:
  ```bash
  curl http://127.0.0.1:8000/docs
  # Should return API documentation
  ```

## ✅ Services Running

- [ ] Backend service running:
  ```bash
  pm2 status
  # prompt-portal-backend should show "online"
  ```
  OR
  ```bash
  ps aux | grep uvicorn
  # Should show uvicorn process
  ```

- [ ] Backend health check passes:
  ```bash
  curl http://127.0.0.1:8000/docs
  # Should return HTML
  ```

- [ ] Nginx running:
  ```bash
  sudo systemctl status nginx
  # Should show "active (running)"
  ```

## ✅ Testing & Verification

### Basic Connectivity

- [ ] HTTP redirects to HTTPS:
  ```bash
  curl -I http://lammp.agaii.org
  # Should show 301/302 redirect to https://
  ```

- [ ] HTTPS site loads:
  ```bash
  curl -I https://lammp.agaii.org
  # Should return 200 OK
  ```

- [ ] API accessible:
  ```bash
  curl https://lammp.agaii.org/api/docs
  # Should return API documentation
  ```

### Browser Testing

- [ ] Main site loads: https://lammp.agaii.org
  - [ ] No SSL warnings
  - [ ] Page renders correctly
  - [ ] No console errors (F12)

- [ ] Registration works:
  - [ ] Can create new account
  - [ ] Redirects to login/dashboard

- [ ] Login works:
  - [ ] Can log in with credentials
  - [ ] Receives JWT token
  - [ ] Redirects to dashboard

- [ ] Templates page works:
  - [ ] Can create new template
  - [ ] Can view templates
  - [ ] Can edit templates
  - [ ] Can delete templates

- [ ] Leaderboard page loads

- [ ] Profile/Settings page loads

### WebSocket Testing

- [ ] WebSocket connection works:
  - Open browser console at https://lammp.agaii.org
  - Run:
    ```javascript
    const ws = new WebSocket('wss://lammp.agaii.org/api/mqtt/ws/test123');
    ws.onopen = () => console.log('✅ WebSocket Connected!');
    ws.onerror = (err) => console.error('❌ WebSocket Error:', err);
    ```
  - Should see "✅ WebSocket Connected!"

### MQTT Testing

- [ ] MQTT functionality works:
  - Navigate to Test & Monitor page
  - Enter session ID
  - Click "Connect to WS"
  - Connection status shows connected
  - Can publish test state

## ✅ Monitoring Setup

- [ ] PM2 configured for auto-restart:
  ```bash
  pm2 startup
  pm2 save
  ```

- [ ] Log viewing works:
  ```bash
  pm2 logs prompt-portal-backend
  # Shows backend logs
  ```

- [ ] Nginx logs accessible:
  ```bash
  sudo tail -f /var/log/nginx/error.log
  ```

## ✅ Security Hardening

- [ ] Strong SECRET_KEY in backend/.env (32+ characters)

- [ ] Database file permissions restricted:
  ```bash
  ls -l backend/app.db
  # Should not be world-readable
  ```

- [ ] .env files not publicly accessible

- [ ] Unnecessary ports closed in firewall

- [ ] SSH key authentication enabled (password disabled)

- [ ] Regular security updates enabled:
  ```bash
  sudo apt list --upgradable
  ```

## ✅ Backup & Recovery

- [ ] Database backup script exists:
  ```bash
  ls /opt/scripts/backup.sh
  ```

- [ ] Backup script tested:
  ```bash
  sudo /opt/scripts/backup.sh
  ls /opt/backups/
  # Should show backup files
  ```

- [ ] Cron jobs configured for automatic backups:
  ```bash
  crontab -l
  # Should show backup schedule
  ```

## ✅ Documentation

- [ ] Domain configuration documented
- [ ] DNS settings recorded
- [ ] SSL certificate details saved
- [ ] Access credentials stored securely
- [ ] Team members know how to access logs

## ✅ Final Verification

- [ ] Share https://lammp.agaii.org with team
- [ ] Test from multiple devices
- [ ] Test from different networks
- [ ] Verify all features work in production
- [ ] Performance acceptable (page load < 3s)

## 🎉 Deployment Complete!

All items checked? Congratulations! Your Prompt Portal is now live at:

**🌐 https://lammp.agaii.org**

---

## 📞 Quick Reference

### Restart Services
```bash
pm2 restart prompt-portal-backend
sudo systemctl reload nginx
```

### View Logs
```bash
pm2 logs prompt-portal-backend
sudo tail -f /var/log/nginx/error.log
```

### Check Status
```bash
pm2 status
sudo systemctl status nginx
sudo certbot certificates
```

### Emergency Rollback
```bash
# Restore .env backup
cp backend/.env.backup backend/.env
# Restore Nginx config
sudo cp /etc/nginx/sites-available/lammp.agaii.org.backup /etc/nginx/sites-available/lammp.agaii.org
# Reload
pm2 restart prompt-portal-backend
sudo systemctl reload nginx
```

---

**Need help?** See [DOMAIN_SETUP.md](./DOMAIN_SETUP.md) for detailed troubleshooting.

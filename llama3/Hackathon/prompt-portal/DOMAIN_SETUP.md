# Domain Setup Guide - lammp.agaii.org

This guide provides step-by-step instructions for configuring the Prompt Portal application with the domain name **lammp.agaii.org**.

## 📋 Prerequisites

- Access to DNS management for agaii.org domain
- Server with public IP address
- Prompt Portal already deployed (run `deploy.sh` or `deploy-production.sh` first)
- Root/sudo access to the server

## 🚀 Quick Setup

### Option 1: Automated Setup (Recommended)

```bash
cd /path/to/prompt-portal
chmod +x setup-domain.sh
./setup-domain.sh
```

This script will:
- Update backend CORS settings
- Configure frontend for the domain
- Set up Nginx with proper reverse proxy
- Check DNS configuration
- Optionally set up SSL certificate

### Option 2: Manual Setup

Follow the detailed steps below.

---

## 📝 Detailed Manual Setup

### Step 1: Configure DNS

Configure your DNS provider (for agaii.org) with the following A record:

```
Type: A
Name: lammp
Host: lammp.agaii.org
Value: YOUR_SERVER_IP
TTL: 3600 (or Auto)
```

**Verify DNS propagation:**
```bash
# Check DNS resolution
dig lammp.agaii.org

# Or use nslookup
nslookup lammp.agaii.org

# Should return your server IP
```

DNS propagation can take anywhere from a few minutes to 48 hours.

---

### Step 2: Update Backend Configuration

Edit `backend/.env` to include the domain in CORS origins:

```bash
cd backend
nano .env
```

Update the `CORS_ORIGINS` line:
```env
CORS_ORIGINS=https://lammp.agaii.org,http://lammp.agaii.org,https://www.lammp.agaii.org,http://localhost:5173,http://127.0.0.1:5173
```

---

### Step 3: Update Frontend Configuration

Create/update `frontend/.env.production`:

```bash
cd ../frontend
cat > .env.production << EOF
VITE_API_BASE=https://lammp.agaii.org/api
VITE_WS_BASE=wss://lammp.agaii.org/api
EOF
```

Also create `.env.local` for local development:
```bash
cat > .env.local << EOF
VITE_API_BASE=https://lammp.agaii.org/api
VITE_WS_BASE=wss://lammp.agaii.org/api
EOF
```

---

### Step 4: Rebuild Frontend

```bash
npm run build
```

If build fails:
```bash
rm -rf node_modules package-lock.json dist
npm install --legacy-peer-deps
npm run build
```

---

### Step 5: Configure Nginx

Create Nginx configuration file:

```bash
sudo nano /etc/nginx/sites-available/lammp.agaii.org
```

Add the following configuration:

```nginx
# Redirect www to non-www
server {
    listen 80;
    listen [::]:80;
    server_name www.lammp.agaii.org;
    return 301 https://lammp.agaii.org$request_uri;
}

# Main server block
server {
    listen 80;
    listen [::]:80;
    server_name lammp.agaii.org;

    # Serve frontend static files
    location / {
        root /path/to/prompt-portal/frontend/dist;
        try_files $uri $uri/ /index.html;
        index index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Proxy API requests to backend
    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support for MQTT
    location /api/mqtt/ws/ {
        proxy_pass http://127.0.0.1:8000/api/mqtt/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket specific timeouts
        proxy_read_timeout 86400s;
        proxy_send_timeout 86400s;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/lammp.agaii.org /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site
```

Test configuration:
```bash
sudo nginx -t
```

Reload Nginx:
```bash
sudo systemctl reload nginx
```

---

### Step 6: Set Up SSL Certificate

Install Certbot (if not already installed):
```bash
sudo apt update
sudo apt install -y certbot python3-certbot-nginx
```

Obtain and install SSL certificate:
```bash
sudo certbot --nginx -d lammp.agaii.org
```

Follow the prompts:
- Enter email address: `admin@agaii.org`
- Agree to Terms of Service: Yes
- Redirect HTTP to HTTPS: Yes (recommended)

Certbot will automatically:
- Obtain SSL certificate from Let's Encrypt
- Update Nginx configuration for HTTPS
- Set up automatic renewal

Verify SSL certificate:
```bash
sudo certbot certificates
```

---

### Step 7: Restart Services

Restart backend to pick up new CORS settings:

**With PM2:**
```bash
cd backend
pm2 restart prompt-portal-backend
```

**Without PM2:**
```bash
cd backend
pkill -f "uvicorn.*app\.main:app"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &
```

Verify backend is running:
```bash
curl http://127.0.0.1:8000/docs
```

---

### Step 8: Configure Firewall

Ensure firewall allows HTTP and HTTPS:

**UFW (Ubuntu/Debian):**
```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw reload
```

**firewalld (CentOS/RHEL):**
```bash
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

---

## ✅ Verification

### 1. Test DNS Resolution
```bash
dig lammp.agaii.org
# Should return your server IP
```

### 2. Test HTTP/HTTPS Access
```bash
# Test HTTP (should redirect to HTTPS)
curl -I http://lammp.agaii.org

# Test HTTPS
curl -I https://lammp.agaii.org

# Test API
curl https://lammp.agaii.org/api/docs
```

### 3. Test WebSocket Connection
```bash
# From browser console at https://lammp.agaii.org
const ws = new WebSocket('wss://lammp.agaii.org/api/mqtt/ws/test');
ws.onopen = () => console.log('Connected!');
```

### 4. Browser Testing
Visit the following URLs in your browser:
- https://lammp.agaii.org - Main site
- https://lammp.agaii.org/api/docs - API documentation
- Register an account and test features

---

## 🔧 Troubleshooting

### DNS Not Resolving

**Problem:** `dig lammp.agaii.org` returns no results

**Solutions:**
1. Wait for DNS propagation (can take up to 48 hours)
2. Check DNS configuration at your domain registrar
3. Use different DNS server for testing: `dig @8.8.8.8 lammp.agaii.org`

### SSL Certificate Failed

**Problem:** Certbot fails to obtain certificate

**Solutions:**
1. Ensure DNS is pointing to your server
2. Check if ports 80 and 443 are open
3. Verify Nginx is running: `sudo systemctl status nginx`
4. Check Certbot logs: `sudo tail -f /var/log/letsencrypt/letsencrypt.log`

### CORS Errors in Browser

**Problem:** Browser console shows CORS errors

**Solutions:**
1. Verify `CORS_ORIGINS` in `backend/.env` includes the domain
2. Restart backend service
3. Clear browser cache and cookies
4. Check backend logs: `pm2 logs prompt-portal-backend`

### WebSocket Connection Fails

**Problem:** MQTT/WebSocket features not working

**Solutions:**
1. Check Nginx WebSocket proxy configuration
2. Verify backend is running: `curl http://127.0.0.1:8000/docs`
3. Check firewall allows WebSocket connections
4. Test WebSocket from server: `wscat -c wss://lammp.agaii.org/api/mqtt/ws/test`

### Backend API Not Responding

**Problem:** API returns 502 Bad Gateway

**Solutions:**
1. Check if backend is running:
   ```bash
   pm2 status
   # or
   ps aux | grep uvicorn
   ```
2. Check backend logs:
   ```bash
   pm2 logs prompt-portal-backend
   # or
   tail -f backend/backend.log
   ```
3. Restart backend service
4. Verify backend port: `sudo ss -tlnp | grep :8000`

---

## 📊 Monitoring & Maintenance

### Check Service Status
```bash
# Nginx status
sudo systemctl status nginx

# Backend status (with PM2)
pm2 status

# Check logs
pm2 logs prompt-portal-backend
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### SSL Certificate Renewal
Certbot automatically renews certificates. Test renewal:
```bash
sudo certbot renew --dry-run
```

### Backup Configuration
```bash
# Backup important files
cp backend/.env backend/.env.backup
cp /etc/nginx/sites-available/lammp.agaii.org /etc/nginx/sites-available/lammp.agaii.org.backup
```

---

## 🌐 Access URLs

After successful setup, your application will be available at:

| Service | URL | Description |
|---------|-----|-------------|
| **Main Site** | https://lammp.agaii.org | Frontend application |
| **API Documentation** | https://lammp.agaii.org/api/docs | Interactive API docs |
| **API Endpoint** | https://lammp.agaii.org/api | Backend API |
| **WebSocket** | wss://lammp.agaii.org/api/mqtt/ws/ | MQTT WebSocket |

---

## 🔐 Security Checklist

- [x] SSL certificate installed (HTTPS enabled)
- [x] HTTP redirects to HTTPS
- [x] Security headers configured in Nginx
- [x] Firewall configured (ports 80, 443, 22 only)
- [x] CORS properly configured
- [x] Database backed up regularly
- [x] Strong SECRET_KEY in backend/.env

---

## 📞 Quick Commands Reference

```bash
# View logs
pm2 logs prompt-portal-backend
sudo tail -f /var/log/nginx/error.log

# Restart services
pm2 restart prompt-portal-backend
sudo systemctl reload nginx

# Test configuration
sudo nginx -t
curl -I https://lammp.agaii.org

# SSL certificate status
sudo certbot certificates

# DNS check
dig lammp.agaii.org
nslookup lammp.agaii.org

# Service status
pm2 status
sudo systemctl status nginx
```

---

## 📚 Additional Resources

- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [Nginx Reverse Proxy Guide](https://docs.nginx.com/nginx/admin-guide/web-server/reverse-proxy/)
- [Certbot Documentation](https://certbot.eff.org/docs/)

---

## 🎉 Success!

Your Prompt Portal is now running on **lammp.agaii.org** with:
- ✅ Custom domain name
- ✅ HTTPS/SSL encryption
- ✅ Reverse proxy setup
- ✅ WebSocket support
- ✅ Production-ready configuration

Enjoy your secure, production-ready Prompt Portal!

# Domain Configuration Summary - lammp.agaii.org

## 📝 Overview

Domain name **lammp.agaii.org** has been configured for the Prompt Portal web application. This document summarizes the changes and setup required.

## 🆕 New Files Created

### 1. **setup-domain.sh** (Main Setup Script)
Automated script that configures the entire domain setup:
- Updates backend CORS settings
- Configures frontend environment for domain
- Sets up Nginx reverse proxy
- Checks DNS configuration
- Optionally installs SSL certificate
- Restarts all services

**Usage:**
```bash
chmod +x setup-domain.sh
./setup-domain.sh
```

### 2. **DOMAIN_SETUP.md** (Detailed Documentation)
Comprehensive guide covering:
- DNS configuration instructions
- Backend/frontend configuration steps
- Nginx setup with full configuration example
- SSL certificate installation with Certbot
- Troubleshooting common issues
- Security checklist
- Monitoring and maintenance

### 3. **DOMAIN_QUICK_GUIDE.md** (Quick Reference)
Quick-start guide with:
- One-line setup command
- DNS configuration at a glance
- Quick troubleshooting commands
- Essential test commands

### 4. **DOMAIN_CHECKLIST.md** (Deployment Checklist)
Step-by-step checklist ensuring:
- All prerequisites met
- DNS properly configured
- Services running correctly
- Security hardened
- Backups configured
- Everything tested

### 5. **README.md** (Updated)
Added domain information:
- Live URL: https://lammp.agaii.org
- Quick start section with domain setup
- Links to domain documentation

## 🔧 Configuration Changes Required

### Backend Configuration (`backend/.env`)

**Add to CORS_ORIGINS:**
```env
CORS_ORIGINS=https://lammp.agaii.org,http://lammp.agaii.org,https://www.lammp.agaii.org,http://localhost:5173
```

This allows the frontend hosted at lammp.agaii.org to make API requests to the backend.

### Frontend Configuration

**Create `frontend/.env.production`:**
```env
VITE_API_BASE=https://lammp.agaii.org/api
VITE_WS_BASE=wss://lammp.agaii.org/api
```

This configures the frontend to use the domain for API and WebSocket connections.

### Nginx Configuration

**Create `/etc/nginx/sites-available/lammp.agaii.org`:**

Key features:
- Serves frontend static files from `frontend/dist`
- Reverse proxy for API requests to backend (port 8000)
- WebSocket proxy support for MQTT connections
- Security headers (X-Frame-Options, X-Content-Type-Options, X-XSS-Protection)
- Static asset caching (1 year for images, fonts, etc.)
- Redirects www to non-www
- HTTPS configuration (added by Certbot)

## 🌐 DNS Configuration Required

Add the following DNS record at your DNS provider:

| Type | Name | Value | TTL |
|------|------|-------|-----|
| A | lammp | YOUR_SERVER_IP | 3600 |

**Example:** If your server IP is `203.0.113.45`:
- **Type:** A
- **Name:** lammp
- **Value:** 203.0.113.45
- **TTL:** 3600 (or Auto)

This creates: `lammp.agaii.org` → `203.0.113.45`

### Verify DNS Propagation

```bash
dig lammp.agaii.org
# Should return your server IP in the ANSWER section
```

DNS propagation typically takes 5-30 minutes but can take up to 48 hours.

## 🔒 SSL Certificate Setup

Once DNS is configured, obtain a free SSL certificate from Let's Encrypt:

```bash
sudo certbot --nginx -d lammp.agaii.org
```

This will:
1. Verify domain ownership (requires DNS to be working)
2. Obtain SSL certificate
3. Automatically configure Nginx for HTTPS
4. Set up auto-renewal (certificates expire every 90 days)

## 📊 Architecture Overview

```
Internet
    ↓
lammp.agaii.org (DNS → Server IP)
    ↓
Nginx (Port 80/443)
    ├─→ / → Frontend Static Files (React/Vite)
    ├─→ /api → Backend Reverse Proxy (Port 8000)
    └─→ /api/mqtt/ws → WebSocket Proxy (Port 8000)
            ↓
    FastAPI Backend (Port 8000)
        ├─→ Database (SQLite)
        └─→ MQTT Broker (External)
```

## 🚀 Deployment Steps

### Quick Deployment (Automated)

```bash
# 1. Ensure basic deployment is done
./deploy.sh

# 2. Configure DNS (see DNS Configuration section above)

# 3. Run domain setup script
chmod +x setup-domain.sh
./setup-domain.sh

# 4. Follow prompts to set up SSL
```

### Manual Deployment

See [DOMAIN_SETUP.md](./DOMAIN_SETUP.md) for detailed manual steps.

## ✅ Testing

After deployment, verify:

### 1. DNS Resolution
```bash
dig lammp.agaii.org
# Should return your server IP
```

### 2. HTTP/HTTPS Access
```bash
curl -I http://lammp.agaii.org
# Should redirect to HTTPS (301/302)

curl -I https://lammp.agaii.org
# Should return 200 OK
```

### 3. API Access
```bash
curl https://lammp.agaii.org/api/docs
# Should return API documentation HTML
```

### 4. Browser Access
- Visit https://lammp.agaii.org
- Should load without SSL warnings
- Can register/login
- All features work (templates, leaderboard, MQTT)

### 5. WebSocket Connection
In browser console at https://lammp.agaii.org:
```javascript
const ws = new WebSocket('wss://lammp.agaii.org/api/mqtt/ws/test');
ws.onopen = () => console.log('Connected!');
```

## 🔍 Troubleshooting

### DNS Not Resolving
- Wait 5-30 minutes for propagation
- Check DNS configuration at provider
- Test with: `dig @8.8.8.8 lammp.agaii.org`

### SSL Certificate Failed
- Ensure DNS is working first
- Check ports 80 and 443 are open
- Verify Nginx is running
- Check Certbot logs: `/var/log/letsencrypt/letsencrypt.log`

### CORS Errors
- Verify domain in `backend/.env` CORS_ORIGINS
- Restart backend: `pm2 restart prompt-portal-backend`
- Clear browser cache

### Backend Not Responding (502 Error)
- Check backend is running: `pm2 status`
- Check backend logs: `pm2 logs prompt-portal-backend`
- Verify port 8000: `sudo ss -tlnp | grep :8000`

## 📦 What's Included

✅ **Automated Setup Script** - One command deployment
✅ **Comprehensive Documentation** - Detailed guides and references
✅ **Deployment Checklist** - Step-by-step verification
✅ **Nginx Configuration** - Production-ready reverse proxy
✅ **SSL Support** - HTTPS with Let's Encrypt
✅ **WebSocket Support** - For real-time MQTT features
✅ **Security Headers** - Basic security hardening
✅ **Static Asset Caching** - Performance optimization

## 🎯 Next Steps

1. **Configure DNS** - Add A record pointing to your server
2. **Run Setup Script** - Execute `./setup-domain.sh`
3. **Verify DNS** - Wait for propagation and test
4. **Install SSL** - Run Certbot to enable HTTPS
5. **Test Application** - Verify all features work
6. **Monitor** - Set up log monitoring and alerts

## 📚 Documentation Files

| File | Purpose |
|------|---------|
| `setup-domain.sh` | Automated setup script |
| `DOMAIN_SETUP.md` | Detailed setup guide |
| `DOMAIN_QUICK_GUIDE.md` | Quick reference |
| `DOMAIN_CHECKLIST.md` | Deployment checklist |
| `README.md` | Updated with domain info |

## 🌐 Final URLs

After successful setup, your application will be available at:

- **Main Site:** https://lammp.agaii.org
- **API Documentation:** https://lammp.agaii.org/api/docs
- **API Endpoint:** https://lammp.agaii.org/api
- **WebSocket:** wss://lammp.agaii.org/api/mqtt/ws/{session}

## 📞 Quick Commands

```bash
# Check DNS
dig lammp.agaii.org

# Setup domain
./setup-domain.sh

# Install SSL
sudo certbot --nginx -d lammp.agaii.org

# Restart services
pm2 restart prompt-portal-backend
sudo systemctl reload nginx

# View logs
pm2 logs prompt-portal-backend
sudo tail -f /var/log/nginx/error.log

# Test
curl -I https://lammp.agaii.org
```

## 💡 Tips

- **DNS Propagation:** Can take 5 minutes to 48 hours
- **SSL Certificate:** Free and auto-renews every 90 days
- **Monitoring:** Set up uptime monitoring for production
- **Backups:** Database backups run daily at 2 AM (if using production deployment)
- **Logs:** Check regularly for errors or issues

## 🎉 Success Criteria

Your domain is properly configured when:

✅ `dig lammp.agaii.org` returns your server IP
✅ https://lammp.agaii.org loads without SSL warnings
✅ Can register and login successfully
✅ All pages load (Dashboard, Templates, Leaderboard)
✅ WebSocket connections work (MQTT features)
✅ API documentation accessible
✅ No console errors in browser (F12)

---

**Documentation created:** October 25, 2025
**Domain:** lammp.agaii.org
**Project:** Prompt Portal - LAM Maze Game Template Manager

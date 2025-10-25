# Quick Domain Setup - lammp.agaii.org

## 🚀 One-Line Setup

```bash
chmod +x setup-domain.sh && ./setup-domain.sh
```

---

## 📋 DNS Configuration

Add this A record to your DNS provider:

```
Type: A
Name: lammp
Value: YOUR_SERVER_IP
TTL: 3600
```

**Full domain:** `lammp.agaii.org`

---

## ✅ Verify DNS

```bash
dig lammp.agaii.org
# Should return your server IP
```

---

## 🔒 Setup SSL (After DNS propagates)

```bash
sudo certbot --nginx -d lammp.agaii.org
```

---

## 🌐 Access URLs

- **Website:** https://lammp.agaii.org
- **API:** https://lammp.agaii.org/api
- **Docs:** https://lammp.agaii.org/api/docs

---

## 🔧 Manual Configuration

If automated script fails, follow these steps:

### 1. Update Backend
```bash
cd backend
# Edit .env and add to CORS_ORIGINS:
# CORS_ORIGINS=https://lammp.agaii.org,http://lammp.agaii.org,...
```

### 2. Update Frontend
```bash
cd frontend
echo 'VITE_API_BASE=https://lammp.agaii.org/api' > .env.production
echo 'VITE_WS_BASE=wss://lammp.agaii.org/api' >> .env.production
npm run build
```

### 3. Configure Nginx
```bash
sudo nano /etc/nginx/sites-available/lammp.agaii.org
```

Paste configuration from DOMAIN_SETUP.md, then:
```bash
sudo ln -s /etc/nginx/sites-available/lammp.agaii.org /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Restart Backend
```bash
pm2 restart prompt-portal-backend
```

---

## 🐛 Troubleshooting

### DNS not working?
```bash
# Check DNS
dig lammp.agaii.org
# Wait 5-10 minutes if just configured
```

### CORS errors?
```bash
# Check backend .env has domain in CORS_ORIGINS
cd backend
cat .env | grep CORS_ORIGINS
# Restart backend
pm2 restart prompt-portal-backend
```

### SSL failed?
```bash
# Check DNS points to server
dig lammp.agaii.org
# Check firewall allows 80/443
sudo ufw status
# Try certbot again
sudo certbot --nginx -d lammp.agaii.org
```

### Backend not responding?
```bash
# Check if running
pm2 status
# Check logs
pm2 logs prompt-portal-backend
# Restart
pm2 restart prompt-portal-backend
```

---

## 📞 Quick Test Commands

```bash
# Test DNS
dig lammp.agaii.org

# Test HTTP (should redirect to HTTPS)
curl -I http://lammp.agaii.org

# Test HTTPS
curl -I https://lammp.agaii.org

# Test API
curl https://lammp.agaii.org/api/docs

# View logs
pm2 logs prompt-portal-backend
```

---

## 📖 Full Documentation

For detailed instructions, see [DOMAIN_SETUP.md](./DOMAIN_SETUP.md)

---

## ✨ That's It!

Your site should now be live at **https://lammp.agaii.org** 🎉

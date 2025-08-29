# Cloud Server Deployment Guide

This guide provides step-by-step instructions for deploying the Prompt Portal application on a cloud server and accessing it via IP address.

## Prerequisites

- A cloud server (Ubuntu 20.04+ recommended)
- SSH access to your server
- Domain name or public IP address
- Basic knowledge of Linux commands

## Server Requirements

- **OS**: Ubuntu 20.04 or later
- **RAM**: Minimum 2GB
- **Storage**: Minimum 10GB free space
- **Ports**: 80, 443, 8000, 1883 (MQTT) should be open

## Deployment Options

We provide two deployment methods:

1. **Development Deployment** - Quick setup for testing
2. **Production Deployment** - Full setup with Nginx, SSL, and process management

---

## Quick Development Deployment

### Step 1: Prepare Your Server

1. **Update your server:**
```bash
sudo apt update && sudo apt upgrade -y
```

2. **Install required packages:**
```bash
sudo apt install -y python3 python3-pip python3-venv nodejs npm git nginx
```

3. **Install PM2 for process management:**
```bash
sudo npm install -g pm2
```

### Step 2: Deploy the Application

1. **Upload your project to the server:**
```bash
# Option 1: Using git (if your code is in a repository)
git clone <your-repository-url> /opt/prompt-portal

# Option 2: Using SCP (from your local machine)
scp -r prompt-portal/ user@your-server-ip:/opt/prompt-portal
```

2. **Set proper permissions:**
```bash
sudo chown -R $USER:$USER /opt/prompt-portal
cd /opt/prompt-portal
```

3. **Run the deployment script:**
```bash
chmod +x deploy.sh
./deploy.sh
```

### Step 3: Configure for IP Access

The deployment script will automatically configure the application to be accessible via your server's IP address.

**Your application will be available at:**
- **Frontend**: `http://YOUR_SERVER_IP`
- **Backend API**: `http://YOUR_SERVER_IP:8000`

---

## Production Deployment

### Step 1: Prepare Your Server

Follow the same steps as in Quick Deployment, plus:

1. **Install SSL certificate tools:**
```bash
sudo apt install -y certbot python3-certbot-nginx
```

2. **Configure firewall:**
```bash
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 8000
sudo ufw allow 1883
sudo ufw --force enable
```

### Step 2: Deploy with Production Configuration

1. **Run the production deployment script:**
```bash
chmod +x deploy-production.sh
./deploy-production.sh
```

2. **Configure your domain (optional):**
If you have a domain name, you can set up SSL:
```bash
sudo certbot --nginx -d yourdomain.com
```

### Step 3: Access Your Application

**With IP address:**
- **Frontend**: `http://YOUR_SERVER_IP`
- **Backend API**: `http://YOUR_SERVER_IP/api`

**With domain (if configured):**
- **Frontend**: `https://yourdomain.com`
- **Backend API**: `https://yourdomain.com/api`

---

## Environment Configuration

### Backend Environment Variables

Edit `/opt/prompt-portal/backend/.env`:

```bash
# Essential settings for cloud deployment
SECRET_KEY=your_very_long_random_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
DATABASE_URL=sqlite:///./app.db

# CORS origins - replace with your server IP or domain
CORS_ORIGINS=http://YOUR_SERVER_IP,http://localhost:5173

# MQTT configuration
MQTT_BROKER_HOST=127.0.0.1
MQTT_BROKER_PORT=1883
MQTT_CLIENT_ID=prompt_portal_backend
MQTT_TOPIC_HINT=maze/hint/+
MQTT_TOPIC_STATE=maze/state
```

### Frontend Environment Variables

Create `/opt/prompt-portal/frontend/.env.production`:

```bash
# Replace YOUR_SERVER_IP with your actual server IP
VITE_API_BASE=http://YOUR_SERVER_IP:8000
VITE_WS_BASE=ws://YOUR_SERVER_IP:8000
```

---

## Service Management

### Using PM2 (Recommended)

**Check status:**
```bash
pm2 status
```

**View logs:**
```bash
pm2 logs prompt-portal-backend
pm2 logs prompt-portal-frontend
```

**Restart services:**
```bash
pm2 restart prompt-portal-backend
pm2 restart prompt-portal-frontend
```

**Stop services:**
```bash
pm2 stop prompt-portal-backend
pm2 stop prompt-portal-frontend
```

### Manual Service Management

**Start backend:**
```bash
cd /opt/prompt-portal/backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Start frontend (development mode):**
```bash
cd /opt/prompt-portal/frontend
npm run dev -- --host 0.0.0.0
```

---

## Troubleshooting

### Common Issues

1. **Port already in use:**
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

2. **Permission denied:**
```bash
sudo chown -R $USER:$USER /opt/prompt-portal
```

3. **Database issues:**
```bash
cd /opt/prompt-portal/backend
source .venv/bin/activate
python create_db.py
```

4. **Frontend build issues:**
```bash
cd /opt/prompt-portal/frontend
rm -rf node_modules dist
npm install
npm run build
```

### Checking Logs

**Backend logs:**
```bash
pm2 logs prompt-portal-backend --lines 50
```

**Frontend logs:**
```bash
pm2 logs prompt-portal-frontend --lines 50
```

**Nginx logs:**
```bash
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log
```

### Health Checks

**Backend health:**
```bash
curl http://YOUR_SERVER_IP:8000/docs
```

**Frontend health:**
```bash
curl http://YOUR_SERVER_IP
```

---

## Security Considerations

1. **Change default passwords and secrets**
2. **Keep your server updated:**
```bash
sudo apt update && sudo apt upgrade -y
```

3. **Configure proper firewall rules**
4. **Use HTTPS in production**
5. **Regular database backups:**
```bash
cp /opt/prompt-portal/backend/app.db /opt/backups/app.db.$(date +%Y%m%d)
```

---

## Monitoring and Maintenance

### Automated Backups

Create a backup script `/opt/scripts/backup.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
cp /opt/prompt-portal/backend/app.db $BACKUP_DIR/app.db.$DATE

# Keep only last 7 days of backups
find $BACKUP_DIR -name "app.db.*" -mtime +7 -delete
```

### Monitoring Script

Create a monitoring script `/opt/scripts/monitor.sh`:
```bash
#!/bin/bash
# Check if services are running
pm2 status | grep -q "online" || {
    echo "Services down, restarting..."
    pm2 restart all
}
```

Set up cron jobs:
```bash
crontab -e
# Add these lines:
# Backup every day at 2 AM
0 2 * * * /opt/scripts/backup.sh
# Monitor every 5 minutes
*/5 * * * * /opt/scripts/monitor.sh
```

---

## Support

If you encounter issues:

1. Check the logs using the commands above
2. Verify all services are running: `pm2 status`
3. Check network connectivity: `curl -I http://YOUR_SERVER_IP:8000`
4. Restart services if needed: `pm2 restart all`

For additional help, refer to the application logs and ensure all environment variables are correctly set.

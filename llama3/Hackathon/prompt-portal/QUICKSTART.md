# 🚀 Quick Start Deployment Guide

This guide will get your Prompt Portal running on a cloud server in under 10 minutes!

## Prerequisites

- Ubuntu 20.04+ cloud server
- SSH access with sudo privileges
- 2GB+ RAM, 10GB+ storage
- Open ports: 22, 80, 443, 8000, 1883

## Option 1: One-Command Deployment (Recommended)

```bash
# Download and run the deployment script
curl -sSL https://raw.githubusercontent.com/your-repo/prompt-portal/main/deploy.sh | bash
```

## Option 2: Manual Deployment

### Step 1: Upload Files to Server

```bash
# From your local machine, upload the project
scp -r prompt-portal/ user@YOUR_SERVER_IP:/opt/prompt-portal

# OR clone from git
ssh user@YOUR_SERVER_IP
sudo git clone https://github.com/your-repo/prompt-portal.git /opt/prompt-portal
sudo chown -R $USER:$USER /opt/prompt-portal
```

### Step 2: Run Deployment Script

```bash
cd /opt/prompt-portal
chmod +x deploy.sh
./deploy.sh
```

### Step 3: Access Your Application

Open your browser and go to: `http://YOUR_SERVER_IP:5173`

## Option 3: Production Deployment with SSL

For production use with domain name and SSL:

```bash
cd /opt/prompt-portal
chmod +x deploy-production.sh
./deploy-production.sh
```

This will:
- Set up Nginx reverse proxy
- Configure SSL with Let's Encrypt
- Set up monitoring and backups
- Configure firewall

## Post-Deployment

### 1. Test Your Installation

1. **Frontend**: Go to `http://YOUR_SERVER_IP:5173`
2. **Backend API**: Go to `http://YOUR_SERVER_IP:8000/docs`
3. **Register**: Create a new account
4. **Create Template**: Add your first prompt template
5. **Test MQTT**: Use the Test & Monitor page

### 2. Set Up MQTT Broker (Optional)

If you need MQTT functionality:

```bash
chmod +x setup-mqtt.sh
./setup-mqtt.sh
```

### 3. Manage Your Server

Use the management script for common tasks:

```bash
chmod +x manage.sh
./manage.sh
```

Or run specific commands:
```bash
./manage.sh status    # Check service status
./manage.sh logs      # View logs
./manage.sh backup    # Create backup
./manage.sh restart   # Restart services
```

## Environment Configuration

### Backend Configuration

Edit `/opt/prompt-portal/backend/.env`:

```env
# Security
SECRET_KEY=your_generated_secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=60

# CORS (replace with your server IP/domain)
CORS_ORIGINS=http://YOUR_SERVER_IP,http://YOUR_DOMAIN

# Database
DATABASE_URL=sqlite:///./app.db

# MQTT Settings
MQTT_BROKER_HOST=127.0.0.1
MQTT_BROKER_PORT=1883
MQTT_CLIENT_ID=prompt_portal_backend
MQTT_TOPIC_HINT=maze/hint/+
MQTT_TOPIC_STATE=maze/state

# Optional: MQTT Authentication
# MQTT_USERNAME=your_mqtt_user
# MQTT_PASSWORD=your_mqtt_password
```

### Frontend Configuration

The deployment script automatically configures the frontend to use your server IP.

## Service URLs

After deployment, your services will be available at:

### Development Deployment
- **Frontend**: `http://YOUR_SERVER_IP:5173`
- **Backend**: `http://YOUR_SERVER_IP:8000`
- **API Docs**: `http://YOUR_SERVER_IP:8000/docs`

### Production Deployment
- **Website**: `http://YOUR_SERVER_IP` or `https://YOUR_DOMAIN`
- **API**: `http://YOUR_SERVER_IP/api` or `https://YOUR_DOMAIN/api`
- **API Docs**: `http://YOUR_SERVER_IP/api/docs` or `https://YOUR_DOMAIN/api/docs`

## Common Commands

```bash
# Check service status
pm2 status
sudo systemctl status nginx

# View logs
pm2 logs prompt-portal-backend
sudo tail -f /var/log/nginx/error.log

# Restart services
pm2 restart all
sudo systemctl restart nginx

# Create backup
/opt/scripts/backup.sh

# Update application
/opt/scripts/update.sh
```

## Troubleshooting

### Services Not Starting

```bash
# Check PM2 processes
pm2 status
pm2 logs prompt-portal-backend

# Restart if needed
pm2 restart all
```

### Can't Access from Browser

```bash
# Check if ports are open
sudo ufw status
sudo netstat -tlnp | grep -E ':80|:8000|:5173'

# Check if services are listening
curl -I http://localhost:8000
curl -I http://localhost:5173
```

### Database Issues

```bash
cd /opt/prompt-portal/backend
source .venv/bin/activate
python create_db.py
```

### Frontend Build Issues

```bash
cd /opt/prompt-portal/frontend
rm -rf node_modules dist
npm install
npm run build
```

## Security Checklist

- [ ] Changed default SECRET_KEY
- [ ] Updated CORS_ORIGINS with your domain/IP
- [ ] Configured firewall (UFW)
- [ ] Set up SSL certificate (production)
- [ ] Regular backups scheduled
- [ ] MQTT authentication enabled (if using MQTT)

## Next Steps

1. **Customize**: Modify the frontend and backend to match your needs
2. **Scale**: Set up load balancing if needed
3. **Monitor**: Set up additional monitoring tools
4. **Backup**: Implement offsite backup strategy
5. **Update**: Keep dependencies updated regularly

## Support

- Check logs: `./manage.sh logs`
- Run health check: `./manage.sh health`
- View service status: `./manage.sh status`
- Create issue on GitHub for bugs

## File Structure

```
/opt/prompt-portal/
├── backend/
│   ├── .env                 # Backend configuration
│   ├── app.db              # SQLite database
│   └── app/                # FastAPI application
├── frontend/
│   ├── dist/               # Built frontend files
│   └── src/                # React source code
├── deploy.sh               # Development deployment
├── deploy-production.sh    # Production deployment
├── setup-mqtt.sh          # MQTT broker setup
├── manage.sh              # Server management
└── DEPLOYMENT.md          # Full deployment guide
```

---

**Your Prompt Portal is now ready! 🎉**

Visit `http://YOUR_SERVER_IP:5173` to start using your application.

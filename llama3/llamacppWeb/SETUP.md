# Complete Setup Instructions for Llama.cpp Web Chat Server

This guide provides step-by-step instructions for setting up and deploying the Llama.cpp Web Chat Server in different environments.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Local Development Setup](#local-development-setup)
3. [Docker Deployment](#docker-deployment)
4. [Linux Production Deployment](#linux-production-deployment)
5. [Windows Production Deployment](#windows-production-deployment)
6. [Configuration](#configuration)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements
- **CPU**: 2 cores (4 cores recommended)
- **RAM**: 2GB minimum (4GB+ recommended)
- **Disk**: 500MB free space
- **Network**: Internet access, MQTT broker connectivity
- **Python**: 3.8+ (for non-Docker)

### Supported Platforms
- Ubuntu 20.04, 20.10, 22.04 LTS
- CentOS 8.x, 9.x
- Debian 11, 12
- Windows 10, 11
- macOS 10.14+
- Docker (any platform with Docker Engine)

### Network Requirements
- MQTT Broker: 47.89.252.2:1883 (configurable)
- Inbound HTTP/HTTPS for web access
- Outbound to MQTT broker

---

## Local Development Setup

### For Testing and Development

#### Step 1: Clone/Navigate to Repository

```bash
cd llamacppWeb
```

#### Step 2: Install Python

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv
```

**macOS:**
```bash
brew install python3
```

**Windows:**
Download from https://www.python.org/ and install (add to PATH)

#### Step 3: Create Virtual Environment

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate.bat
```

#### Step 4: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 5: Start Development Server

```bash
# Default (localhost:5000)
python app.py

# Custom port
PORT=8080 python app.py

# With debug mode
FLASK_DEBUG=True python app.py
```

#### Step 6: Access Application

Open browser to: http://localhost:5000

#### Step 7: Stop Server

Press `Ctrl+C` in terminal

---

## Docker Deployment

### Recommended for Production & Easy Setup

#### Prerequisites
```bash
# Install Docker
# Linux
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# macOS/Windows: Download from https://www.docker.com/products/docker-desktop
```

#### Step 1: Prepare Environment

```bash
cd llamacppWeb
cp .env.docker .env
```

#### Step 2: Verify docker-compose.yml

```bash
cat docker-compose.yml
```

#### Step 3: Start Services

```bash
# Start in background
docker-compose up -d

# Or foreground (for logs)
docker-compose up
```

#### Step 4: Verify Services

```bash
# Check status
docker-compose ps

# View logs
docker-compose logs -f llamacpp-web

# Test health
curl http://localhost:5000/api/health
```

#### Step 5: Access Application

- **Web UI**: http://localhost
- **API**: http://localhost/api/config
- **MQTT**: localhost:1883 (internal)

#### Step 6: Stop Services

```bash
docker-compose down

# With volume cleanup
docker-compose down -v
```

---

## Linux Production Deployment

### Automated Deployment (Recommended)

#### Step 1: Prepare Script

```bash
chmod +x deploy/deploy.sh
cat deploy/deploy.sh  # Review before running
```

#### Step 2: Run Installation

```bash
sudo ./deploy/deploy.sh install
```

This will:
- Install system dependencies (Python, Nginx, Supervisor)
- Create service user (`llamacpp`)
- Setup virtual environment
- Install Python dependencies
- Create systemd service
- Configure Nginx reverse proxy
- Enable service for auto-start

#### Step 3: Start Service

```bash
sudo ./deploy/deploy.sh start

# Verify
sudo ./deploy/deploy.sh status
```

#### Step 4: Check Logs

```bash
sudo ./deploy/deploy.sh logs
```

#### Step 5: Access Application

- **HTTP**: http://your-server-ip
- **HTTPS**: https://your-server-ip (after SSL setup)

---

### Manual Installation (Advanced)

#### Step 1: Update System

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

#### Step 2: Install Dependencies

```bash
sudo apt-get install -y \
    python3 python3-pip python3-venv \
    nginx curl git \
    build-essential
```

#### Step 3: Create Service User

```bash
sudo useradd -m -s /bin/bash llamacpp
```

#### Step 4: Setup Application Directory

```bash
sudo mkdir -p /opt/llamacpp-web
sudo chown llamacpp:llamacpp /opt/llamacpp-web
sudo -u llamacpp git clone <repo> /opt/llamacpp-web/
# or
sudo cp -r llamacppWeb/* /opt/llamacpp-web/
```

#### Step 5: Create Virtual Environment

```bash
cd /opt/llamacpp-web
sudo -u llamacpp python3 -m venv venv
sudo -u llamacpp venv/bin/pip install --upgrade pip
sudo -u llamacpp venv/bin/pip install -r requirements.txt
```

#### Step 6: Create Log Directory

```bash
sudo mkdir -p /var/log/llamacpp-web
sudo chown llamacpp:llamacpp /var/log/llamacpp-web
```

#### Step 7: Create Systemd Service

```bash
sudo tee /etc/systemd/system/llamacpp-web.service > /dev/null << 'EOF'
[Unit]
Description=Llama.cpp Web Chat Server
After=network.target

[Service]
Type=simple
User=llamacpp
Group=llamacpp
WorkingDirectory=/opt/llamacpp-web
Environment="PATH=/opt/llamacpp-web/venv/bin"
Environment="FLASK_ENV=production"
Environment="FLASK_DEBUG=False"
Environment="HOST=0.0.0.0"
Environment="PORT=5000"
Environment="MQTT_BROKER=47.89.252.2"
Environment="MQTT_PORT=1883"

ExecStart=/opt/llamacpp-web/venv/bin/python /opt/llamacpp-web/app.py
Restart=on-failure
RestartSec=10

StandardOutput=append:/var/log/llamacpp-web/app.log
StandardError=append:/var/log/llamacpp-web/error.log

[Install]
WantedBy=multi-user.target
EOF
```

#### Step 8: Enable and Start Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable llamacpp-web
sudo systemctl start llamacpp-web
```

#### Step 9: Configure Nginx

```bash
sudo tee /etc/nginx/sites-available/llamacpp-web > /dev/null << 'EOF'
upstream llamacpp_web {
    server 127.0.0.1:5000;
}

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    client_max_body_size 50M;

    location / {
        proxy_pass http://llamacpp_web;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 3600s;
    }

    location /static {
        alias /opt/llamacpp-web/static;
        expires 30d;
    }

    location /socket.io {
        proxy_pass http://llamacpp_web/socket.io;
        proxy_http_version 1.1;
        proxy_buffering off;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
    }
}
EOF
```

#### Step 10: Enable Nginx Site and Test

```bash
sudo ln -sf /etc/nginx/sites-available/llamacpp-web /etc/nginx/sites-enabled/

# Disable default site if needed
sudo rm /etc/nginx/sites-enabled/default 2>/dev/null || true

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

#### Step 11: Verify Installation

```bash
# Check service
sudo systemctl status llamacpp-web

# View logs
sudo journalctl -u llamacpp-web -f

# Test API
curl http://localhost/api/health
```

---

## Windows Production Deployment

### Using Automated Script

#### Step 1: Open Command Prompt as Administrator

Right-click Command Prompt and select "Run as Administrator"

#### Step 2: Navigate to Deploy Directory

```cmd
cd C:\path\to\llamacppWeb\deploy
```

#### Step 3: Run Installation

```cmd
deploy.bat install
```

This will:
- Create virtual environment
- Install Python dependencies
- Create batch runner script
- Create scheduled task

#### Step 4: Start Service

```cmd
deploy.bat start
```

#### Step 5: Access Application

Open browser to: http://localhost:5000

#### Step 6: Check Status

```cmd
deploy.bat status
```

---

### Manual Installation

#### Step 1: Install Python

- Download from https://www.python.org/
- During installation, check "Add Python to PATH"
- Click "Install Now"

#### Step 2: Open Command Prompt

Press `Win+R`, type `cmd`, press Enter

#### Step 3: Create Virtual Environment

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

#### Step 4: Install Dependencies

```cmd
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Step 5: Run Server

```cmd
python app.py
```

#### Step 6: Access Application

Open browser to: http://localhost:5000

#### Step 7: Keep Server Running

- To stop: Press `Ctrl+C`
- To restart: Re-run `python app.py`

#### Step 8: (Optional) Setup Auto-Start

Create a batch file `run_llamacpp.bat`:

```batch
@echo off
cd /d "C:\path\to\llamacppWeb"
venv\Scripts\activate.bat
python app.py
pause
```

Add to Windows Startup folder:
- Press `Win+R`
- Type `shell:startup`
- Copy batch file to this folder

---

## Configuration

### Environment Variables

Create or edit `.env` file in `llamacppWeb` directory:

```bash
# Flask Configuration
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-very-secret-key-here

# Server Configuration
HOST=0.0.0.0
PORT=5000

# MQTT Configuration
MQTT_BROKER=47.89.252.2
MQTT_PORT=1883
MQTT_USERNAME=optional
MQTT_PASSWORD=optional

# Optional
LOG_LEVEL=INFO
```

### Using Different MQTT Broker

```bash
# Command line
export MQTT_BROKER=your.mqtt.broker
export MQTT_PORT=1883
python app.py

# Or in .env file
MQTT_BROKER=your.mqtt.broker
MQTT_PORT=1883
```

### SSL/TLS Setup

#### Generate Self-Signed Certificate

```bash
sudo openssl req -x509 -newkey rsa:4096 \
  -keyout /etc/ssl/private/llama-key.key \
  -out /etc/ssl/certs/llama-cert.crt \
  -days 365 -nodes
```

#### Or Use Let's Encrypt

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot certonly --standalone -d your-domain.com
```

#### Update Nginx Configuration

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /etc/ssl/certs/llama-cert.crt;
    ssl_certificate_key /etc/ssl/private/llama-key.key;
    # ... rest of config
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
```

---

## Verification

### Health Check

```bash
# HTTP API
curl http://localhost:5000/api/health

# Should return:
# {"status": "ok", "mqtt_connected": true, "timestamp": "..."}
```

### Check MQTT Connectivity

```bash
# Test MQTT connection
telnet 47.89.252.2 1883

# Or using mosquitto
mosquitto_sub -h 47.89.252.2 -t test/topic -t 1
```

### View Application Logs

**Docker:**
```bash
docker-compose logs -f llamacpp-web
```

**Linux (Systemd):**
```bash
sudo journalctl -u llamacpp-web -f
sudo tail -f /var/log/llamacpp-web/app.log
```

**Windows:**
Check terminal window where `python app.py` is running

### Check Service Status

**Docker:**
```bash
docker-compose ps
```

**Linux:**
```bash
sudo systemctl status llamacpp-web
```

**Windows:**
```cmd
deploy.bat status
```

---

## Troubleshooting

### Issue: Port Already in Use

**Error**: `Address already in use` or `Address in use`

**Solution:**

Linux/macOS:
```bash
# Find process using port
lsof -i :5000

# Kill process
kill -9 <PID>

# Or change port
PORT=8080 python app.py
```

Windows:
```cmd
# Find process
netstat -ano | findstr :5000

# Kill process
taskkill /PID <PID> /F

# Or change port
set PORT=8080
python app.py
```

### Issue: Cannot Import Modules

**Error**: `ModuleNotFoundError: No module named 'flask'`

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate.bat  # Windows

# Install requirements
pip install -r requirements.txt

# Verify installation
python -c "import flask; print(flask.__version__)"
```

### Issue: MQTT Connection Failed

**Error**: `Failed to connect to MQTT broker`

**Solution:**
```bash
# Test MQTT connectivity
telnet 47.89.252.2 1883

# Check firewall
sudo ufw status
sudo ufw allow 1883

# Check MQTT_BROKER environment variable
echo $MQTT_BROKER

# Update configuration
export MQTT_BROKER=47.89.252.2
export MQTT_PORT=1883
```

### Issue: WebSocket Connection Failed

**Error**: WebSocket fails in browser console

**Solution:**
- Check Nginx is running and properly configured
- Verify socket.io proxy configuration
- Check browser console for specific errors
- Ensure proper headers in Nginx:
  ```nginx
  proxy_set_header Upgrade $http_upgrade;
  proxy_set_header Connection "upgrade";
  ```

### Issue: High Memory Usage

**Solution:**
- Reduce `MAX_CONCURRENT_SESSIONS` setting
- Clear old chat history
- Monitor active sessions: `curl http://localhost:5000/api/stats`
- Restart service periodically

### Issue: Slow Response Times

**Solution:**
- Check MQTT broker load
- Check LLM backend is responsive
- Check server CPU/memory resources
- Verify network connectivity
- Check firewall/rate limiting

---

## Next Steps

1. ✅ Installation complete
2. ✅ Server running and accessible
3. 📝 Customize configuration as needed
4. 🔒 Setup SSL/TLS for production
5. 📊 Monitor server performance
6. 🔄 Setup automated backups
7. 📈 Configure monitoring/alerting

---

## Support Resources

- **Quick Start**: See QUICK_START.md
- **Full Guide**: See DEPLOYMENT_GUIDE.md
- **README**: See README.md
- **Configuration**: See config/.env.example

---

**Setup Guide Version**: 1.0  
**Last Updated**: January 2025

# Llama.cpp Web Chat Server - Deployment Guide

A complete ChatGPT-like web interface for the Llama.cpp MQTT system.

## Table of Contents

- [Features](#features)
- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
  - [Local Development](#local-development)
  - [Production Deployment (Linux)](#production-deployment-linux)
  - [Production Deployment (Windows)](#production-deployment-windows)
- [Configuration](#configuration)
- [Architecture](#architecture)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [API Documentation](#api-documentation)

## Features

- ✨ **ChatGPT-like UI** - Modern, responsive chat interface
- 🦙 **Llama.cpp Integration** - Direct MQTT communication with llama.cpp backend
- 💾 **Local Chat History** - Chats saved in browser localStorage
- 📚 **Multi-Project Support** - Support for multiple projects (maze, driving, bloodcell, racing, general)
- ⚙️ **Advanced Options** - Temperature, Top-P, Max Tokens customization
- 🔐 **MQTT-Based** - Secure message routing via MQTT broker
- 📱 **Responsive Design** - Works on desktop and mobile
- 🌙 **Dark/Light Theme** - Toggle between themes
- 🚀 **WebSocket Support** - Real-time bidirectional communication
- 📊 **Server Statistics** - Monitor active sessions and health

## System Requirements

### Minimum Requirements

- Python 3.8+
- Node.js 14+ (optional, for frontend development)
- 2 GB RAM
- 500 MB disk space
- MQTT broker (default: 47.89.252.2:1883)

### Supported Operating Systems

- Linux (Ubuntu 20.04+, CentOS 8+)
- Windows 10/11
- macOS 10.14+

## Quick Start

### Local Development

#### 1. Clone/Setup the Project

```bash
cd llamacppWeb
```

#### 2. Create Virtual Environment

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate.bat
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Run the Server

```bash
python app.py
```

The server will start at `http://localhost:5000`

### Production Deployment (Linux)

#### Option 1: Automated Deployment Script

```bash
# Make script executable
chmod +x deploy/deploy.sh

# Run installation (requires sudo)
sudo ./deploy/deploy.sh install

# Start service
sudo ./deploy/deploy.sh start

# View logs
sudo ./deploy/deploy.sh logs

# Restart service
sudo ./deploy/deploy.sh restart
```

#### Option 2: Manual Installation

##### Step 1: Install System Dependencies

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-venv nginx supervisor git curl
```

##### Step 2: Create Service User

```bash
sudo useradd -m -s /bin/bash llamacpp
```

##### Step 3: Setup Application

```bash
# Create installation directory
sudo mkdir -p /opt/llamacpp-web
sudo chown llamacpp:llamacpp /opt/llamacpp-web

# Copy application files
sudo -u llamacpp cp -r llamacppWeb/* /opt/llamacpp-web/

# Create virtual environment
cd /opt/llamacpp-web
sudo -u llamacpp python3 -m venv venv
sudo -u llamacpp venv/bin/pip install -r requirements.txt
```

##### Step 4: Create Systemd Service

```bash
sudo tee /etc/systemd/system/llamacpp-web.service > /dev/null << 'EOF'
[Unit]
Description=Llama.cpp Web Chat Server
After=network.target
Wants=network-online.target

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

sudo systemctl daemon-reload
sudo systemctl enable llamacpp-web
sudo systemctl start llamacpp-web
```

##### Step 5: Setup Nginx Reverse Proxy

```bash
sudo tee /etc/nginx/sites-available/llamacpp-web > /dev/null << 'EOF'
upstream llamacpp_web {
    server 127.0.0.1:5000;
}

server {
    listen 80;
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

sudo ln -sf /etc/nginx/sites-available/llamacpp-web /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

##### Step 6: Verify Installation

```bash
# Check service status
sudo systemctl status llamacpp-web

# View logs
sudo journalctl -u llamacpp-web -f

# Test API
curl http://localhost/api/health
```

### Production Deployment (Windows)

#### Option 1: Automated Deployment Script

1. Open Command Prompt as Administrator
2. Navigate to the deployment directory:
   ```cmd
   cd llamacppWeb\deploy
   ```
3. Run the deployment script:
   ```cmd
   deploy.bat install
   ```
4. Start the server:
   ```cmd
   deploy.bat start
   ```

#### Option 2: Manual Installation

##### Step 1: Install Python

- Download Python 3.8+ from https://www.python.org/
- Add Python to PATH during installation

##### Step 2: Setup Virtual Environment

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

##### Step 3: Install Dependencies

```cmd
pip install -r requirements.txt
```

##### Step 4: Run the Server

```cmd
python app.py
```

Access the server at http://localhost:5000

## Configuration

### Environment Variables

Edit `.env` file (copy from `.env.example`):

```bash
# Flask
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-secret-key-here

# Server
HOST=0.0.0.0
PORT=5000

# MQTT
MQTT_BROKER=47.89.252.2
MQTT_PORT=1883
MQTT_USERNAME=optional_username
MQTT_PASSWORD=optional_password

# Logging
LOG_LEVEL=INFO
```

### MQTT Configuration

To use a different MQTT broker:

```bash
export MQTT_BROKER=your.mqtt.broker
export MQTT_PORT=1883
python app.py
```

### SSL/TLS Setup

For HTTPS, configure Nginx with certificates:

```bash
# Generate self-signed certificate
sudo openssl req -x509 -newkey rsa:4096 -keyout /etc/ssl/private/llama-key.key \
  -out /etc/ssl/certs/llama-cert.crt -days 365 -nodes

# Or use Let's Encrypt
sudo certbot certonly --standalone -d your-domain.com
```

Update Nginx config to use SSL certificates.

## Architecture

### Components

```
┌─────────────────────────────────────┐
│   Frontend (Browser)                │
│ ┌──────────────────────────────────┐│
│ │ HTML/CSS/JavaScript              ││
│ │ • Chat UI                        ││
│ │ • MQTT Client (Paho-MQTT)        ││
│ │ • Local Storage Management       ││
│ └──────────────────────────────────┘│
└──────────────┬──────────────────────┘
               │ WebSocket / HTTP
┌──────────────▼──────────────────────┐
│   Backend (Flask Server)            │
│ ┌──────────────────────────────────┐│
│ │ Flask + Flask-SocketIO           ││
│ │ • HTTP API Endpoints             ││
│ │ • WebSocket Communication        ││
│ │ • Session Management             ││
│ │ • MQTT Client                    ││
│ └──────────────────────────────────┘│
└──────────────┬──────────────────────┘
               │ MQTT
┌──────────────▼──────────────────────┐
│   MQTT Broker                       │
│ • Message Routing                  │
│ • Topic-based Delivery             │
└──────────────┬──────────────────────┘
               │ MQTT
┌──────────────▼──────────────────────┐
│   Llama.cpp Backend                 │
│ (llamacpp_mqtt_deploy.py)          │
│ • LLM Inference                    │
│ • Session Management               │
│ • Response Generation              │
└─────────────────────────────────────┘
```

### Message Flow

1. **User sends message** via web interface
2. **Frontend publishes** to `{project}/user_input` MQTT topic
3. **Backend (llamacpp_mqtt_deploy.py)** receives message
4. **LLM processes** message and generates response
5. **Backend publishes** to `{project}/assistant_response/{sessionId}`
6. **Frontend receives** and displays response

## Usage

### For End Users

1. Open http://localhost:5000 (or your server URL)
2. Select a project from dropdown
3. Type your message in the input area
4. Press Enter or click Send
5. View response in chat history
6. Click "Advanced Options" to customize:
   - Temperature (0-2)
   - Top-P (0-1)
   - Max Tokens (100-4000)
   - Custom System Prompt

### Keyboard Shortcuts

- **Enter**: Send message
- **Shift+Enter**: New line in input
- **Ctrl+K**: Create new chat
- **Ctrl+L**: Clear current chat

### Chat History

- Chats are automatically saved in browser localStorage
- Click chat items to load previous conversations
- Right-click chat item to delete
- Export/import chats from settings

## API Documentation

### HTTP Endpoints

#### `GET /api/config`
Get application configuration.

**Response:**
```json
{
    "mqtt_broker": "47.89.252.2",
    "mqtt_port": 1883,
    "projects": {
        "general": {"name": "General", "description": "..."}
    },
    "version": "1.0.0"
}
```

#### `GET /api/health`
Health check endpoint.

**Response:**
```json
{
    "status": "ok",
    "mqtt_connected": true,
    "timestamp": "2025-01-01T12:00:00"
}
```

#### `GET /api/projects`
Get available projects.

**Response:**
```json
{
    "projects": {
        "general": {...},
        "maze": {...}
    }
}
```

#### `GET /api/stats`
Get server statistics.

**Response:**
```json
{
    "active_sessions": 5,
    "mqtt_connected": true,
    "timestamp": "2025-01-01T12:00:00"
}
```

### WebSocket Events

#### Client → Server

**`connect`**: Initial connection
```javascript
socket.emit('connect_response')
```

**`send_message`**: Send chat message
```javascript
socket.emit('send_message', {
    session_id: 'uuid',
    project: 'maze',
    message: 'Hello',
    temperature: 0.6,
    topP: 0.9,
    maxTokens: 512,
    systemPrompt: 'optional'
})
```

**`create_session`**: Create new session
```javascript
socket.emit('create_session', {
    project: 'maze'
})
```

#### Server → Client

**`message_sent`**: Confirmation message sent
**`response_received`**: Response from LLM
**`error`**: Error occurred

## Troubleshooting

### Issue: Cannot Connect to MQTT Broker

**Solution:**
- Verify MQTT broker is running: `telnet 47.89.252.2 1883`
- Check MQTT_BROKER and MQTT_PORT environment variables
- Ensure firewall allows MQTT port

### Issue: WebSocket Connection Failed

**Solution:**
- Check Nginx is correctly configured for WebSocket
- Verify `proxy_set_header Connection "upgrade"` in Nginx config
- Check browser console for errors

### Issue: SSL Certificate Error

**Solution:**
```bash
# Generate self-signed certificate
sudo openssl req -x509 -newkey rsa:4096 -keyout key.key -out cert.crt -days 365 -nodes

# Update Nginx config with certificate paths
ssl_certificate /etc/ssl/certs/cert.crt;
ssl_certificate_key /etc/ssl/private/key.key;
```

### Issue: Service Won't Start

**Solution:**
```bash
# Check service status
sudo systemctl status llamacpp-web

# View logs
sudo journalctl -u llamacpp-web -n 50

# Test Flask app directly
cd /opt/llamacpp-web
source venv/bin/activate
python app.py
```

### Issue: High CPU Usage

**Solution:**
- Check number of active WebSocket connections
- Review MQTT message frequency
- Increase number of worker threads

### Issue: Out of Memory

**Solution:**
- Reduce `MAX_CONCURRENT_SESSIONS` in backend
- Clear old chat history from localStorage
- Increase server RAM

## Monitoring & Maintenance

### Viewing Logs

**Linux (Systemd):**
```bash
sudo journalctl -u llamacpp-web -f
```

**Windows:**
Check `logs/` directory in installation folder

### Restarting Service

**Linux:**
```bash
sudo systemctl restart llamacpp-web
```

**Windows:**
```cmd
deploy.bat restart
```

### Updating Application

**Linux:**
```bash
cd /opt/llamacpp-web
git pull
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart llamacpp-web
```

**Windows:**
```cmd
cd llamacppWeb
git pull
venv\Scripts\activate.bat
pip install -r requirements.txt
deploy.bat restart
```

## Performance Tuning

### Nginx Configuration

```nginx
# Increase connection limits
worker_connections 4096;

# Enable gzip compression
gzip on;
gzip_types text/plain text/css application/json application/javascript;

# Cache static files
expires 30d;
```

### Flask Configuration

```python
# Increase worker threads
app.config['SOCKETIO_ASYNC_MODE'] = 'threading'
app.config['SOCKETIO_MAX_HTTP_BUFFER_SIZE'] = 1e6
```

## Security Recommendations

1. **Use HTTPS** in production (not just HTTP)
2. **Set strong SECRET_KEY** in environment
3. **Enable firewall** to restrict access
4. **Use MQTT authentication** with username/password
5. **Restrict CORS** to known domains
6. **Keep dependencies updated**: `pip install --upgrade -r requirements.txt`

## Support & Debugging

For issues or questions:

1. Check logs: `journalctl -u llamacpp-web -f`
2. Verify MQTT connectivity: `telnet broker_ip 1883`
3. Test API endpoints: `curl http://localhost:5000/api/health`
4. Check browser console for JavaScript errors
5. Verify environment variables are set

## License

This project is part of the Llama3 Hackathon suite.

## See Also

- [Llama.cpp MQTT Deploy](../llamacpp_mqtt_deploy.py) - Backend LLM server
- [Llama.cpp Documentation](https://github.com/ggerganov/llama.cpp)
- [MQTT Protocol](https://mqtt.org/)
- [Flask Documentation](https://flask.palletsprojects.com/)

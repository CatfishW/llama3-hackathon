# Llama.cpp Web Server - Quick Start Guide

## Installation & Deployment

### Option 1: Local Development (Recommended for Testing)

#### Prerequisites
- Python 3.8+
- MQTT broker running (or access to 47.89.252.2:1883)

#### Steps

1. **Navigate to project directory**
   ```bash
   cd llamacppWeb
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate.bat  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run development server**
   ```bash
   python app.py
   ```

5. **Open browser**
   ```
   http://localhost:5000
   ```

---

### Option 2: Docker Compose (Recommended for Production)

#### Prerequisites
- Docker & Docker Compose installed
- 2GB RAM available
- Ports 80, 443, 5000, 1883, 9001 available

#### Steps

1. **Navigate to project directory**
   ```bash
   cd llamacppWeb
   ```

2. **Copy environment file**
   ```bash
   cp .env.docker .env
   # Edit .env if needed for custom MQTT broker
   ```

3. **Start services**
   ```bash
   docker-compose up -d
   ```

4. **Verify services**
   ```bash
   docker-compose ps
   docker-compose logs -f llamacpp-web
   ```

5. **Access application**
   ```
   http://localhost
   ```

6. **Stop services**
   ```bash
   docker-compose down
   ```

---

### Option 3: Linux Automated Deployment

#### Prerequisites
- Ubuntu 20.04+ or CentOS 8+
- Root/sudo access
- 2GB RAM

#### Steps

1. **Make script executable**
   ```bash
   chmod +x deploy/deploy.sh
   ```

2. **Run installation**
   ```bash
   sudo ./deploy/deploy.sh install
   ```

3. **Start service**
   ```bash
   sudo ./deploy/deploy.sh start
   ```

4. **View status**
   ```bash
   sudo ./deploy/deploy.sh status
   ```

5. **View logs**
   ```bash
   sudo ./deploy/deploy.sh logs
   ```

---

### Option 4: Windows Deployment

#### Prerequisites
- Windows 10/11
- Administrator access
- Python 3.8+ installed
- 2GB RAM

#### Steps

1. **Open Command Prompt as Administrator**

2. **Navigate to deploy folder**
   ```cmd
   cd llamacppWeb\deploy
   ```

3. **Run installation**
   ```cmd
   deploy.bat install
   ```

4. **Start service**
   ```cmd
   deploy.bat start
   ```

5. **Access application**
   ```
   http://localhost:5000
   ```

---

## Verification

### Check if server is running

```bash
# Via HTTP
curl http://localhost:5000/api/health

# Via Docker (if using docker-compose)
docker-compose ps
docker-compose logs llamacpp-web

# Via systemd (if deployed on Linux)
sudo systemctl status llamacpp-web

# Windows (if deployed)
deploy.bat status
```

### Expected Response
```json
{
    "status": "ok",
    "mqtt_connected": true,
    "timestamp": "2025-01-01T12:00:00"
}
```

---

## Common Issues

### Issue: Port Already in Use
**Error**: `Address already in use`

**Solution:**
- Linux: `sudo lsof -i :5000` to find process
- Windows: `netstat -ano | findstr :5000` to find process
- Change PORT in environment variables and restart

### Issue: Cannot Connect to MQTT Broker
**Error**: `MQTT connection failed`

**Solution:**
- Verify broker is running: `telnet 47.89.252.2 1883`
- Check firewall allows MQTT port
- Update MQTT_BROKER environment variable if using different broker

### Issue: WebSocket Connection Failed
**Error**: WebSocket fails in browser console

**Solution (Docker):**
- Ensure nginx container is running
- Check nginx logs: `docker-compose logs nginx`
- Verify socket.io proxy configuration in nginx

### Issue: Slow Performance
**Solution:**
- Check available RAM: `free -h`
- Monitor CPU: `top` or Task Manager
- Check LLM backend is running properly
- Verify MQTT broker performance

---

## Next Steps

1. **Open the web interface** at http://localhost:5000
2. **Select a project** from the dropdown
3. **Type a message** and press Enter
4. **Customize settings** in Advanced Options
5. **View chat history** in the sidebar

---

## Production Considerations

### Security
- [ ] Change SECRET_KEY to a strong random value
- [ ] Enable HTTPS/SSL certificates
- [ ] Configure firewall rules
- [ ] Use strong MQTT credentials
- [ ] Restrict CORS origins

### Performance
- [ ] Use Nginx reverse proxy
- [ ] Enable gzip compression
- [ ] Configure CDN for static files
- [ ] Setup monitoring and alerts
- [ ] Configure log rotation

### Reliability
- [ ] Enable auto-restart on failure
- [ ] Configure backup/recovery
- [ ] Setup health checks
- [ ] Monitor error rates
- [ ] Plan for scaling

### Monitoring
- [ ] Setup application logging
- [ ] Monitor server resources
- [ ] Track error rates
- [ ] Monitor MQTT throughput
- [ ] Alert on failures

---

## Useful Commands

### Docker Compose

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f llamacpp-web

# Restart specific service
docker-compose restart llamacpp-web

# Execute command in container
docker-compose exec llamacpp-web bash

# Clean up (remove volumes)
docker-compose down -v
```

### Linux Systemd

```bash
# Start service
sudo systemctl start llamacpp-web

# Stop service
sudo systemctl stop llamacpp-web

# Restart service
sudo systemctl restart llamacpp-web

# Enable on boot
sudo systemctl enable llamacpp-web

# View status
sudo systemctl status llamacpp-web

# View logs
sudo journalctl -u llamacpp-web -f

# View recent 100 lines
sudo journalctl -u llamacpp-web -n 100
```

### Windows

```cmd
# Start service
deploy.bat start

# Stop service
deploy.bat stop

# Restart service
deploy.bat restart

# View status
deploy.bat status

# View logs
deploy.bat logs
```

---

## Troubleshooting Links

- [Full Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Configuration Options](config/.env.example)
- [API Documentation](DEPLOYMENT_GUIDE.md#api-documentation)
- [Troubleshooting Section](DEPLOYMENT_GUIDE.md#troubleshooting)

---

## Support

For detailed information, see:
- **README.md** - Project overview and features
- **DEPLOYMENT_GUIDE.md** - Comprehensive deployment guide
- **config/.env.example** - Configuration options

---

**Version**: 1.0.0  
**Last Updated**: January 2025

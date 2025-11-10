# Machine B Deployment Guide

## What is Machine B?

**Machine B** is the **web server with a public IP** that acts as a bridge between remote clients (Machine C) and the LLM server (Machine A).

## What to Deploy on Machine B

Machine B needs to run **ONE** of two options:

### Option 1: OpenAI-Compatible Proxy (Recommended for Remote Clients)
✅ **Use this if:** You want to access the LLM from remote machines (Machine C) using the OpenAI SDK

### Option 2: Full Web Application (Frontend + Backend)
✅ **Use this if:** You want a complete web interface with chat UI

---

## 📦 Option 1: OpenAI-Compatible Proxy Server

This is the **simpler option** that exposes an OpenAI-compatible API endpoint for remote access.

### Architecture
```
Machine C (Clients) → Machine B (Proxy :8000) → SSH Tunnel → Machine A (LLM)
```

### Prerequisites

1. **SSH Tunnel Active** (from Machine A):
   ```bash
   # Verify tunnel is working
   curl http://localhost:8080/health
   # Should return: {"status":"ok","slots_idle":8,...}
   ```

2. **Python Environment**:
   ```bash
   # Install dependencies
   pip install fastapi uvicorn httpx python-dotenv pydantic
   
   # Or use requirements.txt
   pip install -r requirements.txt
   ```

### Configuration

Create `.env` file in the `deployment` directory:

```bash
# deployment/.env

# Where llama.cpp is accessible (via SSH tunnel)
LLAMA_BASE_URL=http://127.0.0.1:8080

# Model name to expose
DEFAULT_MODEL=qwen3-30b-a3b-instruct

# Optional: API keys for authentication (comma-separated)
API_KEYS=sk-local-abc,sk-local-xyz

# Optional: CORS settings
# CORS_ORIGINS=*  # Allow all origins (default)
```

### Start the Proxy Server

**Option A: Using PowerShell Script (Windows)**
```powershell
cd Z:\llama3_20250528\llama3
.\deployment\run_openai_proxy.ps1
```

**Option B: Direct Command (Linux/macOS/Windows)**
```bash
cd /path/to/llama3
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000
```

**Option C: Production with Auto-Reload**
```bash
uvicorn deployment.openai_compat_server:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --log-level info
```

### Verify Deployment

```bash
# Test 1: Check proxy is running
curl http://localhost:8000
# Should return: {"status":"ok","upstream":"http://127.0.0.1:8080"}

# Test 2: List models
curl http://localhost:8000/v1/models
# Should return: {"object":"list","data":[{"id":"qwen3-30b-a3b-instruct",...}]}

# Test 3: Chat completion (if API_KEYS set)
curl -H "Authorization: Bearer sk-local-abc" \
     -H "Content-Type: application/json" \
     -d '{"model":"qwen3-30b-a3b-instruct","messages":[{"role":"user","content":"Say hi"}]}' \
     http://localhost:8000/v1/chat/completions
```

### Configure Firewall

```bash
# Ubuntu/Debian
sudo ufw allow 8000/tcp
sudo ufw status

# CentOS/RHEL
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# Windows (PowerShell as Administrator)
New-NetFirewallRule -DisplayName "OpenAI Proxy" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

### Keep Running (Background Service)

**Option A: Using screen**
```bash
screen -S proxy
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000
# Press Ctrl+A, then D to detach
# Reattach: screen -r proxy
```

**Option B: Using tmux**
```bash
tmux new -s proxy
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000
# Press Ctrl+B, then D to detach
# Reattach: tmux attach -t proxy
```

**Option C: Using systemd (Linux)**

Create `/etc/systemd/system/openai-proxy.service`:
```ini
[Unit]
Description=OpenAI Compatible Proxy
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/llama3
Environment="LLAMA_BASE_URL=http://127.0.0.1:8080"
Environment="DEFAULT_MODEL=qwen3-30b-a3b-instruct"
Environment="API_KEYS=sk-local-abc"
ExecStart=/usr/bin/uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable openai-proxy
sudo systemctl start openai-proxy
sudo systemctl status openai-proxy

# View logs
sudo journalctl -u openai-proxy -f
```

### Test from Machine C

```bash
# Set environment variable to Machine B's IP
export TEST_BASE_URL=http://YOUR-MACHINE-B-IP:8000/v1
export TEST_API_KEY=sk-local-abc

# Run test
python deployment/test_openai_proxy.py
```

---

## 📦 Option 2: Full Web Application (Frontend + Backend)

This is the **complete option** with a web UI for interactive chat.

### Architecture
```
Browser → Machine B (Frontend :3001 + Backend :3000) → SSH Tunnel → Machine A (LLM)
```

### Prerequisites

1. **SSH Tunnel Active** (from Machine A)
2. **Node.js** (v16 or higher)
3. **Python 3.8+**
4. **Project Repository** (prompt-portal)

### Deploy Using Script

```bash
# Clone or navigate to project
cd ~/prompt-portal

# Run deployment script
chmod +x deploy.sh
./deploy.sh
```

When prompted:
1. **Domain Configuration**: Enter your domain (or press Enter to skip)
2. **LLM Communication Mode**: Choose `2) SSE`
3. **LLM Server URL**: Enter `http://localhost:8080`

The script will:
- Install dependencies (npm, pip packages)
- Configure environment variables
- Build frontend
- Start backend and frontend services

### Manual Deployment

#### 1. Configure Backend

Create `backend/.env`:
```bash
# LLM Communication Mode
LLM_COMM_MODE=sse

# LLM Server (via SSH tunnel)
LLM_SERVER_URL=http://localhost:8080
LLM_TIMEOUT=300
LLM_TEMPERATURE=0.6
LLM_TOP_P=0.9
LLM_MAX_TOKENS=512

# Optional
LLM_SKIP_THINKING=true
LLM_MAX_HISTORY_TOKENS=10000

# Database (if needed)
DATABASE_URL=sqlite:///./data/app.db

# API Keys
SECRET_KEY=your-secret-key-here
```

#### 2. Start Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

#### 3. Configure Frontend

Create `frontend/.env`:
```bash
REACT_APP_API_URL=http://localhost:3000
REACT_APP_API_BASE_URL=http://YOUR-MACHINE-B-IP:3000
```

#### 4. Start Frontend

```bash
cd frontend
npm install
npm run build  # For production
npm start      # For development

# Or serve build folder
npx serve -s build -l 3001
```

### Configure Nginx (Production)

Create `/etc/nginx/sites-available/llm-app`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Frontend
    location / {
        root /path/to/prompt-portal/frontend/build;
        try_files $uri /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
    }

    # WebSocket/SSE support
    location /api/stream {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 600s;
        chunked_transfer_encoding off;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/llm-app /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 🔄 Comparison: Which Option to Choose?

| Feature | Option 1: Proxy Only | Option 2: Full Web App |
|---------|---------------------|----------------------|
| **Setup Complexity** | ⭐ Simple | ⭐⭐⭐ Complex |
| **Components** | 1 (Proxy server) | 3 (Frontend + Backend + DB) |
| **Resources** | Low | Medium-High |
| **Use Case** | API access from clients | Complete web interface |
| **Ports** | 8000 | 3000 (backend) + 3001 (frontend) |
| **Dependencies** | Python only | Python + Node.js |
| **Client Access** | OpenAI SDK | Web browser |
| **Customization** | API only | Full UI customization |
| **Best For** | Remote scripts, apps | End users, demos |

---

## 🎯 Recommended Setup

### For Your Use Case (Machine C Access):

**✅ Deploy Option 1: OpenAI-Compatible Proxy**

Why?
- ✅ Simple to deploy and maintain
- ✅ Perfect for accessing from Machine C using OpenAI SDK
- ✅ Lower resource usage
- ✅ Already have test scripts ready (`test_openai_proxy.py`)
- ✅ Can scale to multiple clients easily

### Quick Start Commands (Machine B)

```bash
# 1. Verify SSH tunnel is working
curl http://localhost:8080/health

# 2. Navigate to project
cd /path/to/llama3

# 3. Create .env file
cat > deployment/.env << EOF
LLAMA_BASE_URL=http://127.0.0.1:8080
DEFAULT_MODEL=qwen3-30b-a3b-instruct
API_KEYS=sk-local-abc
EOF

# 4. Install dependencies (if not already)
pip install fastapi uvicorn httpx python-dotenv pydantic

# 5. Start proxy in screen
screen -S proxy
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000
# Press Ctrl+A, D to detach

# 6. Verify it's working
curl http://localhost:8000

# 7. Open firewall
sudo ufw allow 8000/tcp

# 8. Test from Machine C
# (On Machine C) python deployment/test_openai_proxy.py
```

---

## 📊 Port Summary

| Service | Port | Access | Purpose |
|---------|------|--------|---------|
| SSH Tunnel Endpoint | 8080 | localhost only | Receives from Machine A |
| OpenAI Proxy | 8000 | 0.0.0.0 (public) | API for clients |
| Backend API (Option 2) | 3000 | 0.0.0.0 (public) | Web app backend |
| Frontend (Option 2) | 3001 | 0.0.0.0 (public) | Web app UI |

---

## 🔍 Verification Checklist

After deployment, verify:

- [ ] SSH tunnel from Machine A is active
  ```bash
  netstat -tlnp | grep 8080
  curl http://localhost:8080/health
  ```

- [ ] Proxy server is running (Option 1)
  ```bash
  ps aux | grep uvicorn
  curl http://localhost:8000
  ```

- [ ] Firewall is configured
  ```bash
  sudo ufw status | grep 8000
  ```

- [ ] Service is accessible from outside
  ```bash
  # From another machine
  curl http://MACHINE-B-IP:8000
  ```

- [ ] Test from Machine C works
  ```bash
  python deployment/test_openai_proxy.py
  ```

---

## 🛠️ Troubleshooting

### Proxy Can't Connect to llama.cpp

```bash
# Check tunnel
curl http://localhost:8080/health

# If fails, restart tunnel on Machine A
ssh -R 8080:localhost:8080 user@machine-b-ip -N
```

### Port Already in Use

```bash
# Find what's using port 8000
sudo lsof -i :8000
# or
sudo netstat -tlnp | grep 8000

# Kill process or use different port
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8001
```

### Can't Access from Outside

```bash
# Check service is listening on 0.0.0.0, not 127.0.0.1
netstat -tlnp | grep 8000
# Should show: 0.0.0.0:8000, not 127.0.0.1:8000

# Check firewall
sudo ufw allow 8000/tcp
sudo ufw status

# Test from Machine B itself first
curl http://localhost:8000
```

### Permission Denied

```bash
# If port < 1024, need sudo or use higher port
# Recommended: Use port 8000 (no sudo needed)

# Or set capability (Linux)
sudo setcap CAP_NET_BIND_SERVICE=+eip $(which python3)
```

---

## 📚 Related Files

- `openai_compat_server.py` - Proxy server source code
- `openai_compat_readme.md` - Proxy server documentation
- `test_openai_proxy.py` - Test script for Machine C
- `example_client.py` - Example Python client
- `MACHINE_C_SETUP.md` - Machine C setup guide
- `SSE_MODE_DEPLOYMENT.md` - Overall architecture

---

## 🚀 Next Steps After Deployment

1. **Test from Machine C**:
   ```bash
   python deployment/test_openai_proxy.py
   ```

2. **Set up HTTPS** (Production):
   - Install certbot
   - Get SSL certificate
   - Configure Nginx reverse proxy

3. **Monitor Service**:
   ```bash
   # View logs
   journalctl -u openai-proxy -f
   
   # Check resource usage
   htop
   ```

4. **Scale if Needed**:
   - Add more GPU servers (Machine A2, A3)
   - Use load balancer
   - Add caching layer

---

## Summary

For **Machine C remote access**, deploy on Machine B:

**✅ OpenAI-Compatible Proxy Server** (Option 1)
- Simple FastAPI service
- Runs on port 8000
- Exposes OpenAI-compatible API
- Perfect for programmatic access

This is the **recommended and simplest** option for your use case!

# Two-Machine Setup Guide: LLM Server + Web Server

## Quick Overview

This guide helps you set up the LAM framework across two machines:

- **Machine A**: LLM server with NVIDIA 4090 GPU (no public IP required)
- **Machine B**: Web server with public IP (runs frontend + backend)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Machine A (LLM Server)                                         │
│  • GPU: NVIDIA 4090                                             │
│  • Private network (no public IP)                               │
│                                                                  │
│  ┌──────────────────┐         ┌─────────────────────┐         │
│  │  llama.cpp       │────────▶│  Reverse SSH        │         │
│  │  server          │         │  Tunnel             │─────────┼─┐
│  │  localhost:8080  │         │                     │         │ │
│  └──────────────────┘         └─────────────────────┘         │ │
│                                                                  │ │
└─────────────────────────────────────────────────────────────────┘ │
                                                                     │
  ┌──────────────────────────────────────────────────────────────┐ │
  │  Machine B (Web Server)                                      │ │
  │  • Public IP: xxx.xxx.xxx.xxx                                │ │
  │  • Domain: your-domain.com (optional)                        │ │
  │                                                               │ │
  │  ┌───────────────┐         ┌──────────────┐                 │ │
  │  │  Frontend     │────────▶│  Backend     │◀─────────────────┘
  │  │  (React)      │         │  (FastAPI)   │
  │  │  Port 3001    │         │  Port 3000   │
  │  └───────────────┘         │              │
  │                            │  Connects to │
  │                            │  localhost:  │
  │                            │  8080        │
  │                            └──────────────┘
  │                                    │
  │                            Tunnel endpoint
  │                            (appears local!)
  └───────────────────────────────────────────────────────────────┘

  Users ────▶ your-domain.com (Machine B) ─[SSH Tunnel]─▶ Machine A GPU
```

## Prerequisites

### Machine A (LLM Server)
- Linux (Ubuntu 20.04+ recommended)
- NVIDIA GPU (4090 or similar)
- CUDA drivers installed
- At least 32GB RAM
- SSH client
- Internet access (for initial setup)

### Machine B (Web Server)
- Linux (Ubuntu 20.04+ recommended) or Windows
- Public IP address or domain name
- SSH server running
- At least 4GB RAM
- Node.js 18+ and Python 3.10+

## Step-by-Step Setup

### 1️⃣ Setup Machine A (LLM Server with 4090)

#### A. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install build tools
sudo apt install -y build-essential git curl wget screen

# Verify CUDA installation
nvidia-smi  # Should show your GPU
```

#### B. Install llama.cpp

```bash
# Clone llama.cpp
cd ~
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

# Build with CUDA support
make LLAMA_CUBLAS=1

# Verify build
./llama-server --version
```

#### C. Download Your Model

```bash
cd ~/llama.cpp/models

# Example: Download Qwen3-30B (Q4 quantization)
# Use your preferred method to download GGUF models
# Models can be found on Hugging Face

# For example:
wget https://huggingface.co/.../model.gguf
# Or use huggingface-cli download

# Verify model file
ls -lh *.gguf
```

#### D. Setup SSH Keys (for passwordless tunnel)

```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096 -C "llm-server-key"

# Copy public key to Machine B
# Replace with your actual Machine B details
ssh-copy-id user@machine-b-ip

# Test connection
ssh user@machine-b-ip "echo 'Connection successful!'"
```

#### E. Configure and Start Services

```bash
# Download the quick start script
cd ~/llama.cpp
wget https://raw.githubusercontent.com/your-repo/prompt-portal/main/start_llm_server.sh
chmod +x start_llm_server.sh

# Edit configuration
nano start_llm_server.sh
# Update these values:
#   REMOTE_USER="your-username"
#   REMOTE_HOST="machine-b-ip-or-domain"
#   MODEL_PATH="models/your-model.gguf"

# Start everything
./start_llm_server.sh
```

The script will:
- Start llama.cpp server on localhost:8080
- Create reverse SSH tunnel to Machine B
- Run both in background screen sessions

#### F. Verify Machine A Setup

```bash
# Check services are running
screen -ls
# Should show: llama and tunnel sessions

# Test local LLM server
curl http://localhost:8080/health
# Should return JSON: {"status":"ok",...}

# View LLM server logs
screen -r llama
# Press Ctrl+A then D to detach

# View tunnel logs
screen -r tunnel
# Press Ctrl+A then D to detach
```

### 2️⃣ Setup Machine B (Web Server)

#### A. Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install Python 3.10+
sudo apt install -y python3 python3-pip python3-venv

# Install git
sudo apt install -y git
```

#### B. Clone Repository

```bash
cd ~
git clone https://github.com/your-repo/prompt-portal.git
cd prompt-portal
```

#### C. Verify Tunnel Connection

```bash
# Before deploying, verify the tunnel from Machine A is working
curl http://localhost:8080/health

# Should return JSON from the LLM server on Machine A
# If this doesn't work, check Machine A tunnel logs
```

#### D. Deploy Application

```bash
# Make deploy script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

**During deployment, you'll be asked:**

1. **Domain Configuration**
   - If you have a domain: Enter it (e.g., `myapp.example.com`)
   - If using IP only: Press N

2. **LLM Communication Mode**
   - Choose `2` for SSE mode

3. **LLM Server URL**
   - Enter: `http://localhost:8080`
   - This connects to Machine A via the SSH tunnel!

The script will automatically:
- Configure backend for SSE mode
- Build frontend
- Start all services
- Configure Nginx (if selected)

#### E. Verify Machine B Setup

```bash
# Check services are running
ps aux | grep uvicorn  # Backend
ps aux | grep node     # Frontend

# Test backend
curl http://localhost:3000/api/health

# Test LLM connection through backend
curl http://localhost:3000/api/llm/health
# Should return LLM server info
```

### 3️⃣ Access Your Application

Open your browser and navigate to:

- **With domain + Nginx**: `https://your-domain.com`
- **With domain, no Nginx**: `http://your-domain.com:3001`
- **IP only**: `http://machine-b-ip:3001`

## Quick Start Commands

### Machine A (LLM Server)

```bash
# Start services
cd ~/llama.cpp
./start_llm_server.sh

# Check status
screen -ls

# View LLM server
screen -r llama

# View tunnel
screen -r tunnel

# Stop services
screen -S llama -X quit
screen -S tunnel -X quit
```

### Machine B (Web Server)

```bash
# Start services
cd ~/prompt-portal
./deploy.sh

# Check logs
tail -f backend/app.log

# Stop services
kill $(cat backend/backend.pid)
kill $(cat frontend/frontend.pid)

# Or use the provided script
./stop_services.sh
```

## Troubleshooting

### Tunnel Not Connected

**On Machine A:**
```bash
# Check tunnel session
screen -r tunnel

# If tunnel failed, check SSH connectivity
ssh user@machine-b-ip

# Manually test tunnel
ssh -R 8080:localhost:8080 user@machine-b-ip -N
```

**On Machine B:**
```bash
# Check if port 8080 is listening
netstat -tlnp | grep 8080

# Test connection
curl http://localhost:8080/health
```

### Backend Can't Connect to LLM

**On Machine B:**
```bash
# Check backend configuration
cd ~/prompt-portal/backend
cat .env | grep LLM

# Should show:
# LLM_COMM_MODE=sse
# LLM_SERVER_URL=http://localhost:8080

# Test connection manually
curl http://localhost:8080/health

# Check backend logs
tail -f app.log
```

### LLM Server Not Responding

**On Machine A:**
```bash
# Check if server is running
ps aux | grep llama-server

# View logs
screen -r llama

# Restart server
screen -S llama -X quit
./start_llm_server.sh
```

### Port Already in Use

If port 8080 is used on Machine B:

**On Machine A (edit start_llm_server.sh):**
```bash
REMOTE_PORT=8081  # Change to different port
```

**On Machine B (edit .env):**
```bash
LLM_SERVER_URL=http://localhost:8081
```

## Performance Tips

### Optimize llama.cpp Settings

Edit `start_llm_server.sh` on Machine A:

```bash
# For faster responses (lower context)
CONTEXT_SIZE=8192

# For better quality (more GPU layers)
GPU_LAYERS=40  # Adjust based on VRAM

# For more concurrent users
PARALLEL=16
```

### Monitor GPU Usage

**On Machine A:**
```bash
# Watch GPU usage
watch -n 1 nvidia-smi

# View detailed stats
nvtop  # Install with: sudo apt install nvtop
```

## Security Considerations

### SSH Tunnel Security
- ✅ SSH tunnel is encrypted end-to-end
- ✅ Only Machine B can access the LLM server
- ✅ No need to expose LLM server to internet

### Additional Security

**Machine A:**
```bash
# Ensure llama.cpp only listens on localhost
# In start_llm_server.sh, verify:
--host 0.0.0.0  # This is OK, protected by no public IP

# Or restrict to localhost only:
--host 127.0.0.1  # More restrictive
```

**Machine B:**
```bash
# Use firewall to restrict access
sudo ufw enable
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP
sudo ufw allow 443/tcp     # HTTPS
sudo ufw allow 3000/tcp    # Backend (or use Nginx)
sudo ufw allow 3001/tcp    # Frontend (or use Nginx)
```

## Maintenance

### Automatic Startup on Reboot

**Machine A (LLM Server):**
```bash
# Add to crontab
crontab -e

# Add this line:
@reboot cd ~/llama.cpp && ./start_llm_server.sh
```

**Machine B (Web Server):**
```bash
# Add to crontab
crontab -e

# Add this line:
@reboot cd ~/prompt-portal && ./deploy.sh
```

### Monitor Services

**Machine A:**
```bash
# Create monitoring script
cat > ~/check_services.sh << 'EOF'
#!/bin/bash
if ! screen -ls | grep -q llama; then
    echo "LLM server down, restarting..."
    cd ~/llama.cpp && ./start_llm_server.sh
fi
EOF

chmod +x ~/check_services.sh

# Add to crontab (check every 5 minutes)
crontab -e
# Add: */5 * * * * ~/check_services.sh
```

## Resources

- **Full Documentation**: See `SSE_MODE_DEPLOYMENT.md`
- **Reverse SSH Guide**: See `maintain_tunnel.sh`
- **LLM Server Guide**: See `start_llm_server.sh`

## Support

### Common Issues

1. **Tunnel keeps disconnecting**: Check network stability, increase keepalive interval
2. **Slow responses**: Reduce context size or increase GPU layers
3. **Out of memory**: Reduce parallel requests or use smaller model

### Getting Help

- Check logs on both machines
- Verify tunnel is active
- Test each component separately
- Review configuration files

## Summary

You now have:
- ✅ LLM server running on Machine A (private network)
- ✅ Reverse SSH tunnel connecting both machines
- ✅ Web application on Machine B (public IP)
- ✅ Secure, encrypted communication
- ✅ Fast, low-latency LLM responses

Your GPU server stays private while your users can access the application from anywhere! 🎉

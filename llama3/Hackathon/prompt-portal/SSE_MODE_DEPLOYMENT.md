# SSE Mode Deployment Guide

## Overview

SSE (Server-Sent Events) mode allows the LAM framework to communicate directly with the LLM server via HTTP/SSE, eliminating the need for an MQTT broker. This is ideal for simplified deployments, especially when using reverse SSH tunneling to connect machines without public IPs.

## Architecture

### Traditional MQTT Mode
```
Frontend → Backend API → MQTT Broker → LLM Service (llamacpp_mqtt_deploy.py)
                                ↓
                          LLM Server (llama.cpp)
```

### SSE Mode
```
Frontend → Backend API → HTTP/SSE → LLM Server (llama.cpp)
```

## Two-Machine Setup

### Scenario
- **Machine A (LLM Server)**: Has NVIDIA 4090, runs llama.cpp server, NO public IP
- **Machine B (Web Server)**: Has public IP, runs frontend + backend

### Solution: Reverse SSH Tunnel

Machine A creates a reverse SSH tunnel to Machine B, exposing its local llama.cpp server on Machine B's localhost.

## Step-by-Step Deployment

### 1. Setup Machine A (LLM Server with 4090)

#### Install llama.cpp

```bash
# Clone and build llama.cpp
cd ~
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
make LLAMA_CUBLAS=1  # For NVIDIA GPU support

# Or download pre-built binaries
```

#### Download Your Model

```bash
# Example: Download a GGUF model
cd ~/llama.cpp/models
# Download your preferred model (Qwen3, Llama3, etc.)
# Place the .gguf file in this directory
```

#### Start llama.cpp Server

```bash
# Example with Qwen3-30B model
cd ~/llama.cpp
./llama-server \
  -m models/qwen3-30b-a3b-instruct-2507-Q4_K_M.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -c 28192 \
  -ngl 35 \
  -t 8 \
  --parallel 8
```

**Important Parameters:**
- `--host 0.0.0.0`: Listen on all interfaces (required for SSH tunnel)
- `--port 8080`: Default port (can be changed)
- `-c 28192`: Context size (adjust based on your model)
- `-ngl 35`: Number of layers to offload to GPU
- `--parallel 8`: Number of parallel requests

#### Keep Server Running with Screen/Tmux

```bash
# Using screen
screen -S llama
./llama-server -m models/your-model.gguf --host 0.0.0.0 --port 8080 -c 28192 -ngl 35
# Press Ctrl+A, then D to detach
# Reattach with: screen -r llama

# Or using tmux
tmux new -s llama
./llama-server -m models/your-model.gguf --host 0.0.0.0 --port 8080 -c 28192 -ngl 35
# Press Ctrl+B, then D to detach
# Reattach with: tmux attach -t llama
```

### 2. Setup SSH Access from Machine A to Machine B

On **Machine A** (LLM server):

```bash
# Generate SSH key if you don't have one
ssh-keygen -t rsa -b 4096 -C "llm-server"

# Copy public key to Machine B
ssh-copy-id user@machine-b-ip

# Test connection
ssh user@machine-b-ip
```

### 3. Create Reverse SSH Tunnel

On **Machine A** (LLM server), create a reverse SSH tunnel:

```bash
# Basic tunnel (manual)
ssh -R 8080:localhost:8080 user@machine-b-ip -N

```bash
ssh -R 8080:localhost:8080 -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes lobin@vpn.agaii.org -N
```
```

**What this does:**
- `-R 8080:localhost:8080`: Forward Machine B's localhost:8080 to Machine A's localhost:8080
- `-N`: Don't execute remote commands (just tunnel)
- `-o ServerAliveInterval=60`: Send keepalive every 60 seconds
- `-o ServerAliveCountMax=3`: Reconnect after 3 failed keepalives

#### Keep Tunnel Running with Screen/Tmux

```bash
# Using screen
screen -S tunnel
ssh -R 8080:localhost:8080 -o ServerAliveInterval=60 user@machine-b-ip -N
# Press Ctrl+A, then D to detach

# Or using tmux
tmux new -s tunnel
ssh -R 8080:localhost:8080 -o ServerAliveInterval=60 user@machine-b-ip -N
# Press Ctrl+B, then D to detach
```

#### Automated Tunnel Script (Recommended)

Save this script on **Machine A** as `maintain_tunnel.sh`:

```bash
#!/bin/bash
# Maintain reverse SSH tunnel with auto-reconnect

REMOTE_USER="lobin"
REMOTE_HOST="vpn.agaii.org"
LOCAL_PORT=8080
REMOTE_PORT=8080

while true; do
    echo "$(date): Starting SSH tunnel..."
    ssh -R ${REMOTE_PORT}:localhost:${LOCAL_PORT} \
        -o ServerAliveInterval=30 \
        -o ServerAliveCountMax=3 \
        -o ExitOnForwardFailure=yes \
        -o StrictHostKeyChecking=no \
        ${REMOTE_USER}@${REMOTE_HOST} -N
    
    echo "$(date): Tunnel disconnected. Reconnecting in 5 seconds..."
    sleep 5
done
```

Make it executable and run:

```bash
chmod +x maintain_tunnel.sh

# Run in screen/tmux
screen -S tunnel
./maintain_tunnel.sh
# Press Ctrl+A, then D to detach
```

#### Setup as System Service (Advanced)

Create `/etc/systemd/system/llm-tunnel.service`:

```ini
[Unit]
Description=LLM Server Reverse SSH Tunnel
After=network.target

[Service]
Type=simple
User=your-username
ExecStart=/usr/bin/ssh -R 8080:localhost:8080 -o ServerAliveInterval=60 -o ServerAliveCountMax=3 -o ExitOnForwardFailure=yes user@machine-b-ip -N
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable llm-tunnel
sudo systemctl start llm-tunnel
sudo systemctl status llm-tunnel
```

### 4. Deploy Web Application on Machine B

On **Machine B** (web server):

```bash
# Clone the repository
cd ~
git clone https://github.com/your-repo/prompt-portal.git
cd prompt-portal

# Run deployment script
chmod +x deploy.sh
./deploy.sh
```

When prompted:

1. **Domain Configuration**: Enter your domain if you have one
2. **LLM Communication Mode**: Choose `2) SSE`
3. **LLM Server URL**: Enter `http://localhost:8080` (this connects to the tunnel!)

The deployment script will automatically:
- Configure backend for SSE mode
- Set `LLM_COMM_MODE=sse` in `.env`
- Set `LLM_SERVER_URL=http://localhost:8080`
- Start frontend and backend services

### 5. Verify Connection

On **Machine B**, test the tunnel:

```bash
# Test that port 8080 is accessible
curl http://localhost:8080/health

# Should return JSON from llama.cpp server
# Example: {"status":"ok","slots_idle":8,"slots_processing":0}
```

If this works, your tunnel is correctly established!

### 6. Access Your Application

Open your browser and navigate to:
- **With domain + Nginx**: `https://your-domain.com`
- **With domain, no Nginx**: `http://your-domain.com:3001`
- **IP only**: `http://machine-b-ip:3001`

## Environment Variables Reference

### Backend `.env` (Machine B)

```bash
# LLM Communication Mode
LLM_COMM_MODE=sse

# LLM Server Configuration (via reverse SSH tunnel)
LLM_SERVER_URL=http://localhost:8080
LLM_TIMEOUT=300
LLM_TEMPERATURE=0.6
LLM_TOP_P=0.9
LLM_MAX_TOKENS=512
LLM_SKIP_THINKING=true
LLM_MAX_HISTORY_TOKENS=10000
```

## Troubleshooting

### Tunnel Not Working

**Check tunnel status on Machine A:**
```bash
# See if SSH process is running
ps aux | grep ssh

# Check tunnel logs
journalctl -u llm-tunnel -f  # If using systemd service
```

**Test from Machine B:**
```bash
# Check if port is listening
netstat -tlnp | grep 8080
# or
ss -tlnp | grep 8080

# Test connection
curl http://localhost:8080/health
```

### Connection Refused

**On Machine A**, ensure llama.cpp is listening on `0.0.0.0`:
```bash
netstat -tlnp | grep 8080
# Should show: 0.0.0.0:8080
```

### Backend Can't Connect to LLM

**Check backend logs:**
```bash
cd ~/prompt-portal/backend
tail -f app.log  # or wherever logs are stored
```

**Verify environment:**
```bash
cd ~/prompt-portal/backend
cat .env | grep LLM
```

### Port Already in Use

If port 8080 is already in use on Machine B:

```bash
# Find what's using the port
lsof -i :8080

# Use a different port
# On Machine A (tunnel):
ssh -R 8081:localhost:8080 user@machine-b-ip -N

# Update Machine B backend .env:
LLM_SERVER_URL=http://localhost:8081
```

## Performance Considerations

### Network Latency
- SSH tunnel adds ~10-50ms latency depending on network
- For best performance, use machines on same network or datacenter
- Enable SSH compression for slower connections: `ssh -C -R ...`

### Throughput
- SSH tunnel can handle gigabit speeds
- llama.cpp streaming works well over SSH
- No noticeable impact on response times for text generation

### Security
- SSH tunnel is encrypted end-to-end
- Only Machine B can access the LLM server
- No need to expose LLM server to internet

## Advanced: Multiple LLM Servers

If you have multiple GPU machines:

**Machine A1** (GPU server 1):
```bash
ssh -R 8080:localhost:8080 user@machine-b-ip -N
```

**Machine A2** (GPU server 2):
```bash
ssh -R 8081:localhost:8080 user@machine-b-ip -N
```

**Machine B** backend configuration:
```bash
# Use load balancer or switch between servers
LLM_SERVER_URL=http://localhost:8080  # or 8081
```

## Comparison: MQTT vs SSE Mode

| Feature | MQTT Mode | SSE Mode |
|---------|-----------|----------|
| **Setup Complexity** | High (requires broker) | Low (direct connection) |
| **Network Topology** | Requires broker with public IP | Works with reverse SSH tunnel |
| **Latency** | Higher (broker hop) | Lower (direct) |
| **Scalability** | Better (pub/sub) | Good (HTTP) |
| **Debugging** | Harder (async messages) | Easier (direct HTTP) |
| **Use Case** | Multiple services, IoT | Simple deployments, remote GPUs |

## Next Steps

1. **Monitor Performance**: Watch response times and adjust parameters
2. **Scale Up**: Add more GPU servers with additional tunnels
3. **Optimize**: Tune llama.cpp parameters for your use case
4. **Secure**: Use firewall rules to restrict access
5. **Automate**: Set up monitoring and auto-restart services

## Quick Start Script

Save this as `quick_start_sse.sh` on **Machine A**:

```bash
#!/bin/bash
# Quick start script for Machine A (LLM server)

# Configuration
REMOTE_USER="user"
REMOTE_HOST="machine-b-ip"
MODEL_PATH="models/qwen3-30b.gguf"

echo "Starting LLM server..."
screen -dmS llama bash -c "
cd ~/llama.cpp
./llama-server -m $MODEL_PATH --host 0.0.0.0 --port 8080 -c 28192 -ngl 35 -t 8 --parallel 8
"

echo "Waiting for server to start..."
sleep 10

echo "Creating reverse SSH tunnel..."
screen -dmS tunnel bash -c "
while true; do
    ssh -R 8080:localhost:8080 -o ServerAliveInterval=60 $REMOTE_USER@$REMOTE_HOST -N
    sleep 5
done
"

echo "Done! Check status with:"
echo "  screen -ls"
echo "  screen -r llama  # View LLM server"
echo "  screen -r tunnel # View tunnel"
```

## Support

For issues or questions:
1. Check logs on both machines
2. Verify SSH tunnel is active
3. Test llama.cpp server directly on Machine A
4. Review backend configuration on Machine B

## Summary

SSE mode with reverse SSH tunneling provides:
- ✅ Simple setup without MQTT broker
- ✅ Secure connection between machines
- ✅ Works with private IP LLM servers
- ✅ Lower latency than MQTT
- ✅ Easy debugging and monitoring
- ✅ Perfect for 2-machine deployments

Your GPU server (Machine A) stays private while your web application (Machine B) can access it securely via the SSH tunnel!

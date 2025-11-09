# SSE Mode Quick Reference

## 🚀 Quick Start

### Machine A (GPU Server)
```bash
# 1. Edit configuration
nano start_llm_server.sh
# Set: REMOTE_USER, REMOTE_HOST, MODEL_PATH

# 2. Start everything
./start_llm_server.sh

# 3. Verify
screen -ls
curl http://localhost:8080/health
```

### Machine B (Web Server)
```bash
# 1. Clone repository
git clone https://github.com/your-repo/prompt-portal.git
cd prompt-portal

# 2. Deploy
./deploy.sh
# Choose: SSE mode, localhost:8080

# 3. Verify
curl http://localhost:8080/health
curl http://localhost:3000/api/llm/health
```

## 📋 Cheat Sheet

### Check Services

**Machine A:**
```bash
screen -ls                    # List sessions
screen -r llama               # View LLM server
screen -r tunnel              # View tunnel
ps aux | grep llama-server    # Check process
nvidia-smi                    # Check GPU
```

**Machine B:**
```bash
ps aux | grep uvicorn         # Backend
ps aux | grep node            # Frontend
netstat -tlnp | grep 8080     # Check tunnel endpoint
tail -f backend/app.log       # View logs
```

### Restart Services

**Machine A:**
```bash
# Stop
screen -S llama -X quit
screen -S tunnel -X quit

# Start
./start_llm_server.sh
```

**Machine B:**
```bash
# Stop
kill $(cat backend/backend.pid)
kill $(cat frontend/frontend.pid)

# Start
./deploy.sh
```

### Test Connection

```bash
# Local LLM (Machine A)
curl http://localhost:8080/health

# Tunnel endpoint (Machine B)
curl http://localhost:8080/health

# Backend LLM connection (Machine B)
curl http://localhost:3000/api/llm/health

# Full API test (Machine B)
curl -X POST http://localhost:3000/api/llm/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"messages":[{"role":"user","content":"Hi"}]}'
```

## 🔧 Configuration Files

### Machine A: `start_llm_server.sh`
```bash
REMOTE_USER="your-username"
REMOTE_HOST="machine-b-ip"
MODEL_PATH="models/your-model.gguf"
```

### Machine B: `backend/.env`
```bash
LLM_COMM_MODE=sse
LLM_SERVER_URL=http://localhost:8080
```

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| Tunnel not working | Check Machine A: `screen -r tunnel` |
| Connection refused | Verify llama.cpp server: `ps aux \| grep llama` |
| Backend can't connect | Test tunnel: `curl http://localhost:8080/health` |
| Port already in use | Change ports in scripts and .env |
| Slow responses | Reduce context size or increase GPU layers |

## 📞 Emergency Commands

```bash
# Kill everything on Machine A
screen -S llama -X quit
screen -S tunnel -X quit
pkill llama-server

# Kill everything on Machine B
kill $(cat backend/backend.pid)
kill $(cat frontend/frontend.pid)
pkill -f uvicorn
pkill -f "vite.*preview"

# Clean start Machine A
cd ~/llama.cpp
./start_llm_server.sh

# Clean start Machine B
cd ~/prompt-portal
./deploy.sh
```

## 📚 Documentation

- Full guide: `SSE_MODE_DEPLOYMENT.md`
- Setup guide: `TWO_MACHINE_SETUP.md`
- Summary: `SSE_IMPLEMENTATION_SUMMARY.md`

## 🎯 Common Ports

| Service | Port | Location |
|---------|------|----------|
| llama.cpp | 8080 | Machine A (local) |
| SSH tunnel | 8080 | Machine B (localhost) |
| Backend | 3000 | Machine B (public) |
| Frontend | 3001 | Machine B (public) |

## ⚡ Performance Tips

### Machine A (LLM Server)
```bash
# Edit start_llm_server.sh
CONTEXT_SIZE=8192      # Smaller = faster
GPU_LAYERS=40          # More = faster (if VRAM allows)
PARALLEL=16            # More users = more concurrent
THREADS=8              # Match your CPU cores
```

### SSH Tunnel
```bash
# Enable compression for slower networks
ssh -C -R 8080:localhost:8080 user@host -N
```

## 🔐 Security Checklist

- ✅ Use SSH key authentication
- ✅ Disable SSH password auth on Machine B
- ✅ Enable firewall on both machines
- ✅ Use HTTPS for production
- ✅ Keep systems updated
- ✅ Monitor tunnel connectivity

## 📊 Monitoring

### Watch GPU Usage (Machine A)
```bash
watch -n 1 nvidia-smi
# or
nvtop
```

### Watch Logs (Machine B)
```bash
tail -f backend/app.log
# or
journalctl -f
```

### Check Tunnel Status
```bash
# Machine B
netstat -tlnp | grep 8080
ss -tlnp | grep 8080
```

## 🎛️ Mode Switching

### Switch to SSE Mode
```bash
# Machine B: backend/.env
LLM_COMM_MODE=sse
LLM_SERVER_URL=http://localhost:8080
# Restart backend
```

### Switch to MQTT Mode
```bash
# Machine B: backend/.env
LLM_COMM_MODE=mqtt
MQTT_BROKER_HOST=47.89.252.2
# Restart backend
```

## 🌐 Access URLs

### Development
- Frontend: `http://localhost:3001`
- Backend: `http://localhost:3000`
- Docs: `http://localhost:3000/docs`

### Production (IP)
- Frontend: `http://YOUR-IP:3001`
- Backend: `http://YOUR-IP:3000`

### Production (Domain + Nginx)
- Frontend: `https://your-domain.com`
- Backend: `https://your-domain.com/api`

## 💡 Tips

1. **Keep terminals open**: Use `screen` or `tmux`
2. **Monitor GPU**: Install `nvtop` for better visibility
3. **Auto-start**: Add to crontab with `@reboot`
4. **Backup configs**: Keep copies of working configurations
5. **Test locally first**: Verify llama.cpp works before tunneling

## ⚠️ Common Mistakes

- ❌ Not setting llama.cpp to `--host 0.0.0.0`
- ❌ Wrong SSH credentials for tunnel
- ❌ Firewall blocking port 8080 on Machine A
- ❌ Not using `screen`/`tmux` (services stop when SSH disconnects)
- ❌ Forgetting to update `.env` file

## 🎓 Learning Path

1. ✅ Setup Machine A with llama.cpp
2. ✅ Test llama.cpp locally
3. ✅ Setup SSH tunnel manually
4. ✅ Verify tunnel from Machine B
5. ✅ Deploy web app on Machine B
6. ✅ Configure for SSE mode
7. ✅ Test end-to-end
8. ✅ Setup auto-restart and monitoring

---

**Need help?** Check the full documentation in `SSE_MODE_DEPLOYMENT.md`

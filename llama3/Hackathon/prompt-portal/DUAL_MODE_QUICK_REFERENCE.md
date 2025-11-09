# LAM Framework - Dual Mode Quick Reference Card

## 🎯 Choose Your Mode

| Feature | MQTT Mode | SSE Mode |
|---------|-----------|----------|
| **Best For** | Distributed systems, multiple LAM instances | 2-machine setup, low latency |
| **Latency** | ~500-1000ms | ~200-500ms |
| **Complexity** | Higher (4 components) | Lower (2 components) |
| **Requirements** | MQTT broker + LAM process | llama.cpp server only |
| **Public IP Required** | Web server only | Web server only |

---

## ⚙️ Configuration

### `.env` File (Backend)

**SSE Mode:**
```bash
LLM_COMM_MODE=sse
LLM_SERVER_URL=http://localhost:8080
LLM_TIMEOUT=120
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2048
```

**MQTT Mode:**
```bash
LLM_COMM_MODE=mqtt
MQTT_BROKER_HOST=47.89.252.2
MQTT_BROKER_PORT=1883
MQTT_USER=your_user
MQTT_PASSWORD=your_password
```

---

## 🚀 Deployment Commands

### SSE Mode (2-Machine Setup)

**Machine A (GPU Server, Windows):**
```powershell
# Start llama-server
cd Z:\llama3_20250528\llama3\${TARGET_FOLDER}\${MODEL_FOLDER_PATH}
.\llama-server.exe --model Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf --port 8080 --host 0.0.0.0

# Create reverse SSH tunnel (explicitly use 127.0.0.1 not localhost)
ssh -R 8080:127.0.0.1:8080 root@vpn.agaii.org -N
```

**Machine B (Web Server, Linux):**
```bash
cd /root/LAM-PromptPortal
./deploy.sh
# Select: 2 (SSE mode)
# Enter URL: http://localhost:8080
```

### MQTT Mode (Traditional)

**GPU Server:**
```bash
cd /path/to/LAM
python llamacpp_mqtt_deploy.py
```

**Web Server:**
```bash
cd /root/LAM-PromptPortal
./deploy.sh
# Select: 1 (MQTT mode)
```

---

## 🧪 Testing Commands

### Health Checks
```bash
# Test llama-server (on Machine B through tunnel)
curl http://localhost:8080/health

# Test backend
curl https://lammp.agaii.org/api/health

# Test with authentication
curl -H "Authorization: Bearer YOUR_TOKEN" https://lammp.agaii.org/api/chatbot/conversations
```

### Chatbot Test
```bash
curl -X POST https://lammp.agaii.org/api/chatbot/send_message \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_id": 1,
    "content": "Hello, how are you?"
  }'
```

### Maze Game Test
```bash
# Request hint
curl -X POST https://lammp.agaii.org/api/mqtt/request_hint \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-123",
    "state": {
      "playerPosition": [0, 0],
      "goal": [5, 5],
      "moves": 0
    }
  }'

# Poll for hint
curl https://lammp.agaii.org/api/mqtt/last_hint?session_id=test-123 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 🔍 Troubleshooting

### Issue: Empty Reply from Server
```bash
# ❌ Wrong (uses IPv6 ::1)
ssh -R 8080:localhost:8080 root@vpn.agaii.org -N

# ✅ Correct (uses IPv4 127.0.0.1)
ssh -R 8080:127.0.0.1:8080 root@vpn.agaii.org -N
```

### Issue: Check if llama-server is listening
```powershell
# Windows
netstat -ano | findstr :8080

# Linux
netstat -tuln | grep 8080
```

### Issue: Check tunnel status
```bash
# On Machine B, check if port 8080 is listening
netstat -tuln | grep 8080

# Test from Machine B
curl http://localhost:8080/health
```

### Issue: Backend not using SSE mode
```bash
# Check environment variable
cd /root/LAM-PromptPortal/backend
cat .env | grep LLM_COMM_MODE

# Should show: LLM_COMM_MODE=sse
```

### Issue: 503 Service Unavailable
- Verify `LLM_COMM_MODE` is set correctly
- Check backend logs: `docker logs prompt-portal-backend` or `journalctl -u lam-backend`
- Ensure tunnel is active
- Test llama-server health check

---

## 📁 Key Files

### Configuration
- `backend/.env` - Environment variables
- `backend/app/config.py` - Configuration class

### Core Services
- `backend/app/services/llm_service.py` - Unified LLM interface
- `backend/app/services/llm_client.py` - Direct HTTP/SSE client
- `backend/app/mqtt.py` - MQTT client

### Routers
- `backend/app/routers/chatbot.py` - Chatbot endpoints (dual-mode)
- `backend/app/routers/mqtt_bridge.py` - Maze game endpoints (dual-mode)

### Helpers
- `maintain_tunnel.sh` / `maintain_tunnel.bat` - Auto-restart tunnel
- `start_llm_server.sh` - Quick start llama-server

---

## 🎮 API Endpoints

### Chatbot (Dual-Mode)
```
POST /api/chatbot/send_message
  - MQTT mode: Publishes to MQTT, waits for response
  - SSE mode: Direct HTTP call, immediate response
```

### Maze Game (Dual-Mode)
```
POST /api/mqtt/request_hint
  - MQTT mode: Returns {"ok": true, "mode": "mqtt"}
  - SSE mode: Returns {"ok": true, "mode": "sse", "hint": "..."}

GET /api/mqtt/last_hint?session_id=xxx
  - Works in both modes (polling)

WebSocket /api/mqtt/ws/hints/{session_id}
  - Works in both modes (real-time)
```

---

## 🔐 Mode Detection in Code

### Python (Backend)
```python
from app.config import settings

if settings.LLM_COMM_MODE.lower() == "sse":
    # SSE mode logic
    from app.services.llm_service import get_llm_service
    llm_service = get_llm_service()
    response = llm_service.process_message(...)
else:
    # MQTT mode logic
    from app.mqtt import send_chat_message
    send_chat_message(...)
```

### JavaScript (Frontend)
```javascript
// Frontend doesn't need to know the mode
// Backend handles it transparently
const response = await fetch('/api/chatbot/send_message', {
  method: 'POST',
  body: JSON.stringify({ conversation_id, content })
});

// Check response if needed
const data = await response.json();
console.log('Mode:', data.mode); // "mqtt" or "sse"
```

---

## 📊 Monitoring

### Check Current Mode
```bash
# Backend logs will show
tail -f /var/log/lam-backend.log | grep "LLM_COMM_MODE"
```

### Performance Metrics
```bash
# Chatbot latency test
time curl -X POST https://lammp.agaii.org/api/chatbot/send_message \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"conversation_id": 1, "content": "test"}'

# MQTT mode: ~500-1000ms
# SSE mode: ~200-500ms
```

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `SSE_MODE_DEPLOYMENT.md` | Complete deployment guide |
| `TWO_MACHINE_SETUP.md` | Quick start for 2-machine setup |
| `SSE_CHATBOT_FIX.md` | Chatbot implementation details |
| `MAZE_GAME_SSE_SUPPORT.md` | Maze game implementation details |
| `SSE_QUICK_REFERENCE.md` | Command cheat sheet |
| `COMPLETE_SSE_IMPLEMENTATION.md` | Full implementation summary |

---

## ✅ Pre-Flight Checklist

### Before Deploying SSE Mode
- [ ] llama.cpp server compiled and tested
- [ ] Model downloaded (Qwen2.5-Coder-32B-Instruct)
- [ ] SSH tunnel tested (explicitly use 127.0.0.1)
- [ ] Health check passes: `curl http://localhost:8080/health`
- [ ] Backend `.env` configured with `LLM_COMM_MODE=sse`
- [ ] Nginx reverse proxy configured
- [ ] SSL certificate active

### After Deploying
- [ ] Backend starts without errors
- [ ] Chatbot sends messages successfully
- [ ] Maze game requests hints
- [ ] WebSocket connections work
- [ ] Function calling works in maze game
- [ ] Check logs for mode confirmation

---

## 🎓 Best Practices

1. **Always use explicit IP (127.0.0.1) in SSH tunnel** - Avoids IPv6/IPv4 issues
2. **Test health endpoint first** - Verify connectivity before complex tests
3. **Check mode in API responses** - Helps debug which path is being used
4. **Monitor tunnel stability** - Use `maintain_tunnel.sh` for production
5. **Keep conversation history** - SSE mode maintains context via SessionManager
6. **Enable function calling for maze game** - Set `use_tools=True`
7. **Use WebSocket for real-time hints** - Better UX than polling

---

## 🆘 Emergency Commands

### Restart Everything (SSE Mode)
```bash
# Machine A (Windows)
# Ctrl+C to stop llama-server, then:
.\llama-server.exe --model Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf --port 8080 --host 0.0.0.0

# Restart tunnel
ssh -R 8080:127.0.0.1:8080 root@vpn.agaii.org -N

# Machine B (Linux)
cd /root/LAM-PromptPortal
./deploy.sh
```

### Quick Switch to MQTT Mode
```bash
cd /root/LAM-PromptPortal/backend
sed -i 's/LLM_COMM_MODE=sse/LLM_COMM_MODE=mqtt/' .env
systemctl restart lam-backend  # or docker-compose restart
```

---

**💡 Remember**: The frontend code doesn't change between modes - all dual-mode logic is in the backend!

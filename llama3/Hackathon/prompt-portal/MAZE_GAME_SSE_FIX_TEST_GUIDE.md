# Quick Test Guide - Maze Game SSE Fix

## 🚀 Quick Start (2-Machine Setup)

### Machine A (4090 GPU Server)
```bash
# 1. Start llama-server
cd Z:\llama3_20250528\llama3\${TARGET_FOLDER}\${MODEL_FOLDER_PATH}
.\llama-server.exe --model Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf --port 8080 --host 0.0.0.0

# 2. Create reverse SSH tunnel to web server
ssh -R 8080:127.0.0.1:8080 root@vpn.agaii.org -N
```

### Machine B (Web Server)
```bash
# 1. Navigate to backend directory
cd /root/LAM-PromptPortal/backend

# 2. Deploy with fix
chmod +x deploy-sse-fix.sh
./deploy-sse-fix.sh

# Or manually:
uvicorn app.main:app --host 0.0.0.0 --port 3000 --reload
```

---

## ✅ Verification Steps

### 1. Check Backend Startup
Watch for these log messages:
```
INFO: UnifiedLLMService initialized in SSE mode
INFO: Application startup complete
```

**If missing**: Check `.env` has `LLM_COMM_MODE=sse`

---

### 2. Test llama.cpp Connectivity
```bash
# From web server (Machine B)
curl http://localhost:8080/health

# Should return:
{"status":"ok"}
```

**If fails**:
- Check SSH tunnel is running: `ps aux | grep ssh | grep 8080`
- Restart tunnel: `ssh -R 8080:127.0.0.1:8080 root@vpn.agaii.org -N`
- Check llama-server is running on Machine A

---

### 3. Test Backend Health
```bash
curl http://localhost:3000/api/health

# Should return backend health info
```

**If fails**: Backend not running or wrong port

---

### 4. Start Maze Game
1. Open browser: `https://lammp.agaii.org`
2. Login
3. Click "Play in Browser"
4. Select a template
5. Choose "LAM Mode"
6. Click "Start Game"

---

### 5. Watch Backend Logs
```bash
# In backend terminal, watch for these messages:
[SSE MODE] Auto-generating hint for publish_state, session: session-XXXXXX
[SSE MODE] Calling LLM with session_id=session-XXXXXX, use_tools=True
[SSE MODE] Got response from LLM: {...
[SSE MODE] Successfully generated and stored hint for session session-XXXXXX
```

**What to look for**:
- ✅ Messages appear every 3 seconds (default publish rate)
- ✅ No error messages
- ✅ "Successfully generated and stored hint" messages

**If no messages appear**:
- Frontend might not be in LAM mode
- Game might not be started
- Check browser console for errors

---

### 6. Verify Hints in Frontend
In the game UI:
- ✅ LAM Details panel shows hints
- ✅ Hints update every few seconds
- ✅ Path suggestions appear (if template enables show_path)
- ✅ Player moves along suggested path in LAM mode

**If hints don't appear**:
- Check browser console (F12) for errors
- Check LAM Details panel is visible (not hidden)
- Try refreshing page and restarting game

---

## 🐛 Troubleshooting

### Issue: "Connection refused" to llama.cpp
```bash
# Check tunnel
ps aux | grep ssh | grep 8080

# Restart tunnel on Machine A
ssh -R 8080:127.0.0.1:8080 root@vpn.agaii.org -N

# Test from Machine B
curl http://localhost:8080/health
```

---

### Issue: "Failed to generate hint"
**Check logs for specific error:**

#### Error: "Connection timeout"
- llama.cpp is overloaded or slow
- Increase `LLM_TIMEOUT` in `.env` (default 30s)
- Use smaller model or increase GPU memory

#### Error: "Model not loaded"
- llama-server not started on Machine A
- Check llama-server terminal for errors

#### Error: "Session manager not initialized"
- Backend config issue
- Restart backend
- Check `LLM_COMM_MODE=sse` in `.env`

---

### Issue: Hints are too slow
**Symptoms**: 
- Long delay between state publish and hint
- Game feels laggy

**Solutions**:
1. **Use smaller model**: 7B or 13B instead of 32B
2. **Reduce max_tokens**: 
   ```bash
   # In .env
   LLM_MAX_TOKENS=256  # Instead of 512
   ```
3. **Increase publish rate**:
   - In game settings, increase MQTT send rate to 5000ms or 10000ms
   - Less frequent requests = less load

4. **Use quantized model**:
   - Q4_K_M (current) is good
   - Q5_K_M for better quality but slower
   - Q3_K_M for faster but lower quality

---

### Issue: Function calling not working
**Symptoms**:
- LAM can't break walls
- LAM can't teleport player
- LAM can't use special abilities

**Check**:
1. **Template has function calling instructions**:
   ```
   You can use these actions:
   - break_wall(x, y): Break a wall at position
   - teleport_player(x, y): Teleport player
   - etc.
   ```

2. **Backend logs show `use_tools=True`**:
   ```
   [SSE MODE] Calling LLM with session_id=..., use_tools=True
   ```

3. **Model supports function calling**:
   - Qwen2.5-Coder: ✅ Yes
   - Llama 3.1: ✅ Yes (if instruct-tuned)
   - Llama 2: ❌ No (use Llama 3+)

---

## 📊 Performance Benchmarks

### Expected Latencies (32B Q4_K_M on RTX 4090)

| Metric | Time |
|--------|------|
| State publish → Hint request | ~50ms |
| LLM processing (simple hint) | 2-4 seconds |
| LLM processing (with tools) | 3-6 seconds |
| Total (publish → hint received) | 3-7 seconds |

**If much slower**:
- Check GPU utilization: `nvidia-smi`
- Check CPU is not bottleneck
- Consider smaller model

---

## 🔍 Debugging Commands

### Check Backend Process
```bash
# Linux
ps aux | grep uvicorn

# Windows PowerShell
Get-Process | Where-Object {$_.ProcessName -like "*python*"}
```

### Check SSH Tunnel
```bash
# Linux/Mac
ps aux | grep ssh | grep 8080

# Windows PowerShell
Get-Process | Where-Object {$_.ProcessName -eq "ssh"}
```

### Test Backend API
```bash
# Health check
curl http://localhost:3000/api/health

# Test hint generation (requires auth token)
curl -X POST http://localhost:3000/api/mqtt/publish_state \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "template_id": 1,
    "state": {
      "player_pos": [1, 1],
      "exit_pos": [9, 9],
      "visible_map": [[1,1,1],[1,0,1],[1,1,1]]
    }
  }'

# Check last hint
curl "http://localhost:3000/api/mqtt/last_hint?session_id=test-session"
```

### Monitor Backend Logs
```bash
# Real-time log monitoring
tail -f /path/to/backend.log | grep "SSE MODE"

# Or if running in terminal, just watch the output
```

### Check llama.cpp Server
```bash
# Health check
curl http://localhost:8080/health

# Get model info
curl http://localhost:8080/v1/models

# Check load (if supported)
curl http://localhost:8080/stats
```

---

## 📈 Success Criteria

### ✅ Fix is working if:
1. Backend logs show `[SSE MODE] Auto-generating hint` messages
2. Hints appear in frontend LAM Details panel
3. Hints update every 3-5 seconds during gameplay
4. LAM provides pathfinding guidance
5. No "Failed to generate hint" errors
6. Game is playable in LAM mode

### ❌ Fix is NOT working if:
1. No `[SSE MODE]` messages in logs
2. Hints don't appear in frontend
3. Constant "Failed to generate hint" errors
4. Game hangs or crashes in LAM mode

---

## 🆘 Getting Help

### Collect This Info Before Asking:

1. **Backend Logs** (last 50 lines):
   ```bash
   tail -n 50 /path/to/backend.log
   ```

2. **Configuration**:
   ```bash
   cat backend/.env | grep LLM
   ```

3. **Connectivity Tests**:
   ```bash
   curl http://localhost:8080/health
   curl http://localhost:3000/api/health
   ```

4. **Browser Console** (F12 in Chrome/Firefox):
   - Any red error messages
   - Network tab showing failed requests

5. **System Info**:
   - OS version
   - Python version: `python --version`
   - GPU: `nvidia-smi` (if applicable)

---

## 📚 Related Documentation

- **MAZE_GAME_SSE_FIX_SUMMARY.md**: Detailed explanation of the fix
- **COMPLETE_SSE_IMPLEMENTATION.md**: Full SSE mode documentation
- **TWO_MACHINE_SETUP.md**: Setup guide for 2-machine deployment
- **SSE_MODE_DEPLOYMENT.md**: Complete deployment guide

---

**Last Updated**: 2025-11-09  
**Fix Version**: 1.0  
**Status**: ✅ Ready for Testing

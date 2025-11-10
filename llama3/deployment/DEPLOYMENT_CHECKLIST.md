# Machine B Deployment Checklist

## 📋 Quick Deployment Checklist

Follow these steps in order on **Machine B** (the web server with public IP):

---

## Prerequisites ✅

- [ ] **Machine A** (GPU server) is running llama.cpp on port 8080
- [ ] **SSH tunnel** from Machine A to Machine B is active and working
- [ ] You have **Python 3.8+** installed on Machine B
- [ ] You have **sudo/admin** access on Machine B

---

## Step 1: Verify SSH Tunnel (5 minutes)

On **Machine B**, run:

```bash
# Test that llama.cpp is accessible via tunnel
curl http://localhost:8080/health
```

**Expected output:**
```json
{"status":"ok","slots_idle":8,"slots_processing":0}
```

❌ **If it fails:** Go to Machine A and restart the SSH tunnel:
```bash
# On Machine A
ssh -R 8080:localhost:8080 user@machine-b-ip -N
```

---

## Step 2: Install Dependencies (3 minutes)

On **Machine B**:

```bash
# Install required Python packages
pip install fastapi uvicorn httpx python-dotenv pydantic

# Or use requirements.txt if available
pip install -r requirements.txt
```

---

## Step 3: Configure Environment (2 minutes)

On **Machine B**, create configuration file:

```bash
# Navigate to project
cd /path/to/llama3/deployment

# Create .env file
cat > .env << 'EOF'
LLAMA_BASE_URL=http://127.0.0.1:8080
DEFAULT_MODEL=qwen3-30b-a3b-instruct
API_KEYS=sk-local-abc
EOF
```

Or manually create `deployment/.env` with:
```ini
LLAMA_BASE_URL=http://127.0.0.1:8080
DEFAULT_MODEL=qwen3-30b-a3b-instruct
API_KEYS=sk-local-abc
```

---

## Step 4: Start the Proxy Server (2 minutes)

On **Machine B**:

### Option A: Quick Test (Foreground)
```bash
cd /path/to/llama3
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000
```

### Option B: Background with Screen (Recommended)
```bash
# Start in screen session
screen -S proxy

# Run the server
cd /path/to/llama3
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000

# Press Ctrl+A, then D to detach
# Reattach later with: screen -r proxy
```

### Option C: Using PowerShell Script (Windows)
```powershell
cd Z:\llama3_20250528\llama3
.\deployment\run_openai_proxy.ps1
```

---

## Step 5: Configure Firewall (2 minutes)

On **Machine B**:

### Linux (Ubuntu/Debian)
```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

### Linux (CentOS/RHEL)
```bash
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

### Windows (PowerShell as Admin)
```powershell
New-NetFirewallRule -DisplayName "OpenAI Proxy" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

---

## Step 6: Verify Deployment (3 minutes)

On **Machine B**, run these tests:

### Test 1: Proxy is running
```bash
curl http://localhost:8000
```
**Expected:** `{"status":"ok","upstream":"http://127.0.0.1:8080"}`

### Test 2: Models endpoint
```bash
curl http://localhost:8000/v1/models
```
**Expected:** JSON with model list

### Test 3: Chat completion
```bash
curl -H "Authorization: Bearer sk-local-abc" \
     -H "Content-Type: application/json" \
     -d '{"model":"qwen3-30b-a3b-instruct","messages":[{"role":"user","content":"Say hi"}]}' \
     http://localhost:8000/v1/chat/completions
```
**Expected:** JSON with AI response

### Test 4: External access
```bash
# From another machine or Machine C
curl http://MACHINE-B-IP:8000
```
**Expected:** `{"status":"ok",...}`

---

## Step 7: Test from Machine C (5 minutes)

On **Machine C** (your client machine):

```bash
# Set configuration
export TEST_BASE_URL="http://MACHINE-B-IP:8000/v1"
export TEST_API_KEY="sk-local-abc"

# Run test script
cd /path/to/llama3
python deployment/test_openai_proxy.py
```

**Expected output:**
```
✓ Proxy server is reachable
✓ Available models: qwen3-30b-a3b-instruct
✓ Chat response: pong
✓ Streaming completed successfully

✓ All tests passed! Machine C can successfully access the LLM.
```

---

## 🎉 Success Criteria

You're done when all these work:

- ✅ `curl http://localhost:8080/health` works (tunnel OK)
- ✅ `curl http://localhost:8000` works (proxy OK)
- ✅ `curl http://MACHINE-B-IP:8000` works (firewall OK)
- ✅ `python deployment/test_openai_proxy.py` passes all tests (end-to-end OK)

---

## 🔧 Common Issues

| Problem | Solution |
|---------|----------|
| **Connection refused on :8080** | Restart SSH tunnel on Machine A |
| **Port 8000 already in use** | Kill existing process or use different port |
| **Can't access from outside** | Check firewall rules |
| **401 Unauthorized** | Check API_KEY matches in .env |
| **Module not found** | Run `pip install -r requirements.txt` |

---

## 📊 What's Running on Machine B

After successful deployment:

```
┌──────────────────────────────────────────┐
│         Machine B (Web Server)           │
│                                          │
│  ┌────────────────────────────────────┐ │
│  │  OpenAI Proxy Server                │ │
│  │  Port: 8000                         │ │
│  │  Accepts: HTTP from anywhere        │ │
│  │  Forwards to: localhost:8080        │ │
│  └────────────────────────────────────┘ │
│                  ↓                       │
│  ┌────────────────────────────────────┐ │
│  │  SSH Tunnel Endpoint                │ │
│  │  Port: 8080 (localhost only)        │ │
│  │  Connected to: Machine A            │ │
│  └────────────────────────────────────┘ │
└──────────────────────────────────────────┘
               ↑
          Port 8000
               ↑
        Machine C (Clients)
```

---

## 🔄 Managing the Service

### Check Status
```bash
# See if proxy is running
ps aux | grep uvicorn

# Check port
netstat -tlnp | grep 8000
```

### Stop Service
```bash
# If running in screen
screen -r proxy
# Press Ctrl+C

# If running as process
pkill -f "uvicorn deployment.openai_compat_server"
```

### Restart Service
```bash
# Reattach to screen and Ctrl+C, then start again
screen -r proxy

# Or kill and restart
pkill -f "uvicorn deployment.openai_compat_server"
screen -S proxy
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000
```

### View Logs
```bash
# If running in screen
screen -r proxy

# If using systemd
sudo journalctl -u openai-proxy -f
```

---

## ⏱️ Total Time Estimate

- Prerequisites verification: **5 minutes**
- Install dependencies: **3 minutes**
- Configure environment: **2 minutes**
- Start proxy server: **2 minutes**
- Configure firewall: **2 minutes**
- Verify deployment: **3 minutes**
- Test from Machine C: **5 minutes**

**Total: ~20-25 minutes** for first-time setup

---

## 📚 Next Steps

After successful deployment:

1. **Bookmark these URLs:**
   - Proxy health: `http://MACHINE-B-IP:8000`
   - API endpoint: `http://MACHINE-B-IP:8000/v1/chat/completions`

2. **Save your configuration:**
   - Machine B IP address
   - API key: `sk-local-abc`
   - Model name: `qwen3-30b-a3b-instruct`

3. **Set up production features** (optional):
   - HTTPS with Nginx + Let's Encrypt
   - Systemd service for auto-start
   - Monitoring and logging
   - Rate limiting

4. **Use from your applications:**
   ```python
   from openai import OpenAI
   client = OpenAI(
       api_key="sk-local-abc",
       base_url="http://MACHINE-B-IP:8000/v1"
   )
   ```

---

## 📞 Support

If you encounter issues:

1. Check this checklist again ✅
2. Review `MACHINE_B_DEPLOYMENT.md` for detailed explanations
3. Run `python deployment/test_openai_proxy.py` for diagnostics
4. Check logs on Machine B: `screen -r proxy`

---

**Last Updated:** 2025-11-10  
**Deployment Type:** OpenAI-Compatible Proxy (SSE Mode)  
**Recommended for:** Remote client access from Machine C

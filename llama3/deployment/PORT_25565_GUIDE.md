# Using Port 25565 - Quick Reference

## Why Port 25565?

Port 25565 is the default Minecraft server port, so it's often already allowed through firewalls and networks. Great choice for easier accessibility!

---

## 🚀 Machine B Setup (Port 25565)

### Start the Proxy Server

**Option 1: Using PowerShell Script (Windows)**
```powershell
cd Z:\llama3_20250528\llama3
.\deployment\run_openai_proxy.ps1
# Default port is now 25565
```

**Option 2: Direct Command**
```bash
cd /path/to/llama3
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 25565
```

**Option 3: Background with Screen (Linux)**
```bash
screen -S proxy
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 25565
# Press Ctrl+A, D to detach
```

### Configure Firewall

**Linux (Ubuntu/Debian)**
```bash
sudo ufw allow 25565/tcp
sudo ufw status
```

**Linux (CentOS/RHEL)**
```bash
sudo firewall-cmd --permanent --add-port=25565/tcp
sudo firewall-cmd --reload
```

**Windows (PowerShell as Admin)**
```powershell
New-NetFirewallRule -DisplayName "LLM Proxy" -Direction Inbound -LocalPort 25565 -Protocol TCP -Action Allow
```

### Verify Deployment

```bash
# Test locally on Machine B
curl http://localhost:25565
# Should return: {"status":"ok","upstream":"http://127.0.0.1:8080"}

# Test from outside
curl http://MACHINE-B-IP:25565
```

---

## 🖥️ Machine C Setup (Port 25565)

### Configure Environment

**Windows PowerShell**
```powershell
$env:TEST_BASE_URL="http://173.61.35.162:25565/v1"
$env:TEST_API_KEY="sk-local-abc"
```

**Linux/macOS**
```bash
export TEST_BASE_URL="http://173.61.35.162:25565/v1"
export TEST_API_KEY="sk-local-abc"
```

### Run Test

```bash
python deployment/test_openai_proxy.py
```

### Use in Your Code

```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-local-abc",
    base_url="http://173.61.35.162:25565/v1"
)

response = client.chat.completions.create(
    model="qwen3-30b-a3b-instruct",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

---

## 🔧 Systemd Service (Linux) - Port 25565

Create `/etc/systemd/system/openai-proxy.service`:

```ini
[Unit]
Description=OpenAI Compatible Proxy on Port 25565
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/llama3
Environment="LLAMA_BASE_URL=http://127.0.0.1:8080"
Environment="DEFAULT_MODEL=qwen3-30b-a3b-instruct"
Environment="API_KEYS=sk-local-abc"
ExecStart=/usr/bin/uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 25565
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
```

---

## 📊 Port Configuration Summary

| Component | Port | Address | Purpose |
|-----------|------|---------|---------|
| llama.cpp (Machine A) | 8080 | 0.0.0.0 | LLM server |
| SSH Tunnel (Machine B) | 8080 | localhost | Tunnel endpoint |
| OpenAI Proxy (Machine B) | **25565** | 0.0.0.0 | **Public API** |

---

## 🧪 Quick Test Commands

```bash
# On Machine B - Test tunnel
curl http://localhost:8080/health

# On Machine B - Test proxy
curl http://localhost:25565

# From Machine C - Test connectivity
curl http://173.61.35.162:25565

# From Machine C - Full test
python deployment/test_openai_proxy.py
```

---

## ⚡ Benefits of Port 25565

1. **Firewall Friendly**: Often already open for Minecraft
2. **Network Friendly**: Less likely to be blocked by ISPs
3. **Memorable**: Easy to remember (Minecraft port)
4. **No Conflicts**: Unlikely to clash with other services

---

## 🔄 Switching from Port 8000 to 25565

If you had services running on port 8000:

1. **Stop old service:**
   ```bash
   pkill -f "uvicorn.*:8000"
   ```

2. **Start on new port:**
   ```bash
   uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 25565
   ```

3. **Update firewall:**
   ```bash
   sudo ufw allow 25565/tcp
   sudo ufw delete allow 8000/tcp  # Optional: remove old rule
   ```

4. **Update clients:**
   ```bash
   # Update BASE_URL everywhere from :8000 to :25565
   ```

---

## 🎯 Complete Setup Example

```bash
# === On Machine B ===

# 1. Verify tunnel
curl http://localhost:8080/health

# 2. Start proxy on port 25565
screen -S proxy
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 25565
# Ctrl+A, D to detach

# 3. Configure firewall
sudo ufw allow 25565/tcp

# 4. Test
curl http://localhost:25565


# === On Machine C ===

# 1. Set configuration
export TEST_BASE_URL="http://MACHINE-B-IP:25565/v1"
export TEST_API_KEY="sk-local-abc"

# 2. Test
python deployment/test_openai_proxy.py
```

---

## 📝 URLs to Use

- **Health check**: `http://MACHINE-B-IP:25565`
- **API base URL**: `http://MACHINE-B-IP:25565/v1`
- **Chat endpoint**: `http://MACHINE-B-IP:25565/v1/chat/completions`
- **Models endpoint**: `http://MACHINE-B-IP:25565/v1/models`

---

## ✅ Success Indicators

When properly configured on port 25565:

```
✓ curl http://localhost:8080/health → llama.cpp responds
✓ curl http://localhost:25565 → proxy responds
✓ curl http://MACHINE-B-IP:25565 → accessible from outside
✓ python test_openai_proxy.py → all tests pass
```

---

**Note**: The default BASE_URL in `test_openai_proxy.py` is now set to port 25565, so it will work out of the box!

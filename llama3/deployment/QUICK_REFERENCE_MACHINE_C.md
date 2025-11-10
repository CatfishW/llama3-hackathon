# Quick Reference: Machine C Remote Access

## 🚀 Quick Start (5 Minutes)

### 1. Install Dependencies (Machine C)
```bash
pip install openai httpx
```

### 2. Configure Environment (Machine C)
```bash
# Windows PowerShell
$env:TEST_BASE_URL="http://YOUR-MACHINE-B-IP:8000/v1"
$env:TEST_API_KEY="sk-local-abc"

# Linux/macOS
export TEST_BASE_URL="http://YOUR-MACHINE-B-IP:8000/v1"
export TEST_API_KEY="sk-local-abc"
```

### 3. Test Connection (Machine C)
```bash
python deployment/test_openai_proxy.py
```

### 4. Use in Your Code (Machine C)
```python
from openai import OpenAI

client = OpenAI(
    api_key="sk-local-abc",
    base_url="http://YOUR-MACHINE-B-IP:8000/v1"
)

response = client.chat.completions.create(
    model="qwen3-30b-a3b-instruct",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

---

## 📋 Pre-Flight Checklist

### Machine A (GPU Server) ☑️
- [ ] llama.cpp server running on port 8080
- [ ] SSH tunnel active to Machine B
  ```bash
  screen -r llama  # Check llama.cpp
  screen -r tunnel # Check SSH tunnel
  ```

### Machine B (Web Server) ☑️
- [ ] Proxy server running on port 8000
  ```bash
  ps aux | grep uvicorn
  ```
- [ ] SSH tunnel receiving connection
  ```bash
  netstat -tlnp | grep 8080
  curl http://localhost:8080/health
  ```
- [ ] Port 8000 open in firewall
  ```bash
  sudo ufw allow 8000/tcp
  ```

### Machine C (Your Machine) ☑️
- [ ] Python 3.8+ installed
- [ ] OpenAI library installed
- [ ] Environment variables configured
- [ ] Network access to Machine B

---

## 🔧 Common Issues & Fixes

| Error | Quick Fix |
|-------|-----------|
| **Connection refused** | Check proxy is running on Machine B:<br>`uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000` |
| **Timeout** | Check firewall on Machine B:<br>`sudo ufw allow 8000/tcp` |
| **401 Unauthorized** | API key mismatch. Check Machine B:<br>`cat deployment/.env \| grep API_KEYS` |
| **502 Bad Gateway** | SSH tunnel down. Restart on Machine A:<br>`ssh -R 8080:localhost:8080 user@machine-b -N` |
| **Model not found** | Check model name matches Machine B config |

---

## 📊 Architecture Diagram

```
Machine C (Client)
    ↓ HTTP Request to :8000
Machine B (Proxy)
    ↓ Forward to localhost:8080
SSH Tunnel
    ↓ Forward to Machine A
Machine A (llama.cpp)
    ↓ Process & Return
SSH Tunnel
    ↓ Return response
Machine B (Proxy)
    ↓ Return to client
Machine C (Client)
```

---

## 🔗 URLs to Know

| URL | Purpose | Location |
|-----|---------|----------|
| `http://localhost:8080/health` | Check llama.cpp | Machine A |
| `http://localhost:8080/health` | Check SSH tunnel | Machine B |
| `http://localhost:8000` | Check proxy server | Machine B |
| `http://MACHINE-B-IP:8000/v1` | Client base URL | Machine C |

---

## 📝 Environment Variables

```bash
# Required
TEST_BASE_URL=http://MACHINE-B-IP:8000/v1
TEST_API_KEY=sk-local-abc

# Optional
TEST_MODEL=qwen3-30b-a3b-instruct
```

---

## 🧪 Test Commands

```bash
# Test from Machine C
python deployment/test_openai_proxy.py

# Quick HTTP test
curl http://MACHINE-B-IP:8000

# Test with custom URL
TEST_BASE_URL=http://custom-ip:8000/v1 python deployment/test_openai_proxy.py
```

---

## 📚 Documentation Files

- `MACHINE_C_SETUP.md` - Complete setup guide (this file)
- `SSE_MODE_DEPLOYMENT.md` - Full deployment architecture
- `openai_compat_readme.md` - Proxy server documentation
- `test_openai_proxy.py` - Test script with diagnostics

---

## 🎯 Success Criteria

When everything is working, you should see:

```
✓ Proxy server is reachable
✓ Available models: qwen3-30b-a3b-instruct
✓ Chat response: pong
✓ Streaming completed successfully

✓ All tests passed! Machine C can successfully access the LLM.
```

---

## 💡 Pro Tips

1. **Save connection details**: Create a `.env` file on Machine C
2. **Use domain names**: Point a domain to Machine B for stable URLs
3. **Enable HTTPS**: Use Nginx + Let's Encrypt for secure connections
4. **Monitor logs**: Check `app.log` on Machine B for debugging
5. **Keep tunnels alive**: Use systemd service for SSH tunnel on Machine A

---

## 🆘 Getting Help

1. Run test script: `python deployment/test_openai_proxy.py`
2. Check the "Troubleshooting" section in output
3. Verify all checklist items above
4. Review full documentation in `MACHINE_C_SETUP.md`

---

**Last Updated**: 2025-11-10  
**Compatible with**: llama.cpp SSE mode deployment

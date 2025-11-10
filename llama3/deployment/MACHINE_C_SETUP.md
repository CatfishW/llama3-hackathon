# Machine C Setup Guide - Remote LLM Access

## Overview

This guide helps you set up **Machine C** (a remote client machine) to access the LLM running on **Machine A** (GPU server) via **Machine B** (web server with proxy).

## Architecture

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│  Machine C  │         │  Machine B  │         │  Machine A  │
│   (Client)  │ ──────> │   (Proxy)   │ ──────> │ (LLM Server)│
│             │  HTTP   │             │  Tunnel │   4090 GPU  │
│ Your Laptop │  :8000  │  Public IP  │  :8080  │  No Pub IP  │
└─────────────┘         └─────────────┘         └─────────────┘
                             │                        │
                             │    SSH Tunnel          │
                             │ <──────────────────────┘
                             │   ssh -R 8080:localhost:8080
```

### Data Flow

1. **Machine C** sends OpenAI-compatible request to **Machine B**:
   - `http://machine-b-ip:8000/v1/chat/completions`

2. **Machine B** proxy forwards to local tunnel endpoint:
   - `http://localhost:8080/chat/completions`

3. **SSH tunnel** forwards to **Machine A**:
   - `http://localhost:8080/chat/completions` (on Machine A)

4. **Machine A** llama.cpp processes request and returns response

## Prerequisites

### On Machine A (GPU Server)
✅ llama.cpp server running on port 8080
✅ SSH tunnel established to Machine B

### On Machine B (Web Server)
✅ OpenAI-compatible proxy server running on port 8000
✅ Port 8000 accessible from internet/network (firewall configured)
✅ SSH tunnel receiving connection from Machine A

### On Machine C (Your Machine)
- Python 3.8 or higher
- Internet/network access to Machine B
- OpenAI Python library

## Setup Instructions

### Step 1: Install Dependencies on Machine C

```bash
# Install OpenAI library
pip install openai httpx

# Or if you have the requirements.txt
pip install -r requirements.txt
```

### Step 2: Verify Machine B Configuration

Before testing from Machine C, ensure Machine B is properly configured:

#### Check SSH Tunnel (on Machine B)

```bash
# Check if port 8080 is listening (tunnel endpoint)
netstat -tlnp | grep 8080
# Should show: 127.0.0.1:8080

# Test llama.cpp is accessible via tunnel
curl http://localhost:8080/health
# Should return JSON like: {"status":"ok","slots_idle":8}
```

#### Check Proxy Server (on Machine B)

```bash
# Check if proxy is running on port 8000
netstat -tlnp | grep 8000
# Should show: 0.0.0.0:8000

# Test proxy is responding
curl http://localhost:8000
# Should return: {"status":"ok","upstream":"http://127.0.0.1:8080"}
```

#### Check Firewall (on Machine B)

```bash
# Allow port 8000 for incoming connections
# On Ubuntu/Debian:
sudo ufw allow 8000/tcp

# On CentOS/RHEL:
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload

# Verify port is accessible from outside
# From Machine C or another machine:
curl http://machine-b-ip:8000
```

### Step 3: Configure Environment Variables (on Machine C)

Create a `.env` file or set environment variables:

```bash
# Windows PowerShell
$env:TEST_BASE_URL="http://173.61.35.162:8000/v1"  # Replace with your Machine B IP
$env:TEST_API_KEY="sk-local-abc"                   # Match proxy server API_KEYS
$env:TEST_MODEL="qwen3-30b-a3b-instruct"           # Your model name

# Windows Command Prompt
set TEST_BASE_URL=http://173.61.35.162:8000/v1
set TEST_API_KEY=sk-local-abc
set TEST_MODEL=qwen3-30b-a3b-instruct

# Linux/macOS
export TEST_BASE_URL="http://173.61.35.162:8000/v1"
export TEST_API_KEY="sk-local-abc"
export TEST_MODEL="qwen3-30b-a3b-instruct"
```

**Important Configuration Notes:**

1. **BASE_URL**: Must point to Machine B's public IP or domain
   - Format: `http://[Machine-B-IP]:8000/v1`
   - Example: `http://173.61.35.162:8000/v1`
   - If using domain: `http://yourdomain.com:8000/v1`

2. **API_KEY**: Must match one of the keys in Machine B's proxy `.env`
   - Check Machine B: `cat ~/prompt-portal/deployment/.env | grep API_KEYS`
   - Default: `sk-local-abc`

3. **MODEL**: Must match the model name configured on Machine B
   - Check Machine B: `cat ~/prompt-portal/deployment/.env | grep DEFAULT_MODEL`

### Step 4: Run the Test Script

```bash
# Navigate to the project directory
cd /path/to/llama3

# Run the test script
python deployment/test_openai_proxy.py
```

Expected output:

```
OpenAI library version: 1.x.x

============================================================
OpenAI Proxy Test Configuration
============================================================
Base URL: http://173.61.35.162:8000/v1
Model: qwen3-30b-a3b-instruct
API Key: sk-local-a...
============================================================

============================================================
OpenAI Proxy Integration Test Suite
============================================================
Testing connection to proxy server...
✓ Proxy server is reachable
  Response: {'status': 'ok', 'upstream': 'http://127.0.0.1:8080'}

Testing /v1/models endpoint...
✓ Available models:
  - qwen3-30b-a3b-instruct

Testing chat completion (non-streaming)...
✓ Chat response: pong

Testing chat completion (streaming)...
Response: AI proxies forward requests between clients and AI servers.
✓ Streaming completed successfully

============================================================
Test Summary
============================================================
Connection           ✓ PASS
Models List          ✓ PASS
Chat Completion      ✓ PASS
Streaming            ✓ PASS
============================================================

✓ All tests passed! Machine C can successfully access the LLM.
```

## Using in Your Application

Once the test passes, you can use the OpenAI client in any Python application:

```python
from openai import OpenAI

# Configure client
client = OpenAI(
    api_key="sk-local-abc",
    base_url="http://173.61.35.162:8000/v1"  # Machine B
)

# Non-streaming request
response = client.chat.completions.create(
    model="qwen3-30b-a3b-instruct",
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "What is quantum computing?"}
    ],
    temperature=0.7,
    max_tokens=500
)
print(response.choices[0].message.content)

# Streaming request
stream = client.chat.completions.create(
    model="qwen3-30b-a3b-instruct",
    messages=[
        {"role": "user", "content": "Explain AI in simple terms"}
    ],
    stream=True,
    max_tokens=300
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
print()
```

## Troubleshooting

### Error: Connection Refused

```
✗ Cannot reach proxy server: [Errno 111] Connection refused
```

**Solutions:**
1. Verify Machine B proxy is running:
   ```bash
   # On Machine B
   ps aux | grep uvicorn
   # Should show: uvicorn deployment.openai_compat_server:app
   ```

2. Check firewall on Machine B:
   ```bash
   sudo ufw status
   # Should show: 8000/tcp ALLOW
   ```

3. Test from Machine B itself:
   ```bash
   curl http://localhost:8000
   ```

4. Verify BASE_URL is correct

### Error: Timeout

```
✗ Cannot reach proxy server: Read timeout
```

**Solutions:**
1. Check network connectivity to Machine B
2. Increase timeout in test script
3. Check if Machine B is under heavy load
4. Verify SSH tunnel is active on Machine B

### Error: Invalid API Key

```
✗ Chat completion failed: 401 Unauthorized
```

**Solutions:**
1. Check API_KEY matches Machine B configuration:
   ```bash
   # On Machine B
   cat ~/prompt-portal/deployment/.env | grep API_KEYS
   ```

2. Update TEST_API_KEY to match

### Error: llama.cpp Not Responding

```
✗ Chat completion failed: 502 Bad Gateway
```

**Solutions:**
1. Check SSH tunnel on Machine B:
   ```bash
   netstat -tlnp | grep 8080
   curl http://localhost:8080/health
   ```

2. If tunnel is down, restart on Machine A:
   ```bash
   ssh -R 8080:localhost:8080 user@machine-b-ip -N
   ```

3. Check llama.cpp is running on Machine A:
   ```bash
   ps aux | grep llama-server
   curl http://localhost:8080/health
   ```

### Error: Model Not Found

```
✗ Chat completion failed: Model not found
```

**Solutions:**
1. List available models:
   ```python
   models = client.models.list()
   for model in models.data:
       print(model.id)
   ```

2. Update TEST_MODEL to match an available model

## Performance Optimization

### 1. Network Latency
- Use a VPN or direct network connection if available
- Consider deploying the proxy server closer to Machine C
- Enable compression in SSH tunnel: `ssh -C -R ...`

### 2. Concurrent Requests
```python
import asyncio
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key="sk-local-abc",
    base_url="http://173.61.35.162:8000/v1"
)

async def concurrent_requests():
    tasks = [
        client.chat.completions.create(
            model="qwen3-30b-a3b-instruct",
            messages=[{"role": "user", "content": f"Question {i}"}]
        )
        for i in range(5)
    ]
    responses = await asyncio.gather(*tasks)
    return responses

# Run
results = asyncio.run(concurrent_requests())
```

### 3. Connection Pooling
```python
import httpx

# Reuse connections
http_client = httpx.Client(
    timeout=300.0,
    limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
)

client = OpenAI(
    api_key="sk-local-abc",
    base_url="http://173.61.35.162:8000/v1",
    http_client=http_client
)
```

## Security Considerations

1. **Use HTTPS in Production**
   - Set up Nginx with SSL on Machine B
   - Use Let's Encrypt for free SSL certificates
   - Update BASE_URL to `https://yourdomain.com:8000/v1`

2. **Strong API Keys**
   ```bash
   # Generate strong API key
   python -c "import secrets; print(f'sk-{secrets.token_urlsafe(32)}')"
   ```

3. **IP Whitelisting**
   - Configure firewall on Machine B to allow only specific IPs
   - Use VPN for secure access

4. **Rate Limiting**
   - Add rate limiting to the proxy server
   - Monitor usage and set quotas

## Integration with Frontend

If you're building a web application on Machine C:

```javascript
// JavaScript/Node.js
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: 'sk-local-abc',
  baseURL: 'http://173.61.35.162:8000/v1',
});

async function chat(message) {
  const response = await openai.chat.completions.create({
    model: 'qwen3-30b-a3b-instruct',
    messages: [{ role: 'user', content: message }],
    stream: true,
  });

  for await (const chunk of response) {
    if (chunk.choices[0].delta.content) {
      process.stdout.write(chunk.choices[0].delta.content);
    }
  }
}

chat('Hello, AI!');
```

## Summary

Machine C (your client) can now:
- ✅ Connect to Machine B's proxy server via HTTP
- ✅ Send OpenAI-compatible requests
- ✅ Receive responses from the LLM on Machine A
- ✅ Use streaming for real-time responses
- ✅ Integrate with any OpenAI SDK-compatible application

The entire setup provides:
- **Transparency**: Use standard OpenAI SDK without modifications
- **Security**: SSH tunnel encrypts Machine A ↔ Machine B communication
- **Flexibility**: Machine C can be anywhere with internet access
- **Performance**: Direct HTTP connection with minimal overhead
- **Scalability**: Add more clients (Machine D, E, F) easily

## Next Steps

1. **Production Deployment**: Set up HTTPS with Nginx on Machine B
2. **Monitoring**: Add logging and metrics collection
3. **Load Balancing**: Connect multiple GPU servers if needed
4. **Caching**: Implement response caching for common queries
5. **Authentication**: Integrate with OAuth or JWT for user management

For more details, see:
- `SSE_MODE_DEPLOYMENT.md` - Complete deployment architecture
- `openai_compat_readme.md` - Proxy server documentation
- `deployment/openai_compat_server.py` - Proxy server source code

# LLM Integration - Quick Reference

## 🎯 What's New

The Prompt Portal now has **direct LLM integration** using OpenAI-compatible APIs! This means:

- ✅ **Direct HTTP API** for LLM inference (no MQTT required for basic chat)
- ✅ **Session management** with automatic conversation history
- ✅ **MQTT support** still works and now uses the same LLM backend
- ✅ **Compatible** with llama.cpp, vLLM, OpenAI API, and more

## 🚀 Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure LLM Server

Edit `backend/.env`:

```bash
LLM_SERVER_URL=http://localhost:8080  # Your llama.cpp server
```

### 3. Start LLM Server

**Option A: llama.cpp server**
```bash
llama-server -m ./your-model.gguf --port 8080
```

**Option B: Use MQTT deployment (includes prompt_portal support)**
```bash
python llamacpp_mqtt_deploy.py --projects prompt_portal
```

### 4. Start Backend

```bash
cd backend
python run_server.py
```

### 5. Test It

```bash
# Health check
curl http://localhost:8000/api/llm/health

# Chat (replace YOUR_TOKEN with actual JWT)
curl -X POST http://localhost:8000/api/llm/chat \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

## 📚 Documentation

- **[LLM_INTEGRATION_GUIDE.md](LLM_INTEGRATION_GUIDE.md)** - Complete usage guide
- **[LLM_INTEGRATION_SUMMARY.md](LLM_INTEGRATION_SUMMARY.md)** - Technical summary

## 🔌 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/llm/chat` | POST | Single-shot completion |
| `/api/llm/chat/session` | POST | Session-based chat |
| `/api/llm/chat/session/{id}/history` | GET | Get conversation history |
| `/api/llm/chat/session/{id}` | DELETE | Clear session |
| `/api/llm/health` | GET | Check LLM service status |

## 💻 Frontend Usage

```typescript
import { llmAPI } from './api'

// Simple chat
const response = await llmAPI.chat([
  { role: 'user', content: 'What is AI?' }
])

// Session-based chat (maintains history)
const sessionResp = await llmAPI.sessionChat('my_session', 'Hello!', {
  system_prompt: 'You are a helpful assistant.'
})

// Get history
const history = await llmAPI.getSessionHistory('my_session')

// Clear session
await llmAPI.clearSession('my_session')
```

## 🔧 Configuration

Key environment variables in `backend/.env`:

```bash
# LLM Server
LLM_SERVER_URL=http://localhost:8080
LLM_TIMEOUT=300

# Generation Parameters
LLM_TEMPERATURE=0.6
LLM_TOP_P=0.9
LLM_MAX_TOKENS=512
LLM_SKIP_THINKING=True

# Session Management
LLM_MAX_HISTORY_TOKENS=10000
```

## 🎮 Use Cases

### 1. Template Testing
Test how different prompts affect LLM behavior:
```typescript
const response = await llmAPI.sessionChat('test', 'Hello!', {
  system_prompt: 'You are a pirate. Speak like a pirate.'
})
```

### 2. Chatbot
Build conversational interfaces:
```typescript
const sessionId = 'chat_' + Date.now()
await llmAPI.sessionChat(sessionId, 'Tell me about Python')
await llmAPI.sessionChat(sessionId, 'What about lists?')
// History is maintained automatically
```

### 3. Game AI
Integrate with games (like the maze):
```typescript
const hint = await llmAPI.sessionChat(`game_${gameId}`, 
  JSON.stringify(gameState),
  { system_prompt: 'You are a maze guide...' }
)
```

## 🆚 HTTP vs MQTT

| Feature | HTTP API | MQTT |
|---------|----------|------|
| **Setup** | ✅ Easy | ⚠️ More complex |
| **Use Case** | Web UI, Testing | Real-time games |
| **Latency** | ~200ms | ~100ms |
| **Session Mgmt** | ✅ Built-in | ⚠️ Manual |

Both methods now use the **same LLM backend**!

## 🐛 Troubleshooting

### "LLM service not initialized"
→ Check `LLM_SERVER_URL` in `.env` and ensure server is running

### "Connection test failed"
→ Test: `curl http://localhost:8080/health`

### Slow responses
→ Set `LLM_SKIP_THINKING=True` for faster responses

## 📦 What Was Added

### Backend
- `app/services/llm_client.py` - LLM service
- `app/routers/llm.py` - API endpoints
- Configuration in `app/config.py`
- Initialization in `app/main.py`

### Frontend
- `llmAPI` methods in `src/api.ts`

### MQTT
- `prompt_portal` project support in `llamacpp_mqtt_deploy.py`
- LLM processing function in `app/mqtt.py`

### Docs
- `LLM_INTEGRATION_GUIDE.md` - Complete guide
- `LLM_INTEGRATION_SUMMARY.md` - Technical details
- `LLM_INTEGRATION_README.md` - This file

## ✅ Compatibility

- ✅ **Backward compatible** - Existing code still works
- ✅ **No breaking changes** - Old MQTT flow preserved
- ✅ **Gradual adoption** - Use new features when ready

## 🎯 Next Steps

1. Read the [Integration Guide](LLM_INTEGRATION_GUIDE.md)
2. Configure your `.env` file
3. Start your LLM server
4. Test the API endpoints
5. Integrate into your frontend

## 💡 Examples

See `LLM_INTEGRATION_GUIDE.md` for:
- Python backend examples
- TypeScript frontend examples
- Error handling patterns
- Performance tips
- Security considerations

## 🤝 Support

- Check health endpoint: `GET /api/llm/health`
- Review logs in backend console
- See troubleshooting section in Integration Guide
- Check MQTT deployment logs if using that option

---

**Ready to start?** Run `./setup_llm.sh` (Linux/Mac) or `setup_llm.bat` (Windows) for automated setup!

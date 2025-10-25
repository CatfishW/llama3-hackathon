# LLM Integration Guide

## Overview

The Prompt Portal now supports direct LLM inference through both HTTP API and MQTT. This integration allows you to:

1. **Direct HTTP API**: Send prompts and get responses via REST endpoints
2. **MQTT Bridge**: Continue using MQTT for real-time game interactions
3. **Unified Backend**: Both methods use the same LLM service (llama.cpp, vLLM, etc.)

## Architecture

```
┌─────────────────┐         ┌──────────────────┐         ┌──────────────────┐
│   Frontend      │         │   Backend        │         │   LLM Server     │
│   (Browser)     │◄───────►│   (FastAPI)      │◄───────►│  (llama.cpp)     │
└─────────────────┘         └──────────────────┘         └──────────────────┘
        │                            │
        │                            │
        │         HTTP API           │
        ├────────────────────────────┤
        │   • /api/llm/chat          │
        │   • /api/llm/chat/session  │
        │   • /api/llm/health        │
        └────────────────────────────┘
                     │
                     │ Also supports
                     ▼
              ┌─────────────┐
              │    MQTT     │
              │   Bridge    │
              └─────────────┘
```

## Configuration

### Backend Configuration

Update `backend/.env`:

```bash
# LLM Server Configuration
LLM_SERVER_URL=http://localhost:8080    # Your llama.cpp server URL
LLM_TIMEOUT=300                          # Request timeout in seconds
LLM_TEMPERATURE=0.6                      # Default sampling temperature
LLM_TOP_P=0.9                           # Default top-p sampling
LLM_MAX_TOKENS=512                      # Default max tokens
LLM_SKIP_THINKING=True                  # Disable thinking mode for faster responses
LLM_MAX_HISTORY_TOKENS=10000           # Max conversation history
```

### Starting the LLM Server

#### Option 1: llama.cpp Server

```bash
# Start llama.cpp server
llama-server -m ./your-model.gguf --port 8080 --host 0.0.0.0

# Or with specific context size
llama-server -m ./your-model.gguf --port 8080 --ctx-size 4096
```

#### Option 2: Use llamacpp_mqtt_deploy.py

The existing MQTT deployment script now supports the `prompt_portal` project:

```bash
cd z:\llama3_20250528\llama3

# For prompt portal only
python llamacpp_mqtt_deploy.py --projects prompt_portal

# For multiple projects including prompt portal
python llamacpp_mqtt_deploy.py --projects "maze driving prompt_portal"

# With custom server URL
python llamacpp_mqtt_deploy.py --projects prompt_portal --server_url http://192.168.1.100:8080
```

## Backend API Usage

### 1. Single-Shot Chat (Stateless)

Send a one-time prompt without maintaining conversation history:

```python
import requests

response = requests.post('http://localhost:8000/api/llm/chat', 
    json={
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ],
        "temperature": 0.7,
        "max_tokens": 100
    },
    headers={"Authorization": f"Bearer {token}"}
)

result = response.json()
print(result['response'])
```

### 2. Session-Based Chat (Stateful)

Maintain conversation history across multiple requests:

```python
import requests

# First message in session
response = requests.post('http://localhost:8000/api/llm/chat/session',
    json={
        "session_id": "my_session_123",
        "message": "Hello, my name is Alice",
        "system_prompt": "You are a friendly assistant."
    },
    headers={"Authorization": f"Bearer {token}"}
)

# Follow-up message (remembers previous context)
response = requests.post('http://localhost:8000/api/llm/chat/session',
    json={
        "session_id": "my_session_123",
        "message": "What's my name?"
    },
    headers={"Authorization": f"Bearer {token}"}
)

result = response.json()
print(result['response'])  # Will remember "Alice"
```

### 3. Get Session History

```python
response = requests.get('http://localhost:8000/api/llm/chat/session/my_session_123/history',
    headers={"Authorization": f"Bearer {token}"}
)

history = response.json()
for msg in history['messages']:
    print(f"{msg['role']}: {msg['content']}")
```

### 4. Clear Session

```python
response = requests.delete('http://localhost:8000/api/llm/chat/session/my_session_123',
    headers={"Authorization": f"Bearer {token}"}
)
```

### 5. Health Check

```python
response = requests.get('http://localhost:8000/api/llm/health')
status = response.json()
print(f"LLM Server: {status['server_url']}")
print(f"Status: {status['status']}")
```

## Frontend Integration

The frontend now has LLM API methods in `src/api.ts`:

```typescript
import { llmAPI } from './api'

// Single-shot chat
const response = await llmAPI.chat([
  { role: 'system', content: 'You are helpful.' },
  { role: 'user', content: 'Hello!' }
])

// Session-based chat
const sessionResponse = await llmAPI.sessionChat('session_123', 'Hello!', {
  system_prompt: 'You are helpful.'
})

// Get session history
const history = await llmAPI.getSessionHistory('session_123')

// Clear session
await llmAPI.clearSession('session_123')

// Health check
const health = await llmAPI.health()
```

## MQTT Integration

The MQTT bridge now uses the same LLM backend. When a message arrives on MQTT topics, it can be processed through the LLM service.

### Publishing to MQTT with LLM Processing

The backend can process MQTT messages through the LLM:

```python
from app.mqtt import process_user_input_with_llm

# Process user input through LLM
response = process_user_input_with_llm(
    session_id="maze_session_123",
    user_message="I'm stuck in the maze!",
    system_prompt="You are a maze guide..."
)

# Response is automatically formatted and can be published back via MQTT
```

## Example Use Cases

### 1. Template Testing

Test how a prompt template affects LLM behavior:

```typescript
// Test a template
const template = "You are a pirate. Respond in pirate speak."
const response = await llmAPI.sessionChat('test_123', 'Hello!', {
  system_prompt: template
})
console.log(response.data.response)  // "Ahoy there, matey!"
```

### 2. Interactive Chatbot

Build a chatbot that maintains context:

```typescript
const sessionId = `chat_${Date.now()}`

// Start conversation
await llmAPI.sessionChat(sessionId, 'Hi, I need help with Python', {
  system_prompt: 'You are a Python programming tutor.'
})

// Continue conversation
await llmAPI.sessionChat(sessionId, 'How do I create a list?')
await llmAPI.sessionChat(sessionId, 'Can you show an example?')

// Review history
const history = await llmAPI.getSessionHistory(sessionId)
```

### 3. Game AI Integration

Use LLM for in-game AI hints (like the maze game):

```typescript
const gameState = {
  player_pos: [5, 7],
  exit_pos: [20, 15],
  obstacles: [[6, 7], [5, 8]]
}

const response = await llmAPI.sessionChat(`game_${gameId}`, 
  JSON.stringify(gameState), 
  {
    system_prompt: 'You are a maze guide. Analyze the game state and provide hints in JSON format.'
  }
)

const hint = JSON.parse(response.data.response)
console.log(hint.hint)
```

## Error Handling

### Service Unavailable

If the LLM server is not running, the API returns 503:

```typescript
try {
  await llmAPI.chat([...])
} catch (error) {
  if (error.response?.status === 503) {
    console.log('LLM service is not available. Please start the server.')
  }
}
```

### Check Server Health

```typescript
const health = await llmAPI.health()
if (health.data.status === 'ok') {
  console.log('LLM service is ready')
} else {
  console.log('LLM service is not ready')
}
```

## Performance Considerations

1. **Session Management**: Sessions are kept in memory. Clear old sessions to free memory.
2. **Rate Limiting**: Consider implementing rate limits for production use.
3. **Timeouts**: Default timeout is 300 seconds. Adjust in config for longer/shorter waits.
4. **Concurrent Requests**: The service uses threading but has a semaphore limit (8 concurrent).
5. **Token Limits**: Messages are trimmed to last 20 messages to avoid context overflow.

## Comparison: HTTP vs MQTT

| Feature | HTTP API | MQTT |
|---------|----------|------|
| **Latency** | ~100-500ms | ~50-200ms |
| **Use Case** | Web UI, Testing | Real-time games |
| **Session Management** | Built-in | Manual |
| **Scalability** | Good | Excellent |
| **Debugging** | Easy (REST tools) | Harder |
| **Integration** | Simple | Requires MQTT client |

## Troubleshooting

### "LLM service not initialized"

- Make sure the backend is running and LLM_SERVER_URL is configured
- Check logs for initialization errors
- Verify the LLM server is accessible

### "Connection test failed"

- Ensure llama.cpp server is running on the configured URL
- Check firewall settings
- Test connectivity: `curl http://localhost:8080/health`

### "Generation timeout"

- Increase LLM_TIMEOUT in config
- Check LLM server resources (CPU/GPU)
- Reduce max_tokens or context size

### Slow Responses

- Enable LLM_SKIP_THINKING=True for faster responses
- Reduce max_tokens
- Use a smaller model
- Check server load

## Migration from Pure MQTT

If you were using pure MQTT before, you can now:

1. **Keep using MQTT** - It still works and now uses the unified LLM backend
2. **Switch to HTTP** - For easier debugging and development
3. **Use both** - MQTT for games, HTTP for testing/UI

The backend will handle both simultaneously.

## Next Steps

1. **Install dependencies**: `cd backend && pip install -r requirements.txt`
2. **Configure environment**: Copy `.env.example` to `.env` and set LLM_SERVER_URL
3. **Start LLM server**: Run llama-server or llamacpp_mqtt_deploy.py
4. **Start backend**: `python run_server.py` or `uvicorn app.main:app`
5. **Test health endpoint**: `curl http://localhost:8000/api/llm/health`
6. **Try frontend integration**: Use `llmAPI` methods in your components

## Additional Resources

- [OpenAI API Documentation](https://platform.openai.com/docs/api-reference)
- [llama.cpp Server Documentation](https://github.com/ggerganov/llama.cpp/blob/master/examples/server/README.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)

# Streaming Support - Quick Reference

## Backend Streaming Methods

### Python (llamacpp_mqtt_deploy.py)
```python
# Use generate_stream() instead of generate()
for chunk in client.generate_stream(messages):
    print(chunk, end='', flush=True)
```

### Web Backend (Python/FastAPI)
```python
from app.services.llm_client import get_llm_client

llm_client = get_llm_client()
for chunk in llm_client.generate_stream(messages):
    yield f"data: {json.dumps({'content': chunk})}\n\n"
```

## API Endpoints

### Streaming Chat (Stateless)
```
POST /api/llm/chat/stream
Content-Type: application/json

{
  "messages": [{"role": "user", "content": "Hello"}],
  "temperature": 0.7,
  "max_tokens": 512
}

Response: text/event-stream
data: {"content": "Hello"}
data: {"content": " there!"}
data: {"done": true}
```

### Streaming Session Chat
```
POST /api/llm/chat/session/stream
Content-Type: application/json

{
  "session_id": "my-session-123",
  "message": "Tell me a story",
  "temperature": 0.8
}

Response: text/event-stream
data: {"content": "Once", "session_id": "my-session-123"}
data: {"content": " upon", "session_id": "my-session-123"}
data: {"done": true, "session_id": "my-session-123"}
```

## Frontend Usage (TypeScript/React)

```typescript
import { llmAPI } from './api'

// Streaming session chat
const [response, setResponse] = useState('')

llmAPI.chatSessionStream(
  { 
    session_id: 'session-123',
    message: 'Hello!',
    temperature: 0.7 
  },
  (chunk) => setResponse(prev => prev + chunk),  // onChunk
  () => console.log('Done!'),                     // onComplete
  (error) => console.error(error)                 // onError
)
```

## Key Features

✅ Real-time token-by-token responses  
✅ Better user experience with immediate feedback  
✅ Session-based conversation support  
✅ Server-Sent Events (SSE) for web  
✅ Automatic error handling  
✅ Compatible with existing non-streaming code  

## Compatibility

| Feature | Streaming | Non-Streaming |
|---------|-----------|---------------|
| Chat completion | ✅ | ✅ |
| Session management | ✅ | ✅ |
| Function calling | ⚠️ Limited | ✅ Full |
| MQTT support | ⚠️ Complex | ✅ Simple |
| Web interface | ✅ Best | ✅ Works |

⚠️ **Note**: Use non-streaming for function calling and MQTT applications.

## Testing

```bash
# Test streaming endpoint
curl -N -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://localhost:8000/api/llm/chat/stream \
  -d '{"messages": [{"role": "user", "content": "Hi"}]}'
```

See STREAMING_SUPPORT.md for complete documentation.

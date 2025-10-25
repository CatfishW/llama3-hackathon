# Streaming Support Documentation

This document explains how to use the streaming functionality added to the llama.cpp MQTT deployment and web application.

## Overview

Streaming allows real-time token-by-token responses from the LLM, providing a better user experience with immediate feedback instead of waiting for the complete response.

## Architecture

### 1. Main Deployment Script (`llamacpp_mqtt_deploy.py`)

The `LlamaCppClient` class now includes a `generate_stream()` method that yields text chunks as they arrive from the LLM server.

```python
def generate_stream(
    self,
    messages: List[Dict[str, str]],
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    debug_info: dict = None,
    tools: Optional[List[Dict]] = None,
    tool_choice: Optional[str] = None
) -> Iterator[str]:
    """Generate response using streaming for real-time output."""
    # ...implementation yields chunks as they arrive
```

### 2. Web Backend (`prompt-portal/backend`)

#### LLM Client Service (`app/services/llm_client.py`)

Two new streaming methods added:

1. **`LLMClient.generate_stream()`** - Core streaming method
2. **`SessionManager.process_message_stream()`** - Session-aware streaming

```python
def generate_stream(
    self,
    messages: List[Dict[str, str]],
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model: str = "default",
    tools: Optional[List[Dict]] = None,
    tool_choice: Optional[str] = "auto"
):
    """Generate response using streaming for real-time output."""
    # Yields chunks as they arrive
```

#### API Router (`app/routers/llm.py`)

Two new streaming endpoints using Server-Sent Events (SSE):

1. **`POST /api/llm/chat/stream`** - Stateless streaming chat
2. **`POST /api/llm/chat/session/stream`** - Session-based streaming chat

Both endpoints return `text/event-stream` responses with:
- `data: {"content": "chunk"}` - Text chunks
- `data: {"done": true}` - Completion signal
- `data: {"error": "message"}` - Error messages

### 3. Web Frontend (`prompt-portal/frontend`)

#### API Client (`src/api.ts`)

The `llmAPI` object now includes streaming methods:

```typescript
llmAPI.chatStream(
  data: { messages, temperature, top_p, max_tokens },
  onChunk: (chunk: string) => void,
  onComplete: () => void,
  onError: (error: any) => void
)

llmAPI.chatSessionStream(
  data: { session_id, message, system_prompt, ... },
  onChunk: (chunk: string) => void,
  onComplete: () => void,
  onError: (error: any) => void
)
```

## Usage Examples

### Example 1: Using Streaming in Python (MQTT Script)

```python
# In your message processor or custom client code
client = LlamaCppClient(config)

messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Tell me about AI."}
]

# Stream the response
for chunk in client.generate_stream(messages):
    print(chunk, end='', flush=True)
```

### Example 2: Using Streaming in Web Frontend (React/TypeScript)

```typescript
import { llmAPI } from './api'

// In your React component
const [response, setResponse] = useState('')
const [isStreaming, setIsStreaming] = useState(false)

const sendMessage = async (message: string) => {
  setIsStreaming(true)
  setResponse('')
  
  await llmAPI.chatSessionStream(
    {
      session_id: 'my-session-123',
      message: message,
      temperature: 0.7,
      max_tokens: 512
    },
    // onChunk - called for each token
    (chunk) => {
      setResponse(prev => prev + chunk)
    },
    // onComplete - called when done
    () => {
      setIsStreaming(false)
      console.log('Streaming complete!')
    },
    // onError - called on errors
    (error) => {
      setIsStreaming(false)
      console.error('Streaming error:', error)
    }
  )
}
```

### Example 3: Using Streaming via FastAPI Backend

```python
from fastapi import FastAPI, Depends
from fastapi.responses import StreamingResponse
from app.services.llm_client import get_llm_client

app = FastAPI()

@app.post("/custom/stream")
async def custom_stream_endpoint(
    request: ChatRequest,
    user = Depends(get_current_user)
):
    llm_client = get_llm_client()
    
    def generate():
        for chunk in llm_client.generate_stream(
            messages=request.messages,
            temperature=request.temperature
        ):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )
```

## Important Notes

### 1. Function Calling / Tools with Streaming

⚠️ **Warning**: Streaming with function calling (tools) is complex because:
- Tool calls are typically returned at the end of the response
- The model needs to complete thinking before deciding on tools
- Streaming tool calls would require special handling

**Recommendation**: Use non-streaming `generate()` method when using tools/function calling.

### 2. MQTT Streaming

The MQTT deployment script includes streaming support, but consider:
- MQTT has message size limits
- Chunking responses over MQTT may require special handling on the client side
- For MQTT, the non-streaming approach may be more reliable

### 3. Performance Considerations

- **Streaming** is better for:
  - User-facing chat interfaces
  - Long responses where immediate feedback is valuable
  - Interactive applications

- **Non-streaming** is better for:
  - Function calling / tool use
  - Batch processing
  - Scenarios where full response is needed before processing

### 4. Error Handling

Always implement proper error handling:
- Network interruptions during streaming
- Server errors mid-stream
- Timeouts
- Client disconnections

## Testing Streaming

### Test the Web Backend

```bash
# Start the backend server
cd prompt-portal/backend
python run_server.py

# Test streaming endpoint with curl
curl -N -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST http://localhost:8000/api/llm/chat/stream \
  -d '{
    "messages": [
      {"role": "user", "content": "Write a short poem"}
    ]
  }'
```

### Test the Main Deployment Script

```python
# test_streaming.py
from llamacpp_mqtt_deploy import LlamaCppClient, DeploymentConfig

config = DeploymentConfig(server_url="http://localhost:8080")
client = LlamaCppClient(config)

messages = [
    {"role": "user", "content": "Count from 1 to 10 slowly"}
]

print("Streaming response:")
for chunk in client.generate_stream(messages):
    print(chunk, end='', flush=True)
print("\n\nDone!")
```

## Configuration

### Backend Configuration

Set these in `prompt-portal/backend/.env`:

```env
LLM_SERVER_URL=http://localhost:8080
LLM_TIMEOUT=300
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=512
```

### Frontend Configuration

Set these in `prompt-portal/frontend/.env`:

```env
VITE_API_BASE=http://localhost:8000
```

## Troubleshooting

### Issue: Streaming stops mid-response

**Causes**:
- LLM server timeout
- Network interruption
- Reverse proxy buffering (nginx)

**Solutions**:
- Increase timeout settings
- Add `X-Accel-Buffering: no` header (already included)
- Check nginx configuration if using reverse proxy

### Issue: Chunks arrive all at once

**Causes**:
- Response buffering by intermediate proxies
- Browser/client buffering

**Solutions**:
- Ensure Server-Sent Events headers are set correctly
- Disable buffering at all proxy levels
- Use HTTP/1.1 (HTTP/2 may cause buffering issues)

### Issue: CORS errors in browser

**Solutions**:
- Configure CORS properly in FastAPI:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],  # Adjust for production
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

## Future Enhancements

Potential improvements for streaming support:

1. **WebSocket Support**: Alternative to SSE for bidirectional communication
2. **Streaming with Function Calling**: Special handling for tool calls during streaming
3. **Progress Indicators**: Token count, estimated completion time
4. **Streaming History**: Save and replay streaming responses
5. **Rate Limiting**: Throttle streaming for better server resource management

## References

- [OpenAI Streaming Documentation](https://platform.openai.com/docs/api-reference/streaming)
- [Server-Sent Events (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [FastAPI StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)

# Backend Integration Guide - TAB Completion SSE

## Overview

The frontend now uses Server-Sent Events (SSE) via HTTP POST for TAB completion instead of MQTT. This guide shows how to implement the required backend endpoint.

## Required Endpoint

```
POST /api/completion/generate
```

## Request Format

```json
{
  "text": "The quick brown",
  "completion_type": "general",
  "temperature": 0.7,
  "top_p": 0.9,
  "max_tokens": 100
}
```

### Request Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | string | ✅ Yes | The input text to complete |
| `completion_type` | string | ❌ No | Type of completion (see below) |
| `temperature` | float | ❌ No | Randomness (0.0-2.0), default 0.7 |
| `top_p` | float | ❌ No | Diversity (0.0-1.0), default 0.9 |
| `max_tokens` | int | ❌ No | Max tokens to generate, default 100 |

### Completion Types

```python
COMPLETION_TYPES = {
    'general': 'General text completion',
    'code': 'Code snippet completion',
    'prompt': 'LLM prompt completion',
    'message': 'Chat message completion',
    'search': 'Search query completion',
    'email': 'Email text completion',
    'description': 'Description/documentation completion'
}
```

## Response Format

Success (200 OK):
```json
{
  "completion": " fox jumps over the lazy dog",
  "timestamp": 1731205200
}
```

Error (400/500):
```json
{
  "error": "Error message",
  "timestamp": 1731205200
}
```

## Implementation Examples

### Python (FastAPI/Flask)

#### FastAPI Example:
```python
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional
import time
import asyncio

router = APIRouter(prefix="/api/completion", tags=["completion"])

class CompletionRequest(BaseModel):
    text: str
    completion_type: Optional[str] = 'general'
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9
    max_tokens: Optional[int] = 100

class CompletionResponse(BaseModel):
    completion: str
    timestamp: int
    error: Optional[str] = None

@router.post("/generate")
async def generate_completion(request: CompletionRequest) -> CompletionResponse:
    """
    Generate text completion using the local LLM.
    """
    try:
        # Validate input
        if not request.text or not request.text.strip():
            raise HTTPException(status_code=400, detail="Empty input text")
        
        if len(request.text) > 10000:
            raise HTTPException(status_code=400, detail="Input text too long")
        
        # Call your LLM
        completion = await call_llm(
            text=request.text,
            completion_type=request.completion_type,
            temperature=request.temperature,
            top_p=request.top_p,
            max_tokens=request.max_tokens
        )
        
        return CompletionResponse(
            completion=completion,
            timestamp=int(time.time())
        )
    
    except HTTPException:
        raise
    except Exception as e:
        return CompletionResponse(
            completion="",
            error=str(e),
            timestamp=int(time.time())
        )

async def call_llm(
    text: str,
    completion_type: str = 'general',
    temperature: float = 0.7,
    top_p: float = 0.9,
    max_tokens: int = 100
) -> str:
    """
    Call your LLM backend.
    Adjust this based on your actual LLM setup.
    """
    # Example with llamacpp_httpserver
    import aiohttp
    
    try:
        # Construct prompt based on type
        prompts = {
            'code': "Complete this code:\n",
            'prompt': "Complete this prompt:\n",
            'message': "Complete this message:\n",
            'search': "Complete this search query:\n",
            'email': "Complete this email:\n",
            'description': "Complete this description:\n",
            'general': "Complete this text:\n"
        }
        
        full_prompt = prompts.get(completion_type, prompts['general']) + text
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                'http://localhost:8000/completion',
                json={
                    'prompt': full_prompt,
                    'temperature': temperature,
                    'top_p': top_p,
                    'n_predict': max_tokens
                }
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('content', '')
                else:
                    raise Exception(f"LLM returned {resp.status}")
    
    except Exception as e:
        print(f"LLM error: {e}")
        return ""
```

#### Flask Example:
```python
from flask import Blueprint, request, jsonify
from datetime import datetime
import time

completion_bp = Blueprint('completion', __name__, url_prefix='/api/completion')

@completion_bp.route('/generate', methods=['POST'])
def generate_completion():
    """Generate text completion"""
    try:
        data = request.get_json()
        
        # Validate
        if not data.get('text'):
            return jsonify({'error': 'Empty input text'}), 400
        
        text = data['text']
        completion_type = data.get('completion_type', 'general')
        temperature = data.get('temperature', 0.7)
        top_p = data.get('top_p', 0.9)
        max_tokens = data.get('max_tokens', 100)
        
        # Call LLM
        completion = call_llm_sync(
            text=text,
            completion_type=completion_type,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens
        )
        
        return jsonify({
            'completion': completion,
            'timestamp': int(time.time())
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'timestamp': int(time.time())
        }), 500

def call_llm_sync(text, completion_type, temperature, top_p, max_tokens):
    """Synchronous LLM call"""
    # Your LLM implementation here
    pass
```

### Node.js (Express)

```javascript
const express = require('express');
const router = express.Router();
const axios = require('axios');

router.post('/api/completion/generate', async (req, res) => {
  try {
    const {
      text,
      completion_type = 'general',
      temperature = 0.7,
      top_p = 0.9,
      max_tokens = 100
    } = req.body;

    // Validate input
    if (!text || !text.trim()) {
      return res.status(400).json({
        error: 'Empty input text',
        timestamp: Math.floor(Date.now() / 1000)
      });
    }

    // Call LLM
    const completion = await callLLM({
      text,
      completion_type,
      temperature,
      top_p,
      max_tokens
    });

    res.json({
      completion,
      timestamp: Math.floor(Date.now() / 1000)
    });

  } catch (error) {
    res.status(500).json({
      error: error.message,
      timestamp: Math.floor(Date.now() / 1000)
    });
  }
});

async function callLLM({ text, completion_type, temperature, top_p, max_tokens }) {
  try {
    // Example: llamacpp_httpserver
    const response = await axios.post('http://localhost:8000/completion', {
      prompt: text,
      temperature,
      top_p,
      n_predict: max_tokens
    });

    return response.data.content || '';
  } catch (error) {
    console.error('LLM error:', error.message);
    return '';
  }
}

module.exports = router;
```

## Integration with Existing LLM Backends

### llamacpp_httpserver
```python
# If using llamacpp_httpserver on port 8000
async def call_llm(text, completion_type, temperature, top_p, max_tokens):
    import aiohttp
    
    async with aiohttp.ClientSession() as session:
        async with session.post(
            'http://localhost:8000/completion',
            json={
                'prompt': text,
                'temperature': temperature,
                'top_p': top_p,
                'n_predict': max_tokens,
                'stop': ['\n', '###']
            }
        ) as resp:
            data = await resp.json()
            return data.get('content', '')
```

### OpenAI API
```python
import openai

async def call_llm(text, completion_type, temperature, top_p, max_tokens):
    response = await openai.ChatCompletion.acreate(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": text}],
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens
    )
    return response.choices[0].message.content
```

### Ollama
```python
import requests

def call_llm(text, completion_type, temperature, top_p, max_tokens):
    response = requests.post(
        'http://localhost:11434/api/generate',
        json={
            'model': 'llama2',
            'prompt': text,
            'temperature': temperature,
            'stream': False
        }
    )
    return response.json().get('response', '')
```

## CORS Configuration

Make sure your backend allows requests from your frontend:

### FastAPI:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Flask:
```python
from flask_cors import CORS

CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "https://yourdomain.com"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})
```

### Express:
```javascript
const cors = require('cors');

app.use(cors({
  origin: ['http://localhost:5173', 'https://yourdomain.com'],
  credentials: true
}));
```

## Authentication

The completion endpoint should check for valid authentication:

```python
# FastAPI example
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthCredentials

security = HTTPBearer()

@router.post("/generate")
async def generate_completion(
    request: CompletionRequest,
    credentials: HTTPAuthCredentials = Depends(security)
) -> CompletionResponse:
    """Requires Bearer token authentication"""
    # Verify token
    user = verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Process completion...
```

## Rate Limiting

Consider adding rate limiting to prevent abuse:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/generate")
@limiter.limit("30/minute")
async def generate_completion(request: Request, ...):
    """Allow 30 requests per minute per IP"""
    pass
```

## Error Handling

Always return proper error responses:

```python
{
  "error": "Description of what went wrong",
  "timestamp": 1731205200
}
```

Common errors:
- `"Empty input text"` - 400
- `"Input text too long"` - 400
- `"Invalid completion_type"` - 400
- `"LLM service unavailable"` - 503
- `"Unauthorized"` - 401

## Monitoring & Logging

Log completion requests for debugging:

```python
import logging

logger = logging.getLogger(__name__)

@router.post("/generate")
async def generate_completion(request: CompletionRequest):
    logger.info(
        f"Completion request: type={request.completion_type}, "
        f"tokens={request.max_tokens}, input_len={len(request.text)}"
    )
    
    start_time = time.time()
    result = await call_llm(...)
    duration = time.time() - start_time
    
    logger.info(f"Completion took {duration:.2f}s")
    
    return result
```

## Testing

Test your endpoint:

```bash
# Test with curl
curl -X POST http://localhost:5000/api/completion/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "text": "The quick brown",
    "completion_type": "general",
    "temperature": 0.7,
    "top_p": 0.9,
    "max_tokens": 50
  }'
```

## Performance Tuning

- **Max tokens**: Lower = faster but shorter responses
- **Temperature**: Higher = more creative but slower
- **Async/await**: Use for concurrent requests
- **Caching**: Cache common completions
- **Timeouts**: Set reasonable timeout (10-30s)

## Migration from MQTT

If you had MQTT completion before:

1. ❌ Remove MQTT completion handler
2. ✅ Add this HTTP endpoint
3. ✅ Update completion logic to use HTTP
4. ✅ Test with frontend

No other changes needed!

---

**Version:** 1.0 SSE  
**Last Updated:** November 10, 2025

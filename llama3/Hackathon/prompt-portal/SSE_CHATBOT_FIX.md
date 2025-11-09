# SSE Mode Chatbot Fix

## Problem
After deploying in SSE mode, the chatbot was returning 503 errors:
```
POST https://lammp.agaii.org/api/chatbot/messages 503 (Service Unavailable)
```

Even though the SSH tunnel and llama.cpp server were working correctly (curl tests passed).

## Root Cause

The `backend/app/routers/chatbot.py` was **hardcoded to use MQTT** and wasn't aware of SSE mode:

1. **MQTT Connection Check**: Always checked for MQTT connection, even in SSE mode
2. **MQTT Message Sending**: Only used `send_chat_message()` (MQTT function)
3. **No SSE Path**: Didn't use the LLM service for direct HTTP communication

## Solution

Updated `backend/app/routers/chatbot.py` to support both modes:

### 1. Mode-Aware Connection Check
```python
# Before (always checked MQTT)
from ..mqtt import mqtt_client
if not mqtt_client or not mqtt_client.is_connected():
    raise HTTPException(status_code=503, ...)

# After (checks only in MQTT mode)
from ..config import settings

if settings.LLM_COMM_MODE.lower() == "mqtt":
    from ..mqtt import mqtt_client
    if not mqtt_client or not mqtt_client.is_connected():
        raise HTTPException(status_code=503, ...)
```

### 2. Dual-Mode Message Sending

Added SSE mode path that uses the LLM service directly:

```python
if settings.LLM_COMM_MODE.lower() == "sse":
    # Use LLM service for direct HTTP communication
    from ..services.llm_service import get_llm_service
    llm_service = get_llm_service()
    
    assistant_content = llm_service.process_message(
        session_id=session.session_key,
        system_prompt=session.system_prompt or _default_prompt(),
        user_message=payload.content,
        temperature=effective_temperature,
        top_p=effective_top_p,
        max_tokens=effective_max_tokens,
        use_tools=False
    )
else:
    # MQTT mode (original behavior)
    response_payload = await send_chat_message(mqtt_payload, timeout=90.0)
```

### 3. Conditional Template Updates

System prompt updates now only publish to MQTT when in MQTT mode:

```python
if settings.LLM_COMM_MODE.lower() == "mqtt":
    if payload.system_prompt is not None:
        publish_template_update(session.session_key, payload.system_prompt)
# In SSE mode, system prompt is stored in session and used on next message
```

## Files Changed

- `backend/app/routers/chatbot.py` - Added SSE mode support

## Testing

### Verify the Fix

**1. Check backend configuration:**
```bash
cd backend
cat .env | grep LLM_COMM_MODE
# Should show: LLM_COMM_MODE=sse
```

**2. Restart backend:**
```bash
kill $(cat backend.pid)
nohup uvicorn app.main:app --host 0.0.0.0 --port 3000 > /dev/null 2>&1 &
echo $! > backend.pid
```

**3. Test via API:**
```bash
# Get auth token first
TOKEN=$(curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your-username","password":"your-password"}' \
  | jq -r .access_token)

# Create a chat session
SESSION=$(curl -X POST http://localhost:3000/api/chatbot/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"Test Chat"}' \
  | jq -r .id)

# Send a message
curl -X POST http://localhost:3000/api/chatbot/messages \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d "{\"session_id\":$SESSION,\"content\":\"Hello!\"}"
```

**4. Test via web interface:**
- Open https://lammp.agaii.org
- Login
- Go to chatbot
- Send a message
- Should receive response from LLM!

## How It Works Now

### SSE Mode Flow:
```
Frontend → Backend API → LLM Service → llama.cpp (via SSH tunnel)
                                        ↓
Frontend ← Backend API ← Response ← llama.cpp
```

### MQTT Mode Flow (unchanged):
```
Frontend → Backend API → MQTT Broker → LLM Deployment
                              ↓
Frontend ← Backend API ← MQTT Broker ← LLM Deployment
```

## Benefits

- ✅ Chatbot works in both MQTT and SSE modes
- ✅ No code duplication (reuses LLM service)
- ✅ Graceful mode detection
- ✅ Clear error messages
- ✅ Backward compatible with MQTT mode

## Notes

- The chatbot now automatically detects the communication mode from `LLM_COMM_MODE` environment variable
- In SSE mode, conversations are managed by the session manager in `llm_client.py`
- In MQTT mode, conversations are managed by `llamacpp_mqtt_deploy.py`
- Both modes maintain conversation history and context

## Troubleshooting

If chatbot still doesn't work:

1. **Check logs:**
   ```bash
   tail -f backend/app.log
   ```

2. **Verify LLM connection:**
   ```bash
   curl http://localhost:8080/health
   ```

3. **Check environment:**
   ```bash
   cat backend/.env | grep LLM
   ```

4. **Restart backend:**
   ```bash
   cd backend
   pkill -f "uvicorn.*app.main"
   uvicorn app.main:app --host 0.0.0.0 --port 3000
   ```

## Summary

The chatbot now fully supports SSE mode! Messages are sent directly to llama.cpp via the SSH tunnel, bypassing the need for an MQTT broker. The fix maintains backward compatibility with MQTT mode while adding seamless SSE support.

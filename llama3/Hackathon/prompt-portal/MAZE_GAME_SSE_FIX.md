# Maze Game SSE Mode Fix

## 🐛 Issue Description

The maze game LLM communication was not working in SSE mode. Hints were not being generated or displayed correctly when using direct HTTP communication with llama.cpp.

## 🔍 Root Cause

The issue was in the response format handling in `/api/mqtt/request_hint` endpoint when running in SSE mode.

### The Problem

When function calling is enabled (`use_tools=True`), the `llm_client.generate()` method returns different formats:

**Without function calls:**
```python
"Here's a hint: move north to reach the exit."
```

**With function calls:**
```json
{
  "hint": "I'll break the wall blocking your path",
  "function_calls": [
    {
      "name": "break_wall",
      "arguments": {"x": 3, "y": 5}
    }
  ]
}
```

The issue: When function calls are present, the response is a **JSON string**, not a plain string. But the code was storing it directly without parsing:

```python
# ❌ BEFORE - Stores JSON string instead of parsed object
LAST_HINTS[session_id] = {
    "hint": hint_response,  # Could be '{"hint": "...", "function_calls": [...]}'
    "timestamp": time.time()
}
```

This caused the frontend to receive malformed data.

## ✅ Solution

Parse the response to detect JSON format and store it as a proper dictionary:

```python
# ✅ AFTER - Parse JSON if present
hint_data = hint_response
try:
    parsed = json.loads(hint_response)
    if isinstance(parsed, dict):
        hint_data = parsed
except (json.JSONDecodeError, TypeError):
    # Response is plain text, use as-is
    hint_data = {"hint": hint_response}

# Ensure hint_data is always a dict
if not isinstance(hint_data, dict):
    hint_data = {"hint": str(hint_data)}

# Store with timestamp
hint_data["timestamp"] = time.time()
LAST_HINTS[session_id] = hint_data
```

## 📊 Expected Formats

### MQTT Mode (Working)
The LAM service sends hints through MQTT with this format:
```json
{
  "hint": "Move north towards the goal",
  "suggestion": "Avoid the germs on the left",
  "function_calls": [...],
  "timestamp": 1704067200.5
}
```

### SSE Mode (Now Fixed)
The llama.cpp server returns:

**Plain text response:**
```json
{
  "hint": "Move north towards the goal",
  "timestamp": 1704067200.5
}
```

**With function calling:**
```json
{
  "hint": "I'll help by breaking the wall",
  "function_calls": [
    {
      "name": "break_wall",
      "arguments": {"x": 3, "y": 5}
    }
  ],
  "timestamp": 1704067200.5
}
```

Both formats are now stored consistently in `LAST_HINTS` dictionary.

## 🧪 Testing

### Test 1: Basic Hint Request
```bash
curl -X POST "http://localhost:3000/api/mqtt/request_hint" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "maze-test-123",
    "state": {
      "playerPosition": [0, 0],
      "goal": [5, 5],
      "walls": [[1, 1], [2, 2]]
    }
  }'
```

**Expected Response (SSE mode):**
```json
{
  "ok": true,
  "session_id": "maze-test-123",
  "hint": {
    "hint": "Move east to avoid the wall at (1,1)",
    "timestamp": 1704067200.5
  },
  "mode": "sse"
}
```

### Test 2: Poll for Hint
```bash
curl "http://localhost:3000/api/mqtt/last_hint?session_id=maze-test-123" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Expected Response:**
```json
{
  "session_id": "maze-test-123",
  "last_hint": {
    "hint": "Move east to avoid the wall at (1,1)",
    "timestamp": 1704067200.5
  },
  "has_hint": true,
  "timestamp": 1704067200.5
}
```

### Test 3: With Function Calling
```bash
curl -X POST "http://localhost:3000/api/mqtt/request_hint" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "maze-test-456",
    "state": {
      "playerPosition": [2, 2],
      "goal": [5, 5],
      "walls": [[3, 2], [3, 3]],
      "breaksRemaining": 2
    }
  }'
```

**Expected Response:**
```json
{
  "ok": true,
  "session_id": "maze-test-456",
  "hint": {
    "hint": "I'll break the wall blocking your path",
    "function_calls": [
      {
        "name": "break_wall",
        "arguments": {"x": 3, "y": 2}
      }
    ],
    "timestamp": 1704067200.5
  },
  "mode": "sse"
}
```

## 🔧 Code Changes

### File: `backend/app/routers/mqtt_bridge.py`

**Location:** `/request_hint` endpoint, SSE mode branch

**Before:**
```python
hint_response = llm_service.process_message(...)

LAST_HINTS[session_id] = {
    "hint": hint_response,
    "timestamp": time.time()
}

await ws.send_json({"hint": hint_response, "session_id": session_id})

return {"ok": True, "session_id": session_id, "hint": hint_response, "mode": "sse"}
```

**After:**
```python
hint_response = llm_service.process_message(...)

# Parse response if it's JSON (happens when function calling is used)
hint_data = hint_response
try:
    parsed = json.loads(hint_response)
    if isinstance(parsed, dict):
        hint_data = parsed
except (json.JSONDecodeError, TypeError):
    hint_data = {"hint": hint_response}

if not isinstance(hint_data, dict):
    hint_data = {"hint": str(hint_data)}

hint_data["timestamp"] = time.time()
LAST_HINTS[session_id] = hint_data

await ws.send_json({"hint": hint_data, "session_id": session_id})

return {"ok": True, "session_id": session_id, "hint": hint_data, "mode": "sse"}
```

## 🎮 Impact on Maze Game

### Before Fix
- ❌ Hints not displaying in SSE mode
- ❌ Function calls not being parsed
- ❌ Frontend receiving malformed data
- ❌ WebSocket messages corrupted

### After Fix
- ✅ Hints display correctly in SSE mode
- ✅ Function calls properly parsed and stored
- ✅ Frontend receives properly formatted data
- ✅ WebSocket messages work correctly
- ✅ Consistent format between MQTT and SSE modes

## 🧩 Related Components

### Backend Components
- **mqtt_bridge.py**: Fixed response parsing in SSE mode
- **llm_client.py**: Returns JSON string when function calling is used
- **llm_service.py**: Wrapper that calls llm_client

### Frontend Components (No changes needed)
- Maze game UI expects hint format: `{ hint: string, function_calls?: [] }`
- Polling and WebSocket code unchanged
- Works with both MQTT and SSE modes transparently

## 📝 Lessons Learned

### 1. Always Parse API Responses
When an API can return different formats (plain text vs JSON), always check and parse appropriately:

```python
# Good pattern
try:
    parsed = json.loads(response)
    if isinstance(parsed, dict):
        data = parsed
except json.JSONDecodeError:
    data = {"content": response}
```

### 2. Consistent Data Structures
Ensure data stored in shared state (like `LAST_HINTS`) has consistent structure regardless of source:

```python
# Always store as dict with standard keys
{
  "hint": "...",
  "timestamp": 123456.789,
  "function_calls": [...]  # Optional
}
```

### 3. Test Both Modes
When implementing dual-mode support, test both MQTT and SSE paths:
- MQTT mode: Data comes pre-parsed from message broker
- SSE mode: Data comes as raw string from HTTP response

### 4. Handle Edge Cases
```python
# Handle all possible response types
if isinstance(data, dict):
    # Already parsed
elif isinstance(data, str):
    try:
        data = json.loads(data)
    except:
        data = {"hint": data}
else:
    data = {"hint": str(data)}
```

## 🚀 Next Steps

### Immediate
- ✅ Fix applied and tested
- ✅ Documentation updated

### Future Improvements
1. Add response schema validation
2. Add unit tests for both response formats
3. Add integration tests for maze game in both modes
4. Consider adding TypeScript types for hint format

## 📚 Related Documentation

- **[MAZE_GAME_SSE_SUPPORT.md](./MAZE_GAME_SSE_SUPPORT.md)** - Complete maze game SSE implementation
- **[DUAL_MODE_QUICK_REFERENCE.md](./DUAL_MODE_QUICK_REFERENCE.md)** - Dual mode configuration
- **[COMPLETE_SSE_IMPLEMENTATION.md](./COMPLETE_SSE_IMPLEMENTATION.md)** - Full SSE implementation details

## ✅ Summary

**Issue:** Maze game hints not working in SSE mode  
**Cause:** JSON response from function calling not being parsed  
**Fix:** Parse JSON response and store as dictionary  
**Status:** ✅ **FIXED**

The maze game now works correctly in both MQTT and SSE modes with proper function calling support!

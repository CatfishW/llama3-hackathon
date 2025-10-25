# Web Integration Update - MQTT State Messages

## Changes Made

### Problem
The web game was publishing to `maze/state` but `llamacpp_mqtt_deploy.py` only subscribed to `maze/user_input`, causing messages to not be received.

### Solution
Updated `llamacpp_mqtt_deploy.py` to support **dual message types**:

1. **User Input Messages** - Chat-style text messages on `{project}/user_input`
2. **State Messages** - Game state JSON on `{project}/state` (maze only)

## Files Modified

### 1. `llamacpp_mqtt_deploy.py`

**Added to ProjectConfig:**
```python
@dataclass
class ProjectConfig:
    name: str
    user_topic: str
    response_topic: str
    system_prompt: str
    enabled: bool = True
    state_topic: str = None      # NEW: For game state messages
    hint_topic: str = None        # NEW: For hint responses
```

**Updated subscription logic:**
- Now subscribes to both `user_topic` AND `state_topic` (if configured)
- Maze project automatically gets both subscriptions

**Enhanced message handling:**
- Detects message type (user input vs state)
- Converts state JSON to structured description
- Routes responses to correct topic (`hint` or `assistant_response`)

**New method:**
```python
def _convert_state_to_message(self, state: dict, project_name: str) -> str:
    """Convert game state dict to descriptive user message."""
    # Extracts: player_pos, exit_pos, visible_map, germs, oxygen
    # Returns: JSON string for LLM processing
```

### 2. `backend/app/config.py`

**Added settings:**
```python
MQTT_TOPIC_USER_INPUT: str = "prompt_portal/user_input"
MQTT_TOPIC_ASSISTANT_RESPONSE: str = "prompt_portal/assistant_response"
```

### 3. `backend/.env.example`

**Added:**
```bash
MQTT_USERNAME=TangClinic
MQTT_PASSWORD=Tang123
MQTT_TOPIC_TEMPLATE=maze/template
MQTT_TOPIC_USER_INPUT=prompt_portal/user_input
MQTT_TOPIC_ASSISTANT_RESPONSE=prompt_portal/assistant_response
```

## How It Works Now

### Maze Game Flow

```
┌─────────────────────────────────────────────────────────────┐
│                     WebGame.tsx                             │
│  User plays maze → Publishes game state                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓ POST /api/mqtt/publish_state
┌─────────────────────────────────────────────────────────────┐
│                Backend FastAPI                              │
│  • Adds template content to state                          │
│  • Publishes to MQTT: maze/state                           │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓ MQTT: maze/state
┌─────────────────────────────────────────────────────────────┐
│            llamacpp_mqtt_deploy.py                          │
│  1. Receives on maze/state                                 │
│  2. Identifies as STATE message                            │
│  3. Converts state to structured description               │
│  4. Processes with LLM                                     │
│  5. Publishes to: maze/hint/{sessionId}                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓ MQTT: maze/hint/{sessionId}
┌─────────────────────────────────────────────────────────────┐
│                Backend MQTT Client                          │
│  • Subscribes to maze/hint/+                               │
│  • Receives hint response                                  │
│  • Pushes via WebSocket to frontend                        │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ↓ WebSocket
┌─────────────────────────────────────────────────────────────┐
│                     WebGame.tsx                             │
│  Displays hint/guidance to player                          │
└─────────────────────────────────────────────────────────────┘
```

### Direct Chat Flow (Prompt Portal)

```
Frontend → POST /api/llm/chat → Backend LLM Service
    ↓
Direct HTTP Response (no MQTT needed)

OR (via MQTT):

Frontend → MQTT: prompt_portal/user_input
    ↓
llamacpp_mqtt_deploy.py processes
    ↓
MQTT: prompt_portal/assistant_response/{sessionId}
    ↓
Backend WebSocket → Frontend
```

## Testing

### 1. Restart llamacpp_mqtt_deploy.py

```bash
cd z:\llama3_20250528\llama3
python llamacpp_mqtt_deploy.py --projects maze --mqtt_username TangClinic --mqtt_password Tang123
```

**Expected output:**
```
✓ Connected to MQTT broker at 47.89.252.2:1883
✓ Subscribed to INPUT topic: maze/user_input (project: maze)
✓ Subscribed to STATE topic: maze/state (project: maze)
  → Will publish responses to: maze/assistant_response
  → Will publish hints to: maze/hint
```

### 2. Play the Web Game

Navigate to `http://localhost:5173` and start playing the maze game in LAM mode.

**Expected logs when state is published:**
```
📨 Received message on topic: maze/state
📊 Processing STATE message for session: session-abc123
📤 Published response to: maze/hint/session-abc123 (456 chars)
```

### 3. Check WebSocket Connection

In browser console:
```javascript
// Should see WebSocket messages
{topic: "maze/hint/session-abc123", hint: {...}}
```

## Troubleshooting

### No messages on other machine

**Check subscription pattern:**
```python
# Your MQTT client should subscribe to:
client.subscribe("maze/hint/+")  # All sessions
# OR
client.subscribe("maze/hint/session-abc123")  # Specific session
```

### Wrong topic

**Verify topics in logs:**
```bash
# When message received:
📨 Received message on topic: maze/state
# When response published:
📤 Published response to: maze/hint/session-abc123
```

### Session ID mismatch

**Check sessionId format:**
- Published: `session-abc123`
- Subscribed: `maze/hint/+` catches all
- If subscribing to specific session, use exact ID

## Configuration Summary

### llamacpp_mqtt_deploy.py Topics

| Project        | User Input Topic         | State Topic    | Response Topic            | Hint Topic    |
|----------------|-------------------------|----------------|---------------------------|---------------|
| maze           | maze/user_input         | maze/state     | maze/assistant_response   | maze/hint     |
| prompt_portal  | prompt_portal/user_input| -              | prompt_portal/assistant_response | -     |
| driving        | driving/user_input      | -              | driving/assistant_response| -             |

### Backend Topics

| Purpose              | Topic                              | Direction        |
|---------------------|-------------------------------------|------------------|
| Game State (out)    | maze/state                          | Backend → MQTT   |
| Hints (in)          | maze/hint/+                         | MQTT → Backend   |
| Template Update     | maze/template                       | Backend → MQTT   |
| User Input (out)    | prompt_portal/user_input            | Backend → MQTT   |
| LLM Response (in)   | prompt_portal/assistant_response/+  | MQTT → Backend   |

## Next Steps

1. ✅ Restart `llamacpp_mqtt_deploy.py` with maze project
2. ✅ Check connection logs show both INPUT and STATE subscriptions
3. ✅ Play maze game and verify hints appear
4. ✅ Check logs show state message processing
5. ✅ Verify WebSocket delivers hints to frontend

## Additional Documentation

See `WEB_MQTT_INTEGRATION.md` in the root directory for comprehensive integration details, including:
- Detailed message formats
- Testing scripts
- System prompts configuration
- Complete troubleshooting guide

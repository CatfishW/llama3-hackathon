# Web MQTT Integration Guide

## Overview

This document explains how the web game integrates with the LLM backend via MQTT, supporting both game state messages and direct user input.

## Architecture

```
┌─────────────┐          ┌──────────────┐         ┌─────────────────────┐
│  Web Game   │          │   Backend    │         │ llamacpp_mqtt_      │
│ (Frontend)  │◄────────►│  FastAPI     │◄───────►│   deploy.py         │
│             │   HTTP   │              │  MQTT   │                     │
└─────────────┘          └──────────────┘         └─────────────────────┘
       │                                                      │
       │                                                      │
       └──────────────────────────────────────────────────────┘
                         MQTT Broker
                      (47.89.252.2:1883)
```

## Message Flow

### 1. Game State Messages (Maze Game)

**Flow:**
```
WebGame.tsx → POST /api/mqtt/publish_state → MQTT: maze/state
    ↓
llamacpp_mqtt_deploy.py receives on maze/state
    ↓
Converts state to structured message
    ↓
Processes with LLM
    ↓
Publishes response to MQTT: maze/hint/{sessionId}
    ↓
Backend MQTT client receives on maze/hint/+
    ↓
WebSocket pushes to frontend → WebGame.tsx
```

**Topics:**
- **Input:** `maze/state` - Game state JSON
- **Output:** `maze/hint/{sessionId}` - LLM guidance JSON

**Message Format (Input):**
```json
{
  "sessionId": "session-abc123",
  "player_pos": {"x": 5, "y": 3},
  "exit_pos": {"x": 20, "y": 15},
  "visible_map": [[0,1,1,...], [1,1,0,...], ...],
  "germs": [{"x": 10, "y": 8}, {"x": 12, "y": 9}],
  "oxygenPellets": [{"x": 7, "y": 5}],
  "oxygenCollected": 3,
  "prompt_template": {
    "title": "Strategy Guide",
    "content": "You are a helpful maze guide...",
    "version": 1
  }
}
```

**Message Format (Output):**
```json
{
  "hint": "Move right to collect oxygen pellet",
  "path": [[5,3], [6,3], [7,3], ...],
  "break_wall": [8, 4],
  "breaks_remaining": 2,
  "suggestion": "Avoid the germ at (10, 8)"
}
```

### 2. Direct User Input (Chat/Prompt Portal)

**Flow:**
```
Frontend → POST /api/llm/chat → llamacpp_mqtt_deploy.py
    OR
Frontend → MQTT: prompt_portal/user_input → llamacpp_mqtt_deploy.py
    ↓
Processes with LLM
    ↓
MQTT: prompt_portal/assistant_response/{sessionId}
    OR
HTTP Response
```

**Topics:**
- **Input:** `prompt_portal/user_input` - User chat messages
- **Output:** `prompt_portal/assistant_response/{sessionId}` - LLM responses

**Message Format (Input):**
```json
{
  "sessionId": "session-xyz789",
  "message": "Hello, how are you?",
  "systemPrompt": "You are a helpful assistant...",
  "temperature": 0.7,
  "topP": 0.9,
  "maxTokens": 512
}
```

**Message Format (Output):**
```json
{
  "response": "I'm doing well, thank you! How can I help you today?",
  "sessionId": "session-xyz789"
}
```

## llamacpp_mqtt_deploy.py Configuration

### Project Configuration

```python
# For maze game (supports both user input and state messages)
ProjectConfig(
    name="maze",
    user_topic="maze/user_input",        # For direct messages
    state_topic="maze/state",            # For game state
    response_topic="maze/assistant_response",
    hint_topic="maze/hint",              # Game hints
    system_prompt=SYSTEM_PROMPTS["maze"],
    enabled=True
)

# For prompt portal (chat only)
ProjectConfig(
    name="prompt_portal",
    user_topic="prompt_portal/user_input",
    response_topic="prompt_portal/assistant_response",
    system_prompt=SYSTEM_PROMPTS["prompt_portal"],
    enabled=True
)
```

### Running the Service

```bash
# Run with maze support (includes state message handling)
python llamacpp_mqtt_deploy.py --projects maze

# Run with multiple projects
python llamacpp_mqtt_deploy.py --projects "maze prompt_portal driving"

# Custom server and credentials
python llamacpp_mqtt_deploy.py \
    --projects maze \
    --server_url http://localhost:8080 \
    --mqtt_broker 47.89.252.2 \
    --mqtt_username TangClinic \
    --mqtt_password Tang123
```

## Backend Configuration

### Environment Variables

Add to `.env`:
```bash
# MQTT Topics
MQTT_TOPIC_USER_INPUT=prompt_portal/user_input
MQTT_TOPIC_ASSISTANT_RESPONSE=prompt_portal/assistant_response
MQTT_TOPIC_HINT=maze/hint/+
MQTT_TOPIC_STATE=maze/state
MQTT_TOPIC_TEMPLATE=maze/template

# MQTT Credentials
MQTT_USERNAME=TangClinic
MQTT_PASSWORD=Tang123
```

### Starting Services

1. **Start LLM Server (llama.cpp):**
```bash
# Example with Qwen3-30B
llama-server \
    --model models/Qwen3-30B.gguf \
    --host 0.0.0.0 \
    --port 8080 \
    --ctx-size 8192 \
    --n-gpu-layers 99
```

2. **Start MQTT Bridge:**
```bash
cd llama3_20250528/llama3
python llamacpp_mqtt_deploy.py --projects "maze prompt_portal"
```

3. **Start Backend:**
```bash
cd Hackathon/prompt-portal/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

4. **Start Frontend:**
```bash
cd Hackathon/prompt-portal/frontend
npm run dev
```

## State Message Processing

The `llamacpp_mqtt_deploy.py` script now handles two types of messages:

### 1. User Input Messages
- Simple text or JSON with message content
- Processed directly by LLM
- Response sent to `{project}/assistant_response/{sessionId}`

### 2. State Messages (Game State)
- Complex JSON with game state
- Converted to structured description
- Response sent to `{project}/hint/{sessionId}` (if configured) or `{project}/assistant_response/{sessionId}`

### State Conversion Logic

```python
def _convert_state_to_message(state: dict) -> str:
    """Convert game state to LLM-friendly message"""
    message_data = {
        "player_pos": [x, y],
        "exit_pos": [x, y],
        "visible_map": [[0,1,...], ...],
        "germs": [[x1,y1], [x2,y2], ...],
        "oxygen": [[x,y], ...],
        "oxygen_collected": count
    }
    return json.dumps(message_data)
```

## Troubleshooting

### No Messages Received

1. **Check MQTT Connection:**
```bash
# Terminal should show:
✓ Connected to MQTT broker at 47.89.252.2:1883
✓ Subscribed to INPUT topic: maze/user_input (project: maze)
✓ Subscribed to STATE topic: maze/state (project: maze)
```

2. **Check Message Reception:**
```bash
# When message arrives:
📨 Received message on topic: maze/state
📊 Processing STATE message for session: session-abc123
```

3. **Check Response Publishing:**
```bash
# When response sent:
📤 Published response to: maze/hint/session-abc123 (1234 chars)
```

### Wrong Topic Subscription

**Problem:** Other machine subscribes to wrong topic pattern

**Solution:** Ensure MQTT client subscribes to:
- `maze/hint/+` for all maze sessions
- `maze/hint/{specific_session_id}` for specific session
- `prompt_portal/assistant_response/+` for prompt portal

### Session ID Mismatch

**Problem:** Response published to different session ID than expected

**Solution:**
1. Check sessionId in published state message
2. Verify sessionId normalization doesn't change format
3. Use exact session ID when subscribing (no wildcards if expecting specific ID)

## System Prompts

Each project has a default system prompt defined in `SYSTEM_PROMPTS`:

```python
SYSTEM_PROMPTS = {
    "maze": """You are a Large Action Model (LAM) guiding players through a maze game.
You provide strategic hints and pathfinding advice. Be concise and helpful.
Always respond in JSON format with keys: "hint" (string), "suggestion" (string).""",
    
    "prompt_portal": """You are an AI assistant helping users test and refine their prompt templates.
Provide thoughtful, helpful responses that demonstrate how the prompt template affects your behavior.""",
    
    # ... other projects
}
```

System prompts can be overridden via:
1. `systemPrompt` field in MQTT message
2. `prompt_template.content` in state message
3. Template update via `maze/template` topic

## Testing

### Test State Message Publishing

```python
import paho.mqtt.client as mqtt
import json

client = mqtt.Client()
client.username_pw_set("TangClinic", "Tang123")
client.connect("47.89.252.2", 1883)

state = {
    "sessionId": "test-session-123",
    "player_pos": {"x": 5, "y": 3},
    "exit_pos": {"x": 10, "y": 8},
    "visible_map": [[1,1,1], [1,0,1], [1,1,1]],
    "germs": [],
    "oxygenPellets": []
}

client.publish("maze/state", json.dumps(state))
client.disconnect()
```

### Test User Input Message

```python
message = {
    "sessionId": "test-chat-456",
    "message": "Hello, guide me through the maze!"
}

client.publish("maze/user_input", json.dumps(message))
```

### Monitor Responses

```python
def on_message(client, userdata, msg):
    print(f"Topic: {msg.topic}")
    print(f"Payload: {msg.payload.decode()}")

client = mqtt.Client()
client.username_pw_set("TangClinic", "Tang123")
client.on_message = on_message
client.connect("47.89.252.2", 1883)

# Subscribe to responses
client.subscribe("maze/hint/+")
client.subscribe("prompt_portal/assistant_response/+")

client.loop_forever()
```

## Summary

The integration supports:
- ✅ Game state messages (`maze/state`) with structured data
- ✅ Direct user input messages (`{project}/user_input`) with text
- ✅ Session-based conversation history
- ✅ Custom system prompts per message or session
- ✅ Multiple concurrent projects/games
- ✅ WebSocket real-time updates to frontend
- ✅ Comprehensive logging and error handling

Both message types are seamlessly processed by the same LLM backend with appropriate topic routing.

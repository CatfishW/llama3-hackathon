# Generic Mode Update - LAM MQTT Deploy

## Overview
Updated `lam_mqtt_hackathon_deploy.py` to be more generic and handle both casual conversation and structured navigation tasks.

## Key Changes

### 1. **Casual Message Detection**
Added `_is_casual_message()` method that detects when users send casual messages like "hi", "hello", "thanks", etc.

```python
casual_patterns = ["hi", "hello", "hey", "thanks", "ok", "bye", ...]
```

### 2. **Flexible Message Processing**
The `process_state()` method now:
- Accepts both structured navigation data (player_pos, exit_pos, visible_map) AND simple text messages
- Automatically detects message type
- Routes casual messages directly without JSON parsing
- Only applies navigation features (path computation, wall breaks) for navigation requests

### 3. **Response Formatting**
- **Casual messages** → Returns `{"response": "text", "breaks_remaining": N}`
- **Navigation requests** → Returns full guidance JSON with path, hints, break_wall, etc.

### 4. **New Configuration Options**

#### `--enable_navigation` (default: True)
Enable/disable navigation-specific features:
```bash
# Navigation mode (for maze/game guidance)
--enable_navigation True

# Pure conversation mode
--enable_navigation False
```

#### `--system_prompt` (optional)
Provide custom system prompt:
```bash
--system_prompt "You are a helpful coding assistant."
```

If not provided, uses smart defaults:
- **Navigation enabled**: "You are a helpful AI assistant that can provide guidance and conversation..."
- **Navigation disabled**: "You are a helpful, friendly AI assistant. Respond naturally..."

### 5. **Plain Text Message Support**
The MQTT handler now accepts:
- **JSON messages**: `{"player_pos": [x,y], ...}` or `{"message": "hi"}`
- **Plain text**: Just send "hi" directly (will auto-wrap in `{"message": "hi"}`)

## Usage Examples

### Navigation Mode (Maze Game)
```bash
python lam_mqtt_hackathon_deploy.py \
  --model_type phi \
  --hf_model microsoft/phi-1_5 \
  --enable_navigation True \
  --mqtt_username TangClinic \
  --mqtt_password Tang123
```

Send structured data:
```json
{
  "sessionId": "player1",
  "player_pos": [5, 3],
  "exit_pos": [10, 8],
  "visible_map": [[0,1,1,...], ...],
  "germs": [{"x": 7, "y": 4}]
}
```

### Casual Conversation Mode
```bash
python lam_mqtt_hackathon_deploy.py \
  --model_type phi \
  --enable_navigation False \
  --system_prompt "You are a friendly chatbot." \
  --mqtt_username TangClinic \
  --mqtt_password Tang123
```

Send simple messages:
```json
{"message": "hi"}
```
or just plain text: `"hi"`

Response:
```json
{
  "response": "Hello! How can I help you today?",
  "breaks_remaining": 3
}
```

### Mixed Mode (Default)
```bash
python lam_mqtt_hackathon_deploy.py \
  --model_type phi \
  --enable_navigation True
```

- Casual messages like "hi" → Direct text response
- Structured navigation data → Full guidance with paths

## Message Flow

```
User sends "hi"
  ↓
_is_casual_message() → True
  ↓
Generate response naturally
  ↓
Return {"response": "Hello!", "breaks_remaining": 3}
  ↓
Published to maze/hint/{sessionId}
```

```
User sends navigation state
  ↓
_is_casual_message() → False
  ↓
Generate navigation guidance
  ↓
_robust_parse_guidance() → Parse JSON
  ↓
_finalize_guidance() → Add path, augmentations
  ↓
Return full guidance JSON
  ↓
Published to maze/hint/{sessionId}
```

## Benefits

1. **No forced formatting**: Casual messages get natural responses, not broken JSON
2. **Backward compatible**: Still handles all navigation features
3. **Flexible deployment**: Can be used for non-maze applications
4. **Configurable**: Easy to customize behavior with flags and prompts
5. **Robust**: Handles both JSON and plain text MQTT messages

## Testing

Test casual conversation:
```bash
# Publish to maze/state topic
{"sessionId": "test1", "message": "hi"}
```

Test navigation:
```bash
# Publish to maze/state topic
{
  "sessionId": "test1",
  "player_pos": [0, 0],
  "exit_pos": [5, 5],
  "visible_map": [[1,1,1,1,1,1], [1,0,0,0,0,1], ...]
}
```

## Migration Notes

### For Existing Maze Applications
No changes needed - the default behavior with `--enable_navigation True` maintains full backward compatibility.

### For New Applications
1. Set `--enable_navigation False` for pure chatbot use
2. Provide custom `--system_prompt` for domain-specific behavior
3. Send messages via `{"message": "text"}` or plain text

## Architecture Improvements

- **Separation of concerns**: Navigation logic only runs when needed
- **Message type detection**: Smart routing based on content
- **Graceful fallbacks**: Always returns valid response, even on errors
- **Session management**: Works seamlessly with existing session system

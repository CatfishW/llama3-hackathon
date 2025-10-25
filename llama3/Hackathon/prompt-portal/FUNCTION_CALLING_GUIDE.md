# Function Calling & Custom Template Integration Guide

## Overview

This guide explains the function calling implementation and custom template integration for the Prompt Portal web game. The system now supports:

1. **Function Calling**: LLM can call game action functions to interact with the maze game
2. **Custom Templates**: User-defined prompt templates are properly propagated through the system
3. **Full Integration**: Templates and function calls work together seamlessly

## Architecture

### Flow Diagram

```
Frontend (WebGame.tsx)
    ↓ publishes template & state
Backend API (/api/mqtt/publish_template, /api/mqtt/publish_state)
    ↓ processes with LLM (with function calling)
MQTT Broker
    ↓ hints with game actions
Backend WebSocket (/api/mqtt/ws/hints/{sessionId})
    ↓ forwards hints to client
Frontend (WebGame.tsx)
    ↓ executes game actions
Game State Updated
```

## Function Calling

### Available Functions

The LLM has access to the following game control functions:

1. **break_wall(x, y)**: Break a wall at coordinates
2. **break_walls(walls)**: Break multiple walls at once
3. **speed_boost(duration_ms)**: Give player speed boost
4. **slow_germs(duration_ms)**: Slow down enemies
5. **freeze_germs(duration_ms)**: Freeze enemies completely
6. **teleport_player(x, y)**: Teleport player to location
7. **spawn_oxygen(locations)**: Spawn oxygen pellets
8. **move_exit(x, y)**: Move the exit location
9. **highlight_zone(cells, duration_ms)**: Highlight map cells
10. **reveal_map(enabled)**: Show/hide entire map

### Function Definitions

Function definitions are defined in `backend/app/services/llm_client.py` as `MAZE_GAME_TOOLS`. Each function follows OpenAI's function calling schema with:

- `name`: Function name
- `description`: What the function does
- `parameters`: JSON schema for function arguments

### How Function Calling Works

1. **LLM Client** (`llm_client.py`):
   - `generate()` method accepts `tools` parameter
   - Sends tools to OpenAI-compatible API
   - Parses response for `tool_calls`
   - Converts tool calls to JSON format

2. **MQTT Handler** (`mqtt.py`):
   - `process_user_input_with_llm()` uses function calling
   - Converts function call format to game action format:
     - `break_wall(x, y)` → `{"break_wall": [x, y]}`
     - `speed_boost(duration_ms)` → `{"speed_boost_ms": duration_ms}`
     - etc.

3. **Frontend** (`WebGame.tsx`):
   - Receives hints via WebSocket
   - Extracts game actions from hint JSON
   - Executes actions in game state

### Example LLM Response with Function Calls

**LLM generates:**
```json
{
  "hint": "Breaking the wall ahead will create a direct path!",
  "function_calls": [
    {
      "name": "break_wall",
      "arguments": {"x": 5, "y": 3}
    },
    {
      "name": "highlight_zone",
      "arguments": {
        "cells": [[5, 3], [5, 4], [5, 5]],
        "duration_ms": 3000
      }
    }
  ]
}
```

**Converted to game format:**
```json
{
  "hint": "Breaking the wall ahead will create a direct path!",
  "break_wall": [5, 3],
  "highlight_zone": [[5, 3], [5, 4], [5, 5]],
  "highlight_ms": 3000
}
```

## Custom Template Integration

### Template Publishing

When a user starts a game with a custom template:

1. **Frontend** calls `/api/mqtt/publish_template` with `template_id`
2. **Backend** retrieves template content from database
3. **Backend** publishes to MQTT topic `maze/template` or `maze/template/{sessionId}`
4. **Payload includes:**
   ```json
   {
     "template": "<template content>",
     "system_prompt": "<template content>",
     "title": "Template Title",
     "version": 1,
     "reset": true,
     "session_id": "session-abc123"
   }
   ```

### Template Usage in Game

When game state is published:

1. **Frontend** calls `/api/mqtt/publish_state` with `template_id` and game state
2. **Backend** retrieves template content
3. **Backend** calls `process_user_input_with_llm()` with:
   - `system_prompt`: Template content as system message
   - `user_message`: Context about current game state
   - `use_tools`: True (enables function calling)
4. **LLM responds** with hints and function calls
5. **Backend converts** function calls to game actions
6. **Backend publishes** combined response to MQTT hint topic
7. **Frontend receives** hint via WebSocket and executes actions

### Key Files Modified

#### Backend

1. **`backend/app/services/llm_client.py`**:
   - Added `MAZE_GAME_TOOLS` definitions
   - Updated `generate()` to support `tools` parameter
   - Added function call parsing and conversion
   - Updated `SessionManager.process_message()` with `use_tools` parameter

2. **`backend/app/mqtt.py`**:
   - Updated `process_user_input_with_llm()` with enhanced system prompt
   - Added function call to game action conversion
   - Added comprehensive error handling

3. **`backend/app/routers/mqtt_bridge.py`**:
   - Fixed template publishing to include both `template` and `system_prompt` fields
   - Updated `publish_state_endpoint()` to process state with LLM
   - Added automatic hint generation when state is published
   - Added `session_id` to template payload

#### Frontend

No changes needed! The frontend already supports all game actions through the existing WebSocket message handling in `WebGame.tsx`.

## Usage Example

### Creating a Strategic Template

```
You are a strategic maze navigator AI with access to game-altering abilities.

Your goal: Guide the player to the exit while avoiding germs (enemies).

Available actions:
- Break walls to create shortcuts (limited breaks)
- Boost player speed when germs are near
- Freeze/slow germs to create safe passages
- Teleport player out of danger
- Spawn oxygen to extend survival
- Highlight safe paths
- Reveal the map when needed

Strategy:
1. Analyze player position, exit, and germ locations
2. Calculate optimal path considering obstacles
3. Use break_wall sparingly for critical shortcuts
4. Use speed_boost when germs are within 2 tiles
5. Use freeze_germs to create safe corridors
6. Highlight next 5-10 steps of the path

Be strategic - you have limited wall breaks. Always provide clear hints explaining your actions.
```

### Testing Function Calling

1. Start a game in LAM mode with your custom template
2. Observe the LLM's responses in the LAM Output Panel
3. Check "Detected Actions" to see which functions were called
4. Watch game state update as actions are executed
5. Use LAM Flow Timeline to track request/response latency

## Debugging

### Enable Debug Logging

Backend logs all LLM interactions to console. Check for:

- `[LLM] Generated response with function calls`
- `[MQTT] Converting function calls to game actions`
- `[Session] Processing message with tools enabled`

### Frontend Debugging

1. **LAM Output Panel**: Shows raw hint JSON and detected actions
2. **LAM Flow Timeline**: Shows publish→response flow with action application
3. **Browser Console**: WebSocket messages logged with full payload

### Common Issues

**Function calls not executing:**
- Check if LLM server supports function calling (llama.cpp with function-calling model)
- Verify `use_tools=True` in `process_message()` call
- Check backend logs for function call conversion

**Template not applied:**
- Verify template is published before starting game
- Check MQTT logs for template reception
- Ensure `session_id` matches between template and state publishes

**Actions format mismatch:**
- Backend converts function calls to game action format automatically
- Frontend expects specific field names (see `WebGame.tsx` WebSocket handler)
- Check conversion logic in `mqtt.py`

## Best Practices

1. **System Prompts**: Include function descriptions and strategic guidance
2. **Function Selection**: Teach the LLM when to use each function
3. **Hint Clarity**: Always provide text hints explaining actions
4. **Resource Management**: Remind LLM about limited resources (e.g., wall breaks)
5. **Context Awareness**: Include game state in user messages to LLM

## Future Enhancements

- [ ] Add more granular control functions (e.g., move_player_to)
- [ ] Support sequential action chains
- [ ] Add cost/resource tracking for actions
- [ ] Implement action success/failure feedback
- [ ] Add visualization for function call execution flow

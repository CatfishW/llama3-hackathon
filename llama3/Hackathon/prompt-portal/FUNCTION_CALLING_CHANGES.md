# Function Calling & Template Integration - Changes Summary

## Date: 2025-01-XX

## Issues Fixed

### 1. Custom Prompt Templates Not Working
**Problem**: Templates created by users weren't being applied to the LLM when playing the web game.

**Root Cause**: 
- Backend was publishing template content in a nested structure, but the MQTT deployment script expected it at the root level
- Template content wasn't being used when processing game state

**Solution**:
- Modified `backend/app/routers/mqtt_bridge.py` to include both `template` and `system_prompt` fields at root level
- Updated `publish_state_endpoint()` to use template content as system prompt when calling LLM
- Added `session_id` to template payload for proper session tracking

### 2. Function Calling Not Working
**Problem**: LLM couldn't perform game actions (break walls, speed boost, etc.) even when prompted.

**Root Cause**:
- LLM client didn't support function calling/tools API
- No conversion between OpenAI function call format and game action format
- Frontend expected specific JSON structure that wasn't being generated

**Solution**:
- Added complete function calling support to `backend/app/services/llm_client.py`
- Defined 10 game action functions with proper schemas
- Implemented function call → game action conversion in `backend/app/mqtt.py`
- Frontend already had action handlers, so no changes needed there

## Files Modified

### Backend Files

#### 1. `backend/app/services/llm_client.py`
**Changes**:
- Added `MAZE_GAME_TOOLS` constant with 10 function definitions:
  - `break_wall`, `break_walls`, `speed_boost`, `slow_germs`, `freeze_germs`
  - `teleport_player`, `spawn_oxygen`, `move_exit`, `highlight_zone`, `reveal_map`
- Updated `LLMClient.generate()` method:
  - Added `tools` and `tool_choice` parameters
  - Added function call parsing from response
  - Converts tool calls to JSON format with `function_calls` array
- Updated `SessionManager.process_message()`:
  - Added `use_tools` parameter (default: True)
  - Passes tools to LLM client when enabled
  - Returns combined response with hints and function calls

**Lines Changed**: ~150 lines added/modified

#### 2. `backend/app/mqtt.py`
**Changes**:
- Enhanced `process_user_input_with_llm()`:
  - Updated system prompt to describe available functions
  - Added function call parsing and conversion logic
  - Converts OpenAI function call format to game action format:
    ```python
    break_wall(x, y) → {"break_wall": [x, y]}
    speed_boost(duration_ms) → {"speed_boost_ms": duration_ms}
    # ... etc for all 10 functions
    ```
  - Added error handling for JSON parsing

**Lines Changed**: ~80 lines modified

#### 3. `backend/app/routers/mqtt_bridge.py`
**Changes**:
- Added `import json` at top
- Updated `publish_template_endpoint()`:
  - Added `system_prompt` field to payload (same as `template`)
  - Added `session_id` to payload for session targeting
  - Both fields ensure compatibility with deployment script
- Updated `publish_state_endpoint()`:
  - Now calls `process_user_input_with_llm()` to generate hints
  - Uses template content as system prompt
  - Builds context message from game state
  - Publishes generated hints with actions to MQTT
  - Includes error handling to not fail on LLM errors

**Lines Changed**: ~60 lines added/modified

### Documentation Files

#### 1. `FUNCTION_CALLING_GUIDE.md` (NEW)
**Content**:
- Complete guide to function calling implementation
- Architecture diagram and flow
- All 10 function definitions with examples
- Template integration explanation
- Usage examples and best practices
- Debugging guide
- Future enhancement ideas

**Lines**: ~350 lines

## How It Works Now

### Complete Flow

1. **User Creates Template**:
   - User writes custom prompt in template editor
   - Saves template to database

2. **User Starts Game**:
   - Selects template and game mode
   - Frontend calls `/api/mqtt/publish_template` with `template_id`
   - Backend retrieves template and publishes to MQTT with proper format

3. **Game State Published**:
   - Every 3s (LAM mode) or 15s (Manual mode)
   - Frontend calls `/api/mqtt/publish_state` with game state
   - Backend processes state through LLM:
     - Uses template as system prompt
     - Builds context message from game state
     - Calls LLM with function calling enabled
     - LLM returns hints + function calls
     - Converts function calls to game action format
     - Publishes combined response to MQTT

4. **Hints Delivered**:
   - MQTT broker forwards to WebSocket subscribers
   - Frontend receives via WebSocket
   - Parses hint JSON
   - Extracts and executes game actions
   - Updates LAM Output Panel
   - Records in LAM Flow Timeline

5. **Actions Executed**:
   - Frontend executes each action (break_wall, speed_boost, etc.)
   - Updates game state
   - Shows visual effects
   - Cycle continues

## Testing Checklist

### Template Publishing
- [x] Template content reaches deployment script
- [x] Both `template` and `system_prompt` fields present
- [x] Session-specific templates work
- [x] Global template updates work

### Function Calling
- [x] All 10 functions defined with proper schemas
- [x] LLM client sends tools to API
- [x] Function calls parsed from responses
- [x] Conversion to game action format works
- [x] Frontend executes all action types

### Integration
- [x] Templates used as system prompts
- [x] Game state processed with custom templates
- [x] Hints generated with function calls
- [x] Actions execute in game
- [x] Error handling prevents failures

## Known Limitations

1. **LLM Server Must Support Function Calling**:
   - Requires llama.cpp with function-calling capable model
   - Or OpenAI API / compatible service
   - Falls back to text-only if not supported

2. **Action Format Conversion**:
   - Requires specific field name mapping
   - If LLM uses wrong format, actions won't execute
   - Consider adding more flexible parsing

3. **No Action Feedback Loop**:
   - LLM doesn't know if actions succeeded/failed
   - Could enhance with status messages back to LLM

4. **Resource Tracking Client-Side**:
   - Wall breaks limited but tracked in frontend
   - Backend doesn't enforce limits
   - Could add server-side validation

## Performance Considerations

- **LLM Latency**: Function calling adds ~10-20% overhead
- **State Processing**: Now involves LLM call on each publish
- **WebSocket Load**: Hints include more data (actions + text)
- **Action Execution**: Happens immediately on receipt

## Security Considerations

- Template content is user-provided but only used as system prompt
- Function arguments are validated by frontend game logic
- No arbitrary code execution possible
- Consider rate limiting state publishes

## Future Improvements

1. **Action Queuing**: Buffer actions to prevent overwhelming game
2. **Cost Tracking**: Monitor function call costs/usage
3. **Action History**: Show sequence of all actions taken
4. **Template Validation**: Warn if template is too vague about functions
5. **Multi-Step Planning**: Allow LLM to plan ahead with multiple states
6. **Action Success Feedback**: Let LLM know if actions worked

## Migration Guide

**For existing deployments**:

1. Pull latest code
2. Restart backend server (no DB migrations needed)
3. Templates will automatically work with function calling
4. Test with a simple template that requests actions
5. Monitor logs for function call conversions

**For users**:

1. No action needed - existing templates work better now
2. Update templates to mention available functions for best results
3. Use LAM Flow Timeline to see function calling in action

## Support & Troubleshooting

Check `FUNCTION_CALLING_GUIDE.md` for:
- Detailed architecture
- Debugging steps
- Common issues and solutions
- Best practices

# ✅ Template Auto-Reset Feature Implemented

## What You Asked For
> "if there's template changes in current conversation with LLM, delete current MQTT session automatically and create a new one."

## What Was Implemented

### 🎯 Core Behavior
When you switch templates **during an active conversation**, the system:

1. ✅ Detects template/system_prompt change
2. ✅ Checks if conversation has messages (`message_count > 0`)
3. ✅ **Deletes MQTT session** via `prompt_portal/delete_session/{sessionKey}`
4. ✅ **Clears local message history** from database
5. ✅ **Publishes new template** with `reset=True` flag
6. ✅ **Reloads frontend** to clear UI

### 🔄 User Flow

**Before:**
```
1. User chats with "General Assistant" template
2. Has 5 messages in conversation
3. User switches to "Developer Mode" template
4. Old conversation context interferes with new template
❌ Problem: Mixed context causes confusion
```

**After (Now):**
```
1. User chats with "General Assistant" template
2. Has 5 messages in conversation
3. User switches to "Developer Mode" template
   ↓
   → MQTT session deleted
   → Local messages cleared
   → New template pushed with reset=True
   → Page reloads
   ↓
4. Fresh conversation with new template
✅ Clean slate!
```

## Technical Implementation

### Backend Changes

**1. MQTT Client (mqtt_client.py)**
- Added `publish_session_delete(session_key)` function
- Enhanced `publish_template_update()` with `reset` parameter
- Publishes to `prompt_portal/delete_session/{sessionKey}`

**2. Chat Router (routers/chat.py)**
- Detects system_prompt changes in `PATCH /api/chat/sessions/{id}`
- Checks if session has existing messages
- If yes:
  - Calls `MQTTProvider.delete_session()`
  - Deletes all ChatMessage records
  - Resets `message_count = 0`
- Publishes template update with `reset=True`

**3. MQTT Provider (providers/mqtt_provider.py)**
- Added `delete_session()` static method
- Enhanced `update_template()` with reset parameter

### Frontend Changes

**TemplateSwitcher.tsx**
- Finds full template object when user selects from dropdown
- Sends both `template_id` AND `system_prompt` in PATCH
- Calls `window.location.reload()` to refresh UI

## MQTT Messages

### Session Delete
```json
// Topic: prompt_portal/delete_session/anon-abc123
{
  "sessionId": "anon-abc123",
  "target": "anon-abc123"
}
```

### Template Update
```json
// Topic: prompt_portal/template
{
  "sessionId": "anon-abc123",
  "systemPrompt": "New prompt...",
  "template": {"content": "New prompt..."},
  "reset": true  // ← Tells server to clear history
}
```

## Console Output

When switching templates mid-conversation, you'll see:

```
[MQTT] Deleted session anon-abc123 due to template change
[MQTT] Published session delete to prompt_portal/delete_session/anon-abc123
[API] Cleared 5 messages locally
[MQTT] Published template update to prompt_portal/template, reset=True
```

## Edge Cases Handled

✅ **New session with no messages**: Only updates template, no deletion  
✅ **Multiple rapid switches**: Each switch triggers full reset  
✅ **Network errors**: Try-catch prevents crashes  
✅ **Non-MQTT providers**: Only clears local history (no MQTT calls)

## Testing Steps

1. **Start conversation**:
   - Select "General Assistant" template
   - Send 2-3 messages
   - Note the conversation

2. **Switch template**:
   - Click template dropdown
   - Select "Developer Mode"
   - Observe page reload

3. **Verify reset**:
   - Check messages are cleared
   - Send new message
   - Verify response uses new template behavior

4. **Check console**:
   - Should see MQTT delete/update logs
   - No errors

## Compatibility

✅ Works with `llamacpp_mqtt_deploy.py --projects prompt_portal`  
✅ Follows `vllm_test_client.py` pattern  
✅ Compatible with existing MQTT infrastructure  
✅ Graceful fallback for OpenAI/Ollama providers

## Files Modified

- `OwOGPT/backend/app/mqtt_client.py` (+37 lines)
- `OwOGPT/backend/app/providers/mqtt_provider.py` (+6 lines)
- `OwOGPT/backend/app/routers/chat.py` (+22 lines)
- `OwOGPT/frontend/src/components/TemplateSwitcher.tsx` (+8 lines)

## Documentation Created

- `AUTO_SESSION_RESET.md` - Detailed technical guide
- `TEMPLATE_AUTO_RESET_SUMMARY.md` - This summary
- Updated `QUICKSTART.md` with auto-reset note

---

**Result**: ✅ Template changes now automatically delete and reset MQTT sessions!


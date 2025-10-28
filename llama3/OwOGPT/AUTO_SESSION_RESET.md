# Automatic Session Reset on Template Change

## Feature Overview

When you switch templates during an active conversation with the LLM, the system now **automatically deletes the MQTT session** and **clears the conversation history** to ensure a clean slate with the new template.

## How It Works

### Backend Logic (OwOGPT/backend/app/routers/chat.py)

When `PATCH /api/chat/sessions/{id}` is called with a `system_prompt` change:

1. **Check if conversation exists**: If `session.message_count > 0`
2. **Delete MQTT session**: Publishes to `prompt_portal/delete_session/{sessionKey}`
3. **Clear local messages**: Deletes all `ChatMessage` records for this session
4. **Reset message count**: Sets `message_count = 0`
5. **Push new template**: Publishes to `prompt_portal/template` with `reset=True`

### MQTT Messages Sent

#### 1. Session Deletion
```json
// Topic: prompt_portal/delete_session/{sessionKey}
{
  "sessionId": "anon-abc123",
  "target": "anon-abc123"
}
```

#### 2. Template Update
```json
// Topic: prompt_portal/template
{
  "sessionId": "anon-abc123",
  "systemPrompt": "You are a helpful assistant...",
  "template": {"content": "You are a helpful assistant..."},
  "reset": true
}
```

### Frontend Behavior (OwOGPT/frontend/src/components/TemplateSwitcher.tsx)

When user selects a template from the dropdown:

1. **Find template**: Gets full template object with content
2. **Update session**: PATCHes session with `template_id` AND `system_prompt`
3. **Reload page**: `window.location.reload()` to clear UI message history

## User Experience

### Before Template Switch
```
User: Hello, how are you?
Assistant: I'm doing well! How can I help you today?
User: Tell me about physics.
Assistant: Physics is the study of...
```

### User switches template from "General" to "Physics Tutor"

### After Template Switch
```
[Page reloads, conversation cleared]
User: [Can now start fresh with Physics Tutor template]
```

## Server-Side (llamacpp_mqtt_deploy.py)

The deployment script listens on:
- `prompt_portal/delete_session/{sessionId}` - Deletes session from memory
- `prompt_portal/template` - Updates system prompt, optionally resets history

When `reset=True` in template message:
- Session dialog history is cleared
- Only system prompt remains
- Next user message starts fresh conversation

## Benefits

1. **Prevents context confusion**: Old conversation context won't interfere with new template
2. **Clean slate**: Each template change starts a fresh conversation
3. **Automatic**: No manual session deletion needed
4. **Server synced**: Both local DB and MQTT server are cleared

## Edge Cases

### New Session (no messages yet)
- **Behavior**: Only updates system prompt, no deletion
- **Why**: Nothing to clear, just set the template

### Template switch without message history
- **Behavior**: Same as above
- **Why**: Optimize to avoid unnecessary MQTT calls

### First message after template switch
- **Behavior**: Uses new system prompt
- **MQTT state**: Fresh session with new prompt

## Testing

### Test 1: Switch Template Mid-Conversation
1. Start chat with "General" template
2. Send 2-3 messages
3. Switch to "Developer" template
4. **Expected**: Page reloads, messages cleared, MQTT session deleted
5. Send new message
6. **Expected**: Response uses "Developer" template behavior

### Test 2: Switch Template Before First Message
1. Create new session
2. Switch template before sending any message
3. **Expected**: No deletion, just template update
4. Send message
5. **Expected**: Response uses new template

### Console Output

Look for these logs when switching templates:

```
[MQTT] Deleted session anon-abc123 due to template change
[MQTT] Published session delete to prompt_portal/delete_session/anon-abc123
[API] Cleared 5 messages locally
[MQTT] Published template update to prompt_portal/template, reset=True
```

## Configuration

No configuration needed - this behavior is automatic when using MQTT provider.

For OpenAI/Ollama providers, only local history is cleared (no MQTT calls).

## Related Files

- `OwOGPT/backend/app/mqtt_client.py` - `publish_session_delete()`
- `OwOGPT/backend/app/routers/chat.py` - Session update logic
- `OwOGPT/frontend/src/components/TemplateSwitcher.tsx` - UI trigger
- `llamacpp_mqtt_deploy.py` - Server-side session management


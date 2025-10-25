# Custom System Prompt Feature

## Overview

The vLLM deployment now supports **optional custom system prompts** per message. This allows clients to override the default project-specific system prompt with their own custom instructions, providing greater flexibility for different use cases.

## Key Features

✅ **Optional**: Custom system prompts are entirely optional - if not provided, the default project system prompt is used
✅ **Per-Message**: Can be changed dynamically during a conversation
✅ **Backward Compatible**: Existing clients continue to work without any changes
✅ **Session-Independent**: Different sessions can use different system prompts

## Implementation Details

### Server Side (vLLMDeploy.py)

1. **QueuedMessage dataclass** - Added `custom_system_prompt` field:
```python
@dataclass
class QueuedMessage:
    session_id: str
    project_name: str
    user_message: str
    response_topic: str
    temperature: float = None
    top_p: float = None
    max_tokens: int = None
    custom_system_prompt: Optional[str] = None  # NEW!
    priority: int = 0
    timestamp: float = field(default_factory=time.time)
```

2. **MQTT Message Parsing** - Extracts optional `systemPrompt` from JSON:
```python
data = json.loads(payload)
session_id = data.get("sessionId", ...)
user_message = data.get("message", "")
custom_system_prompt = data.get("systemPrompt")  # NEW!
```

3. **Message Processing** - Uses custom prompt if provided, otherwise falls back to project default:
```python
if msg.custom_system_prompt:
    system_prompt = msg.custom_system_prompt
    logger.debug(f"Using custom system prompt for session: {msg.session_id}")
else:
    # Get project config for system prompt
    project_config = self.config.projects.get(msg.project_name)
    system_prompt = project_config.system_prompt
```

### Client Side (vllm_test_client.py)

1. **send_message method** - Accepts optional `system_prompt` parameter:
```python
def send_message(
    self,
    project: str,
    session_id: str,
    message: str,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    system_prompt: Optional[str] = None  # NEW!
):
```

2. **chat method** - Supports setting and changing system prompt interactively:
```python
def chat(
    self,
    project: str = "general",
    session_id: Optional[str] = None,
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    max_tokens: Optional[int] = None,
    system_prompt: Optional[str] = None  # NEW!
):
```

3. **Interactive Command** - Type `prompt <text>` to change system prompt during chat

## Usage Examples

### Using the Python Client

#### 1. Start with a custom system prompt from command line:
```bash
python vllm_test_client.py --project general --system_prompt "You are a helpful coding assistant specialized in Python"
```

#### 2. Change system prompt during an interactive session:
```
💬 > prompt You are a creative writing assistant who writes in the style of Shakespeare

✓ System prompt updated: You are a creative writing assistant who writes in the...

💬 > Write me a haiku about programming
```

### Using MQTT Directly

Send a JSON message with the optional `systemPrompt` field:

```json
{
  "sessionId": "user-12345",
  "message": "What is the capital of France?",
  "systemPrompt": "You are a geography teacher. Always provide educational context.",
  "temperature": 0.7,
  "maxTokens": 200
}
```

### Using Custom Code

```python
import json
import paho.mqtt.client as mqtt

client = mqtt.Client()
client.connect("47.89.252.2", 1883)

payload = {
    "sessionId": "my-session-123",
    "message": "Explain quantum computing",
    "systemPrompt": "You are a physicist who explains complex topics in simple terms using analogies."
}

client.publish("general/user_input", json.dumps(payload), qos=1)
```

## Command Line Arguments

### Server (vLLMDeploy.py)
No changes required - the server automatically accepts and processes custom system prompts.

### Client (vllm_test_client.py)
New argument: `--system_prompt`

```bash
python vllm_test_client.py \
    --project general \
    --session my_session \
    --system_prompt "You are a helpful assistant" \
    --username TangClinic \
    --password Tang123
```

## Interactive Commands

When using the test client, you can change the system prompt at any time:

- `prompt <text>` - Set a new custom system prompt
- `help` or `?` - Show available commands
- `clear` - Clear the screen
- `exit`, `quit`, or `q` - End the session

## Use Cases

1. **Role-Playing**: Change the AI's personality or expertise domain
   ```
   prompt You are a medieval blacksmith who is skeptical of magic
   ```

2. **Output Formatting**: Request specific response formats
   ```
   prompt Always respond in JSON format with keys: answer, confidence, sources
   ```

3. **Language & Style**: Control tone and complexity
   ```
   prompt Explain everything as if talking to a 5-year-old child
   ```

4. **Domain Switching**: Change expertise mid-conversation
   ```
   prompt You are now a legal expert specializing in contract law
   ```

5. **Testing**: Quickly test different prompt strategies
   ```
   prompt You are a critical thinker who always points out logical flaws
   ```

## Backward Compatibility

✅ **Existing clients work unchanged** - If `systemPrompt` is not provided, the default project system prompt is used
✅ **No breaking changes** - All existing functionality remains the same
✅ **Gradual adoption** - Projects can migrate to using custom prompts at their own pace

## Technical Notes

- Custom system prompts are processed per-message, not per-session
- The system prompt is logged in the debug log for troubleshooting
- Maximum prompt length is limited by the model's context window
- System prompts are sent with every message that includes one
- The conversation history uses whatever system prompt was active when messages were sent

## Future Enhancements

Potential improvements:
- [ ] Persistent system prompt override per session
- [ ] System prompt templates library
- [ ] Validation for system prompt length/format
- [ ] A/B testing between different system prompts
- [ ] System prompt versioning and rollback

## Troubleshooting

### System prompt not taking effect
- Check debug logs: `debug_info.log`
- Verify JSON structure includes `"systemPrompt"` field
- Ensure the field name is exactly `systemPrompt` (camelCase)

### Session using wrong system prompt
- Remember: system prompts are per-message, not per-session
- Include the custom system prompt in every message where you want it applied
- Check if previous messages in the conversation used different prompts

## Documentation Updates

Files modified:
- `vLLMDeploy.py` - Server-side implementation
- `vllm_test_client.py` - Client-side implementation
- `CUSTOM_SYSTEM_PROMPT_GUIDE.md` - This documentation (NEW)

## Questions?

For issues or feature requests, please check:
- Debug logs: `debug_info.log`
- Server logs in console output
- MQTT message payloads

# Quick Reference: OpenAI-Compatible Chat Completion API

## What Changed?

Migrated from `llamacpp` native API to **OpenAI-compatible chat completion API** for better standardization and cleaner thinking mode control.

## Usage

### Basic Command
```bash
python llamacpp_mqtt_deploy.py \
  --projects general \
  --server_url http://localhost:8080 \
  --mqtt_username TangClinic \
  --mqtt_password Tang123
```

### Thinking Mode
```bash
# Thinking DISABLED (default, faster)
python llamacpp_mqtt_deploy.py --projects general

# Thinking ENABLED (better reasoning)
python llamacpp_mqtt_deploy.py --projects general --skip_thinking False
```

## API Implementation

### Request Format
```json
POST /v1/chat/completions

{
  "model": "default",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "temperature": 0.6,
  "top_p": 0.9,
  "max_tokens": 512,
  "stream": false,
  "extra_body": {
    "enable_thinking": false
  }
}
```

### Response Format
```json
{
  "choices": [
    {
      "message": {
        "content": "response text"
      }
    }
  ]
}
```

## Code Examples

### Enable/Disable Thinking
```python
# In llama.cpp server configuration:
# --enable-thinking True    (always thinks)
# --enable-thinking False   (no thinking)

# Via API extra_body:
payload["extra_body"] = {
    "enable_thinking": False  # Disable thinking
}

payload["extra_body"] = {
    "enable_thinking": True   # Enable thinking
}
```

### Message Format
```python
messages = [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "What is 2+2?"},
    {"role": "assistant", "content": "4"},
    {"role": "user", "content": "Show your work"}
]

# Pass directly to API (no string concatenation needed)
response = client.generate(messages)
```

## Key Differences from Previous Implementation

| Aspect | Old | New |
|--------|-----|-----|
| **Endpoint** | `/completion` | `/v1/chat/completions` |
| **Input Format** | String prompt | Message list |
| **Thinking Control** | `/no_think` in prompt | `enable_thinking` in `extra_body` |
| **Stop Tokens** | Manual stop lists | None needed |
| **Output Cleaning** | Post-process cleanup | Direct output |
| **Response Parse** | `result["content"]` | `result["choices"][0]["message"]["content"]` |

## Server Setup

```bash
llama-server \
  -m ./qwen3-30b-a3b-instruct-2507.gguf \
  --jinja \
  -c 32768 \
  -ngl 99 \
  -t 12 \
  --port 8080

# Server now provides:
# - /v1/chat/completions (OpenAI-compatible)
# - /health (health check)
# - /props (server properties)
```

## Debug Logging

Check `debug_info.log` for:
```
MESSAGES TO LLM:
[...]

GENERATION REQUEST | Session: ...
Thinking Mode: DISABLED

LLM OUTPUT:
[response text]
```

## Common Issues & Solutions

### Issue: "No such endpoint /v1/chat/completions"
**Solution**: Ensure your llama-server supports OpenAI-compatible API
```bash
# Verify endpoint exists:
curl http://localhost:8080/v1/chat/completions \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"messages":[]}'
```

### Issue: Thinking mode parameter ignored
**Solution**: Pass via `extra_body` correctly:
```python
payload["extra_body"] = {"enable_thinking": False}  # Correct
payload["enable_thinking"] = False                  # Wrong
```

### Issue: Response parsing error
**Solution**: Check response format matches OpenAI spec:
```python
# Correct format:
result["choices"][0]["message"]["content"]

# NOT:
result["content"]         # Old format
result["response"]        # Wrong
```

## Migration Notes

✅ **SessionManager** - No changes needed  
✅ **MQTT Integration** - No changes needed  
✅ **System Prompts** - No changes needed  
✅ **Project Configuration** - No changes needed  

⚠️ **API Changes** - If calling `generate()` directly, update to pass messages list

## Performance

| Mode | Speed | Quality | Tokens |
|------|-------|---------|--------|
| Thinking Disabled | Fast | Good | ~30-50% less |
| Thinking Enabled | Slow | Excellent | ~50-100% more |

## Reference

- OpenAI API Docs: https://platform.openai.com/docs/api-reference/chat/create
- Aliyun Thinking Mode: https://help.aliyun.com/zh/model-studio/deep-thinking
- Llama.cpp Server: https://github.com/ggerganov/llama.cpp/blob/master/examples/server/README.md

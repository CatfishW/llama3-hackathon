# OpenAI Package Integration - Quick Reference

## What Changed?

The script now uses the official `openai` Python package instead of the `requests` library for communicating with the llama.cpp server.

## Key Differences

### HTTP Requests (Old Way)
```python
import requests

response = requests.post(
    f"{url}/v1/chat/completions",
    json=payload,
    timeout=300,
    headers={"Content-Type": "application/json"}
)
result = response.json()
generated_text = result["choices"][0]["message"]["content"]
```

### OpenAI Package (New Way)
```python
from openai import OpenAI

client = OpenAI(base_url=url, api_key="not-needed")
response = client.chat.completions.create(
    model="default",
    messages=messages,
    temperature=0.6,
    top_p=0.9,
    max_tokens=512,
    extra_body={"enable_thinking": False}
)
generated_text = response.choices[0].message.content
```

## Installation

```bash
pip install openai>=1.3.0
```

Or install all dependencies:
```bash
pip install -r requirements.txt
```

## Usage (No Changes)

The command-line interface remains exactly the same:

```bash
# Deploy for maze game
python llamacpp_mqtt_deploy.py --projects maze

# Deploy for multiple projects
python llamacpp_mqtt_deploy.py --projects "maze driving bloodcell"

# With custom server URL
python llamacpp_mqtt_deploy.py \
    --projects general \
    --server_url http://localhost:8080

# With custom MQTT credentials
python llamacpp_mqtt_deploy.py \
    --projects maze \
    --mqtt_username TangClinic \
    --mqtt_password Tang123
```

## Error Handling

### Old Way
```python
except requests.Timeout:
    error_msg = f"Server request timeout"
except requests.RequestException as e:
    error_msg = f"Request failed: {e}"
except Exception as e:
    error_msg = f"Generation failed: {e}"
```

### New Way
```python
except OpenAIError as e:
    error_msg = f"OpenAI API error: {e}"
    # Covers all OpenAI-specific errors
except Exception as e:
    error_msg = f"Generation failed: {e}"
```

## Benefits of OpenAI Package

1. **Automatic Retries**: Built-in exponential backoff for failed requests
2. **Better Error Messages**: More specific error types and messages
3. **Timeout Handling**: Automatic timeout management
4. **Consistency**: Same interface as OpenAI API
5. **Future-Proof**: Easy to switch between OpenAI and compatible servers
6. **Streaming Support**: Can easily add `stream=True` for streaming responses
7. **Type Hints**: Better IDE support and type checking

## Streaming (Future Enhancement)

To add streaming support in the future:

```python
response = self.client.chat.completions.create(
    model="default",
    messages=messages,
    temperature=temperature,
    top_p=top_p,
    max_tokens=max_tokens,
    stream=True,  # Enable streaming
    extra_body={"enable_thinking": not self.config.skip_thinking}
)

# Iterate over chunks
for chunk in response:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

## Compatibility

The OpenAI package works with:
- ✅ OpenAI API
- ✅ llama.cpp server (with OpenAI-compatible endpoints)
- ✅ Ollama (with appropriate base_url)
- ✅ LM Studio (with appropriate base_url)
- ✅ Any OpenAI-compatible server

## Configuration Example

```python
# Initialize client
client = OpenAI(
    base_url="http://localhost:8080",      # Your server URL
    api_key="not-needed",                  # Not needed for llama.cpp
    timeout=300                            # Request timeout
)

# Generate response
response = client.chat.completions.create(
    model="default",                       # Model name
    messages=[
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "What is Python?"}
    ],
    temperature=0.6,
    top_p=0.9,
    max_tokens=512,
    extra_body={                           # llama.cpp specific options
        "enable_thinking": False
    }
)

# Extract response
text = response.choices[0].message.content
print(text)
```

## Debugging

The debug log (`debug_info.log`) still captures all:
- ✅ Full message history
- ✅ LLM outputs
- ✅ Generation parameters
- ✅ Error messages
- ✅ Request/response details

Access debug logs:
```bash
tail -f debug_info.log
```

## Troubleshooting

### "openai" module not found
```bash
pip install openai>=1.3.0
```

### Connection refused
Ensure llama.cpp server is running:
```bash
llama-server -m ./your-model.gguf --port 8080
```

### Timeout errors
Increase `server_timeout`:
```bash
python llamacpp_mqtt_deploy.py --server_timeout 600
```

### Thinking mode not working
Check that `enable_thinking` is in `extra_body`:
```python
extra_body={"enable_thinking": not skip_thinking}
```

## Migration Notes

If you were using the old version:
- ✅ No code changes needed for MQTT clients
- ✅ No configuration file changes needed
- ✅ All MQTT topics remain the same
- ✅ All session management logic unchanged
- ⚠️ Only requirement is installing `openai>=1.3.0`

## Code Location

- **Main script**: `llamacpp_mqtt_deploy.py` (lines 147-296)
- **LlamaCppClient class**: Uses `OpenAI` client from line 147
- **generate() method**: Lines 196-261
- **Error handling**: Lines 254-261

## Dependencies

```
openai>=1.3.0      # Official OpenAI Python package
paho-mqtt          # MQTT client
fire               # CLI framework
```

`requests` is no longer needed!

## Performance Impact

- **Negligible**: Same underlying HTTP calls, just cleaner API
- **Better**: Automatic retries can reduce failure rates
- **Same**: Inference time unchanged
- **Same**: MQTT latency unchanged

## Next Steps

1. Install the new package: `pip install openai>=1.3.0`
2. Run the deployment script as normal
3. Check `debug_info.log` for detailed request/response logs
4. Monitor performance and error rates

All other functionality remains the same!

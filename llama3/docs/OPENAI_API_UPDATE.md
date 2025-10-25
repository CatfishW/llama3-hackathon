# OpenAI-Compatible Chat Completion API Update

## Overview

Updated `llamacpp_mqtt_deploy.py` to use OpenAI-compatible chat completion API format with `extra_body` parameter for controlling thinking mode, replacing the previous prompt-based `/no_think` directive approach.

## Key Changes

### 1. API Endpoint Change
**Before:**
```
POST /completion (llama.cpp native endpoint)
```

**After:**
```
POST /v1/chat/completions (OpenAI-compatible endpoint)
```

### 2. Request Format
**Before:**
```python
payload = {
    "prompt": "formatted_prompt_string",
    "temperature": 0.6,
    "top_p": 0.9,
    "n_predict": 512,
    "stop": ["</think>", "<think>", "**Final Answer**"]
}
```

**After:**
```python
payload = {
    "model": "default",
    "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "temperature": 0.6,
    "top_p": 0.9,
    "max_tokens": 512,
    "stream": False,
    "extra_body": {
        "enable_thinking": False  # or True
    }
}
```

### 3. Thinking Mode Control
**Before:**
- Used `/no_think` directive injected into prompt
- Used stop tokens: `["</think>", "<think>", "**Final Answer**"]`
- Required post-processing cleanup of thinking output

**After:**
- Uses standard `enable_thinking` parameter via `extra_body`
- No stop tokens needed
- No post-processing cleanup required
- Cleaner and follows OpenAI API standard

```python
# Disable thinking (skip_thinking=True)
payload["extra_body"] = {"enable_thinking": False}

# Enable thinking (skip_thinking=False)
payload["extra_body"] = {"enable_thinking": True}
```

### 4. Methods Removed
Deleted the following methods that are no longer needed:
- `stream_generate()` - Streaming not used in current implementation
- `_clean_qwq_output()` - Output cleaning not needed with proper API parameter

### 5. Response Format
**Before:**
```json
{
  "content": "generated text"
}
```

**After:**
```json
{
  "choices": [
    {
      "message": {
        "content": "generated text"
      }
    }
  ]
}
```

**Parsing:**
```python
# Extract from OpenAI-compatible response
generated_text = result["choices"][0]["message"]["content"]
```

### 6. LlamaCppClient.generate() Signature
**Before:**
```python
def generate(
    self,
    prompt: str,  # Single prompt string
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    debug_info: dict = None
) -> str
```

**After:**
```python
def generate(
    self,
    messages: List[Dict[str, str]],  # Message list
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    debug_info: dict = None
) -> str
```

### 7. format_chat() Method
**Before:**
```python
def format_chat(self, messages: List[Dict[str, str]]) -> str:
    # Concatenated messages into a single prompt string
    return "System: ...\n\nUser: ...\n\nAssistant:"
```

**After:**
```python
def format_chat(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    # Return messages as-is for OpenAI API
    return messages
```

## Benefits

✅ **Cleaner Code**: No prompt injection or string manipulation needed  
✅ **Standard Compliance**: Follows OpenAI API specification  
✅ **Better Compatibility**: Works with any OpenAI-compatible server  
✅ **Simpler Maintenance**: No output cleaning logic required  
✅ **Official Parameter**: Uses `enable_thinking` as documented by Aliyun  
✅ **More Reliable**: Model handles thinking mode natively, not via prompt tricks  

## Usage

### Deploy with Thinking Disabled (Default)
```bash
python llamacpp_mqtt_deploy.py \
  --projects "maze driving bloodcell" \
  --server_url http://localhost:8080 \
  --mqtt_username TangClinic \
  --mqtt_password Tang123
```

### Deploy with Thinking Enabled
```bash
python llamacpp_mqtt_deploy.py \
  --projects general \
  --skip_thinking False \
  --server_url http://localhost:8080
```

## Server Requirements

Your llama.cpp server must support OpenAI-compatible API:

```bash
llama-server -m ./qwen3-30b-a3b-instruct-2507.gguf \
  --jinja \
  -c 32768 \
  -ngl 99 \
  -t 12 \
  --port 8080
```

The `/v1/chat/completions` endpoint should be available at:
```
http://localhost:8080/v1/chat/completions
```

## Debug Logging

The debug log now shows:
- Message format sent to LLM (not prompt concatenation)
- Thinking mode setting (ENABLED/DISABLED)
- Raw LLM output (no cleaning needed)
- Full API response structure

Example log entry:
```
MESSAGES TO LLM:
[
  {"role": "system", "content": "You are..."},
  {"role": "user", "content": "What is..."},
  {"role": "assistant", "content": "..."}
]

LLM OUTPUT:
The answer is...
```

## Migration Checklist

- [x] Updated API endpoint from `/completion` to `/v1/chat/completions`
- [x] Changed request payload to OpenAI format
- [x] Removed stop token logic
- [x] Removed `/no_think` directive injection
- [x] Removed `_clean_qwq_output()` method
- [x] Removed `stream_generate()` method (can be re-added if needed)
- [x] Updated `generate()` to accept messages list
- [x] Updated `format_chat()` to return messages as-is
- [x] Updated SessionManager to pass messages to generate()
- [x] Updated response parsing for OpenAI format
- [x] Tested thinking mode control via `extra_body`

## Backward Compatibility

⚠️ **Breaking Changes:**
- `generate()` method signature changed (now accepts messages list, not prompt string)
- If you have custom code calling `generate()` directly, it needs to be updated

✅ **Compatible:**
- SessionManager and MessageProcessor integration unchanged
- MQTT communication format unchanged
- Configuration parameters unchanged
- Debug logging format similar

## Future Enhancements

- [ ] Add support for streaming via `/v1/chat/completions` with `stream: true`
- [ ] Add support for `thinking_budget` parameter for limiting reasoning length
- [ ] Add support for function calling if server supports it
- [ ] Improve error handling for server-specific response variations

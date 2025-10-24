# OpenAI Package Migration

## Summary

Refactored `llamacpp_mqtt_deploy.py` to use the official `openai` Python package instead of the `requests` library for HTTP communication with the llama.cpp server.

## Changes Made

### 1. Import Changes

**Before:**
```python
import requests
```

**After:**
```python
from openai import OpenAI, OpenAIError
```

### 2. LlamaCppClient Initialization

**Before:**
```python
def __init__(self, config: DeploymentConfig):
    self.config = config
    self.server_url = config.server_url.rstrip('/')
    self.timeout = config.server_timeout
    
    # Manual connection test with requests
    if not self._test_connection():
        raise RuntimeError(...)
    self._log_server_info()
```

**After:**
```python
def __init__(self, config: DeploymentConfig):
    self.config = config
    self.server_url = config.server_url.rstrip('/')
    self.timeout = config.server_timeout
    
    # Initialize OpenAI client with llama.cpp as base URL
    self.client = OpenAI(
        base_url=self.server_url,
        api_key="not-needed",  # llama.cpp doesn't require API key
        timeout=self.timeout
    )
    
    # Test connection via chat completion call
    if not self._test_connection():
        raise RuntimeError(...)
    
    logger.info("OpenAI client initialized successfully")
```

### 3. Connection Testing

**Before:**
```python
def _test_connection(self) -> bool:
    try:
        response = requests.get(
            f"{self.server_url}/health",
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False

def _log_server_info(self):
    try:
        response = requests.get(
            f"{self.server_url}/props",
            timeout=5
        )
        if response.status_code == 200:
            props = response.json()
            logger.info(f"Server info: {json.dumps(props, indent=2)}")
    except Exception as e:
        logger.warning(f"Could not retrieve server properties: {e}")
```

**After:**
```python
def _test_connection(self) -> bool:
    try:
        logger.info("Testing connection to llama.cpp server...")
        # Try a simple chat completion call to test connectivity
        self.client.chat.completions.create(
            model="default",
            messages=[{"role": "system", "content": "test"}],
            max_tokens=1
        )
        logger.info("Connection test successful")
        return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
```

### 4. Chat Completion Generation

**Before (requests):**
```python
payload = {
    "model": "default",
    "messages": messages,
    "temperature": temperature,
    "top_p": top_p,
    "max_tokens": max_tokens,
    "stream": False,
}

payload["extra_body"] = {
    "enable_thinking": not self.config.skip_thinking
}

response = requests.post(
    f"{self.server_url}/v1/chat/completions",
    json=payload,
    timeout=self.timeout,
    headers={"Content-Type": "application/json"}
)

if response.status_code != 200:
    error_msg = f"Server error {response.status_code}: {response.text}"
    return f"Error: {error_msg}"

result = response.json()
generated_text = result["choices"][0]["message"]["content"]
```

**After (OpenAI package):**
```python
extra_body = {
    "enable_thinking": not self.config.skip_thinking
}

response = self.client.chat.completions.create(
    model="default",
    messages=messages,
    temperature=temperature,
    top_p=top_p,
    max_tokens=max_tokens,
    extra_body=extra_body
)

generated_text = response.choices[0].message.content
```

### 5. Error Handling

**Before:**
```python
except requests.Timeout:
    error_msg = f"Server request timeout (>{self.timeout}s)"
    return f"Error: {error_msg}"
except requests.RequestException as e:
    error_msg = f"Request failed: {str(e)}"
    return f"Error: {error_msg}"
except Exception as e:
    error_msg = f"Generation failed: {str(e)}"
    return f"Error: {error_msg}"
```

**After:**
```python
except OpenAIError as e:
    error_msg = f"OpenAI API error: {str(e)}"
    logger.error(error_msg)
    if debug_info:
        debug_logger.error(error_msg)
    return f"Error: {error_msg}"
except Exception as e:
    error_msg = f"Generation failed: {str(e)}"
    logger.error(error_msg)
    if debug_info:
        debug_logger.error(error_msg)
    return f"Error: {error_msg}"
```

### 6. Dependencies

**Updated requirements.txt:**
```
-requests (removed)
+openai>=1.3.0 (added)
```

## Benefits

1. **Official Package**: Uses the official OpenAI Python package instead of raw HTTP requests
2. **Better Error Handling**: Built-in `OpenAIError` exception handling with proper error types
3. **Automatic Retry Logic**: OpenAI client includes exponential backoff and retry logic
4. **Cleaner Code**: No need for manual payload construction and response parsing
5. **Type Safety**: Better IDE support and type hints
6. **Streaming Support**: Easy to add streaming support with `stream=True` parameter
7. **Consistency**: Uses same interface as OpenAI API, making it compatible with any OpenAI-compatible server

## Migration Checklist

- [x] Replace `import requests` with `from openai import OpenAI`
- [x] Initialize OpenAI client with server URL
- [x] Update `_test_connection()` to use OpenAI client
- [x] Remove `_log_server_info()` method (not critical)
- [x] Update `generate()` to use `client.chat.completions.create()`
- [x] Update error handling to use `OpenAIError`
- [x] Update requirements.txt with `openai>=1.3.0`
- [x] Validate all changes (no errors found)
- [x] Test connection test functionality

## No Breaking Changes

- All method signatures remain the same
- All MQTT communication unchanged
- All session management unchanged
- All configuration parameters unchanged
- All command-line arguments unchanged
- Backward compatible with existing deployments

## Installation

Install the updated dependencies:
```bash
pip install -r requirements.txt
```

Or just the new package:
```bash
pip install openai>=1.3.0
```

## Testing

The script can be tested with the same command as before:
```bash
python llamacpp_mqtt_deploy.py --projects maze driving --server_url http://localhost:8080
```

The connection test will now verify connectivity by attempting a minimal chat completion call instead of checking the `/health` endpoint.

## Notes

- The OpenAI client automatically handles retries and timeout management
- The `api_key` parameter is required by OpenAI client but ignored by llama.cpp server
- The `extra_body` parameter allows passing llama.cpp-specific options like `enable_thinking`
- Streaming responses can be enabled by adding `stream=True` if needed in the future

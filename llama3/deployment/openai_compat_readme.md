# OpenAI-Compatible Proxy for llama.cpp

This small FastAPI server exposes OpenAI-style endpoints and proxies requests to your local llama.cpp HTTP server. It supports both non-streaming and streaming (SSE) responses.

## Why

- Keep your application code unchanged by pointing the OpenAI SDK to this proxy using `base_url`.
- Add simple API key auth, CORS, and config without modifying llama.cpp.

## Configure

Create a `.env` (optional) next to the repo root or set env vars:

- `LLAMA_BASE_URL` (default `http://127.0.0.1:8080`) — where llama.cpp `llama-server` is listening
- `DEFAULT_MODEL` (default `qwen3-30b-a3b-instruct`) — model id to expose via `/v1/models`
- `API_KEYS` (optional) — comma-separated keys to require `Authorization: Bearer <key>`

Example `.env`:

```
LLAMA_BASE_URL=http://127.0.0.1:8080
DEFAULT_MODEL=qwen3-30b-a3b-instruct
API_KEYS=sk-local-abc
```

## Install

```
pip install -r requirements.txt
```

## Run

```
uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000
```

Your OpenAI-compatible base URL is now: `http://localhost:8000/v1`.

## Use with OpenAI Python SDK

```python
from openai import OpenAI
client = OpenAI(api_key="sk-local-abc", base_url="http://localhost:8000/v1")
resp = client.chat.completions.create(
    model="qwen3-30b-a3b-instruct",
    messages=[{"role":"user","content":"Hello"}],
)
print(resp.choices[0].message.content)
```

### Streaming example

```python
from openai import OpenAI
client = OpenAI(api_key="sk-local-abc", base_url="http://localhost:8000/v1")
with client.chat.completions.stream(
    model="qwen3-30b-a3b-instruct",
    messages=[{"role":"user","content":"Write a haiku about llamas"}],
) as stream:
    for event in stream:
        if event.type == "content.delta":
            print(event.delta, end="", flush=True)
```

## cURL

```
# Non-stream
curl -H "Authorization: Bearer sk-local-abc" -H "Content-Type: application/json" -d '{
  "model":"qwen3-30b-a3b-instruct",
  "messages":[{"role":"user","content":"Hello"}]
}' http://localhost:8000/v1/chat/completions

# Stream
curl -N -H "Authorization: Bearer sk-local-abc" -H "Content-Type: application/json" -d '{
  "model":"qwen3-30b-a3b-instruct",
  "messages":[{"role":"user","content":"Stream?"}],
  "stream": true
}' http://localhost:8000/v1/chat/completions
```

## Notes

- This proxy makes a best-effort mapping between OpenAI fields and llama.cpp. Adjust in `deployment/openai_compat_server.py` as needed.
- For remote usage over reverse SSH + SSE, expose the proxy port locally and forward it through your tunnel. The proxy keeps `text/event-stream` intact for streaming.
- If your upstream llama.cpp uses different endpoints or field names, tweak the `llama_completion` function.

"""
OpenAI-compatible API proxy for local llama.cpp server.

- Exposes /v1/chat/completions, /v1/completions, /v1/models
- Supports both HTTP and HTTPS upstream connections
- Supports serving over HTTPS (required for browsers on HTTPS pages)
- Streams via SSE like OpenAI when stream=True
- Config via env vars or .env:
    LLAMA_BASE_URL=http://127.0.0.1:8080     # or https://... for SSL
    API_KEYS=sk-local-abc,sk-local-def       # optional comma-separated list; if set, require Bearer token
    DEFAULT_MODEL=qwen3-30b-a3b-instruct
    REQUEST_TIMEOUT=300                       # request timeout in seconds
    CONNECT_TIMEOUT=30                        # connection timeout in seconds
    
    # Upstream SSL/TLS Configuration (for connecting to llama.cpp)
    SSL_VERIFY=true                           # set to "false" for self-signed certs
    SSL_CA_BUNDLE=/path/to/ca-bundle.crt     # optional custom CA bundle
    SSL_CLIENT_CERT=/path/to/client.crt      # optional client certificate
    SSL_CLIENT_KEY=/path/to/client.key       # optional client key
    
    # Server SSL/TLS Configuration (for serving HTTPS to clients)
    SERVER_SSL_CERT=/path/to/server.crt      # SSL certificate for this server
    SERVER_SSL_KEY=/path/to/server.key       # SSL private key for this server

Run (HTTP):
    uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000

Run (HTTPS - required when clients connect from HTTPS pages):
    uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000 \\
        --ssl-keyfile=/path/to/server.key --ssl-certfile=/path/to/server.crt

    Or use environment variables:
        SERVER_SSL_CERT=/path/to/server.crt SERVER_SSL_KEY=/path/to/server.key \\
        python -m deployment.openai_compat_server

Quick self-signed cert for testing:
    openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt -days 365 -nodes \\
        -subj "/C=US/ST=State/L=City/O=Organization/CN=173.61.35.162"

Use with OpenAI SDK (python):
    from openai import OpenAI
    client = OpenAI(api_key="sk-local-abc", base_url="https://173.61.35.162:8000/v1")
    client.chat.completions.create(model="qwen3-30b-a3b-instruct", messages=[{"role":"user","content":"Hello"}])
"""
from __future__ import annotations

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator, List, Union

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()

# ---------- Configuration ----------
LLAMA_BASE_URL = os.getenv("LLAMA_BASE_URL", "http://127.0.0.1:8888").rstrip("/")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen3-vl-30b-a3b-instruct")
API_KEYS = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "300"))
CONNECT_TIMEOUT = float(os.getenv("CONNECT_TIMEOUT", "30"))
# Max characters for messages (rough estimate: 4 chars ≈ 1 token, 8192 tokens = ~32000 chars)
MAX_CONTEXT_CHARS = int(os.getenv("MAX_CONTEXT_CHARS", "24000"))
# SSL/TLS Configuration
# Set to "false" to disable SSL verification (for self-signed certs)
SSL_VERIFY = os.getenv("SSL_VERIFY", "true").lower() not in ("false", "0", "no")
# Optional: Path to CA bundle or client certificate
SSL_CA_BUNDLE = os.getenv("SSL_CA_BUNDLE", None)
SSL_CLIENT_CERT = os.getenv("SSL_CLIENT_CERT", None)
SSL_CLIENT_KEY = os.getenv("SSL_CLIENT_KEY", None)

# Server SSL/TLS Configuration (for serving HTTPS to clients)
# Required when clients connect from HTTPS pages to avoid mixed content errors
SERVER_SSL_CERT = os.getenv("SERVER_SSL_CERT", None)
SERVER_SSL_KEY = os.getenv("SERVER_SSL_KEY", None)
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = 28888

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------- Shared HTTP Client ----------
http_client: httpx.AsyncClient | None = None


def _create_ssl_context() -> httpx.Client | bool:
    """Create SSL context based on configuration."""
    if not SSL_VERIFY:
        logger.warning("SSL verification is DISABLED - not recommended for production")
        return False
    
    if SSL_CA_BUNDLE:
        import ssl
        ctx = ssl.create_default_context(cafile=SSL_CA_BUNDLE)
        if SSL_CLIENT_CERT:
            ctx.load_cert_chain(SSL_CLIENT_CERT, SSL_CLIENT_KEY)
        return ctx
    
    return True  # Use default SSL verification


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage shared HTTP client lifecycle."""
    global http_client
    timeout = httpx.Timeout(REQUEST_TIMEOUT, connect=CONNECT_TIMEOUT)
    ssl_context = _create_ssl_context()
    
    http_client = httpx.AsyncClient(
        timeout=timeout,
        verify=ssl_context,
        follow_redirects=True,
    )
    
    protocol = "https" if LLAMA_BASE_URL.startswith("https://") else "http"
    logger.info(f"Proxy started, upstream: {LLAMA_BASE_URL} (protocol: {protocol}, ssl_verify: {SSL_VERIFY})")
    yield
    await http_client.aclose()
    logger.info("Proxy shutdown")


app = FastAPI(
    title="OpenAI-Compatible Proxy for llama.cpp",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Security ----------
async def verify_auth(request: Request) -> None:
    """Verify Bearer token if API_KEYS is configured."""
    if not API_KEYS:
        return
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = auth.removeprefix("Bearer ").strip()
    if token not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")


# ---------- Schemas ----------
class ToolFunction(BaseModel):
    """Function definition for a tool."""
    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None


class Tool(BaseModel):
    """Tool definition (OpenAI format)."""
    type: str = "function"
    function: ToolFunction


class ToolCallFunction(BaseModel):
    """Function call within a tool call."""
    name: str
    arguments: str  # JSON string of arguments


class ToolCall(BaseModel):
    """Tool call in assistant message."""
    id: str
    type: str = "function"
    function: ToolCallFunction


class ChatMessage(BaseModel):
    """Chat message with optional tool call support."""
    role: str
    content: Union[str, List[Any], None] = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None  # For tool response messages
    name: str | None = None  # Function name for tool responses


class ChatCompletionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model: str | None = None
    messages: list[ChatMessage]
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = Field(default=None, alias="max_tokens")
    stop: list[str] | str | None = None
    n: int = 1
    presence_penalty: float | None = None
    stream: bool = False
    # Tool calling support
    tools: list[Tool] | None = None
    tool_choice: str | dict[str, Any] | None = None  # "auto", "none", "required", or {"type": "function", "function": {"name": "..."}}
    parallel_tool_calls: bool | None = None


class CompletionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model: str | None = None
    prompt: str
    temperature: float | None = None
    top_p: float | None = None
    max_tokens: int | None = None
    stop: list[str] | str | None = None
    n: int = 1
    presence_penalty: float | None = None
    stream: bool = False


# ---------- llama.cpp Client Helpers ----------
def _truncate_messages(messages: list[dict[str, Any]], max_chars: int) -> list[dict[str, Any]]:
    """Truncate conversation history to fit within context limit.
    
    Strategy: Keep system message (first) + most recent messages.
    Multimodal messages (content is a list) are not truncated.
    """
    if not messages:
        return messages
    
    # Calculate total chars, treating multimodal content as 0 chars (not truncatable)
    total_chars = sum(len(m.get("content", "")) if isinstance(m.get("content"), str) else 0 for m in messages)
    if total_chars <= max_chars:
        return messages
    
    logger.warning(f"Truncating messages: {total_chars} chars -> {max_chars} chars limit")
    
    # Always keep system message if present
    system_msg = None
    other_msgs = list(messages)
    if messages and messages[0].get("role") == "system":
        system_msg = messages[0]
        other_msgs = messages[1:]
    
    # Calculate available space (multimodal content counts as 0)
    system_content = system_msg.get("content", "") if system_msg else ""
    system_chars = len(system_content) if isinstance(system_content, str) else 0
    available = max_chars - system_chars
    
    # Keep most recent messages that fit
    kept = []
    for msg in reversed(other_msgs):
        content = msg.get("content")
        # Multimodal messages (list content) are always kept without truncation
        if isinstance(content, list):
            kept.insert(0, msg)
            continue
        msg_chars = len(content) if content else 0
        if available >= msg_chars:
            kept.insert(0, msg)
            available -= msg_chars
        else:
            # Truncate this message if it's the last user message and nothing else fits
            if not kept and msg.get("role") == "user" and isinstance(content, str):
                truncated_content = content[:available - 100] + "\n...[truncated]"
                kept.insert(0, {"role": msg["role"], "content": truncated_content})
            break
    
    result = ([system_msg] if system_msg else []) + kept
    logger.info(f"Kept {len(result)}/{len(messages)} messages after truncation")
    return result


def _serialize_messages(messages: list[Any]) -> list[dict[str, Any]]:
    """Convert messages to plain dicts for JSON serialization.
    
    Preserves content as-is (string or list for multimodal).
    Handles tool calls and tool responses.
    """
    result = []
    for msg in messages:
        if isinstance(msg, dict):
            serialized = {"role": msg.get("role", ""), "content": msg.get("content")}
            # Preserve tool-related fields
            if msg.get("tool_calls"):
                serialized["tool_calls"] = msg["tool_calls"]
            if msg.get("tool_call_id"):
                serialized["tool_call_id"] = msg["tool_call_id"]
            if msg.get("name"):
                serialized["name"] = msg["name"]
            result.append(serialized)
        elif hasattr(msg, "model_dump"):
            dumped = msg.model_dump(exclude_none=True)
            result.append(dumped)
        else:
            # Fallback for other object types - preserve content type
            content = getattr(msg, "content", "")
            serialized = {"role": str(getattr(msg, "role", "")), "content": content}
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                serialized["tool_calls"] = [tc.model_dump() if hasattr(tc, "model_dump") else tc for tc in msg.tool_calls]
            if hasattr(msg, "tool_call_id") and msg.tool_call_id:
                serialized["tool_call_id"] = msg.tool_call_id
            if hasattr(msg, "name") and msg.name:
                serialized["name"] = msg.name
            result.append(serialized)
    return result


def _serialize_tools(tools: list[Any] | None) -> list[dict[str, Any]] | None:
    """Serialize tools to plain dicts."""
    if not tools:
        return None
    result = []
    for tool in tools:
        if isinstance(tool, dict):
            result.append(tool)
        elif hasattr(tool, "model_dump"):
            result.append(tool.model_dump(exclude_none=True))
        else:
            result.append({"type": "function", "function": tool})
    return result


def _build_llama_payload(payload: dict[str, Any], is_chat: bool, stream: bool) -> dict[str, Any]:
    """Build llama.cpp-compatible payload from OpenAI-style request."""
    if is_chat:
        messages = _serialize_messages(payload.get("messages", []))
        messages = _truncate_messages(messages, MAX_CONTEXT_CHARS)
        mapped = {
            "messages": messages,
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            "max_tokens": payload.get("max_tokens"),
            "stop": payload.get("stop"),
            "stream": stream,
            "n": payload.get("n", 1),
            "repeat_penalty": payload.get("presence_penalty"),
            # Tool calling support
            "tools": _serialize_tools(payload.get("tools")),
            "tool_choice": payload.get("tool_choice"),
            "parallel_tool_calls": payload.get("parallel_tool_calls"),
        }
    else:
        mapped = {
            "prompt": payload.get("prompt", ""),
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            "max_tokens": payload.get("max_tokens"),
            "n_predict": payload.get("max_tokens"),  # llama.cpp alternate field
            "stop": payload.get("stop"),
            "stream": stream,
            "n": payload.get("n", 1),
            "repeat_penalty": payload.get("presence_penalty"),
        }
    return {k: v for k, v in mapped.items() if v is not None}


def _extract_response_data(result: dict[str, Any], is_chat: bool) -> tuple[str | None, list[dict] | None, str | None]:
    """Extract content, tool_calls, and finish_reason from llama.cpp response.
    
    Returns: (content, tool_calls, finish_reason)
    """
    if is_chat:
        # Try to get from choices first (OpenAI format)
        choices = result.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content")
            tool_calls = message.get("tool_calls")
            finish_reason = choices[0].get("finish_reason", "stop")
            return content, tool_calls, finish_reason
        
        # Fallback to direct fields (llama.cpp format)
        content = result.get("content") or result.get("message", {}).get("content")
        tool_calls = result.get("tool_calls") or result.get("message", {}).get("tool_calls")
        finish_reason = result.get("finish_reason", "stop")
        return content, tool_calls, finish_reason
    
    # Non-chat completions
    content = (
        result.get("content")
        or result.get("text")
        or result.get("choices", [{}])[0].get("text")
        or ""
    )
    return content, None, "stop"


def _extract_chunk_data(obj: dict[str, Any], is_chat: bool) -> tuple[str | None, list[dict] | None, str | None]:
    """Extract content, tool_calls delta, and finish_reason from a streaming chunk.
    
    Returns: (content, tool_calls, finish_reason)
    """
    if is_chat:
        choices = obj.get("choices", [])
        if choices:
            delta = choices[0].get("delta", {})
            content = delta.get("content")
            tool_calls = delta.get("tool_calls")
            finish_reason = choices[0].get("finish_reason")
            return content, tool_calls, finish_reason
        
        # Fallback to direct content
        content = obj.get("content")
        tool_calls = obj.get("tool_calls")
        finish_reason = obj.get("finish_reason")
        return content, tool_calls, finish_reason
    
    # Non-chat
    content = (
        obj.get("content")
        or obj.get("text")
        or obj.get("choices", [{}])[0].get("text")
        or ""
    )
    return content, None, None


async def _stream_upstream(
    url: str,
    payload: dict[str, Any],
    model: str,
    is_chat: bool,
) -> AsyncGenerator[bytes, None]:
    """Stream responses from llama.cpp and convert to OpenAI SSE format.
    
    Handles both text content and tool calls in streaming responses.
    """
    start_time = time.time()
    id_prefix = "chatcmpl" if is_chat else "cmpl"
    object_type = "chat.completion.chunk" if is_chat else "text_completion.chunk"
    accumulated_finish_reason = None
    
    try:
        async with http_client.stream("POST", url, json=payload) as response:
            if response.status_code >= 400:
                error_text = await response.aread()
                logger.error(f"Upstream stream error {response.status_code}: {error_text.decode()[:500]}")
                yield f"data: {json.dumps({'error': {'message': f'Upstream error: {error_text.decode()[:200]}'}})}\n\n".encode()
                return
            async for line in response.aiter_lines():
                if not line:
                    continue

                data = line.removeprefix("data: ").strip()
                if data == "[DONE]":
                    if is_chat:
                        # Send final chunk with finish_reason
                        final_reason = accumulated_finish_reason or "stop"
                        done_chunk = {
                            "id": f"{id_prefix}-{int(start_time)}",
                            "object": object_type,
                            "choices": [{"delta": {}, "index": 0, "finish_reason": final_reason}],
                        }
                        yield f"data: {json.dumps(done_chunk)}\n\n".encode()
                    yield b"data: [DONE]\n\n"
                    break

                try:
                    obj = json.loads(data)
                    content, tool_calls, finish_reason = _extract_chunk_data(obj, is_chat)
                    if finish_reason:
                        accumulated_finish_reason = finish_reason
                except json.JSONDecodeError:
                    content = data
                    tool_calls = None
                    finish_reason = None

                if is_chat:
                    # Build delta with content and/or tool_calls
                    delta = {}
                    if content:
                        delta["content"] = content
                    if tool_calls:
                        delta["tool_calls"] = tool_calls
                    
                    # Skip empty deltas unless we have a finish_reason
                    if not delta and not finish_reason:
                        continue
                    
                    chunk = {
                        "id": f"{id_prefix}-{int(start_time)}",
                        "object": object_type,
                        "created": int(start_time),
                        "model": model,
                        "choices": [{"delta": delta, "index": 0, "finish_reason": finish_reason}],
                    }
                else:
                    chunk = {
                        "id": f"{id_prefix}-{int(start_time)}",
                        "object": object_type,
                        "model": model,
                        "choices": [{"text": content or "", "index": 0, "finish_reason": finish_reason}],
                    }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode()

    except httpx.ConnectError as e:
        logger.error(f"Connection error to upstream {url}: {e}")
        yield f"data: {json.dumps({'error': {'message': f'Connection failed: {str(e)}', 'type': 'connection_error'}})}\n\n".encode()
    except httpx.TimeoutException as e:
        logger.error(f"Timeout connecting to upstream {url}: {e}")
        yield f"data: {json.dumps({'error': {'message': f'Request timeout: {str(e)}', 'type': 'timeout_error'}})}\n\n".encode()
    except httpx.HTTPError as e:
        logger.error(f"HTTP error from upstream: {e}")
        yield f"data: {json.dumps({'error': {'message': str(e), 'type': 'http_error'}})}\n\n".encode()


def _streaming_response(generator: AsyncGenerator[bytes, None]) -> StreamingResponse:
    """Create a StreamingResponse with SSE headers."""
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ---------- Endpoints ----------
@app.get("/")
async def root():
    """Root endpoint showing proxy status."""
    return {"status": "ok", "upstream": LLAMA_BASE_URL}


@app.get("/health")
async def health():
    """Health check endpoint with upstream connectivity test."""
    upstream_ok = False
    upstream_error = None
    try:
        response = await http_client.get(f"{LLAMA_BASE_URL}/health", timeout=5.0)
        upstream_ok = response.status_code < 400
    except httpx.HTTPError as e:
        upstream_error = str(e)
    except Exception as e:
        upstream_error = f"Unexpected error: {e}"
    
    return {
        "status": "healthy" if upstream_ok else "degraded",
        "upstream": {
            "url": LLAMA_BASE_URL,
            "connected": upstream_ok,
            "error": upstream_error,
        },
        "ssl_verify": SSL_VERIFY,
    }


@app.get("/v1/models")
async def list_models(_: None = Depends(verify_auth)):
    """List available models, querying upstream if possible."""
    try:
        response = await http_client.get(f"{LLAMA_BASE_URL}/v1/models")
        if response.status_code == 200:
            return response.json()
    except httpx.HTTPError as e:
        logger.debug(f"Failed to fetch models from upstream: {e}")

    return {
        "object": "list",
        "data": [
            {
                "id": DEFAULT_MODEL,
                "object": "model",
                "owned_by": "local-llamacpp",
            }
        ],
    }


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, _: None = Depends(verify_auth)):
    """Handle chat completion requests (OpenAI-compatible)."""
    model = req.model or DEFAULT_MODEL
    payload = req.model_dump(by_alias=True)
    llama_payload = _build_llama_payload(payload, is_chat=True, stream=req.stream)
    url = f"{LLAMA_BASE_URL}/v1/chat/completions"

    logger.debug(f"Sending to {url}: {json.dumps(llama_payload, default=str)[:500]}")

    if req.stream:
        return _streaming_response(_stream_upstream(url, llama_payload, model, is_chat=True))

    try:
        response = await http_client.post(url, json=llama_payload)
        response.raise_for_status()
        result = response.json()
    except httpx.ConnectError as e:
        logger.error(f"Connection error to upstream: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to upstream server: {e}")
    except httpx.TimeoutException as e:
        logger.error(f"Timeout error: {e}")
        raise HTTPException(status_code=504, detail=f"Upstream request timeout: {e}")
    except httpx.HTTPStatusError as e:
        error_body = e.response.text[:500] if e.response else "No response body"
        logger.error(f"Upstream error {e.response.status_code}: {error_body}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Upstream error: {error_body}")

    content, tool_calls, finish_reason = _extract_response_data(result, is_chat=True)
    
    # Build the response message
    message: dict[str, Any] = {"role": "assistant"}
    if content is not None:
        message["content"] = content
    if tool_calls:
        message["tool_calls"] = tool_calls
        # When there are tool calls, finish_reason should be "tool_calls"
        if finish_reason == "stop":
            finish_reason = "tool_calls"
    
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {"index": 0, "message": message, "finish_reason": finish_reason}
        ],
        "usage": result.get("usage", {}),
    }


@app.post("/v1/completions")
async def completions(req: CompletionRequest, _: None = Depends(verify_auth)):
    """Handle text completion requests (OpenAI-compatible)."""
    model = req.model or DEFAULT_MODEL
    payload = req.model_dump(by_alias=True)
    llama_payload = _build_llama_payload(payload, is_chat=False, stream=req.stream)
    url = f"{LLAMA_BASE_URL}/v1/completions"

    logger.debug(f"Sending to {url}: {json.dumps(llama_payload, default=str)[:500]}")

    if req.stream:
        return _streaming_response(_stream_upstream(url, llama_payload, model, is_chat=False))

    try:
        response = await http_client.post(url, json=llama_payload)
        response.raise_for_status()
        result = response.json()
    except httpx.ConnectError as e:
        logger.error(f"Connection error to upstream: {e}")
        raise HTTPException(status_code=503, detail=f"Cannot connect to upstream server: {e}")
    except httpx.TimeoutException as e:
        logger.error(f"Timeout error: {e}")
        raise HTTPException(status_code=504, detail=f"Upstream request timeout: {e}")
    except httpx.HTTPStatusError as e:
        error_body = e.response.text[:500] if e.response else "No response body"
        logger.error(f"Upstream error {e.response.status_code}: {error_body}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Upstream error: {error_body}")

    content, _, finish_reason = _extract_response_data(result, is_chat=False)
    return {
        "id": f"cmpl-{int(time.time())}",
        "object": "text_completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"text": content or "", "index": 0, "finish_reason": finish_reason or "stop"}],
        "usage": result.get("usage", {}),
    }


# ---------- Main Entry Point ----------
if __name__ == "__main__":
    import uvicorn
    
    ssl_kwargs = {}
    if SERVER_SSL_CERT and SERVER_SSL_KEY:
        ssl_kwargs = {
            "ssl_certfile": SERVER_SSL_CERT,
            "ssl_keyfile": SERVER_SSL_KEY,
        }
        logger.info(f"Starting HTTPS server on {SERVER_HOST}:{SERVER_PORT}")
    else:
        logger.info(f"Starting HTTP server on {SERVER_HOST}:{SERVER_PORT}")
        logger.warning(
            "Running without HTTPS. Browsers on HTTPS pages will block requests. "
            "Set SERVER_SSL_CERT and SERVER_SSL_KEY to enable HTTPS."
        )
    
    uvicorn.run(
        app,
        host=SERVER_HOST,
        port=SERVER_PORT,
        **ssl_kwargs,
    )

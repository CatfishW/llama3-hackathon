"""
OpenAI-compatible API proxy for local llama.cpp server.

- Exposes /v1/chat/completions, /v1/completions, /v1/models
- Streams via SSE like OpenAI when stream=True
- Config via env vars or .env:
    LLAMA_BASE_URL=http://127.0.0.1:8080
    API_KEYS=sk-local-abc,sk-local-def          # optional comma-separated list; if set, require Bearer token
    DEFAULT_MODEL=qwen3-30b-a3b-instruct

Run:
    uvicorn deployment.openai_compat_server:app --host 0.0.0.0 --port 8000

Use with OpenAI SDK (python):
    from openai import OpenAI
    client = OpenAI(api_key="sk-local-abc", base_url="http://localhost:8000/v1")
    client.chat.completions.create(model="qwen3-30b-a3b-instruct", messages=[{"role":"user","content":"Hello"}])
"""
from __future__ import annotations

import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import httpx
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

load_dotenv()

# ---------- Configuration ----------
LLAMA_BASE_URL = os.getenv("LLAMA_BASE_URL", "http://127.0.0.1:8080")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen3-30b-a3b-instruct")
API_KEYS = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "300"))

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ---------- Shared HTTP Client ----------
http_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage shared HTTP client lifecycle."""
    global http_client
    timeout = httpx.Timeout(REQUEST_TIMEOUT, connect=30.0)
    http_client = httpx.AsyncClient(timeout=timeout)
    logger.info(f"Proxy started, upstream: {LLAMA_BASE_URL}")
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
class ChatMessage(BaseModel):
    role: str
    content: str


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
def _build_llama_payload(payload: dict[str, Any], is_chat: bool, stream: bool) -> dict[str, Any]:
    """Build llama.cpp-compatible payload from OpenAI-style request."""
    if is_chat:
        mapped = {
            "messages": payload.get("messages", []),
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            "max_tokens": payload.get("max_tokens"),
            "stop": payload.get("stop"),
            "stream": stream,
            "n": payload.get("n", 1),
            "repeat_penalty": payload.get("presence_penalty"),
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


def _extract_text_from_response(result: dict[str, Any], is_chat: bool) -> str:
    """Extract text content from llama.cpp response."""
    if is_chat:
        return (
            result.get("content")
            or result.get("message", {}).get("content")
            or result.get("choices", [{}])[0].get("message", {}).get("content")
            or ""
        )
    return (
        result.get("content")
        or result.get("text")
        or result.get("choices", [{}])[0].get("text")
        or ""
    )


def _extract_text_from_chunk(obj: dict[str, Any], is_chat: bool) -> str:
    """Extract text from a streaming chunk."""
    if is_chat:
        return (
            obj.get("content")
            or obj.get("choices", [{}])[0].get("delta", {}).get("content")
            or ""
        )
    return (
        obj.get("content")
        or obj.get("text")
        or obj.get("choices", [{}])[0].get("text")
        or ""
    )


async def _stream_upstream(
    url: str,
    payload: dict[str, Any],
    model: str,
    is_chat: bool,
) -> AsyncGenerator[bytes, None]:
    """Stream responses from llama.cpp and convert to OpenAI SSE format."""
    start_time = time.time()
    id_prefix = "chatcmpl" if is_chat else "cmpl"
    object_type = "chat.completion.chunk" if is_chat else "text_completion.chunk"
    
    try:
        async with http_client.stream("POST", url, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue

                data = line.removeprefix("data: ").strip()
                if data == "[DONE]":
                    if is_chat:
                        done_chunk = {
                            "id": f"{id_prefix}-{int(start_time)}",
                            "object": object_type,
                            "choices": [{"delta": {}, "index": 0, "finish_reason": "stop"}],
                        }
                        yield f"data: {json.dumps(done_chunk)}\n\n".encode()
                    yield b"data: [DONE]\n\n"
                    break

                try:
                    obj = json.loads(data)
                    text = _extract_text_from_chunk(obj, is_chat)
                except json.JSONDecodeError:
                    text = data

                if is_chat:
                    chunk = {
                        "id": f"{id_prefix}-{int(start_time)}",
                        "object": object_type,
                        "created": int(start_time),
                        "model": model,
                        "choices": [{"delta": {"content": text}, "index": 0, "finish_reason": None}],
                    }
                else:
                    chunk = {
                        "id": f"{id_prefix}-{int(start_time)}",
                        "object": object_type,
                        "model": model,
                        "choices": [{"text": text, "index": 0, "finish_reason": None}],
                    }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode()

    except httpx.HTTPError as e:
        logger.error(f"Upstream error: {e}")
        yield f"data: {json.dumps({'error': {'message': str(e)}})}\n\n".encode()


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
    """Health check endpoint."""
    return {"status": "healthy"}


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
    url = f"{LLAMA_BASE_URL}/chat/completions"

    if req.stream:
        return _streaming_response(_stream_upstream(url, llama_payload, model, is_chat=True))

    try:
        response = await http_client.post(url, json=llama_payload)
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))

    text = _extract_text_from_response(result, is_chat=True)
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
        ],
        "usage": result.get("usage", {}),
    }


@app.post("/v1/completions")
async def completions(req: CompletionRequest, _: None = Depends(verify_auth)):
    """Handle text completion requests (OpenAI-compatible)."""
    model = req.model or DEFAULT_MODEL
    payload = req.model_dump(by_alias=True)
    llama_payload = _build_llama_payload(payload, is_chat=False, stream=req.stream)
    url = f"{LLAMA_BASE_URL}/completion"

    if req.stream:
        return _streaming_response(_stream_upstream(url, llama_payload, model, is_chat=False))

    try:
        response = await http_client.post(url, json=llama_payload)
        response.raise_for_status()
        result = response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))

    text = _extract_text_from_response(result, is_chat=False)
    return {
        "id": f"cmpl-{int(time.time())}",
        "object": "text_completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"text": text, "index": 0, "finish_reason": "stop"}],
        "usage": result.get("usage", {}),
    }

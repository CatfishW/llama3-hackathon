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
import os
import json
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

LLAMA_BASE_URL = os.getenv("LLAMA_BASE_URL", "http://127.0.0.1:8080")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen3-30b-a3b-instruct")
API_KEYS = [k.strip() for k in os.getenv("API_KEYS", "").split(",") if k.strip()]

app = FastAPI(title="OpenAI-Compatible Proxy for llama.cpp", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Security ----------
async def verify_auth(request: Request):
    if not API_KEYS:
        return
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = auth[len("Bearer ") :].strip()
    if token not in API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid API key")

# ---------- llama.cpp Client Helpers ----------

async def llama_completion(payload: Dict[str, Any], stream: bool = False) -> Any:
    """Calls llama.cpp /completion or /chat/completions depending on input.

    llama.cpp server endpoints (as of 2024/2025) typically expose:
    - POST /completion             (prompt, stream)
    - POST /chat/completions       (messages, stream)
    - GET  /v1/models or /models   (optional)
    This proxy normalizes to OpenAI shape.
    """
    endpoint = "/chat/completions" if "messages" in payload else "/completion"
    url = f"{LLAMA_BASE_URL}{endpoint}"

    # Map OpenAI-like fields to llama.cpp
    mapped = {}
    if endpoint == "/completion":
        # text completion
        mapped = {
            "prompt": payload.get("prompt", ""),
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            # llama.cpp sometimes expects n_predict for /completion
            "max_tokens": payload.get("max_tokens"),
            "n_predict": payload.get("max_tokens"),
            "stop": payload.get("stop"),
            "stream": stream,
            "n": payload.get("n", 1),
            "repeat_penalty": payload.get("presence_penalty"),
        }
    else:
        # chat
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

    # remove None values
    mapped = {k: v for k, v in mapped.items() if v is not None}

    timeout = httpx.Timeout(300.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        if stream:
            # Expect server-sent event stream (data: {...}\n\n)
            resp = await client.post(url, json=mapped)
            resp.raise_for_status()
            return resp.aiter_lines()
        else:
            resp = await client.post(url, json=mapped)
            resp.raise_for_status()
            return resp.json()

# ---------- Schemas (subset) ----------

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = Field(default=None, alias="max_tokens")
    stop: Optional[List[str] | str] = None
    n: Optional[int] = 1
    presence_penalty: Optional[float] = None
    stream: Optional[bool] = False

class CompletionRequest(BaseModel):
    model: Optional[str] = None
    prompt: str
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    stop: Optional[List[str] | str] = None
    n: Optional[int] = 1
    presence_penalty: Optional[float] = None
    stream: Optional[bool] = False

# ---------- OpenAI-compatible Endpoints ----------

@app.get("/v1/models")
async def list_models(_: Any = Depends(verify_auth)):
    # Best effort: query llama.cpp if available
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(f"{LLAMA_BASE_URL}/v1/models")
            if r.status_code == 200:
                data = r.json()
                return data
    except Exception:
        pass
    # Fallback static
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
async def chat_completions(req: ChatCompletionRequest, _: Any = Depends(verify_auth)):
    model = req.model or DEFAULT_MODEL
    payload = req.model_dump(by_alias=True)
    payload["model"] = model

    if req.stream:
        async def event_generator() -> AsyncGenerator[bytes, None]:
            start_time = time.time()
            try:
                upstream = await llama_completion(payload, stream=True)
                async for line in upstream:
                    if not line:
                        continue
                    # Forward as OpenAI delta chunks
                    if line.startswith("data: "):
                        data = line[len("data: "):]
                    else:
                        data = line

                    if data.strip() == "[DONE]":
                        yield b"data: {\"id\": \"chatcmpl-done\", \"choices\": [{\"delta\": {}, \"finish_reason\": \"stop\"}]}\n\n"
                        break

                    try:
                        obj = json.loads(data)
                    except Exception:
                        # send as-is in a text delta
                        chunk = {
                            "id": f"chatcmpl-{int(start_time)}",
                            "object": "chat.completion.chunk",
                            "choices": [
                                {"delta": {"content": data}, "index": 0, "finish_reason": None}
                            ],
                        }
                        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8")
                        continue

                    # Map llama.cpp chunk to OpenAI delta
                    text = obj.get("content") or obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if text is None:
                        text = ""
                    chunk = {
                        "id": f"chatcmpl-{int(start_time)}",
                        "object": "chat.completion.chunk",
                        "created": int(start_time),
                        "model": model,
                        "choices": [
                            {"delta": {"content": text}, "index": 0, "finish_reason": None}
                        ],
                    }
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8")
            except httpx.HTTPError as e:
                err = {"error": {"message": str(e)}}
                yield f"data: {json.dumps(err)}\n\n".encode("utf-8")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # non-streaming
    try:
        result = await llama_completion(payload, stream=False)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))

    # Map to OpenAI shape
    text = None
    if isinstance(result, dict):
        # try chat-like response structures
        text = (
            result.get("content")
            or result.get("message", {}).get("content")
            or result.get("choices", [{}])[0].get("message", {}).get("content")
        )
    if text is None:
        text = ""

    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}
        ],
        "usage": result.get("usage", {}) if isinstance(result, dict) else {},
    }

@app.post("/v1/completions")
async def completions(req: CompletionRequest, _: Any = Depends(verify_auth)):
    model = req.model or DEFAULT_MODEL
    payload = req.model_dump(by_alias=True)
    payload["model"] = model

    if req.stream:
        async def event_generator() -> AsyncGenerator[bytes, None]:
            start_time = time.time()
            try:
                upstream = await llama_completion(payload, stream=True)
                async for line in upstream:
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data = line[len("data: "):]
                    else:
                        data = line
                    if data.strip() == "[DONE]":
                        yield b"data: [DONE]\n\n"
                        break
                    try:
                        obj = json.loads(data)
                    except Exception:
                        text = data
                    else:
                        text = obj.get("content") or obj.get("text") or obj.get("choices", [{}])[0].get("text", "")
                    chunk = {
                        "id": f"cmpl-{int(start_time)}",
                        "object": "text_completion.chunk",
                        "choices": [{"text": text, "index": 0, "finish_reason": None}],
                        "model": model,
                    }
                    yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode("utf-8")
            except httpx.HTTPError as e:
                err = {"error": {"message": str(e)}}
                yield f"data: {json.dumps(err)}\n\n".encode("utf-8")

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # non-streaming
    try:
        result = await llama_completion(payload, stream=False)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))

    text = None
    if isinstance(result, dict):
        text = result.get("content") or result.get("text") or result.get("choices", [{}])[0].get("text")
    if text is None:
        text = ""

    return {
        "id": f"cmpl-{int(time.time())}",
        "object": "text_completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{"text": text, "index": 0, "finish_reason": "stop"}],
        "usage": result.get("usage", {}) if isinstance(result, dict) else {},
    }

@app.get("/")
async def root():
    return {"status": "ok", "upstream": LLAMA_BASE_URL}

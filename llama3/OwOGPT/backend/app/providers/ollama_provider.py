from typing import Optional, Dict, Any
import aiohttp
from ..config import settings
from .base import LLMProvider


class OllamaProvider(LLMProvider):
    async def chat(
        self,
        *,
        session_key: str,
        message: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        url = f"{settings.OLLAMA_HOST}/api/chat"
        body: Dict[str, Any] = {
            "model": settings.OLLAMA_MODEL,
            "messages": [],
            "stream": False,
        }
        if system_prompt:
            body["messages"].append({"role": "system", "content": system_prompt})
        body["messages"].append({"role": "user", "content": message})
        if temperature is not None:
            body["options"] = {"temperature": temperature}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body) as resp:
                data = await resp.json()
                content = data.get("message", {}).get("content", "")
                return {"content": content, "raw": data}



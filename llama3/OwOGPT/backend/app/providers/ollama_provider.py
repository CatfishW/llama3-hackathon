from typing import Optional, Dict, Any, List
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
        images: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        url = f"{settings.OLLAMA_HOST}/api/chat"
        body: Dict[str, Any] = {
            "model": settings.OLLAMA_MODEL,
            "messages": [],
            "stream": False,
        }
        if system_prompt:
            body["messages"].append({"role": "system", "content": system_prompt})
        user_message: Dict[str, Any] = {"role": "user", "content": message}
        if images:
            # Ollama expects base64 images list
            user_message["images"] = [img.split(",",1)[1] if img.startswith("data:image") else img for img in images]
        body["messages"].append(user_message)
        if temperature is not None:
            body["options"] = {"temperature": temperature}

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=body) as resp:
                data = await resp.json()
                content = data.get("message", {}).get("content", "")
                return {"content": content, "raw": data}



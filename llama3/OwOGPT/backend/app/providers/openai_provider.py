from typing import Optional, Dict, Any
import asyncio
from openai import OpenAI
from ..config import settings
from .base import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else OpenAI()

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
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})

        resp = await asyncio.to_thread(
            self.client.chat.completions.create,
            model=settings.OPENAI_MODEL,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )

        # Normalize content access across SDK versions
        raw_dict = resp.model_dump() if hasattr(resp, "model_dump") else getattr(resp, "to_dict", lambda: {} )()
        content: str = ""
        try:
            if hasattr(resp, "choices") and resp.choices:
                choice0 = resp.choices[0]
                # Support both dict-like and attr-like access
                msg = choice0.get("message") if isinstance(choice0, dict) else getattr(choice0, "message", None)
                if msg is not None:
                    if isinstance(msg, dict):
                        content = msg.get("content") or ""
                    else:
                        content = getattr(msg, "content", "") or ""
        except Exception:
            # fallback: attempt to read from raw dict
            choices = raw_dict.get("choices", []) if isinstance(raw_dict, dict) else []
            if choices:
                msg = choices[0].get("message")
                if isinstance(msg, dict):
                    content = msg.get("content") or ""

        return {"content": content, "raw": raw_dict}



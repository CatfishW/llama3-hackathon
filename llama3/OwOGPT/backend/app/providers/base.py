from typing import Optional, Dict, Any, List


class LLMProvider:
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
        raise NotImplementedError



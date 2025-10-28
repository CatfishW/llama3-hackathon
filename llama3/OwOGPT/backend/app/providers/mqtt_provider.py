from typing import Optional, Dict, Any

from ..mqtt_client import publish_chat, publish_template_update, publish_session_delete
from .base import LLMProvider


class MQTTProvider(LLMProvider):
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
        payload: Dict[str, Any] = {
            "sessionId": session_key,
            "message": message,
        }
        if system_prompt:
            payload["systemPrompt"] = system_prompt
        if temperature is not None:
            payload["temperature"] = temperature
        if top_p is not None:
            payload["topP"] = top_p
        if max_tokens is not None:
            payload["maxTokens"] = max_tokens

        response = await publish_chat(payload)
        return response

    @staticmethod
    def update_template(session_key: str, system_prompt: str, reset: bool = True) -> None:
        """Update template and optionally reset conversation history."""
        publish_template_update(session_key, system_prompt, reset=reset)
    
    @staticmethod
    def delete_session(session_key: str) -> None:
        """Delete session on MQTT side (clears server history)."""
        publish_session_delete(session_key)



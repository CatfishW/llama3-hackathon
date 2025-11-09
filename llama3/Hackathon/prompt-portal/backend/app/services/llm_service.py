"""
Unified LLM Service Interface

This module provides a unified interface for LLM communication that works
with both MQTT and SSE (Direct HTTP) modes. It abstracts the communication
layer so routers can use the same API regardless of the underlying transport.

Modes:
- MQTT: Uses MQTT broker for communication with LLM service
- SSE: Uses direct HTTP/SSE communication with llama.cpp server
"""

import logging
from typing import Optional, Dict, List, Iterator
from ..config import settings

logger = logging.getLogger(__name__)

# Import based on communication mode
_comm_mode = settings.LLM_COMM_MODE.lower()

if _comm_mode == "sse":
    from .llm_client import get_llm_client, get_session_manager, LLMClient, SessionManager
    _use_sse = True
else:
    # MQTT mode - services are managed by mqtt.py
    _use_sse = False


class UnifiedLLMService:
    """
    Unified interface for LLM communication.
    Automatically uses MQTT or SSE based on configuration.
    """
    
    def __init__(self):
        self.mode = settings.LLM_COMM_MODE.lower()
        logger.info(f"UnifiedLLMService initialized in {self.mode.upper()} mode")
    
    def is_sse_mode(self) -> bool:
        """Check if running in SSE mode"""
        return self.mode == "sse"
    
    def is_mqtt_mode(self) -> bool:
        """Check if running in MQTT mode"""
        return self.mode == "mqtt"
    
    def get_llm_client(self) -> Optional["LLMClient"]:
        """
        Get LLM client (SSE mode only).
        Returns None in MQTT mode.
        """
        if self.is_sse_mode():
            return get_llm_client()
        return None
    
    def get_session_manager(self) -> Optional["SessionManager"]:
        """
        Get session manager (SSE mode only).
        Returns None in MQTT mode.
        """
        if self.is_sse_mode():
            return get_session_manager()
        return None
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: str = "default",
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = "auto"
    ) -> str:
        """
        Generate response (SSE mode only).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens to generate
            model: Model name
            tools: Tool definitions for function calling
            tool_choice: Tool usage mode
            
        Returns:
            Generated response string
            
        Raises:
            RuntimeError: If called in MQTT mode or service unavailable
        """
        if not self.is_sse_mode():
            raise RuntimeError(
                "generate() is only available in SSE mode. "
                "In MQTT mode, use MQTT publish/subscribe directly."
            )
        
        client = self.get_llm_client()
        if client is None:
            raise RuntimeError("LLM client not initialized")
        
        return client.generate(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            model=model,
            tools=tools,
            tool_choice=tool_choice
        )
    
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: str = "default",
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = "auto"
    ) -> Iterator[str]:
        """
        Generate streaming response (SSE mode only).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens to generate
            model: Model name
            tools: Tool definitions for function calling
            tool_choice: Tool usage mode
            
        Yields:
            Generated text chunks
            
        Raises:
            RuntimeError: If called in MQTT mode or service unavailable
        """
        if not self.is_sse_mode():
            raise RuntimeError(
                "generate_stream() is only available in SSE mode. "
                "In MQTT mode, use MQTT publish/subscribe directly."
            )
        
        client = self.get_llm_client()
        if client is None:
            raise RuntimeError("LLM client not initialized")
        
        yield from client.generate_stream(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            model=model,
            tools=tools,
            tool_choice=tool_choice
        )
    
    def process_message(
        self,
        session_id: str,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_tools: bool = True
    ) -> str:
        """
        Process a session-based message (SSE mode only).
        
        Args:
            session_id: Session identifier
            system_prompt: System prompt
            user_message: User's message
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens
            use_tools: Whether to enable function calling tools
            
        Returns:
            Generated response
            
        Raises:
            RuntimeError: If called in MQTT mode or service unavailable
        """
        if not self.is_sse_mode():
            raise RuntimeError(
                "process_message() is only available in SSE mode. "
                "In MQTT mode, use MQTT publish/subscribe directly."
            )
        
        session_manager = self.get_session_manager()
        if session_manager is None:
            raise RuntimeError("Session manager not initialized")
        
        return session_manager.process_message(
            session_id=session_id,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            use_tools=use_tools
        )
    
    def process_message_stream(
        self,
        session_id: str,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_tools: bool = False
    ) -> Iterator[str]:
        """
        Process a session-based message with streaming (SSE mode only).
        
        Args:
            session_id: Session identifier
            system_prompt: System prompt
            user_message: User's message
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens
            use_tools: Whether to enable function calling tools
            
        Yields:
            Generated text chunks
            
        Raises:
            RuntimeError: If called in MQTT mode or service unavailable
        """
        if not self.is_sse_mode():
            raise RuntimeError(
                "process_message_stream() is only available in SSE mode. "
                "In MQTT mode, use MQTT publish/subscribe directly."
            )
        
        session_manager = self.get_session_manager()
        if session_manager is None:
            raise RuntimeError("Session manager not initialized")
        
        yield from session_manager.process_message_stream(
            session_id=session_id,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            use_tools=use_tools
        )
    
    def get_session_history(self, session_id: str) -> Optional[List[Dict[str, str]]]:
        """
        Get session conversation history (SSE mode only).
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of messages or None if session not found
            
        Raises:
            RuntimeError: If called in MQTT mode
        """
        if not self.is_sse_mode():
            raise RuntimeError(
                "get_session_history() is only available in SSE mode. "
                "In MQTT mode, sessions are managed by the MQTT deployment service."
            )
        
        session_manager = self.get_session_manager()
        if session_manager is None:
            raise RuntimeError("Session manager not initialized")
        
        return session_manager.get_session_history(session_id)
    
    def clear_session(self, session_id: str):
        """
        Clear a session's conversation history (SSE mode only).
        
        Args:
            session_id: Session identifier
            
        Raises:
            RuntimeError: If called in MQTT mode
        """
        if not self.is_sse_mode():
            raise RuntimeError(
                "clear_session() is only available in SSE mode. "
                "In MQTT mode, sessions are managed by the MQTT deployment service."
            )
        
        session_manager = self.get_session_manager()
        if session_manager is None:
            raise RuntimeError("Session manager not initialized")
        
        session_manager.clear_session(session_id)


# Global service instance
_service: Optional[UnifiedLLMService] = None


def get_llm_service() -> UnifiedLLMService:
    """Get the global unified LLM service instance"""
    global _service
    if _service is None:
        _service = UnifiedLLMService()
    return _service

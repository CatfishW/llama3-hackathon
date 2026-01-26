"""
Unified LLM Service Interface

This module provides a unified interface for LLM communication over
direct HTTP/SSE.
"""

import logging
from typing import Optional, Dict, List, Iterator

logger = logging.getLogger(__name__)

from .llm_client import get_llm_client, get_session_manager, LLMClient, SessionManager


class UnifiedLLMService:
    """
    Unified interface for LLM communication (SSE-only).
    """
    
    def __init__(self):
        self.mode = "sse"
        self._client_cache: Dict[str, LLMClient] = {}
        logger.info("UnifiedLLMService initialized in SSE mode")
    
    def is_sse_mode(self) -> bool:
        """Check if running in SSE mode"""
        return True
    
    def get_llm_client(self, model_name: Optional[str] = None) -> Optional["LLMClient"]:
        """
        Get LLM client, optionally for a specific model configuration.
        """
        if not model_name or model_name == "default":
            return get_llm_client()
        
        # Check cache
        if model_name in self._client_cache:
            return self._client_cache[model_name]
        
        # Create new client for this model configuration
        try:
            from .llm_client import get_llm_client_for_user
            client = get_llm_client_for_user(model_name)
            self._client_cache[model_name] = client
            return client
        except Exception as e:
            logger.error(f"Failed to create LLM client for model config {model_name}: {e}")
            return get_llm_client()
    
    def get_session_manager(self) -> Optional["SessionManager"]:
        """
        Get session manager.
        """
        return get_session_manager()

    def _resolve_model_for_call(self, model: Optional[str]) -> Optional[str]:
        if not model or model == "default":
            return "default"
        try:
            from ..models_config import get_models_manager
            models_manager = get_models_manager()
            if models_manager.get_model_by_name(model):
                return "default"
        except Exception as e:
            logger.warning(f"Failed to resolve model name '{model}': {e}")
        return model
    
    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = "default",
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = "auto"
    ) -> str:
        """
        Generate response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens to generate
            model: Model name (config name)
            tools: Tool definitions for function calling
            tool_choice: Tool usage mode
            
        Returns:
            Generated response string
            
        Raises:
            RuntimeError: If service unavailable
        """
        client = self.get_llm_client(model)
        if client is None:
            raise RuntimeError("LLM client not initialized")
        
        model_for_call = self._resolve_model_for_call(model)
        return client.generate(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            model=model_for_call,
            tools=tools,
            tool_choice=tool_choice
        )
    
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = "default",
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = "auto"
    ) -> Iterator[str]:
        """
        Generate streaming response.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens to generate
            model: Model name (config name)
            tools: Tool definitions for function calling
            tool_choice: Tool usage mode
            
        Yields:
            Generated text chunks
            
        Raises:
            RuntimeError: If service unavailable
        """
        client = self.get_llm_client(model)
        if client is None:
            raise RuntimeError("LLM client not initialized")
        
        model_for_call = self._resolve_model_for_call(model)
        yield from client.generate_stream(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            model=model_for_call,
            tools=tools,
            tool_choice=tool_choice
        )
    
    async def agenerate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: Optional[str] = "default",
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = "auto"
    ):
        """Async version of generate_stream"""
        client = self.get_llm_client(model)
        if client is None:
            raise RuntimeError("LLM client not initialized")
        
        model_for_call = self._resolve_model_for_call(model)
        async for chunk in client.agenerate_stream(
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            model=model_for_call,
            tools=tools,
            tool_choice=tool_choice
        ):
            yield chunk
    
    def process_message(
        self,
        session_id: str,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_tools: bool = True,
        use_history: bool = True,
        max_history_messages: Optional[int] = None,
        model: Optional[str] = None
    ) -> str:
        """
        Process a session-based message.
        
        Args:
            session_id: Session identifier
            system_prompt: System prompt
            user_message: User's message
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens
            use_tools: Whether to enable function calling tools
            use_history: Whether to maintain conversation history (disable for stateless calls like maze game)
            max_history_messages: Maximum number of user/assistant message pairs to keep (excluding system prompt)
            model: Model name to use
            
        Returns:
            Generated response
            
        Raises:
            RuntimeError: If service unavailable
        """
        session_manager = self.get_session_manager()
        if session_manager is None:
            raise RuntimeError("Session manager not initialized")
        
        llm_client = self.get_llm_client(model)
        
        model_for_call = self._resolve_model_for_call(model)
        return session_manager.process_message(
            session_id=session_id,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            use_tools=use_tools,
            use_history=use_history,
            max_history_messages=max_history_messages,
            model=model_for_call,
            llm_client=llm_client
        )
    
    def process_message_stream(
        self,
        session_id: str,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_tools: bool = False,
        max_history_messages: Optional[int] = None,
        model: Optional[str] = None
    ) -> Iterator[str]:
        """
        Process a session-based message with streaming.
        
        Args:
            session_id: Session identifier
            system_prompt: System prompt
            user_message: User's message
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens
            use_tools: Whether to enable function calling tools
            max_history_messages: Maximum number of user/assistant message pairs to keep (excluding system prompt)
            model: Model name to use
            
        Yields:
            Generated text chunks
            
        Raises:
            RuntimeError: If service unavailable
        """
        session_manager = self.get_session_manager()
        if session_manager is None:
            raise RuntimeError("Session manager not initialized")
        
        llm_client = self.get_llm_client(model)
        
        model_for_call = self._resolve_model_for_call(model)
        yield from session_manager.process_message_stream(
            session_id=session_id,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            use_tools=use_tools,
            max_history_messages=max_history_messages,
            model=model_for_call,
            llm_client=llm_client
        )
    
    async def aprocess_message_stream(
        self,
        session_id: str,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_tools: bool = False,
        max_history_messages: Optional[int] = None,
        model: Optional[str] = None
    ):
        """Async version of process_message_stream"""
        session_manager = self.get_session_manager()
        if session_manager is None:
            raise RuntimeError("Session manager not initialized")
        
        llm_client = self.get_llm_client(model)
        model_for_call = self._resolve_model_for_call(model)
        
        async for chunk in session_manager.aprocess_message_stream(
            session_id=session_id,
            system_prompt=system_prompt,
            user_message=user_message,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            use_tools=use_tools,
            max_history_messages=max_history_messages,
            model=model_for_call,
            llm_client=llm_client
        ):
            yield chunk
    
    def get_session_history(self, session_id: str) -> Optional[List[Dict[str, str]]]:
        """
        Get session conversation history.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of messages or None if session not found
            
        Raises:
            RuntimeError: If service unavailable
        """
        session_manager = self.get_session_manager()
        if session_manager is None:
            raise RuntimeError("Session manager not initialized")
        
        return session_manager.get_session_history(session_id)
    
    def clear_session(self, session_id: str):
        """
        Clear a session's conversation history.
        
        Args:
            session_id: Session identifier
            
        Raises:
            RuntimeError: If service unavailable
        """
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

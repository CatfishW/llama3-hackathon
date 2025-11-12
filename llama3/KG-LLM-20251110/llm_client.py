"""LLM client wrapper for EPERM system."""

from __future__ import annotations
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from config import LLM_CONFIG, SYSTEM_CONFIG


class LLMClient:
    """Wrapper for OpenAI-compatible LLM API."""
    
    def __init__(self):
        """Initialize LLM client."""
        try:
            self.client = OpenAI(
                api_key=LLM_CONFIG["api_key"],
                base_url=LLM_CONFIG["base_url"]
            )
        except TypeError:
            # Handle older OpenAI library versions
            import httpx
            self.client = OpenAI(
                api_key=LLM_CONFIG["api_key"],
                base_url=LLM_CONFIG["base_url"],
                http_client=httpx.Client(timeout=30.0)
            )
        self.model = LLM_CONFIG["model"]
        self.temperature = LLM_CONFIG["temperature"]
        self.max_tokens = LLM_CONFIG["max_tokens"]
        self.cache = {} if SYSTEM_CONFIG["cache_enabled"] else None
        
    def chat(
        self, 
        messages: List[Dict[str, str]], 
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_cache: bool = True
    ) -> str:
        """
        Send chat completion request to LLM.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (override config)
            max_tokens: Max tokens to generate (override config)
            use_cache: Whether to use cached responses
            
        Returns:
            Generated text response
        """
        # Check cache
        if use_cache and self.cache is not None:
            cache_key = str(messages)
            if cache_key in self.cache:
                if SYSTEM_CONFIG["verbose"]:
                    print("  [Cache hit]")
                return self.cache[cache_key]
        
        # Make request
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )
            content = response.choices[0].message.content
            
            # Cache response
            if use_cache and self.cache is not None:
                self.cache[cache_key] = content
                
            return content
            
        except Exception as e:
            print(f"Error calling LLM: {e}")
            raise
    
    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ):
        """
        Stream chat completion response.
        
        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature
            max_tokens: Max tokens to generate
            
        Yields:
            Text chunks as they arrive
        """
        try:
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True,
            )
            
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            print(f"Error streaming from LLM: {e}")
            raise
    
    def generate_with_prompt(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        use_cache: bool = True
    ) -> str:
        """
        Convenience method for simple prompting.
        
        Args:
            system_prompt: System message
            user_prompt: User message
            temperature: Sampling temperature
            use_cache: Whether to use cache
            
        Returns:
            Generated response
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        return self.chat(messages, temperature=temperature, use_cache=use_cache)
    
    def clear_cache(self):
        """Clear the response cache."""
        if self.cache is not None:
            self.cache.clear()
            print("Cache cleared")

"""
LLM Client Service for Prompt Portal

This service provides a unified interface to communicate with LLM backends
(llama.cpp, vLLM, etc.) using OpenAI-compatible API.

Based on the architecture from llamacpp_mqtt_deploy.py but adapted for
direct HTTP communication within the web application.
"""

import json
import logging
import time
from typing import Dict, List, Optional
try:
    # Optional dependency; server should still boot without it
    from openai import OpenAI, OpenAIError  # type: ignore
    _OPENAI_AVAILABLE = True
except Exception:  # pragma: no cover - graceful degradation in minimal envs
    class OpenAIError(Exception):
        pass
    OpenAI = None  # type: ignore
    _OPENAI_AVAILABLE = False
import threading

logger = logging.getLogger(__name__)


# Define game action tools/functions for function calling
MAZE_GAME_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "break_wall",
            "description": "Break a wall at the specified coordinates to create a path. Use sparingly - limited breaks available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate of the wall to break"},
                    "y": {"type": "integer", "description": "Y coordinate of the wall to break"}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "break_walls",
            "description": "Break multiple walls at once. Each wall is specified as [x, y] coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "walls": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2
                        },
                        "description": "Array of [x, y] coordinates of walls to break"
                    }
                },
                "required": ["walls"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "speed_boost",
            "description": "Give the player a temporary speed boost for faster movement",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_ms": {"type": "integer", "description": "Duration of speed boost in milliseconds", "default": 1500}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slow_germs",
            "description": "Slow down germs (enemies) temporarily",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_ms": {"type": "integer", "description": "Duration of slow effect in milliseconds", "default": 3000}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "freeze_germs",
            "description": "Freeze germs (enemies) completely for a duration",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_ms": {"type": "integer", "description": "Duration of freeze effect in milliseconds", "default": 3500}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "teleport_player",
            "description": "Teleport the player to a specific location on the map",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate to teleport to"},
                    "y": {"type": "integer", "description": "Y coordinate to teleport to"}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_oxygen",
            "description": "Spawn oxygen pellets at specified locations for the player to collect",
            "parameters": {
                "type": "object",
                "properties": {
                    "locations": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2
                        },
                        "description": "Array of [x, y] coordinates where oxygen should spawn"
                    }
                },
                "required": ["locations"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_exit",
            "description": "Move the exit/goal location to a new position",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "New X coordinate for exit"},
                    "y": {"type": "integer", "description": "New Y coordinate for exit"}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "highlight_zone",
            "description": "Highlight a zone/area on the map to draw attention",
            "parameters": {
                "type": "object",
                "properties": {
                    "cells": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer"},
                            "minItems": 2,
                            "maxItems": 2
                        },
                        "description": "Array of [x, y] coordinates to highlight"
                    },
                    "duration_ms": {"type": "integer", "description": "How long to highlight in milliseconds", "default": 5000}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reveal_map",
            "description": "Toggle map reveal to show/hide the entire map layout",
            "parameters": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "description": "Whether to reveal the map"}
                },
                "required": ["enabled"]
            }
        }
    }
]


class LLMClient:
    """
    HTTP client for LLM inference using OpenAI-compatible API.
    Supports llama.cpp server, vLLM, and other OpenAI-compatible endpoints.
    Now supports multi-model configuration with dynamic API switching.
    
    Backend Types:
        - "auto": Auto-detect based on server response/URL
        - "llama.cpp": Use llama.cpp-specific parameters (enable_thinking, etc.)
        - "vllm": Use vLLM-compatible parameters (no extra_body)
        - "openai": Use standard OpenAI API parameters
    """
    
    def __init__(
        self,
        server_url: str,
        timeout: int = 300,
        default_temperature: float = 0.6,
        default_top_p: float = 0.9,
        default_max_tokens: int = 512,
        skip_thinking: bool = True,
        api_key: str = "not-needed",
        backend_type: str = "auto"
    ):
        """
        Initialize LLM client.
        
        Args:
            server_url: URL of the LLM server (e.g., http://localhost:8080)
            timeout: Request timeout in seconds
            default_temperature: Default sampling temperature
            default_top_p: Default top-p sampling
            default_max_tokens: Default max tokens to generate
            skip_thinking: Disable thinking mode (adds /no_think directive for llama.cpp)
            api_key: API key for authentication (default: "not-needed")
            backend_type: Backend type - "auto", "llama.cpp", "vllm", or "openai"
        """
        self.server_url = server_url.rstrip('/')
        self.timeout = timeout
        self.default_temperature = default_temperature
        self.default_top_p = default_top_p
        self.default_max_tokens = default_max_tokens
        self.skip_thinking = skip_thinking
        self.api_key = api_key
        self.backend_type = backend_type
        
        # Auto-detect backend type from URL if set to "auto"
        if self.backend_type == "auto":
            self.backend_type = self._detect_backend_type()
        
        logger.info(f"Initializing LLM client: {self.server_url} (backend: {self.backend_type})")
        
        # Prepare base URL for OpenAI client
        # vLLM and most OpenAI-compatible servers expect the base_url to include /v1
        # llama.cpp also uses /v1 endpoints, so we need to ensure /v1 is in the URL
        base_url = self.server_url
        if not base_url.endswith("/v1") and not base_url.endswith("/v1/"):
            base_url = f"{base_url}/v1"
            logger.info(f"Added /v1 suffix to base URL: {base_url}")
        
        # Initialize OpenAI client with LLM server as base URL when available
        if _OPENAI_AVAILABLE and OpenAI is not None:
            # Note: api_key is required by OpenAI client
            self.client = OpenAI(
                base_url=base_url,
                api_key=self.api_key,
                timeout=self.timeout
            )
        else:
            # Degraded mode: no OpenAI client; generation calls will raise at runtime
            self.client = None
        
        # Test connection to server
        if not self._test_connection():
            logger.warning(
                f"Could not connect to LLM server at {self.server_url}. "
                f"LLM features will not work until server is available."
            )
        else:
            logger.info("LLM client initialized successfully")
    
    def _detect_backend_type(self) -> str:
        """
        Auto-detect backend type from server URL patterns.
        
        Returns:
            Detected backend type: "llama.cpp", "vllm", or "openai"
        """
        url_lower = self.server_url.lower()
        
        # Check for common vLLM patterns
        if "vllm" in url_lower or ":8000" in url_lower:
            logger.info("Auto-detected vLLM backend from URL pattern")
            return "vllm"
        
        # Check for OpenAI API
        if "api.openai.com" in url_lower:
            logger.info("Auto-detected OpenAI backend from URL")
            return "openai"
        
        # Check for common llama.cpp patterns (port 8080 is common for llama.cpp)
        if ":8080" in url_lower or "llama" in url_lower:
            logger.info("Auto-detected llama.cpp backend from URL pattern")
            return "llama.cpp"
        
        # Default to vllm as it's the most common OpenAI-compatible server
        logger.info("Could not auto-detect backend, defaulting to vllm (OpenAI-compatible)")
        return "vllm"
    
    def update_config(self, server_url: str, api_key: str, backend_type: str = "auto"):
        """
        Update client configuration for a different model.
        
        Args:
            server_url: New API base URL
            api_key: New API key
            backend_type: Backend type - "auto", "llama.cpp", "vllm", or "openai"
        """
        self.server_url = server_url.rstrip('/')
        self.api_key = api_key
        self.backend_type = backend_type
        
        # Auto-detect if needed
        if self.backend_type == "auto":
            self.backend_type = self._detect_backend_type()
        
        # Prepare base URL - ensure /v1 suffix for OpenAI-compatible APIs
        base_url = self.server_url
        if not base_url.endswith("/v1") and not base_url.endswith("/v1/"):
            base_url = f"{base_url}/v1"
            logger.info(f"Added /v1 suffix to base URL: {base_url}")
        
        if _OPENAI_AVAILABLE and OpenAI is not None:
            self.client = OpenAI(
                base_url=base_url,
                api_key=self.api_key,
                timeout=self.timeout
            )
            logger.info(f"Updated LLM client configuration: {self.server_url} (backend: {self.backend_type})")
        else:
            logger.warning("OpenAI package not available, cannot update client")
    
    def _test_connection(self) -> bool:
        """Test connection to LLM server."""
        if self.client is None:
            logger.warning("LLM client not available (openai package missing); skipping connection test")
            return False
        try:
            logger.info("Testing connection to LLM server...")
            # Try a simple chat completion call to test connectivity
            self.client.chat.completions.create(
                model="default",
                messages=[{"role": "system", "content": "test"}],
                max_tokens=1
            )
            logger.info("Connection test successful")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
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
        Generate response using OpenAI-compatible chat completion API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (default from config)
            top_p: Top-p sampling (default from config)
            max_tokens: Maximum tokens to generate (default from config)
            model: Model name (default: "default")
            tools: List of tool/function definitions for function calling
            tool_choice: How to use tools - "auto", "none", or specific tool
            
        Returns:
            Generated response string (may include function calls as JSON)
        """
        # Use defaults if not specified
        temperature = temperature if temperature is not None else self.default_temperature
        top_p = top_p if top_p is not None else self.default_top_p
        max_tokens = max_tokens if max_tokens is not None else self.default_max_tokens
        
        if self.client is None:
            raise RuntimeError("LLM client is not available on this server (openai not installed)")
        try:
            start_time = time.time()
            
            # Build API call parameters (compatible with all backends)
            api_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
            }
            
            # Add llama.cpp-specific extra_body parameters only for that backend
            if self.backend_type == "llama.cpp":
                api_params["extra_body"] = {
                    "enable_thinking": not self.skip_thinking
                }
            
            # Add tools if provided (for function calling)
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = tool_choice
            
            # Call chat completions using OpenAI client
            response = self.client.chat.completions.create(**api_params)
            
            generation_time = time.time() - start_time
            
            # Extract generated text from response
            message = response.choices[0].message
            
            # Check if the response includes function calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Convert tool calls to JSON format that the game can understand
                function_calls = []
                for tool_call in message.tool_calls:
                    function_calls.append({
                        "name": tool_call.function.name,
                        "arguments": json.loads(tool_call.function.arguments)
                    })
                
                # Return combined response with function calls
                result = {
                    "hint": message.content or "",
                    "function_calls": function_calls
                }
                generated_text = json.dumps(result)
            else:
                generated_text = message.content or ""
            
            logger.info(f"Generated response in {generation_time:.2f}s")
            
            return generated_text
            
        except OpenAIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        except Exception as e:
            error_msg = f"Generation failed: {str(e)}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    
    def generate_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        model: str = "default",
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = "auto"
    ):
        """
        Generate response using streaming for real-time output.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (default from config)
            top_p: Top-p sampling (default from config)
            max_tokens: Maximum tokens to generate (default from config)
            model: Model name (default: "default")
            tools: List of tool/function definitions for function calling
            tool_choice: How to use tools - "auto", "none", or specific tool
            
        Yields:
            Generated text chunks as they arrive (as strings or Server-Sent Events format)
        """
        # Use defaults if not specified
        temperature = temperature if temperature is not None else self.default_temperature
        top_p = top_p if top_p is not None else self.default_top_p
        max_tokens = max_tokens if max_tokens is not None else self.default_max_tokens
        
        if self.client is None:
            yield "Error: LLM client is not available on this server (openai not installed)"
            return
        try:
            start_time = time.time()
            
            # Build API call parameters (compatible with all backends)
            api_params = {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                "stream": True  # Enable streaming
            }
            
            # Add llama.cpp-specific extra_body parameters only for that backend
            if self.backend_type == "llama.cpp":
                api_params["extra_body"] = {
                    "enable_thinking": not self.skip_thinking
                }
            
            # Add tools if provided (for function calling)
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = tool_choice
            
            # Call chat completions with streaming
            stream = self.client.chat.completions.create(**api_params)
            
            full_response = ""
            for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        full_response += delta.content
                        yield delta.content
            
            generation_time = time.time() - start_time
            logger.info(f"Streamed response in {generation_time:.2f}s, {len(full_response)} chars")
            
        except OpenAIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            logger.error(error_msg)
            yield f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Generation failed: {str(e)}"
            logger.error(error_msg)
            yield f"Error: {error_msg}"
    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for a text string.
        
        Args:
            text: Input text
            
        Returns:
            Estimated number of tokens
        """
        # Rough estimation: ~4 characters per token
        return len(text) // 4


class SessionManager:
    """
    Manages conversation sessions with history trimming.
    Compatible with the MQTT deployment's session management.
    """
    
    def __init__(self, llm_client: LLMClient, max_history_tokens: int = 10000, max_history_messages: Optional[int] = None):
        """
        Initialize session manager.
        
        Args:
            llm_client: LLM client instance
            max_history_tokens: Maximum tokens to keep in conversation history
            max_history_messages: Maximum number of messages to keep (excluding system prompt). If set, takes precedence over token-based trimming.
        """
        self.llm_client = llm_client
        self.max_history_tokens = max_history_tokens
        self.max_history_messages = max_history_messages
        self.sessions: Dict[str, Dict] = {}
        self.session_locks: Dict[str, threading.RLock] = {}
        self.global_lock = threading.RLock()
        
        if max_history_messages:
            logger.info(f"Session manager initialized with max_history_messages={max_history_messages}")
        else:
            logger.info("Session manager initialized")
    
    def get_or_create_session(
        self,
        session_id: str,
        system_prompt: str
    ) -> Dict:
        """
        Get existing session or create a new one.
        
        Args:
            session_id: Unique session identifier
            system_prompt: System prompt for the session
            
        Returns:
            Session dictionary
        """
        # Fast path: check if session exists without locking
        existing = self.sessions.get(session_id)
        if existing:
            existing["last_access"] = time.time()
            return existing
        
        # Slow path: create new session with minimal locking
        with self.global_lock:
            existing = self.sessions.get(session_id)
            if existing:
                existing["last_access"] = time.time()
                return existing
            
            # Create session
            session = {
                "dialog": [{"role": "system", "content": system_prompt}],
                "session_id": session_id,
                "created_at": time.time(),
                "last_access": time.time(),
                "message_count": 0,
            }
            self.sessions[session_id] = session
            self.session_locks[session_id] = threading.RLock()
            logger.info(f"Created new session: {session_id}")
        
        return self.sessions[session_id]
    
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
        max_history_messages: Optional[int] = None
    ) -> str:
        """
        Process a user message and generate a response.
        
        Args:
            session_id: Session identifier
            system_prompt: System prompt
            user_message: User's message
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens
            use_tools: Whether to enable function calling tools
            use_history: Whether to maintain conversation history (disable for stateless calls like maze game)
            max_history_messages: Maximum number of user/assistant message pairs to keep (excluding system prompt). 
                                 If not specified, uses self.max_history_messages.
            
        Returns:
            Generated response (may include function calls)
        """
        # Determine effective max_history_messages
        effective_max_history_messages = max_history_messages if max_history_messages is not None else self.max_history_messages
        
        if use_history:
            # Get or create session with history
            session = self.get_or_create_session(session_id, system_prompt)
            session_lock = self.session_locks.get(session_id, threading.RLock())
            
            # Build the prompt first (with minimal locking)
            with session_lock:
                # Add user message to dialog
                session["dialog"].append({"role": "user", "content": user_message})
                session["message_count"] += 1
                
                # Trim history based on max_history_messages if set
                if effective_max_history_messages is not None:
                    # Keep system message + last N user/assistant message pairs
                    # Calculate how many non-system messages to keep
                    non_system_messages = session["dialog"][1:]  # Skip system message
                    
                    # Keep only the last (max_history_messages * 2) non-system messages
                    # because each pair is user + assistant response
                    messages_to_keep = effective_max_history_messages * 2
                    if len(non_system_messages) > messages_to_keep:
                        # Keep system message + recent messages
                        session["dialog"] = [session["dialog"][0]] + non_system_messages[-messages_to_keep:]
                        logger.debug(f"Trimmed dialog to {len(session['dialog'])} messages (max_history_messages={effective_max_history_messages})")
                else:
                    # Simple trimming: keep only last N messages (old behavior)
                    max_messages = 20
                    if len(session["dialog"]) > max_messages:
                        # Keep system message and last N-1 messages
                        session["dialog"] = [session["dialog"][0]] + session["dialog"][-(max_messages-1):]
                
                # Prepare messages for API call
                messages = session["dialog"].copy()
        else:
            # Stateless mode: just system + user message (no history)
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
            session_lock = None
        
        # Now do inference WITHOUT holding session lock!
        try:
            # Use tools if requested (for maze game with function calling)
            tools = MAZE_GAME_TOOLS if use_tools else None
            
            response = self.llm_client.generate(
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice="auto" if tools else None
            )
            
            # Add assistant response to history (only if using history)
            if use_history and session_lock:
                with session_lock:
                    session["dialog"].append({"role": "assistant", "content": response})
            
            return response
                
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(f"Session {session_id}: {error_msg}")
            raise
    
    def process_message_stream(
        self,
        session_id: str,
        system_prompt: str,
        user_message: str,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        use_tools: bool = False,  # Note: streaming with tools is complex, disabled by default
        max_history_messages: Optional[int] = None
    ):
        """
        Process a user message and generate a streaming response.
        
        Args:
            session_id: Session identifier
            system_prompt: System prompt
            user_message: User's message
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens
            use_tools: Whether to enable function calling tools (not recommended for streaming)
            max_history_messages: Maximum number of user/assistant message pairs to keep (excluding system prompt)
            
        Yields:
            Generated text chunks as they arrive
        """
        # Determine effective max_history_messages
        effective_max_history_messages = max_history_messages if max_history_messages is not None else self.max_history_messages
        
        # Get or create session
        session = self.get_or_create_session(session_id, system_prompt)
        session_lock = self.session_locks.get(session_id, threading.RLock())
        
        # Build the prompt first (with minimal locking)
        with session_lock:
            # Add user message to dialog
            session["dialog"].append({"role": "user", "content": user_message})
            session["message_count"] += 1
            
            # Trim history based on max_history_messages if set
            if effective_max_history_messages is not None:
                # Keep system message + last N user/assistant message pairs
                non_system_messages = session["dialog"][1:]  # Skip system message
                
                # Keep only the last (max_history_messages * 2) non-system messages
                messages_to_keep = effective_max_history_messages * 2
                if len(non_system_messages) > messages_to_keep:
                    session["dialog"] = [session["dialog"][0]] + non_system_messages[-messages_to_keep:]
                    logger.debug(f"Trimmed dialog to {len(session['dialog'])} messages (max_history_messages={effective_max_history_messages})")
            else:
                # Simple trimming: keep only last N messages (old behavior)
                max_messages = 20
                if len(session["dialog"]) > max_messages:
                    # Keep system message and last N-1 messages
                    session["dialog"] = [session["dialog"][0]] + session["dialog"][-(max_messages-1):]
            
            # Prepare messages for API call
            messages = session["dialog"].copy()
        
        # Now do inference WITHOUT holding session lock!
        full_response = ""
        try:
            # Use tools if requested (for maze game with function calling)
            # Note: Streaming with tools/function calling is complex
            tools = MAZE_GAME_TOOLS if use_tools else None
            
            for chunk in self.llm_client.generate_stream(
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                tools=tools,
                tool_choice="auto" if tools else None
            ):
                full_response += chunk
                yield chunk
            
            # Add assistant response to history (lock again briefly)
            with session_lock:
                session["dialog"].append({"role": "assistant", "content": full_response})
                
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(f"Session {session_id}: {error_msg}")
            yield f"\n\nError: {error_msg}"
    
    def clear_session(self, session_id: str):
        """Clear a session's conversation history."""
        with self.global_lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
            if session_id in self.session_locks:
                del self.session_locks[session_id]
            logger.info(f"Cleared session: {session_id}")
    
    def get_session_history(self, session_id: str) -> Optional[List[Dict[str, str]]]:
        """Get the conversation history for a session."""
        session = self.sessions.get(session_id)
        if session:
            return session["dialog"].copy()
        return None


# Global instances (will be initialized on startup)
_llm_client: Optional[LLMClient] = None
_session_manager: Optional[SessionManager] = None


def init_llm_service(
    server_url: str,
    timeout: int = 300,
    temperature: float = 0.6,
    top_p: float = 0.9,
    max_tokens: int = 512,
    skip_thinking: bool = True,
    max_history_tokens: int = 10000,
    backend_type: str = "auto"
):
    """
    Initialize the global LLM service.
    Should be called once during application startup.
    
    Args:
        server_url: URL of the LLM server
        timeout: Request timeout in seconds
        temperature: Default sampling temperature
        top_p: Default top-p sampling
        max_tokens: Default max tokens to generate
        skip_thinking: Disable thinking mode for llama.cpp
        max_history_tokens: Maximum tokens to keep in conversation history
        backend_type: Backend type - "auto", "llama.cpp", "vllm", or "openai"
    """
    global _llm_client, _session_manager
    
    _llm_client = LLMClient(
        server_url=server_url,
        timeout=timeout,
        default_temperature=temperature,
        default_top_p=top_p,
        default_max_tokens=max_tokens,
        skip_thinking=skip_thinking,
        backend_type=backend_type
    )
    
    _session_manager = SessionManager(
        llm_client=_llm_client,
        max_history_tokens=max_history_tokens
    )
    
    logger.info("LLM service initialized")


def get_llm_client() -> LLMClient:
    """Get the global LLM client instance."""
    if _llm_client is None:
        raise RuntimeError("LLM service not initialized. Call init_llm_service first.")
    return _llm_client


def get_llm_client_for_user(user_model_name: Optional[str] = None) -> LLMClient:
    """
    Get an LLM client configured for a specific user's selected model.
    
    Args:
        user_model_name: Name of the model selected by the user. If None, uses default.
        
    Returns:
        LLM client configured with the user's selected model
    """
    from ..models_config import get_models_manager
    
    models_manager = get_models_manager()
    
    # Get the model configuration
    if user_model_name:
        model_config = models_manager.get_model_by_name(user_model_name)
        if not model_config:
            logger.warning(f"Model '{user_model_name}' not found, using default")
            model_config = models_manager.get_all_models()[0]
    else:
        # Use first available model as default
        models = models_manager.get_all_models()
        if not models:
            raise RuntimeError("No models configured")
        model_config = models[0]
    
    # Create a new client with the model's configuration
    # Determine backend type from provider or use auto-detection
    provider = getattr(model_config, 'provider', 'openai').lower()
    if provider == 'vllm' or 'vllm' in model_config.apiBase.lower():
        backend_type = 'vllm'
    elif provider == 'llama.cpp' or 'llama' in model_config.apiBase.lower():
        backend_type = 'llama.cpp'
    else:
        backend_type = 'auto'
    
    client = LLMClient(
        server_url=model_config.apiBase,
        api_key=model_config.apiKey,
        timeout=300,
        default_temperature=0.6,
        default_top_p=0.9,
        default_max_tokens=512,
        skip_thinking=True,
        backend_type=backend_type
    )
    
    return client


def get_session_manager() -> SessionManager:
    """Get or lazily initialize the global session manager.

    Lazily creates a minimal SessionManager even if OpenAI isn't installed so
    routes that only read history can function without hard deps.
    """
    global _session_manager
    if _session_manager is None:
        try:
            # Create a degraded LLM client; generation will fail if invoked
            client = LLMClient(server_url="http://localhost:8000", skip_thinking=True)  # type: ignore[arg-type]
        except Exception:
            # As last resort, create a dummy shim with required interface
            class _Dummy:
                def generate(self, *a, **k):
                    raise RuntimeError("LLM unavailable")
                def generate_stream(self, *a, **k):
                    yield "Error: LLM unavailable"
            client = _Dummy()  # type: ignore
        _session_manager = SessionManager(llm_client=client, max_history_tokens=10000)
        logger.warning("SessionManager lazily initialized in degraded mode")
    return _session_manager

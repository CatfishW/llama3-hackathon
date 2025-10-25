"""
Llama.cpp MQTT Deployment Script

This script provides LLM inference using llama.cpp server via HTTP API,
supporting multiple concurrent users across different projects via MQTT.

Features:
- HTTP API calls to llama.cpp server
- Multi-user concurrent support
- Project-based topic routing
- Session-based conversation management
- Flexible configuration via command-line
- Comprehensive logging and error handling

Usage:
    python llamacpp_mqtt_deploy.py --projects maze driving bloodcell --server_url http://localhost:8080

Author: Llama.cpp MQTT Deployment Team
Date: 2025
"""

import json
import logging
import os
import queue
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple

import fire
import paho.mqtt.client as mqtt
from openai import OpenAI, OpenAIError

# ============================================================================
# Configuration and Logging Setup
# ============================================================================

# Main logger for console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Debug logger for detailed information (file only)
debug_logger = logging.getLogger('debug')
debug_logger.setLevel(logging.DEBUG)
debug_handler = logging.FileHandler('debug_info.log', mode='a', encoding='utf-8')
debug_handler.setFormatter(logging.Formatter(
    '%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
))
debug_logger.addHandler(debug_handler)
debug_logger.propagate = False  # Don't propagate to root logger


@dataclass
class ProjectConfig:
    """Configuration for a single project/topic."""
    name: str
    user_topic: str
    response_topic: str
    system_prompt: str
    enabled: bool = True
    # Optional state topic for game state messages (e.g., maze/state)
    state_topic: str = None
    # Optional hint topic for hint responses (e.g., maze/hint/{sessionId})
    hint_topic: str = None
    # Optional template management topics
    template_topic: str = None
    clear_topic: str = None
    delete_topic: str = None
    # Optional tool definitions for function calling
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[str] = None


@dataclass
class DeploymentConfig:
    """Global deployment configuration."""
    # MQTT Configuration
    mqtt_broker: str = "47.89.252.2"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = None
    mqtt_password: Optional[str] = None
    
    # Llama.cpp Server Configuration
    server_url: str = "http://localhost:8080"
    server_timeout: int = 300  # seconds, increase for longer context
    
    # Generation Configuration
    default_temperature: float = 0.6
    default_top_p: float = 0.9
    default_max_tokens: int = 512
    skip_thinking: bool = True  # Disable deep thinking mode (adds /no_think directive)
    
    # Session Management
    max_history_tokens: int = 10000
    max_concurrent_sessions: int = 100
    session_timeout: int = 3600  # seconds
    
    # Performance Configuration
    num_worker_threads: int = 12  # Number of worker threads
    batch_timeout: float = 0.1  # seconds
    max_queue_size: int = 1000  # Maximum messages in queue
    
    # Rate Limiting
    max_requests_per_session: int = 20  # Max requests per minute per session
    rate_limit_window: int = 60  # Rate limit window in seconds
    
    # Projects
    projects: Dict[str, ProjectConfig] = field(default_factory=dict)


# ============================================================================
# Default System Prompts for Various Projects
# ============================================================================

SYSTEM_PROMPTS = {
    "maze": """You are a Large Action Model (LAM) guiding players through a maze game.
You provide strategic hints and pathfinding advice. Be concise and helpful.
Always respond in JSON format with keys: "hint" (string), "suggestion" (string).""",
    
    "driving": """You are Cap, a goofy peer agent in a physics learning game about forces and motion.
Your role is to learn from the player's explanations. Never directly give the right answer.
Keep responses under 50 words. Be playful, use first person, and encourage the player to explain their reasoning.
Always end with state tags: <Cont or EOS><PlayerOp:x><AgentOP:y>""",
    
    "bloodcell": """You are a peer agent in an educational game about red blood cells.
You know nothing initially and learn from the player's explanations. Never correct them directly.
Keep responses under 20 words. Provide emotional support and ask for detailed explanations.
Speak like a junior high school student with cool Gen-Z slang and humor.""",
    
    "racing": """You are a peer agent helping players understand physics in a racing game.
Focus on concepts like force, mass, and acceleration. Learn from player explanations.
Keep responses concise and supportive. Never reveal correct answers directly.""",
    
    "prompt_portal": """You are an AI assistant helping users test and refine their prompt templates.
Provide thoughtful, helpful responses that demonstrate how the prompt template affects your behavior.
Be clear, concise, and adapt to the style and tone specified in the user's prompt template.
If the prompt asks you to respond in a specific format (JSON, etc.), follow that format exactly.""",
    
    "general": """You are a helpful AI assistant. Provide clear, concise, and accurate responses."""
}


# ============================================================================
# Tool Definitions
# ============================================================================

MAZE_ACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "break_wall",
            "description": "Break a wall at the specified coordinates to create a new opening.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "X coordinate of the wall"},
                    "y": {"type": "integer", "description": "Y coordinate of the wall"}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "break_walls",
            "description": "Break multiple walls at once. Each wall is provided as [x, y].",
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
                        "description": "Array of [x, y] wall coordinates"
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
            "description": "Give the player a temporary speed boost.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_ms": {
                        "type": "integer",
                        "description": "Duration of the boost in milliseconds",
                        "default": 1500
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "slow_germs",
            "description": "Slow the germs (enemies) for a short period.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_ms": {
                        "type": "integer",
                        "description": "Duration of the slow effect in milliseconds",
                        "default": 3000
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "freeze_germs",
            "description": "Freeze germs completely for a duration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "duration_ms": {
                        "type": "integer",
                        "description": "Duration of the freeze effect in milliseconds",
                        "default": 3500
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "teleport_player",
            "description": "Teleport the player to a specific location on the map.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "Destination X coordinate"},
                    "y": {"type": "integer", "description": "Destination Y coordinate"}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "spawn_oxygen",
            "description": "Spawn oxygen pellets at the specified coordinates.",
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
                        "description": "Array of [x, y] oxygen coordinates"
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
            "description": "Move the maze exit to a new location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "New exit X coordinate"},
                    "y": {"type": "integer", "description": "New exit Y coordinate"}
                },
                "required": ["x", "y"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "highlight_zone",
            "description": "Highlight a set of cells to draw the player's attention.",
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
                        "description": "Array of [x, y] cell coordinates to highlight"
                    },
                    "duration_ms": {
                        "type": "integer",
                        "description": "Highlight duration in milliseconds",
                        "default": 5000
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "reveal_map",
            "description": "Toggle full-map reveal mode on or off.",
            "parameters": {
                "type": "object",
                "properties": {
                    "enabled": {"type": "boolean", "description": "True to reveal the map"}
                },
                "required": ["enabled"]
            }
        }
    }
]


# ============================================================================
# Llama.cpp API Client
# ============================================================================

class LlamaCppClient:
    """
    HTTP client for llama.cpp server inference using OpenAI package.
    """
    
    def __init__(self, config: DeploymentConfig):
        """
        Initialize llama.cpp client.
        
        Args:
            config: Deployment configuration
        """
        self.config = config
        self.server_url = config.server_url.rstrip('/')
        self.timeout = config.server_timeout
        
        logger.info(f"Initializing Llama.cpp client: {self.server_url}")
        
        # Initialize OpenAI client with llama.cpp server as base URL
        # Note: api_key is required by OpenAI client but not used by llama.cpp
        self.client = OpenAI(
            base_url=self.server_url,
            api_key="not-needed",  # llama.cpp doesn't require API key
            timeout=self.timeout
        )
        
        # Test connection to server
        if not self._test_connection():
            raise RuntimeError(
                f"Failed to connect to llama.cpp server at {self.server_url}. "
                f"Make sure the server is running with: "
                f"llama-server -m ./your-model.gguf --port 8080"
            )
        
        logger.info("OpenAI client initialized successfully")
    
    def _test_connection(self) -> bool:
        """Test connection to llama.cpp server."""
        try:
            logger.info("Testing connection to llama.cpp server...")
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
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None,
        debug_info: dict = None,
        tools: Optional[List[Dict]] = None,
        tool_choice: Optional[str] = None
    ) -> str:
        """
        Generate response using OpenAI-compatible chat completion API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (default from config)
            top_p: Top-p sampling (default from config)
            max_tokens: Maximum tokens to generate (default from config)
            debug_info: Optional debug info dict to log details
            tools: Optional tool definitions for structured function calling
            tool_choice: Tool usage mode ("auto", "none", or specific tool name)
            
        Returns:
            Generated response string
        """
        # Use defaults from config if not specified
        temperature = temperature or self.config.default_temperature
        top_p = top_p or self.config.default_top_p
        max_tokens = max_tokens or self.config.default_max_tokens
        
        # Debug log: generation parameters
        if debug_info:
            debug_logger.debug("=" * 80)
            debug_logger.debug(f"GENERATION REQUEST | Session: {debug_info.get('session_id', 'unknown')}")
            debug_logger.debug(f"Temperature: {temperature}, Top-P: {top_p}, Max Tokens: {max_tokens}")
            debug_logger.debug(f"Thinking Mode: {'DISABLED' if self.config.skip_thinking else 'ENABLED'}")
            debug_logger.debug("-" * 80)
            debug_logger.debug(f"MESSAGES TO LLM:\n{json.dumps(messages, indent=2, ensure_ascii=False)}")
            debug_logger.debug("-" * 80)
            if tools:
                debug_logger.debug(f"Tools supplied: {[tool['function']['name'] for tool in tools if 'function' in tool]}")
        
        try:
            start_time = time.time()
            
            # Prepare extra body parameters for llama.cpp
            extra_body = {
                "enable_thinking": not self.config.skip_thinking
            }
            
            request_kwargs = {
                "model": "default",
                "messages": messages,
                "temperature": temperature,
                "top_p": top_p,
                "max_tokens": max_tokens,
                "extra_body": extra_body
            }

            if tools:
                request_kwargs["tools"] = tools
                if tool_choice:
                    request_kwargs["tool_choice"] = tool_choice
            
            # Call chat completions using OpenAI client
            response = self.client.chat.completions.create(**request_kwargs)
            
            generation_time = time.time() - start_time
            
            # Extract generated text from response
            message = response.choices[0].message

            generated_text = message.content or ""

            # If the model returned tool calls, convert them into structured JSON
            if tools and getattr(message, "tool_calls", None):
                guidance: Dict[str, object] = {}

                hint_text = (message.content or "").strip()
                if hint_text:
                    guidance["hint"] = hint_text

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name if tool_call.function else None
                    if not tool_name:
                        continue
                    try:
                        args = json.loads(tool_call.function.arguments or "{}")
                    except json.JSONDecodeError as exc:
                        logger.warning(f"Failed to parse arguments for tool '{tool_name}': {exc}")
                        if debug_info:
                            debug_logger.warning(f"Tool '{tool_name}' argument parse error: {exc}")
                        continue

                    if tool_name == "break_wall":
                        x = args.get("x")
                        y = args.get("y")
                        if x is not None and y is not None:
                            guidance["break_wall"] = [int(x), int(y)]
                    elif tool_name == "break_walls":
                        walls = args.get("walls")
                        if isinstance(walls, list):
                            sanitized = []
                            for wall in walls:
                                if isinstance(wall, (list, tuple)) and len(wall) >= 2:
                                    sanitized.append([int(wall[0]), int(wall[1])])
                            if sanitized:
                                guidance["break_walls"] = sanitized
                    elif tool_name == "speed_boost":
                        duration = args.get("duration_ms") or args.get("duration")
                        if duration is not None:
                            guidance["speed_boost_ms"] = int(duration)
                    elif tool_name == "slow_germs":
                        duration = args.get("duration_ms") or args.get("duration")
                        if duration is not None:
                            guidance["slow_germs_ms"] = int(duration)
                    elif tool_name == "freeze_germs":
                        duration = args.get("duration_ms") or args.get("duration")
                        if duration is not None:
                            guidance["freeze_germs_ms"] = int(duration)
                    elif tool_name == "teleport_player":
                        x = args.get("x")
                        y = args.get("y")
                        if x is not None and y is not None:
                            guidance["teleport_player"] = [int(x), int(y)]
                    elif tool_name == "spawn_oxygen":
                        locs = args.get("locations")
                        if isinstance(locs, list):
                            oxygen_cells = []
                            for loc in locs:
                                if isinstance(loc, (list, tuple)) and len(loc) >= 2:
                                    oxygen_cells.append([int(loc[0]), int(loc[1])])
                            if oxygen_cells:
                                existing = guidance.setdefault("spawn_oxygen", [])
                                if isinstance(existing, list):
                                    existing.extend(oxygen_cells)
                                else:
                                    guidance["spawn_oxygen"] = oxygen_cells
                    elif tool_name == "move_exit":
                        x = args.get("x")
                        y = args.get("y")
                        if x is not None and y is not None:
                            guidance["move_exit"] = [int(x), int(y)]
                    elif tool_name == "highlight_zone":
                        cells = args.get("cells")
                        if isinstance(cells, list):
                            zone = []
                            for cell in cells:
                                if isinstance(cell, (list, tuple)) and len(cell) >= 2:
                                    zone.append([int(cell[0]), int(cell[1])])
                            if zone:
                                guidance["highlight_zone"] = zone
                        duration = args.get("duration_ms") or args.get("duration")
                        if duration is not None:
                            guidance["highlight_ms"] = int(duration)
                    elif tool_name == "reveal_map":
                        if "enabled" in args:
                            guidance["reveal_map"] = bool(args.get("enabled"))

                # Ensure hint key exists for downstream UI even if empty
                guidance.setdefault("hint", hint_text or "")
                try:
                    generated_text = json.dumps(guidance, ensure_ascii=False)
                except Exception as exc:
                    logger.error(f"Failed to encode tool guidance as JSON: {exc}")
                    if debug_info:
                        debug_logger.error(f"Tool guidance JSON encode failed: {exc}")
                    generated_text = hint_text or ""
            
            # Debug log: generation output
            if debug_info:
                debug_logger.debug(f"LLM OUTPUT:\n{generated_text}")
                debug_logger.debug("-" * 80)
                debug_logger.debug(f"Generation Time: {generation_time:.3f}s")
                debug_logger.debug(f"Output Length: {len(generated_text)} chars")
                debug_logger.debug("=" * 80 + "\n")
            
            return generated_text
            
        except OpenAIError as e:
            error_str = str(e)
            # Check for context size exceeded error
            if 'context size' in error_str.lower() or '400' in error_str:
                error_msg = f"Context size exceeded. Try reducing max_tokens or enable better history trimming."
                logger.error(f"OpenAI API error (context): {error_str}")
                debug_logger.error(f"Context size exceeded in session {debug_info.get('session_id', 'unknown')}")
            else:
                error_msg = f"OpenAI API error: {error_str}"
                logger.error(error_msg)
            if debug_info:
                debug_logger.error(error_msg)
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Generation failed: {str(e)}"
            logger.error(error_msg)
            if debug_info:
                debug_logger.error(error_msg)
            return f"Error: {error_msg}"

    
    def count_tokens(self, text: str) -> int:
        """
        Estimate token count for a text string.
        
        Args:
            text: Input text
            
        Returns:
            Estimated number of tokens
        """
        # More conservative estimation: ~3.5 characters per token for safety
        # This helps prevent context overflow
        return max(1, len(text) // 3 + len(text) % 3)
    
    def format_chat(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Return messages as-is for OpenAI-compatible API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Messages list for API call
        """
        return messages


# ============================================================================
# Session Management
# ============================================================================

class SessionManager:
    """
    Manages conversation sessions with history trimming and thread-safety.
    """
    
    def __init__(self, config: DeploymentConfig, client: LlamaCppClient):
        """
        Initialize session manager.
        
        Args:
            config: Deployment configuration
            client: Llama.cpp client
        """
        self.config = config
        self.client = client
        self.sessions: Dict[Tuple[str, str], Dict] = {}
        self.session_locks: Dict[Tuple[str, str], threading.RLock] = {}
        self.global_lock = threading.RLock()
        
        # Rate limiting: track request timestamps per session
        self.request_timestamps: Dict[Tuple[str, str], List[float]] = {}
        self.rate_limit_lock = threading.RLock()
        
        # Global inference semaphore to limit concurrent calls
        self.inference_semaphore = threading.Semaphore(8)
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_sessions, daemon=True)
        self.cleanup_thread.start()
        
    def get_or_create_session(
        self,
        session_id: str,
        project_name: str,
        system_prompt: str
    ) -> Dict:
        """
        Get existing session or create a new one.
        
        Args:
            session_id: Unique session identifier
            project_name: Project name
            system_prompt: System prompt for the session
            
        Returns:
            Session dictionary
        """
        session_key = (project_name, session_id)

        # Fast path: check if session exists without locking
        existing = self.sessions.get(session_key)
        if existing:
            existing["last_access"] = time.time()
            return existing
        
        # Slow path: create new session with minimal locking
        with self.global_lock:
            existing = self.sessions.get(session_key)
            if existing:
                existing["last_access"] = time.time()
                return existing
                
            # Check session limit
            if len(self.sessions) >= self.config.max_concurrent_sessions:
                self._evict_oldest_session()

            # Create session
            session = {
                "dialog": [{"role": "system", "content": system_prompt}],
                "project": project_name,
                "session_id": session_id,
                "created_at": time.time(),
                "last_access": time.time(),
                "message_count": 0,
            }
            self.sessions[session_key] = session
            self.session_locks[session_key] = threading.RLock()
            logger.info(
                f"Created new session: {project_name}/{session_id[:16]}..."
            )
            
        return self.sessions[session_key]
    
    def process_message(
        self,
        session_id: str,
        project_name: str,
        system_prompt: str,
        user_message: str,
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None,
        client_id: Optional[str] = None
    ) -> str:
        """
        Process a user message and generate a response.
        
        Args:
            session_id: Session identifier
            project_name: Project name
            system_prompt: System prompt
            user_message: User's message
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens
            client_id: Optional client identifier for debugging
            
        Returns:
            Generated response
        """
        # Rate limiting check
        if not self._check_rate_limit(project_name, session_id):
            return "Error: Rate limit exceeded. Please slow down your requests."
        
        # Debug log: incoming user message
        debug_logger.info("╔" + "═" * 78 + "╗")
        client_suffix = f" | Client: {client_id}" if client_id else ""
        debug_logger.info(
            f"║ NEW MESSAGE | Session: {session_id[:16]}... | Project: {project_name}{client_suffix}"
        )
        debug_logger.info("╠" + "═" * 78 + "╣")
        debug_logger.info(f"USER MESSAGE:\n{user_message}")
        debug_logger.info("─" * 80)
        
        # Get or create session
        session = self.get_or_create_session(session_id, project_name, system_prompt)
        session_key = (project_name, session_id)
        
        # Get session lock but DON'T hold it during inference!
        session_lock = self.session_locks.get(session_key, threading.RLock())
        project_config = self.config.projects.get(project_name)

        # Build the prompt first (with minimal locking)
        with session_lock:
            repeat_count = session.get("repeat_count", 0)
            assistant_repeat_count = session.get("assistant_repeat_count", 0)
            last_raw_user = session.get("last_user_message_raw")
            adjusted_message = user_message

            if last_raw_user == user_message:
                repeat_count += 1
            else:
                repeat_count = 0

            session["repeat_count"] = repeat_count
            session["last_user_message_raw"] = user_message

            if (
                project_config
                and project_config.name == "maze"
                and (repeat_count >= 1 or assistant_repeat_count >= 1)
            ):
                # Give the model explicit context when the state or response keeps repeating.
                stuck_payload = {
                    "stuck": True,
                    "state_repeat_count": repeat_count + 1,
                    "assistant_repeat_count": assistant_repeat_count + 1,
                    "instruction": (
                        "Player appears stuck. Provide a fresh hint or pick a different tool "
                        "(show_path, highlight_zone, reveal_map, etc.) to unblock progress."
                    ),
                }
                adjusted_message = f"{user_message}\n\nSTUCK_CONTEXT: {json.dumps(stuck_payload, ensure_ascii=False)}"
                debug_logger.debug(
                    "Injected stuck context | repeat_count=%s assistant_repeat_count=%s",
                    repeat_count,
                    assistant_repeat_count,
                )

            # Add user message to dialog
            session["dialog"].append({"role": "user", "content": adjusted_message})
            session["message_count"] += 1
            
            debug_logger.debug(f"Conversation history length: {len(session['dialog'])} messages")
            
            # Token-based trimming: remove old messages if history exceeds max_history_tokens
            total_tokens = sum(self.client.count_tokens(msg.get('content', '')) for msg in session['dialog'])
            debug_logger.debug(f"Total conversation tokens: {total_tokens} / {self.config.max_history_tokens} limit")
            
            if total_tokens > self.config.max_history_tokens:
                # Keep system message and trim from the beginning
                system_msg = session['dialog'][0]
                remaining = session['dialog'][1:]
                
                # Binary search to find how many messages to keep
                while len(remaining) > 1:
                    test_tokens = sum(self.client.count_tokens(msg.get('content', '')) for msg in remaining)
                    if test_tokens <= self.config.max_history_tokens - self.client.count_tokens(system_msg.get('content', '')):
                        break
                    remaining = remaining[1:]  # Remove oldest message
                
                session['dialog'] = [system_msg] + remaining
                new_total_tokens = sum(self.client.count_tokens(msg.get('content', '')) for msg in session['dialog'])
                debug_logger.debug(f"Trimmed history to {len(session['dialog'])} messages, new token count: {new_total_tokens}")
            
            # Also enforce a max message count for safety
            max_messages = 50
            if len(session['dialog']) > max_messages:
                session['dialog'] = [session['dialog'][0]] + session['dialog'][-(max_messages-1):]
                debug_logger.debug(f"Also trimmed to last {max_messages} messages for safety")
            
            # Prepare messages for API call
            messages = self.client.format_chat(session["dialog"])
        
        # Now do inference WITHOUT holding session lock!
        try:
            debug_info = {
                'session_id': session_id,
                'project': project_name,
                'message_count': session['message_count'],
                'user_message': user_message
            }
            if client_id:
                debug_info['client_id'] = client_id
            
            if project_config and project_config.tools:
                debug_info['tools_used'] = [tool['function']['name'] for tool in project_config.tools if 'function' in tool]

            # Use semaphore to limit concurrent calls
            with self.inference_semaphore:
                response = self.client.generate(
                    messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    debug_info=debug_info,
                    tools=project_config.tools if project_config else None,
                    tool_choice=project_config.tool_choice if project_config else None
                )
            
            # Debug log: final response to user
            debug_logger.info(f"ASSISTANT RESPONSE:\n{response}")
            debug_logger.info("╚" + "═" * 78 + "╝\n")
            
            # Add assistant response to history (lock again briefly)
            with session_lock:
                session["dialog"].append({"role": "assistant", "content": response})
                session["last_access"] = time.time()
                previous_response = session.get("last_assistant_response", "")
                if previous_response.strip() == response.strip():
                    session["assistant_repeat_count"] = session.get("assistant_repeat_count", 0) + 1
                else:
                    session["assistant_repeat_count"] = 0
                session["last_assistant_response"] = response
            
            return response
                
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.error(f"Session {project_name}/{session_id}: {error_msg}")
            debug_logger.error(f"ERROR in session {project_name}/{session_id}: {error_msg}")
            debug_logger.info("╚" + "═" * 78 + "╝\n")
            return error_msg
    
    def _check_rate_limit(self, project_name: str, session_id: str) -> bool:
        """Check if a session is within rate limits."""
        current_time = time.time()
        session_key = (project_name, session_id)
        
        with self.rate_limit_lock:
            timestamps = self.request_timestamps.setdefault(session_key, [])
            
            # Remove timestamps outside the rate limit window
            cutoff_time = current_time - self.config.rate_limit_window
            timestamps[:] = [ts for ts in timestamps if ts > cutoff_time]
            
            # Check if we're over the limit
            if len(timestamps) >= self.config.max_requests_per_session:
                logger.warning(
                    f"Rate limit exceeded for session: {project_name}/{session_id[:8]}..."
                )
                return False
            
            # Add current timestamp
            timestamps.append(current_time)
            return True
    
    def _evict_oldest_session(self):
        """Evict the oldest session when limit is reached."""
        if not self.sessions:
            return
        
        oldest_key = min(
            self.sessions.keys(),
            key=lambda sid: self.sessions[sid]["last_access"]
        )
        
        self.sessions.pop(oldest_key, None)
        self.session_locks.pop(oldest_key, None)
        self.request_timestamps.pop(oldest_key, None)
        project_name, session_id = oldest_key
        logger.info(f"Evicted oldest session: {project_name}/{session_id[:16]}...")
    
    def _cleanup_sessions(self):
        """Background thread to cleanup expired sessions."""
        while True:
            time.sleep(300)  # Check every 5 minutes
            
            current_time = time.time()
            expired = []
            
            with self.global_lock:
                for sid, session in list(self.sessions.items()):
                    if current_time - session["last_access"] > self.config.session_timeout:
                        expired.append(sid)
                
                for sid in expired:
                    self.sessions.pop(sid, None)
                    self.session_locks.pop(sid, None)
                    self.request_timestamps.pop(sid, None)
            
            if expired:
                logger.info(
                    f"Cleaned up {len(expired)} expired sessions: "
                    + ", ".join(f"{sid[0]}/{sid[1][:8]}" for sid in expired)
                )

    # ------------------------------------------------------------------
    # Session maintenance helpers (template resets, cleanup, etc.)
    # ------------------------------------------------------------------

    def update_project_prompt(self, project_name: str, new_prompt: str):
        """Update the default system prompt for a project."""
        project_config = self.config.projects.get(project_name)
        if project_config:
            project_config.system_prompt = new_prompt

    def reset_session(
        self,
        project_name: str,
        session_id: str,
        system_prompt: Optional[str] = None,
        reset_history: bool = True
    ) -> bool:
        """Reset a session's system prompt and optionally clear history."""
        if not session_id:
            return False

        session_key = (project_name, session_id)
        project_config = self.config.projects.get(project_name)
        project_prompt = system_prompt or (project_config.system_prompt if project_config else "You are a helpful assistant.")

        with self.global_lock:
            session = self.sessions.get(session_key)
            if not session:
                # Create session so future messages pick up new prompt
                session = self.get_or_create_session(session_id, project_name, project_prompt)
            lock = self.session_locks.setdefault(session_key, threading.RLock())

        with lock:
            prompt_text = system_prompt or project_prompt
            if not prompt_text and session["dialog"]:
                prompt_text = session["dialog"][0].get("content", "")
            if reset_history:
                session["dialog"] = [{"role": "system", "content": prompt_text}]
                session["message_count"] = 0
            else:
                session["dialog"][0] = {"role": "system", "content": prompt_text}
            session["last_access"] = time.time()

        return True

    def reset_all_sessions(
        self,
        project_name: str,
        system_prompt: Optional[str] = None,
        reset_history: bool = True
    ) -> int:
        """Reset all sessions for a project. Returns the number of sessions touched."""
        affected = 0
        targets = [key for key in self.sessions.keys() if key[0] == project_name]
        for _, session_id in targets:
            if self.reset_session(project_name, session_id, system_prompt, reset_history):
                affected += 1
        return affected

    def clear_session(self, project_name: str, session_id: str) -> bool:
        """Clear a session's history while keeping its system prompt."""
        return self.reset_session(project_name, session_id, reset_history=True)

    def clear_all_sessions(self, project_name: str) -> int:
        """Clear history for all sessions in a project."""
        return self.reset_all_sessions(project_name, reset_history=True)

    def delete_session(self, project_name: str, session_id: str) -> bool:
        """Delete a specific session entirely."""
        session_key = (project_name, session_id)
        with self.global_lock:
            removed = self.sessions.pop(session_key, None) is not None
            self.session_locks.pop(session_key, None)
            self.request_timestamps.pop(session_key, None)
        return removed

    def delete_all_sessions(self, project_name: str) -> int:
        """Delete all sessions for a project."""
        with self.global_lock:
            targets = [key for key in self.sessions.keys() if key[0] == project_name]
            for key in targets:
                self.sessions.pop(key, None)
                self.session_locks.pop(key, None)
                self.request_timestamps.pop(key, None)
        return len(targets)

    def aggressive_cleanup(self, project_name: str, session_id: str, keep_system_only: bool = True) -> bool:
        """
        Aggressively clean up a session's history when context overflows.
        
        Args:
            project_name: Project name
            session_id: Session ID
            keep_system_only: If True, keep only system message; if False, keep last user+assistant pair
            
        Returns:
            True if cleanup was performed
        """
        session_key = (project_name, session_id)
        
        with self.global_lock:
            session = self.sessions.get(session_key)
            if not session:
                return False
            
            lock = self.session_locks.get(session_key, threading.RLock())
        
        with lock:
            original_len = len(session['dialog'])
            
            if keep_system_only:
                # Keep only system message
                session['dialog'] = [session['dialog'][0]] if session['dialog'] else []
            else:
                # Keep system message and last user/assistant pair
                system_msg = session['dialog'][0] if session['dialog'] else None
                user_msgs = [m for m in session['dialog'] if m.get('role') == 'user']
                assistant_msgs = [m for m in session['dialog'] if m.get('role') == 'assistant']
                
                if user_msgs and assistant_msgs:
                    session['dialog'] = [system_msg, user_msgs[-1], assistant_msgs[-1]]
                elif user_msgs:
                    session['dialog'] = [system_msg, user_msgs[-1]]
                elif system_msg:
                    session['dialog'] = [system_msg]
            
            session['message_count'] = len(session['dialog'])
            new_len = len(session['dialog'])
            
            logger.warning(f"🧹 Aggressive cleanup for {project_name}/{session_id}: {original_len} → {new_len} messages")
            return True


# ============================================================================
# Message Queue and Processing
# ============================================================================

@dataclass
class QueuedMessage:
    """Message queued for processing."""
    session_id: str
    project_name: str
    user_message: str
    response_topic: str
    client_id: Optional[str] = None
    request_id: Optional[str] = None
    temperature: float = None
    top_p: float = None
    max_tokens: int = None
    custom_system_prompt: Optional[str] = None
    priority: int = 0
    timestamp: float = field(default_factory=time.time)


class MessageProcessor:
    """
    Processes queued messages.
    """
    
    def __init__(
        self,
        config: DeploymentConfig,
        session_manager: SessionManager,
        mqtt_client: mqtt.Client
    ):
        """
        Initialize message processor.
        
        Args:
            config: Deployment configuration
            session_manager: Session manager
            mqtt_client: MQTT client for publishing responses
        """
        self.config = config
        self.session_manager = session_manager
        self.mqtt_client = mqtt_client
        self.message_queue = queue.PriorityQueue(maxsize=config.max_queue_size)
        self.running = True
        
        # Separate queue for publishing responses (non-blocking)
        self.publish_queue = queue.Queue()
        
        # Statistics
        self.stats = {
            "processed": 0,
            "errors": 0,
            "rejected": 0,
            "total_latency": 0.0
        }
        self.stats_lock = threading.Lock()
        
    def enqueue(self, message: QueuedMessage):
        """Add message to processing queue."""
        try:
            self.message_queue.put((message.priority, message.timestamp, message), block=False)
            logger.debug(f"Enqueued message from session {message.session_id[:8]}...")
        except queue.Full:
            logger.error(f"Message queue full! Rejecting message from session {message.session_id[:8]}...")
            error_msg = "Server is overloaded. Please try again in a moment."
            self.mqtt_client.publish(message.response_topic, error_msg, qos=0)
            with self.stats_lock:
                self.stats["rejected"] += 1
    
    def process_loop(self):
        """Main processing loop for a worker thread."""
        while self.running:
            try:
                priority, timestamp, msg = self.message_queue.get(timeout=1.0)
                
                start_time = time.time()
                self._process_single_message(msg)
                latency = time.time() - start_time
                
                with self.stats_lock:
                    self.stats["processed"] += 1
                    self.stats["total_latency"] += latency
                
                logger.info(
                    f"Processed message for session {msg.session_id[:8]}... "
                    f"in {latency:.3f}s"
                )
                
                self.message_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in processing loop: {e}")
                with self.stats_lock:
                    self.stats["errors"] += 1
    
    def _process_single_message(self, msg: QueuedMessage):
        """Process a single message."""
        try:
            # Determine system prompt
            if msg.custom_system_prompt:
                system_prompt = msg.custom_system_prompt
                logger.debug(f"Using custom system prompt for session: {msg.session_id}")
                debug_logger.debug(f"Custom system prompt: {system_prompt[:100]}...")
            else:
                project_config = self.config.projects.get(msg.project_name)
                if not project_config:
                    logger.warning(f"Unknown project: {msg.project_name}, using general prompt")
                    system_prompt = SYSTEM_PROMPTS["general"]
                else:
                    system_prompt = project_config.system_prompt
            
            # Process message
            response = self.session_manager.process_message(
                session_id=msg.session_id,
                project_name=msg.project_name,
                system_prompt=system_prompt,
                user_message=msg.user_message,
                temperature=msg.temperature,
                top_p=msg.top_p,
                max_tokens=msg.max_tokens,
                client_id=msg.client_id
            )
            
            # Check if we got a context size error
            if 'context size' in response.lower() or ('error' in response.lower() and '400' in response):
                logger.warning(f"Context overflow detected for session {msg.session_id}, triggering cleanup...")
                
                # Try aggressive cleanup and retry once
                self.session_manager.aggressive_cleanup(msg.project_name, msg.session_id, keep_system_only=False)
                
                # Retry with cleaned history
                response = self.session_manager.process_message(
                    session_id=msg.session_id,
                    project_name=msg.project_name,
                    system_prompt=system_prompt,
                    user_message=msg.user_message,
                    temperature=msg.temperature,
                    top_p=msg.top_p,
                    max_tokens=msg.max_tokens,
                    client_id=msg.client_id
                )
                
                if 'context size' not in response.lower():
                    response = f"[Session history was too long and was reset]\n\n{response}"
            
            # Queue response for publishing
            self.publish_queue.put((msg.response_topic, response), block=False)
            debug_logger.debug(f"Response queued for publishing\n")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            debug_logger.error(f"Error in message processor: {e}")
            error_response = f"Error: {str(e)}"
            try:
                self.publish_queue.put((msg.response_topic, error_response), block=False)
            except queue.Full:
                logger.error(f"Publish queue full, dropping error response")
            debug_logger.debug(f"Error response queued\n")
    
    def get_stats(self) -> Dict:
        """Get processing statistics."""
        with self.stats_lock:
            stats = self.stats.copy()
            if stats["processed"] > 0:
                stats["avg_latency"] = stats["total_latency"] / stats["processed"]
            else:
                stats["avg_latency"] = 0.0
            return stats
    
    def publish_loop(self):
        """Background loop for publishing responses (non-blocking)."""
        while self.running:
            try:
                response_topic, response = self.publish_queue.get(timeout=1.0)
                
                response_topic = response_topic.rstrip("/")
                
                # Publish with QoS 0
                result = self.mqtt_client.publish(response_topic, response, qos=0)
                
                # Log publish status
                if result.rc == 0:
                    logger.info(f"📤 Published response to: {response_topic} ({len(response)} chars)")
                else:
                    logger.warning(f"⚠️  Publish may have failed to: {response_topic} (rc={result.rc})")
                
                debug_logger.debug(f"Response published to topic: {response_topic}\n")
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error publishing response: {e}")
                debug_logger.error(f"Error in publish loop: {e}\n")


# ============================================================================
# MQTT Handler
# ============================================================================

class MQTTHandler:
    """
    Handles MQTT communication and message routing.
    """
    
    def __init__(
        self,
        config: DeploymentConfig,
        message_processor: MessageProcessor
    ):
        """
        Initialize MQTT handler.
        
        Args:
            config: Deployment configuration
            message_processor: Message processor
        """
        self.config = config
        self.message_processor = message_processor
        
        # Create MQTT client
        client_id = f"llamacpp-deploy-{uuid.uuid4().hex[:8]}"
        self.client = mqtt.Client(client_id=client_id, callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        
        # Set authentication if provided
        if config.mqtt_username and config.mqtt_password:
            self.client.username_pw_set(config.mqtt_username, config.mqtt_password)
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        # Reconnection settings
        self.client.reconnect_delay_set(min_delay=1, max_delay=120)
        
    def _on_connect(self, client, userdata, flags, rc, properties=None):
        """Callback for MQTT connection."""
        if rc == 0:
            logger.info(f"✓ Connected to MQTT broker at {self.config.mqtt_broker}:{self.config.mqtt_port}")
            
            # Subscribe to all enabled project topics
            for project_name, project_config in self.config.projects.items():
                if project_config.enabled:
                    # Subscribe to user input topic
                    topic = project_config.user_topic
                    client.subscribe(topic, qos=1)
                    logger.info(f"✓ Subscribed to INPUT topic: {topic} (project: {project_name})")
                    
                    # Subscribe to state topic if configured (for game state messages)
                    if project_config.state_topic:
                        client.subscribe(project_config.state_topic, qos=1)
                        logger.info(f"✓ Subscribed to STATE topic: {project_config.state_topic} (project: {project_name})")
                    
                    logger.info(f"  → Will publish responses to: {project_config.response_topic}")
                    if project_config.hint_topic:
                        logger.info(f"  → Will publish hints to: {project_config.hint_topic}")

                    if project_config.template_topic:
                        tpl_base = project_config.template_topic.rstrip('/')
                        client.subscribe(tpl_base, qos=1)
                        client.subscribe(f"{tpl_base}/+", qos=1)
                        logger.info(f"✓ Subscribed to TEMPLATE topic: {tpl_base} (project: {project_name})")

                    if project_config.clear_topic:
                        clr_base = project_config.clear_topic.rstrip('/')
                        client.subscribe(clr_base, qos=1)
                        client.subscribe(f"{clr_base}/+", qos=1)
                        logger.info(f"✓ Subscribed to CLEAR topic: {clr_base} (project: {project_name})")

                    if project_config.delete_topic:
                        del_base = project_config.delete_topic.rstrip('/')
                        client.subscribe(del_base, qos=1)
                        client.subscribe(f"{del_base}/+", qos=1)
                        logger.info(f"✓ Subscribed to DELETE topic: {del_base} (project: {project_name})")
        else:
            logger.error(f"✗ Failed to connect to MQTT broker, code: {rc}")
    
    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        """Callback for MQTT disconnection."""
        if rc != 0:
            logger.warning(f"Unexpected disconnect from MQTT broker, code: {rc}")
    
    def _normalize_session_id(self, raw_session_id) -> str:
        """Convert arbitrary session identifiers into a safe string."""
        if isinstance(raw_session_id, str):
            candidate = raw_session_id.strip()
            if candidate:
                return candidate
        elif raw_session_id is not None:
            candidate = str(raw_session_id).strip()
            if candidate:
                logger.debug(f"Session id coerced to string: original={raw_session_id!r} -> {candidate!r}")
                return candidate

        generated = f"default-{uuid.uuid4().hex[:8]}"
        logger.debug(
            "Missing or empty sessionId in payload; generated fallback id %s", generated
        )
        return generated

    def _convert_state_to_message(self, state: dict, project_name: str) -> str:
        """Convert game state dict to descriptive user message."""
        try:
            # Extract key state information
            player_pos = state.get("player_pos", {})
            exit_pos = state.get("exit_pos", {})
            visible_map = state.get("visible_map", [])
            germs = state.get("germs", [])
            oxygen_pellets = state.get("oxygenPellets", [])
            oxygen_collected = state.get("oxygenCollected", 0)
            
            # Convert to lists of [x, y] coords
            def to_xy_list(objs):
                out = []
                for it in (objs or []):
                    if isinstance(it, dict) and "x" in it and "y" in it:
                        out.append([int(it["x"]), int(it["y"])])
                    elif isinstance(it, (list, tuple)) and len(it) == 2:
                        out.append([int(it[0]), int(it[1])])
                return out
            
            # Create structured message
            message_data = {
                "player_pos": [player_pos.get("x", 0), player_pos.get("y", 0)] if isinstance(player_pos, dict) else player_pos,
                "exit_pos": [exit_pos.get("x", 0), exit_pos.get("y", 0)] if isinstance(exit_pos, dict) else exit_pos,
                "visible_map": visible_map,
                "germs": to_xy_list(germs),
                "oxygen": to_xy_list(oxygen_pellets),
                "oxygen_collected": oxygen_collected
            }
            
            return json.dumps(message_data, ensure_ascii=False)
            
        except Exception as e:
            logger.error(f"Error converting state to message: {e}")
            debug_logger.error(f"State conversion error: {e}")
            # Return minimal fallback
            return json.dumps({"error": "Invalid state data", "raw_state": str(state)[:200]})

    def _resolve_response_topic(self, base_topic: str, session_id: str, reply_topic: Optional[str]) -> str:
        """Choose the MQTT topic used for assistant responses."""
        session_topic = f"{base_topic}/{session_id}"

        if isinstance(reply_topic, str):
            candidate = reply_topic.strip()
            if not candidate:
                logger.warning("Ignoring empty replyTopic override")
                return session_topic

            if any(wildcard in candidate for wildcard in ("#", "+")):
                logger.warning("Ignoring replyTopic with MQTT wildcards: %s", candidate)
                return session_topic

            expected_prefix = f"{base_topic}/"
            if not candidate.startswith(expected_prefix):
                logger.warning(
                    "Ignoring replyTopic '%s' that does not start with expected prefix '%s'",
                    candidate,
                    expected_prefix,
                )
                return session_topic

            suffix = candidate[len(expected_prefix):].strip("/")
            if not suffix:
                logger.warning("Ignoring replyTopic missing session segment: %s", candidate)
                return session_topic

            suffix_parts = suffix.split("/")
            candidate_session = suffix_parts[0]
            if candidate_session != session_id:
                logger.debug(
                    "replyTopic session mismatch (payload='%s', expected session='%s'); using client override",
                    candidate_session,
                    session_id,
                )

            return candidate

        return session_topic

    # ------------------------------------------------------------------
    # Topic helpers for template & session maintenance commands
    # ------------------------------------------------------------------

    def _topic_matches(self, topic: str, base: Optional[str]) -> bool:
        if not base:
            return False
        base_clean = base.rstrip('/')
        return topic == base_clean or topic.startswith(f"{base_clean}/")

    def _extract_topic_session(self, topic: str, base: Optional[str]) -> Optional[str]:
        if not base:
            return None
        base_clean = base.rstrip('/')
        if topic == base_clean:
            return None
        prefix = f"{base_clean}/"
        if topic.startswith(prefix):
            suffix = topic[len(prefix):].strip()
            return suffix or None
        return None

    def _publish_hint_notice(self, project_config: ProjectConfig, session_id: Optional[str], payload: Dict[str, object]):
        if not session_id or not project_config:
            return
        target_base = project_config.hint_topic or project_config.response_topic
        if not target_base:
            return
        topic = f"{target_base.rstrip('/')}/{session_id}"
        try:
            message = json.dumps(payload, ensure_ascii=False)
        except Exception as exc:
            logger.error(f"Failed to encode hint notice for session {session_id}: {exc}")
            return
        logger.debug(f"Publishing hint notice to {topic}: {message}")
        self.client.publish(topic, message, qos=0)

    def _handle_template_message(self, project_name: str, project_config: ProjectConfig, payload_text: str, topic: str):
        try:
            payload = json.loads(payload_text) if payload_text else {}
        except json.JSONDecodeError as exc:
            logger.error(f"Invalid JSON in template message for {project_name}: {exc}")
            return

        raw_template = (
            payload.get("template")
            or payload.get("system_prompt")
            or payload.get("prompt_template")
        )
        if isinstance(raw_template, dict):
            raw_template = raw_template.get("content") or raw_template.get("template")

        if not isinstance(raw_template, str) or not raw_template.strip():
            logger.warning(f"Template update missing template content for project {project_name}")
            return

        new_prompt = raw_template.strip()
        reset = bool(payload.get("reset", True))
        if payload.get("max_breaks") is not None:
            logger.info(f"Template payload requested max_breaks={payload.get('max_breaks')} (not managed by this deploy script)")
        session_id = payload.get("session_id") or payload.get("sessionId")
        if not session_id:
            session_id = self._extract_topic_session(topic, project_config.template_topic)

        logger.info(f"Template update for project '{project_name}' (session: {session_id or 'GLOBAL'}), reset={reset}")
        self.message_processor.session_manager.update_project_prompt(project_name, new_prompt)

        if session_id:
            self.message_processor.session_manager.reset_session(
                project_name,
                session_id,
                system_prompt=new_prompt,
                reset_history=reset,
            )
            self._publish_hint_notice(project_config, session_id, {"hint": "Template updated"})
        else:
            if reset:
                affected = self.message_processor.session_manager.reset_all_sessions(
                    project_name,
                    system_prompt=new_prompt,
                    reset_history=True,
                )
                logger.info(f"Reset {affected} sessions after global template update for {project_name}")
            else:
                affected = self.message_processor.session_manager.reset_all_sessions(
                    project_name,
                    system_prompt=new_prompt,
                    reset_history=False,
                )
                logger.info(f"Updated prompt for {affected} sessions without clearing history for {project_name}")

    def _handle_clear_history_message(self, project_name: str, project_config: ProjectConfig, payload_text: str, topic: str):
        try:
            payload = json.loads(payload_text) if payload_text else {}
        except json.JSONDecodeError as exc:
            logger.error(f"Invalid JSON in clear-history message for {project_name}: {exc}")
            return

        target = payload.get("session_id") or payload.get("sessionId") or payload.get("target")
        if not target:
            target = self._extract_topic_session(topic, project_config.clear_topic)

        if target and str(target).lower() != "all":
            session_id = str(target)
            cleared = self.message_processor.session_manager.clear_session(project_name, session_id)
            logger.info(f"Clear history request for {project_name}/{session_id}: {'cleared' if cleared else 'not found'}")
            if cleared:
                self._publish_hint_notice(project_config, session_id, {"hint": "History cleared"})
        else:
            count = self.message_processor.session_manager.clear_all_sessions(project_name)
            logger.info(f"Cleared history for {count} sessions in project {project_name}")

    def _handle_delete_session_message(self, project_name: str, project_config: ProjectConfig, payload_text: str, topic: str):
        try:
            payload = json.loads(payload_text) if payload_text else {}
        except json.JSONDecodeError as exc:
            logger.error(f"Invalid JSON in delete-session message for {project_name}: {exc}")
            return

        target = payload.get("session_id") or payload.get("sessionId") or payload.get("target")
        if not target:
            target = self._extract_topic_session(topic, project_config.delete_topic)

        if target and str(target).lower() != "all":
            session_id = str(target)
            removed = self.message_processor.session_manager.delete_session(project_name, session_id)
            logger.info(f"Delete session request for {project_name}/{session_id}: {'deleted' if removed else 'not found'}")
        else:
            count = self.message_processor.session_manager.delete_all_sessions(project_name)
            logger.info(f"Deleted {count} sessions for project {project_name}")

    def _on_message(self, client, userdata, msg):
        """Callback for incoming MQTT messages."""
        try:
            payload = msg.payload.decode('utf-8')
            
            logger.info(f"📨 Received message on topic: {msg.topic}")
            debug_logger.debug(f"RAW MQTT MESSAGE | Topic: {msg.topic}")
            debug_logger.debug(f"Payload: {payload}")
            
            # Handle template and maintenance commands first
            for pname, pconfig in self.config.projects.items():
                if self._topic_matches(msg.topic, pconfig.template_topic):
                    self._handle_template_message(pname, pconfig, payload, msg.topic)
                    return
                if self._topic_matches(msg.topic, pconfig.clear_topic):
                    self._handle_clear_history_message(pname, pconfig, payload, msg.topic)
                    return
                if self._topic_matches(msg.topic, pconfig.delete_topic):
                    self._handle_delete_session_message(pname, pconfig, payload, msg.topic)
                    return

            # Find which project this message belongs to and message type
            project_name = None
            response_topic = None
            is_state_message = False
            project_config = None
            
            for pname, pconfig in self.config.projects.items():
                if msg.topic == pconfig.user_topic:
                    project_name = pname
                    response_topic = pconfig.response_topic
                    project_config = pconfig
                    is_state_message = False
                    break
                elif pconfig.state_topic and msg.topic == pconfig.state_topic:
                    project_name = pname
                    # For state messages, use hint_topic if available, otherwise response_topic
                    response_topic = pconfig.hint_topic if pconfig.hint_topic else pconfig.response_topic
                    project_config = pconfig
                    is_state_message = True
                    break
            
            if not project_name:
                logger.warning(f"❌ Received message from unknown topic: {msg.topic}")
                expected = []
                for p in self.config.projects.values():
                    expected.append(p.user_topic)
                    if p.state_topic:
                        expected.append(p.state_topic)
                logger.warning(f"   Expected topics: {expected}")
                debug_logger.warning(f"Unknown topic: {msg.topic}")
                return
            
            # Parse message based on type
            try:
                data = json.loads(payload)
                
                if is_state_message:
                    # Game state message - convert to descriptive text
                    session_id = self._normalize_session_id(data.get("sessionId"))
                    user_message = self._convert_state_to_message(data, project_name)
                    logger.info(f"📊 Processing STATE message for session: {session_id}")
                else:
                    # Regular user input message
                    session_id = self._normalize_session_id(data.get("sessionId"))
                    user_message = data.get("message", "")
                    logger.info(f"💬 Processing USER message for session: {session_id}")
                
                temperature = data.get("temperature")
                top_p = data.get("topP")
                max_tokens = data.get("maxTokens")
                custom_system_prompt = data.get("systemPrompt") or data.get("prompt_template", {}).get("content")
                reply_topic_override = data.get("replyTopic")
                client_id = data.get("clientId")
                request_id = data.get("requestId")
                
                debug_logger.debug(f"PARSED | Session: {session_id}, Project: {project_name}, Type: {'STATE' if is_state_message else 'USER'}")
                debug_logger.debug(f"Message: {user_message[:200]}...")
                if temperature or top_p or max_tokens:
                    debug_logger.debug(f"Custom params - Temp: {temperature}, TopP: {top_p}, MaxTokens: {max_tokens}")
                if custom_system_prompt:
                    debug_logger.debug(f"Custom system prompt: {custom_system_prompt[:100]}...")
                if client_id:
                    debug_logger.debug(f"Client id: {client_id}")
                if request_id:
                    debug_logger.debug(f"Request id: {request_id}")
                
                if not user_message.strip():
                    logger.warning(f"Empty message received from session: {session_id}")
                    debug_logger.warning(f"Empty message from session: {session_id}")
                    return
                
            except json.JSONDecodeError:
                # Not JSON, treat as plain text user message
                session_id = self._normalize_session_id(None)
                user_message = payload
                temperature = None
                top_p = None
                max_tokens = None
                custom_system_prompt = None
                reply_topic_override = None
                client_id = None
                request_id = None
                is_state_message = False
                debug_logger.debug(f"JSON decode failed, using raw payload as message")
            
            # Format response topic
            response_topic_full = self._resolve_response_topic(
                response_topic,
                session_id,
                reply_topic_override,
            )
            
            # Create queued message
            queued_msg = QueuedMessage(
                session_id=session_id,
                project_name=project_name,
                user_message=user_message,
                response_topic=response_topic_full,
                client_id=client_id,
                request_id=request_id,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                custom_system_prompt=custom_system_prompt
            )
            
            # Enqueue for processing
            self.message_processor.enqueue(queued_msg)
            logger.debug(f"Enqueued message from session: {session_id}")
            debug_logger.debug(f"Message enqueued for processing | Session: {session_id}\n")
            
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
            debug_logger.error(f"Error handling MQTT message: {e}\n")
    
    def connect(self):
        """Connect to MQTT broker."""
        try:
            self.client.connect(self.config.mqtt_broker, self.config.mqtt_port, keepalive=60)
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False
    
    def start_loop(self):
        """Start MQTT network loop."""
        self.client.loop_forever()
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.client.disconnect()


# ============================================================================
# Main Deployment Function
# ============================================================================

def main(
    # Project selection
    projects: str = "general",
    
    # Llama.cpp Server Configuration
    server_url: str = "http://localhost:8080",
    server_timeout: int = 300,
    
    # Generation parameters
    temperature: float = 1.2,
    top_p: float = 0.9,
    max_tokens: int = 512,
    
    # Session management
    max_history_tokens: int = 3000,
    max_concurrent_sessions: int = 100,
    
    # MQTT configuration
    mqtt_broker: str = "47.89.252.2",
    mqtt_port: int = 1883,
    mqtt_username: Optional[str] = None,
    mqtt_password: Optional[str] = None,
    
    # Performance
    num_workers: int = 12,
    
    # Output processing
    skip_thinking: bool = True,
):
    """
    Deploy Llama.cpp model with MQTT interface for multiple projects.
    
    Args:
        projects: Project names to enable (space or comma separated)
        server_url: URL of llama.cpp server (default: http://localhost:8080)
        server_timeout: Request timeout in seconds (default: 300)
        temperature: Default sampling temperature
        top_p: Default top-p sampling
        max_tokens: Default max tokens to generate
        max_history_tokens: Maximum tokens to keep in conversation history
        max_concurrent_sessions: Maximum concurrent sessions
        mqtt_broker: MQTT broker address
        mqtt_port: MQTT broker port
        mqtt_username: MQTT username (optional)
        mqtt_password: MQTT password (optional)
        num_workers: Number of worker threads
        skip_thinking: Disable thinking mode (adds /no_think to prompt).
                      For Qwen3-30B with deep thinking enabled, set to False to show thinking.
                      Default: True (thinking mode disabled for faster responses)
    
    Thinking Mode Control:
        When skip_thinking=True (default):
        - Adds /no_think directive to disable Qwen3 deep thinking
        - Faster response times with direct answers
        - Lower token consumption
        
        When skip_thinking=False:
        - Allows full thinking/reasoning process
        - Longer response times but potentially better reasoning
        - Higher token consumption (thinking tokens count as output)
    
    Examples:
        # Deploy for maze game only (thinking disabled)
        python llamacpp_mqtt_deploy.py --projects maze
        
        # Deploy with thinking enabled for better reasoning
        python llamacpp_mqtt_deploy.py --projects "maze driving" --skip_thinking False
        
        # Deploy for multiple projects (space-separated)
        python llamacpp_mqtt_deploy.py --projects "maze driving bloodcell"
        
        # With custom server URL and MQTT credentials
        python llamacpp_mqtt_deploy.py \\
            --projects "maze driving" \\
            --server_url http://192.168.1.100:8080 \\
            --mqtt_username user \\
            --mqtt_password pass
        
        # With custom generation parameters
        python llamacpp_mqtt_deploy.py \\
            --projects general \\
            --temperature 0.7 \\
            --top_p 0.95 \\
            --max_tokens 1024 \\
            --skip_thinking False
    """
    
    logger.info("=" * 80)
    logger.info("Llama.cpp MQTT Deployment")
    logger.info("=" * 80)
    
    # Initialize debug log
    debug_logger.info("\n" + "=" * 80)
    debug_logger.info("LLAMA.CPP DEPLOYMENT STARTED")
    debug_logger.info(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    debug_logger.info("=" * 80 + "\n")
    
    # Parse projects parameter
    if isinstance(projects, str):
        projects_list = [p.strip() for p in projects.replace(',', ' ').split() if p.strip()]
    else:
        projects_list = projects
    
    # Create project configurations
    project_configs = {}
    for project_name in projects_list:
        system_prompt = SYSTEM_PROMPTS.get(project_name, SYSTEM_PROMPTS["general"])
        
        # Special handling for maze project - also subscribe to state topic
        if project_name == "maze":
            project_configs[project_name] = ProjectConfig(
                name=project_name,
                user_topic=f"{project_name}/user_input",
                state_topic=f"{project_name}/state",  # Game state messages
                response_topic=f"{project_name}/assistant_response",
                hint_topic=f"{project_name}/hint",  # Hint responses for game
                template_topic=f"{project_name}/template",
                clear_topic=f"{project_name}/clear_history",
                delete_topic=f"{project_name}/delete_session",
                system_prompt=system_prompt,
                enabled=True,
                tools=MAZE_ACTION_TOOLS,
                tool_choice="auto"
            )
        else:
            project_configs[project_name] = ProjectConfig(
                name=project_name,
                user_topic=f"{project_name}/user_input",
                response_topic=f"{project_name}/assistant_response",
                system_prompt=system_prompt,
                enabled=True
            )
    
    # Create deployment config
    config = DeploymentConfig(
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        server_url=server_url,
        server_timeout=server_timeout,
        default_temperature=temperature,
        default_top_p=top_p,
        default_max_tokens=max_tokens,
        max_history_tokens=max_history_tokens,
        max_concurrent_sessions=max_concurrent_sessions,
        num_worker_threads=num_workers,
        skip_thinking=skip_thinking,
        projects=project_configs
    )
    
    logger.info(f"Enabled projects: {', '.join(projects_list)}")
    logger.info(f"Llama.cpp server: {server_url}")
    logger.info(f"Request timeout: {server_timeout}s")
    logger.info(f"Temperature: {temperature}")
    logger.info(f"Top-P: {top_p}")
    logger.info(f"Max tokens: {max_tokens}")
    logger.info(f"Skip thinking output: {skip_thinking}")
    logger.info(f"Worker threads: {num_workers}")
    logger.info(f"Max queue size: {config.max_queue_size}")
    logger.info(f"Rate limiting: {config.max_requests_per_session} req/{config.rate_limit_window}s per session")
    
    try:
        # 1. Initialize llama.cpp client
        logger.info("-" * 80)
        logger.info("Step 1: Initializing Llama.cpp client...")
        client = LlamaCppClient(config)
        
        # 2. Initialize session manager
        logger.info("-" * 80)
        logger.info("Step 2: Initializing session manager...")
        session_manager = SessionManager(config, client)
        
        # 3. Initialize message processor
        logger.info("-" * 80)
        logger.info("Step 3: Initializing message processor...")
        mqtt_client = mqtt.Client(
            client_id=f"llamacpp-temp-{uuid.uuid4().hex[:8]}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        message_processor = MessageProcessor(config, session_manager, mqtt_client)
        
        # 4. Initialize MQTT handler
        logger.info("-" * 80)
        logger.info("Step 4: Initializing MQTT handler...")
        mqtt_handler = MQTTHandler(config, message_processor)
        
        # Update message processor with real client
        message_processor.mqtt_client = mqtt_handler.client
        
        # 5. Start worker threads
        logger.info("-" * 80)
        logger.info(f"Step 5: Starting {num_workers} worker threads...")
        thread_pool = ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="llamacpp-worker")
        for i in range(num_workers):
            thread_pool.submit(message_processor.process_loop)
        logger.info(f"Started {num_workers} worker threads")
        
        # Start publisher thread
        logger.info("Starting response publisher thread...")
        publisher_thread = threading.Thread(target=message_processor.publish_loop, daemon=True, name="llamacpp-publisher")
        publisher_thread.start()
        logger.info("Started response publisher thread")
        
        # 6. Connect to MQTT broker
        logger.info("-" * 80)
        logger.info("Step 6: Connecting to MQTT broker...")
        if not mqtt_handler.connect():
            logger.error("Failed to connect to MQTT broker. Exiting.")
            return
        
        # 7. Start MQTT loop
        logger.info("-" * 80)
        logger.info("Deployment ready! Listening for messages...")
        logger.info("=" * 80)
        logger.info("📝 Debug logging enabled: debug_info.log")
        logger.info("   (Contains full user inputs, LLM prompts, and outputs)")
        logger.info("-" * 80)
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)
        
        # Statistics reporting thread
        def report_stats():
            while True:
                time.sleep(60)
                stats = message_processor.get_stats()
                queue_size = message_processor.message_queue.qsize()
                logger.info(
                    f"📊 Stats: Processed={stats['processed']}, Errors={stats['errors']}, "
                    f"Rejected={stats.get('rejected', 0)}, QueueSize={queue_size}, "
                    f"AvgLatency={stats['avg_latency']:.3f}s"
                )
                if queue_size > config.max_queue_size * 0.7:
                    logger.warning(f"⚠️  Queue is {queue_size}/{config.max_queue_size} ({queue_size*100//config.max_queue_size}% full) - Server may be overloaded!")
        
        stats_thread = threading.Thread(target=report_stats, daemon=True)
        stats_thread.start()
        
        # Start MQTT loop (blocking)
        mqtt_handler.start_loop()
        
    except KeyboardInterrupt:
        logger.info("\nShutdown signal received...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        # Cleanup
        logger.info("Cleaning up...")
        if 'mqtt_handler' in locals():
            mqtt_handler.disconnect()
        if 'thread_pool' in locals():
            message_processor.running = False
            thread_pool.shutdown(wait=True, timeout=10)
        logger.info("Shutdown complete")


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    fire.Fire(main)
'''
llama-server -m qwen3-30b-a3b-instruct-2507-Q4_K_M.gguft --host 0.0.0.0 --port 8080 -c 568192 -ngl 40 -t 8 --parallel 8 --jinja
'''

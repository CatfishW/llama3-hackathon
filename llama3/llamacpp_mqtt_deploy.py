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
    
    "general": """You are a helpful AI assistant. Provide clear, concise, and accurate responses."""
}


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
        debug_info: dict = None
    ) -> str:
        """
        Generate response using OpenAI-compatible chat completion API.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (default from config)
            top_p: Top-p sampling (default from config)
            max_tokens: Maximum tokens to generate (default from config)
            debug_info: Optional debug info dict to log details
            
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
        
        try:
            start_time = time.time()
            
            # Prepare extra body parameters for llama.cpp
            extra_body = {
                "enable_thinking": not self.config.skip_thinking
            }
            
            # Call chat completions using OpenAI client
            response = self.client.chat.completions.create(
                model="default",
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                extra_body=extra_body
            )
            
            generation_time = time.time() - start_time
            
            # Extract generated text from response
            generated_text = response.choices[0].message.content
            
            # Debug log: generation output
            if debug_info:
                debug_logger.debug(f"LLM OUTPUT:\n{generated_text}")
                debug_logger.debug("-" * 80)
                debug_logger.debug(f"Generation Time: {generation_time:.3f}s")
                debug_logger.debug(f"Output Length: {len(generated_text)} chars")
                debug_logger.debug("=" * 80 + "\n")
            
            return generated_text
            
        except OpenAIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
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
        # Rough estimation: ~4 characters per token
        return len(text) // 4
    
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
        
        # Build the prompt first (with minimal locking)
        with session_lock:
            # Add user message to dialog
            session["dialog"].append({"role": "user", "content": user_message})
            session["message_count"] += 1
            
            debug_logger.debug(f"Conversation history length: {len(session['dialog'])} messages")
            
            # Simple trimming: keep only last N messages
            max_messages = 20
            if len(session["dialog"]) > max_messages:
                session["dialog"] = [session["dialog"][0]] + session["dialog"][-(max_messages-1):]
                debug_logger.debug(f"Trimmed to last {max_messages} messages")
            
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
            
            # Use semaphore to limit concurrent calls
            with self.inference_semaphore:
                response = self.client.generate(
                    messages,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    debug_info=debug_info
                )
            
            # Debug log: final response to user
            debug_logger.info(f"ASSISTANT RESPONSE:\n{response}")
            debug_logger.info("╚" + "═" * 78 + "╝\n")
            
            # Add assistant response to history (lock again briefly)
            with session_lock:
                session["dialog"].append({"role": "assistant", "content": response})
                session["last_access"] = time.time()
            
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
                self.mqtt_client.publish(response_topic, response, qos=0)
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
            logger.info(f"Connected to MQTT broker at {self.config.mqtt_broker}:{self.config.mqtt_port}")
            
            # Subscribe to all enabled project topics
            for project_name, project_config in self.config.projects.items():
                if project_config.enabled:
                    topic = project_config.user_topic
                    client.subscribe(topic, qos=1)
                    logger.info(f"Subscribed to topic: {topic} (project: {project_name})")
        else:
            logger.error(f"Failed to connect to MQTT broker, code: {rc}")
    
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

    def _on_message(self, client, userdata, msg):
        """Callback for incoming MQTT messages."""
        try:
            payload = msg.payload.decode('utf-8')
            
            debug_logger.debug(f"RAW MQTT MESSAGE | Topic: {msg.topic}")
            debug_logger.debug(f"Payload: {payload}")
            
            # Find which project this message belongs to
            project_name = None
            response_topic = None
            
            for pname, pconfig in self.config.projects.items():
                if msg.topic == pconfig.user_topic:
                    project_name = pname
                    response_topic = pconfig.response_topic
                    break
            
            if not project_name:
                logger.warning(f"Received message from unknown topic: {msg.topic}")
                debug_logger.warning(f"Unknown topic: {msg.topic}")
                return
            
            # Parse message
            try:
                data = json.loads(payload)
                session_id = self._normalize_session_id(data.get("sessionId"))
                user_message = data.get("message", "")
                
                temperature = data.get("temperature")
                top_p = data.get("topP")
                max_tokens = data.get("maxTokens")
                custom_system_prompt = data.get("systemPrompt")
                reply_topic_override = data.get("replyTopic")
                client_id = data.get("clientId")
                request_id = data.get("requestId")
                
                debug_logger.debug(f"PARSED | Session: {session_id}, Project: {project_name}")
                debug_logger.debug(f"Message: {user_message}")
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
                session_id = self._normalize_session_id(None)
                user_message = payload
                temperature = None
                top_p = None
                max_tokens = None
                custom_system_prompt = None
                reply_topic_override = None
                client_id = None
                request_id = None
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
    temperature: float = 0.6,
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

"""
vLLM-based Multi-Project MQTT Deployment Script

This script provides an efficient, scalable deployment of language models using vLLM,
supporting multiple concurrent users across different projects via MQTT.

Features:
- vLLM-powered inference with automatic batching
- Multi-user concurrent support
- Project-based topic routing
- Session-based conversation management
- Flexible configuration via command-line
- Comprehensive logging and error handling

Usage:
    python vLLMDeploy.py --projects maze driving bloodcell --model Qwen/QwQ-32B

Author: vLLM Deployment Team
Date: 2025
"""

import json
import logging
import queue
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import fire
import paho.mqtt.client as mqtt
from vllm import LLM, SamplingParams

# ============================================================================
# Configuration and Logging Setup
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


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
    
    # Model Configuration
    model_name: str = "Qwen/QwQ-32B"
    max_model_len: int = 4096
    tensor_parallel_size: int = 1
    gpu_memory_utilization: float = 0.90
    quantization: Optional[str] = None  # e.g., "awq", "gptq", None
    visible_devices: Optional[str] = None  # e.g., "0", "1,2", "2" to specify GPU(s)
    
    # Generation Configuration
    default_temperature: float = 0.6
    default_top_p: float = 0.9
    default_max_tokens: int = 512
    
    # Session Management
    max_history_tokens: int = 3000
    max_concurrent_sessions: int = 100
    session_timeout: int = 3600  # seconds
    
    # Performance Configuration
    num_worker_threads: int = 4
    batch_timeout: float = 0.1  # seconds
    
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
# vLLM Inference Engine
# ============================================================================

class vLLMInference:
    """
    Wrapper for vLLM inference engine with optimized batching and generation.
    """
    
    def __init__(self, config: DeploymentConfig):
        """
        Initialize vLLM model.
        
        Args:
            config: Deployment configuration
        """     
        self.config = config
        logger.info(f"Initializing vLLM with model: {config.model_name}")       
        
        # Set visible GPUs if specified
        import os
        if config.visible_devices:
            os.environ["CUDA_VISIBLE_DEVICES"] = config.visible_devices
            logger.info(f"Setting CUDA_VISIBLE_DEVICES to: {config.visible_devices}")
        
        # Initialize vLLM
        try:
            self.llm = LLM(
                model=config.model_name,
                tensor_parallel_size=config.tensor_parallel_size,
                max_model_len=config.max_model_len,
                gpu_memory_utilization=config.gpu_memory_utilization,
                quantization=config.quantization,
                trust_remote_code=True,
                enforce_eager=False,  # Use CUDA graphs for better performance
            )
            logger.info("vLLM model initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vLLM: {e}")
            raise
        
        # Get tokenizer for token counting
        self.tokenizer = self.llm.get_tokenizer()
        
    def generate(
        self,
        prompts: List[str],
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None
    ) -> List[str]:
        """
        Generate responses for a batch of prompts.
        
        Args:
            prompts: List of prompt strings
            temperature: Sampling temperature (default from config)
            top_p: Top-p sampling (default from config)
            max_tokens: Maximum tokens to generate (default from config)
            
        Returns:
            List of generated response strings
        """
        if not prompts:
            return []
        
        # Use defaults from config if not specified
        temperature = temperature or self.config.default_temperature
        top_p = top_p or self.config.default_top_p
        max_tokens = max_tokens or self.config.default_max_tokens
        
        # Create sampling params
        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
        )
        
        try:
            # Generate with vLLM (automatic batching)
            outputs = self.llm.generate(prompts, sampling_params)
            
            # Extract generated text
            results = [output.outputs[0].text for output in outputs]
            return results
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return [f"Error: {str(e)}"] * len(prompts)
    
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.
        
        Args:
            text: Input text
            
        Returns:
            Number of tokens
        """
        return len(self.tokenizer.encode(text))
    
    def format_chat(self, messages: List[Dict[str, str]]) -> str:
        """
        Format messages into a chat prompt using the model's chat template.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            
        Returns:
            Formatted prompt string
        """
        try:
            # Use tokenizer's chat template if available
            if hasattr(self.tokenizer, 'apply_chat_template'):
                return self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
            else:
                # Fallback: simple concatenation
                parts = []
                for msg in messages:
                    role = msg['role'].capitalize()
                    content = msg['content']
                    parts.append(f"{role}: {content}")
                parts.append("Assistant:")
                return "\n\n".join(parts)
        except Exception as e:
            logger.warning(f"Chat formatting failed, using fallback: {e}")
            # Simple fallback
            return "\n\n".join([f"{m['role']}: {m['content']}" for m in messages]) + "\n\nAssistant:"


# ============================================================================
# Session Management
# ============================================================================

class SessionManager:
    """
    Manages conversation sessions with history trimming and thread-safety.
    """
    
    def __init__(self, config: DeploymentConfig, inference: vLLMInference):
        """
        Initialize session manager.
        
        Args:
            config: Deployment configuration
            inference: vLLM inference engine
        """
        self.config = config
        self.inference = inference
        self.sessions: Dict[str, Dict] = {}
        self.session_locks: Dict[str, threading.RLock] = {}
        self.global_lock = threading.RLock()
        
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
        # Check if session exists
        if session_id in self.sessions:
            session = self.sessions[session_id]
            session["last_access"] = time.time()
            return session
        
        # Create new session
        with self.global_lock:
            if session_id not in self.sessions:
                # Check session limit
                if len(self.sessions) >= self.config.max_concurrent_sessions:
                    self._evict_oldest_session()
                
                # Create session
                self.sessions[session_id] = {
                    "dialog": [{"role": "system", "content": system_prompt}],
                    "project": project_name,
                    "created_at": time.time(),
                    "last_access": time.time(),
                    "message_count": 0
                }
                self.session_locks[session_id] = threading.RLock()
                logger.info(f"Created new session: {session_id} for project: {project_name}")
            else:
                self.sessions[session_id]["last_access"] = time.time()
                
            return self.sessions[session_id]
    
    def process_message(
        self,
        session_id: str,
        project_name: str,
        system_prompt: str,
        user_message: str,
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None
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
            
        Returns:
            Generated response
        """
        # Get or create session
        session = self.get_or_create_session(session_id, project_name, system_prompt)
        
        # Thread-safe processing
        with self.session_locks.get(session_id, threading.RLock()):
            try:
                # Add user message
                session["dialog"].append({"role": "user", "content": user_message})
                session["message_count"] += 1
                
                # Trim history if needed
                self._trim_dialog(session)
                
                # Format prompt
                prompt = self.inference.format_chat(session["dialog"])
                
                # Generate response
                responses = self.inference.generate(
                    [prompt],
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens
                )
                
                response = responses[0] if responses else "Error: No response generated"
                
                # Add assistant response to history
                session["dialog"].append({"role": "assistant", "content": response})
                session["last_access"] = time.time()
                
                return response
                
            except Exception as e:
                error_msg = f"Error processing message: {str(e)}"
                logger.error(f"Session {session_id}: {error_msg}")
                return error_msg
    
    def _trim_dialog(self, session: Dict):
        """
        Trim dialog history to stay within token limits.
        
        Args:
            session: Session dictionary to trim
        """
        dialog = session["dialog"]
        
        # Always keep system message
        if len(dialog) <= 1:
            return
        
        # Calculate total tokens
        total_text = " ".join([msg["content"] for msg in dialog])
        total_tokens = self.inference.count_tokens(total_text)
        
        # Remove oldest messages (except system) if over limit
        while total_tokens > self.config.max_history_tokens and len(dialog) > 2:
            # Remove oldest user-assistant pair
            dialog.pop(1)
            if len(dialog) > 1:
                dialog.pop(1)
            
            total_text = " ".join([msg["content"] for msg in dialog])
            total_tokens = self.inference.count_tokens(total_text)
        
        logger.debug(f"Dialog trimmed to {len(dialog)} messages, ~{total_tokens} tokens")
    
    def _evict_oldest_session(self):
        """Evict the oldest session when limit is reached."""
        if not self.sessions:
            return
        
        oldest_id = min(
            self.sessions.keys(),
            key=lambda sid: self.sessions[sid]["last_access"]
        )
        
        del self.sessions[oldest_id]
        if oldest_id in self.session_locks:
            del self.session_locks[oldest_id]
        
        logger.info(f"Evicted oldest session: {oldest_id}")
    
    def _cleanup_sessions(self):
        """Background thread to cleanup expired sessions."""
        while True:
            time.sleep(300)  # Check every 5 minutes
            
            current_time = time.time()
            expired = []
            
            with self.global_lock:
                for sid, session in self.sessions.items():
                    if current_time - session["last_access"] > self.config.session_timeout:
                        expired.append(sid)
                
                for sid in expired:
                    del self.sessions[sid]
                    if sid in self.session_locks:
                        del self.session_locks[sid]
            
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")


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
    temperature: float = None
    top_p: float = None
    max_tokens: int = None
    priority: int = 0  # Lower = higher priority
    timestamp: float = field(default_factory=time.time)


class MessageProcessor:
    """
    Processes queued messages with batching optimization.
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
        self.message_queue = queue.PriorityQueue(maxsize=1000)
        self.running = True
        
        # Statistics
        self.stats = {
            "processed": 0,
            "errors": 0,
            "total_latency": 0.0
        }
        self.stats_lock = threading.Lock()
        
    def enqueue(self, message: QueuedMessage):
        """
        Add message to processing queue.
        
        Args:
            message: Message to enqueue
        """
        try:
            # Priority queue: (priority, timestamp, message)
            self.message_queue.put((message.priority, message.timestamp, message), timeout=5)
        except queue.Full:
            logger.error("Message queue is full, dropping message")
    
    def process_loop(self):
        """Main processing loop for a worker thread."""
        while self.running:
            try:
                # Get message with timeout
                priority, timestamp, msg = self.message_queue.get(timeout=1.0)
                
                # Process message
                start_time = time.time()
                self._process_single_message(msg)
                latency = time.time() - start_time
                
                # Update statistics
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
        """
        Process a single message.
        
        Args:
            msg: Message to process
        """
        try:
            # Get project config for system prompt
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
                max_tokens=msg.max_tokens
            )
            
            # Publish response
            self.mqtt_client.publish(msg.response_topic, response, qos=1)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            error_response = f"Error: {str(e)}"
            self.mqtt_client.publish(msg.response_topic, error_response, qos=1)
    
    def get_stats(self) -> Dict:
        """Get processing statistics."""
        with self.stats_lock:
            stats = self.stats.copy()
            if stats["processed"] > 0:
                stats["avg_latency"] = stats["total_latency"] / stats["processed"]
            else:
                stats["avg_latency"] = 0.0
            return stats


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
        client_id = f"vllm-deploy-{uuid.uuid4().hex[:8]}"
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
    
    def _on_message(self, client, userdata, msg):
        """Callback for incoming MQTT messages."""
        try:
            # Decode message
            payload = msg.payload.decode('utf-8')
            
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
                return
            
            # Parse message (expect JSON with sessionId and message)
            try:
                data = json.loads(payload)
                session_id = data.get("sessionId", f"default-{uuid.uuid4().hex[:8]}")
                user_message = data.get("message", "")
                
                # Optional parameters
                temperature = data.get("temperature")
                top_p = data.get("topP")
                max_tokens = data.get("maxTokens")
                
                if not user_message.strip():
                    logger.warning(f"Empty message received from session: {session_id}")
                    return
                
            except json.JSONDecodeError:
                # Fallback: treat entire payload as message
                session_id = f"default-{uuid.uuid4().hex[:8]}"
                user_message = payload
                temperature = None
                top_p = None
                max_tokens = None
            
            # Format response topic with session ID
            response_topic_full = f"{response_topic}/{session_id}"
            
            # Create queued message
            queued_msg = QueuedMessage(
                session_id=session_id,
                project_name=project_name,
                user_message=user_message,
                response_topic=response_topic_full,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens
            )
            
            # Enqueue for processing
            self.message_processor.enqueue(queued_msg)
            logger.debug(f"Enqueued message from session: {session_id}")
            
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
    
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
    # Project selection (toggle which topics to enable)
    projects: List[str] = ["general"],
    
    # Model configuration
    model: str = "Qwen/QwQ-32B",
    max_model_len: int = 4096,
    tensor_parallel_size: int = 1,
    gpu_memory_utilization: float = 0.90,
    quantization: Optional[str] = None,
    
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
    num_workers: int = 4,
):
    """
    Deploy vLLM model with MQTT interface for multiple projects.
    
    Args:
        projects: List of project names to enable (e.g., ["maze", "driving", "bloodcell"])
        model: Model name or path (default: Qwen/QwQ-32B)
        max_model_len: Maximum model context length
        tensor_parallel_size: Number of GPUs for tensor parallelism
        gpu_memory_utilization: GPU memory utilization (0.0-1.0)
        quantization: Quantization method (awq, gptq, etc.)
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
    
    Examples:
        # Deploy for maze game only
        python vLLMDeploy.py --projects maze
        
        # Deploy for multiple projects
        python vLLMDeploy.py --projects maze driving bloodcell racing
        
        # With custom MQTT settings
        python vLLMDeploy.py --projects driving --mqtt_username user --mqtt_password pass
        
        # With quantization
        python vLLMDeploy.py --projects general --quantization awq
    """
    
    logger.info("=" * 80)
    logger.info("vLLM Multi-Project MQTT Deployment")
    logger.info("=" * 80)
    
    # Create project configurations
    project_configs = {}
    for project_name in projects:
        # Get system prompt
        system_prompt = SYSTEM_PROMPTS.get(project_name, SYSTEM_PROMPTS["general"])
        
        # Create project config
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
        model_name=model,
        max_model_len=max_model_len,
        tensor_parallel_size=tensor_parallel_size,
        gpu_memory_utilization=gpu_memory_utilization,
        quantization=quantization,
        default_temperature=temperature,
        default_top_p=top_p,
        default_max_tokens=max_tokens,
        max_history_tokens=max_history_tokens,
        max_concurrent_sessions=max_concurrent_sessions,
        num_worker_threads=num_workers,
        projects=project_configs
    )
    
    logger.info(f"Enabled projects: {', '.join(projects)}")
    logger.info(f"Model: {model}")
    logger.info(f"Max model length: {max_model_len}")
    logger.info(f"Tensor parallel size: {tensor_parallel_size}")
    logger.info(f"GPU memory utilization: {gpu_memory_utilization}")
    
    try:
        # 1. Initialize vLLM inference engine
        logger.info("-" * 80)
        logger.info("Step 1: Initializing vLLM inference engine...")
        inference = vLLMInference(config)
        
        # 2. Initialize session manager
        logger.info("-" * 80)
        logger.info("Step 2: Initializing session manager...")
        session_manager = SessionManager(config, inference)
        
        # 3. Initialize message processor
        logger.info("-" * 80)
        logger.info("Step 3: Initializing message processor...")
        # Create dummy client for initialization
        mqtt_client = mqtt.Client(
            client_id=f"vllm-temp-{uuid.uuid4().hex[:8]}",
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
        thread_pool = ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="vllm-worker")
        for i in range(num_workers):
            thread_pool.submit(message_processor.process_loop)
        logger.info(f"Started {num_workers} worker threads")
        
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
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)
        
        # Statistics reporting thread
        def report_stats():
            while True:
                time.sleep(60)
                stats = message_processor.get_stats()
                logger.info(
                    f"Stats: Processed={stats['processed']}, Errors={stats['errors']}, "
                    f"AvgLatency={stats['avg_latency']:.3f}s"
                )
        
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

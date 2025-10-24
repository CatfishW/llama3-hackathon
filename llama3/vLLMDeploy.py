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
import os
import queue
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fire
import paho.mqtt.client as mqtt
from vllm import LLM, SamplingParams

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
    
    # Model Configuration
    model_name: str = "Qwen/QwQ-32B"
    max_model_len: int = 4096
    tensor_parallel_size: int = 1
    gpu_memory_utilization: float = 0.90
    quantization: Optional[str] = None  # e.g., "awq", "gptq", None
    visible_devices: Optional[str] = None  # e.g., "0", "1,2", "2" to specify GPU(s)
    model_provider: str = "auto"
    model_cache_dir: str = "./models/modelscope"
    model_revision: Optional[str] = None
    auto_download: bool = True
    remote_model_id: Optional[str] = None
    
    # Generation Configuration
    default_temperature: float = 0.6
    default_top_p: float = 0.9
    default_max_tokens: int = 512
    skip_thinking: bool = True  # Remove QwQ-style thinking from outputs
    
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
# Model Registry and Download Utilities
# ============================================================================


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model_id: str
    revision: Optional[str] = None
    aliases: Tuple[str, ...] = ()
    default_quantization: Optional[str] = None


MODEL_SPECS: Tuple[ModelSpec, ...] = (
    ModelSpec(
        provider="modelscope",
        model_id="Qwen/QwQ-32B",
        aliases=("qwq-32b", "qwen-qwq-32b", "qwen/qwq-32b", "qwen_qwq_32b"),
    ),
    ModelSpec(
        provider="modelscope",
        model_id="Qwen/Qwen1.5-14B-Chat",
        aliases=("qwen1.5-14b-chat", "qwen15-14b-chat", "qwen-1.5-14b-chat"),
    ),
    ModelSpec(
        provider="modelscope",
        model_id="Qwen/Qwen3-14B",
        aliases=("qwen3-14b", "qwen-3-14b", "qwen/qwen3-14b"),
    ),
    ModelSpec(
        provider="modelscope",
        model_id="Qwen/Qwen3-VL-4B-Instruct-FP8",
        aliases=(
            "qwen3-vl-4b-instruct-fp8",
            "qwen3-vl-4b-instruct",
            "qwen3-vl-4b",
            "qwen/qwen3-vl-4b-instruct-fp8",
        ),
        default_quantization="fp8",
    ),
    ModelSpec(
        provider="modelscope",
        model_id="Qwen/Qwen2-72B-Instruct",
        aliases=("qwen2-72b-instruct", "qwen2-72b", "qwen2_instruct"),
    ),
    ModelSpec(
        provider="modelscope",
        model_id="ZhipuAI/chatglm3-6b",
        aliases=("chatglm3-6b", "chatglm3", "zhipuai/chatglm3-6b"),
    ),
    ModelSpec(
        provider="modelscope",
        model_id="Shanghai_AI_Laboratory/internlm2-chat-7b",
        aliases=("internlm2-chat-7b", "internlm2-7b", "internlm2"),
    ),
    ModelSpec(
        provider="modelscope",
        model_id="01ai/Yi-34B-Chat",
        aliases=("yi-34b-chat", "yi34b", "01ai/yi-34b-chat"),
    ),
)


MODEL_ALIAS_LOOKUP: Dict[str, ModelSpec] = {}
for spec in MODEL_SPECS:
    keys = {spec.model_id.lower()}
    keys.update(alias.lower() for alias in spec.aliases)
    for key in keys:
        MODEL_ALIAS_LOOKUP[key] = spec


def resolve_model_identifier(
    identifier: str,
    provider_hint: str = "auto"
) -> Tuple[str, str, Optional[str], Optional[ModelSpec]]:
    """Resolve a model identifier to provider, remote id/path, and revision."""
    if not identifier:
        raise ValueError("Model identifier is required")

    candidate = identifier.strip()
    lookup_key = candidate.lower()

    spec = MODEL_ALIAS_LOOKUP.get(lookup_key)
    if spec:
        return spec.provider, spec.model_id, spec.revision, spec

    if "://" in candidate:
        scheme, remainder = candidate.split("://", 1)
        scheme_lower = scheme.lower()
        if scheme_lower in {"modelscope", "modelspace"}:
            return "modelscope", remainder, None, None
        if scheme_lower in {"hf", "huggingface"}:
            return "huggingface", remainder, None, None

    if os.path.isdir(candidate) or os.path.isfile(candidate):
        return "local", candidate, None, None

    provider_hint_lower = (provider_hint or "auto").lower()
    if provider_hint_lower in {"modelscope", "modelspace"}:
        return "modelscope", candidate, None, None
    if provider_hint_lower in {"huggingface", "hf"}:
        return "huggingface", candidate, None, None
    if provider_hint_lower == "local":
        return "local", candidate, None, None

    # Detect likely filesystem paths (relative or absolute)
    if candidate.startswith(("./", "../", "\\", "/")):
        return "local", candidate, None, None
    if len(candidate) > 1 and candidate[1] == ":" and candidate[0].isalpha():
        return "local", candidate, None, None

    # Fallback: treat plain identifiers as ModelScope ids
    return "modelscope", candidate, None, None


class ModelDownloader:
    """Ensure requested models are available locally before vLLM loads them."""

    def __init__(
        self,
        provider: str,
        cache_dir: Optional[str],
        revision: Optional[str],
        auto_download: bool,
    ):
        self.provider = (provider or "local").lower()
        self.cache_dir = Path(cache_dir).expanduser() if cache_dir else None
        self.revision = revision
        self.auto_download = auto_download

    def ensure(self, model_identifier: str) -> str:
        """Return a filesystem path for the requested model."""
        if self.provider in {"", "local"}:
            return self._validate_local_path(model_identifier)
        if self.provider in {"modelscope", "modelspace"}:
            return self._download_modelscope(model_identifier)
        if self.provider in {"huggingface", "hf"}:
            raise RuntimeError(
                "Hugging Face downloads are disabled in this deployment. "
                "Please switch to ModelScope or provide a local path."
            )
        return self._validate_local_path(model_identifier)

    def _validate_local_path(self, model_path: str) -> str:
        path = Path(model_path).expanduser()
        if path.exists():
            return str(path.resolve())
        if self.auto_download:
            raise FileNotFoundError(
                f"Auto-download requested but provider '{self.provider}' "
                f"cannot fetch model '{model_path}'."
            )
        raise FileNotFoundError(
            f"Model path '{model_path}' does not exist. "
            "Provide a valid local path or enable automatic download."
        )

    def _download_modelscope(self, model_id: str) -> str:
        model_id = model_id.strip()
        if not model_id:
            raise ValueError("Model id cannot be empty for ModelScope downloads")

        try:
            from modelscope import snapshot_download
        except ImportError as exc:
            raise RuntimeError(
                "Optional dependency 'modelscope' is not installed. "
                "Install it with `pip install modelscope`."
            ) from exc

        cache_dir = None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_dir = str(self.cache_dir)

        download_action = "Ensuring"
        if self.auto_download:
            download_action = "Downloading"
        else:
            logger.info("Auto download disabled; reusing cached snapshot if available.")

        logger.info(
            f"{download_action} model '{model_id}' from ModelScope (cache: {cache_dir or 'default'})"
        )

        try:
            local_path = snapshot_download(
                model_id,
                cache_dir=cache_dir,
                revision=self.revision,
            )
        except Exception as exc:  # pragma: no cover - network errors vary
            raise RuntimeError(
                f"Failed to download model '{model_id}' from ModelScope: {exc}"
            ) from exc

        logger.info(f"Model available at: {local_path}")
        return str(Path(local_path).resolve())

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
        if config.remote_model_id and config.model_provider not in {"", "local"}:
            logger.info(
                f"Remote identifier: {config.model_provider}://{config.remote_model_id}"
            )
        
        # Set visible GPUs if specified
        import os
        if config.visible_devices:
            os.environ["CUDA_VISIBLE_DEVICES"] = str(config.visible_devices)
            logger.info(f"Setting CUDA_VISIBLE_DEVICES to: {config.visible_devices}")
        
        # Initialize vLLM with quantization support
        try:
            # Build initialization kwargs
            init_kwargs = {
                "model": config.model_name,
                "tensor_parallel_size": config.tensor_parallel_size,
                "max_model_len": config.max_model_len,
                "gpu_memory_utilization": config.gpu_memory_utilization,
                "trust_remote_code": True,
                "enforce_eager": False,  # Use CUDA graphs for better performance
            }
            
            # Add quantization if specified
            if config.quantization:
                quantization_lower = config.quantization.lower()
                
                # Validate and set quantization
                supported_quant = ["awq", "gptq", "squeezellm", "fp8", "bitsandbytes"]
                if quantization_lower in supported_quant:
                    init_kwargs["quantization"] = quantization_lower
                    logger.info(f"Enabling {quantization_lower.upper()} quantization")
                    
                    # Special handling for different quantization methods
                    if quantization_lower == "fp8":
                        # FP8 quantization - requires specific hardware
                        logger.info("FP8 quantization requires Ada Lovelace or newer GPUs")
                    elif quantization_lower == "bitsandbytes":
                        # BitsAndBytes (4-bit/8-bit) quantization
                        logger.info("Using BitsAndBytes quantization (4-bit/8-bit)")
                    elif quantization_lower in ["awq", "gptq"]:
                        # AWQ/GPTQ require pre-quantized models
                        logger.info(f"Using {quantization_lower.upper()} - ensure model is pre-quantized")
                else:
                    logger.warning(
                        f"Unsupported quantization: {config.quantization}. "
                        f"Supported methods: {', '.join(supported_quant)}"
                    )
                    logger.warning("Proceeding without quantization")
            
            # Initialize model
            self.llm = LLM(**init_kwargs)
            
            # Log success with quantization status
            if config.quantization:
                logger.info(f"vLLM model initialized successfully with {config.quantization.upper()} quantization")
            else:
                logger.info("vLLM model initialized successfully (no quantization)")
                
        except Exception as e:
            logger.error(f"Failed to initialize vLLM: {e}")
            if config.quantization:
                logger.error(
                    f"Quantization '{config.quantization}' may not be compatible with this model. "
                    "Try without quantization or use a pre-quantized model."
                )
            raise
        
        # Get tokenizer for token counting
        self.tokenizer = self.llm.get_tokenizer()
        
    def generate(
        self,
        prompts: List[str],
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None,
        debug_info: dict = None
    ) -> List[str]:
        """
        Generate responses for a batch of prompts.
        
        Args:
            prompts: List of prompt strings
            temperature: Sampling temperature (default from config)
            top_p: Top-p sampling (default from config)
            max_tokens: Maximum tokens to generate (default from config)
            debug_info: Optional debug info dict to log details
            
        Returns:
            List of generated response strings
        """
        if not prompts:
            return []
        
        # Use defaults from config if not specified
        temperature = temperature or self.config.default_temperature
        top_p = top_p or self.config.default_top_p
        max_tokens = max_tokens or self.config.default_max_tokens
        
        # Debug log: generation parameters
        if debug_info:
            debug_logger.debug("=" * 80)
            debug_logger.debug(f"GENERATION REQUEST | Session: {debug_info.get('session_id', 'unknown')}")
            debug_logger.debug(f"Temperature: {temperature}, Top-P: {top_p}, Max Tokens: {max_tokens}")
            debug_logger.debug("-" * 80)
            debug_logger.debug(f"FULL PROMPT TO LLM:\n{prompts[0]}")
            debug_logger.debug("-" * 80)
        
        # Create sampling params with stop strings to prevent QwQ thinking
        sampling_params = SamplingParams(
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stop=["</think>", "<think>"],
            skip_special_tokens=True,
        )
        
        try:
            # Generate with vLLM (automatic batching)
            start_time = time.time()
            outputs = self.llm.generate(prompts, sampling_params)
            generation_time = time.time() - start_time
            
            # Extract generated text
            results = [output.outputs[0].text for output in outputs]
            
            # Post-process to remove QwQ thinking (if enabled)
            cleaned_results = []
            for result in results:
                if self.config.skip_thinking:
                    cleaned = self._clean_qwq_output(result)
                else:
                    cleaned = result
                cleaned_results.append(cleaned)
            
            # Debug log: generation output
            if debug_info:
                debug_logger.debug(f"LLM RAW OUTPUT:\n{results[0]}")
                if results[0] != cleaned_results[0]:
                    debug_logger.debug("-" * 80)
                    debug_logger.debug(f"CLEANED OUTPUT:\n{cleaned_results[0]}")
                debug_logger.debug("-" * 80)
                debug_logger.debug(f"Generation Time: {generation_time:.3f}s")
                debug_logger.debug(f"Output Length: {len(cleaned_results[0])} chars")
                debug_logger.debug("=" * 80 + "\n")
            
            return cleaned_results
            
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            if debug_info:
                debug_logger.error(f"GENERATION ERROR | Session: {debug_info.get('session_id', 'unknown')}")
                debug_logger.error(f"Error: {str(e)}")
                debug_logger.error("=" * 80 + "\n")
            return [f"Error: {str(e)}"] * len(prompts)
    
    def _clean_qwq_output(self, text: str) -> str:
        """
        Clean QwQ model's thinking process from the output.
        QwQ models output reasoning before the final answer.
        
        Args:
            text: Raw model output
            
        Returns:
            Cleaned output with thinking removed
        """
        # Check for "Final Answer" marker
        if "**Final Answer**" in text:
            # Extract everything after "Final Answer"
            parts = text.split("**Final Answer**")
            if len(parts) > 1:
                answer = parts[-1].strip()
                # Remove leading markers
                answer = answer.lstrip("*: \n")
                return answer
        
        # Check for common thinking patterns and extract last substantial paragraph
        # QwQ often has "Alright," "Okay," "Let me think" patterns
        thinking_markers = [
            "Alright,", "Okay,", "Let me think", "Let me check",
            "Let me confirm", "The user is asking", "I need to"
        ]
        
        # If text contains multiple thinking markers, try to extract the actual answer
        marker_count = sum(1 for marker in thinking_markers if marker in text)
        
        if marker_count > 2:  # Likely contains thinking
            # Split into sentences/paragraphs
            paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
            
            # Find the last paragraph that looks like an answer (not thinking)
            for paragraph in reversed(paragraphs):
                # Skip if it contains thinking markers
                has_thinking = any(marker.lower() in paragraph.lower() for marker in thinking_markers)
                if not has_thinking and len(paragraph) > 20:  # Substantial content
                    return paragraph
        
        # If no patterns found, return original (might be clean already)
        return text.strip()
    
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
                    add_generation_prompt=True,
                    enable_thinking=False
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
            if "token_cache" not in session:
                token_cache = [self.inference.count_tokens(msg["content"]) for msg in session["dialog"]]
                session["token_cache"] = token_cache
                session["total_tokens"] = sum(token_cache)
            return session
        
        # Create new session
        with self.global_lock:
            if session_id not in self.sessions:
                # Check session limit
                if len(self.sessions) >= self.config.max_concurrent_sessions:
                    self._evict_oldest_session()
                
                system_tokens = self.inference.count_tokens(system_prompt)

                # Create session
                self.sessions[session_id] = {
                    "dialog": [{"role": "system", "content": system_prompt}],
                    "project": project_name,
                    "created_at": time.time(),
                    "last_access": time.time(),
                    "message_count": 0,
                    "token_cache": [system_tokens],
                    "total_tokens": system_tokens,
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
        # Debug log: incoming user message
        debug_logger.info("╔" + "═" * 78 + "╗")
        debug_logger.info(f"║ NEW MESSAGE | Session: {session_id[:16]}... | Project: {project_name}")
        debug_logger.info("╠" + "═" * 78 + "╣")
        debug_logger.info(f"USER MESSAGE:\n{user_message}")
        debug_logger.info("─" * 80)
        
        # Get or create session
        session = self.get_or_create_session(session_id, project_name, system_prompt)
        
        # Thread-safe processing
        with self.session_locks.get(session_id, threading.RLock()):
            try:
                # Add user message
                session["dialog"].append({"role": "user", "content": user_message})
                session["message_count"] += 1
                token_cache = session.get("token_cache")
                if token_cache is None:
                    token_cache = [self.inference.count_tokens(msg["content"]) for msg in session["dialog"][:-1]]
                    session["token_cache"] = token_cache
                user_tokens = self.inference.count_tokens(user_message)
                token_cache.append(user_tokens)
                session["total_tokens"] = session.get("total_tokens", sum(token_cache[:-1])) + user_tokens
                
                # Debug log: conversation history before trimming
                debug_logger.debug(f"Conversation history length: {len(session['dialog'])} messages")
                debug_logger.debug(f"Message count: {session['message_count']}")
                
                # Trim history if needed
                self._trim_dialog(session)
                
                # Debug log: conversation history after trimming
                debug_logger.debug(f"After trimming: {len(session['dialog'])} messages")
                for i, msg in enumerate(session['dialog']):
                    debug_logger.debug(f"  [{i}] {msg['role']}: {msg['content'][:100]}...")
                
                # Format prompt
                prompt = self.inference.format_chat(session["dialog"])
                
                # Prepare debug info
                debug_info = {
                    'session_id': session_id,
                    'project': project_name,
                    'message_count': session['message_count'],
                    'user_message': user_message
                }
                
                # Generate response
                responses = self.inference.generate(
                    [prompt],
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    debug_info=debug_info
                )
                
                response = responses[0] if responses else "Error: No response generated"
                
                # Debug log: final response to user
                debug_logger.info(f"ASSISTANT RESPONSE:\n{response}")
                debug_logger.info("╚" + "═" * 78 + "╝\n")
                
                # Add assistant response to history
                session["dialog"].append({"role": "assistant", "content": response})
                token_cache = session.get("token_cache")
                if token_cache is None:
                    token_cache = [self.inference.count_tokens(msg["content"]) for msg in session["dialog"][:-1]]
                    session["token_cache"] = token_cache
                assistant_tokens = self.inference.count_tokens(response)
                token_cache.append(assistant_tokens)
                session["total_tokens"] = session.get("total_tokens", sum(token_cache[:-1])) + assistant_tokens
                self._trim_dialog(session)
                session["last_access"] = time.time()
                
                return response
                
            except Exception as e:
                error_msg = f"Error processing message: {str(e)}"
                logger.error(f"Session {session_id}: {error_msg}")
                debug_logger.error(f"ERROR in session {session_id}: {error_msg}")
                debug_logger.info("╚" + "═" * 78 + "╝\n")
                return error_msg
    
    def _trim_dialog(self, session: Dict):
        """
        Trim dialog history to stay within token limits.
        
        Args:
            session: Session dictionary to trim
        """
        dialog = session["dialog"]
        token_cache = session.get("token_cache")
        if token_cache is None:
            token_cache = [self.inference.count_tokens(msg["content"]) for msg in dialog]
            session["token_cache"] = token_cache
        
        # Always keep system message
        if len(dialog) <= 1:
            session["total_tokens"] = token_cache[0] if token_cache else 0
            return

        if len(token_cache) != len(dialog):
            token_cache[:] = [self.inference.count_tokens(msg["content"]) for msg in dialog]
        
        total_tokens = session.get("total_tokens")
        if total_tokens is None:
            total_tokens = sum(token_cache)
        
        # Remove oldest messages (except system) if over limit
        while total_tokens > self.config.max_history_tokens and len(dialog) > 2:
            # Remove oldest user-assistant pair
            if len(token_cache) > 1:
                total_tokens -= token_cache.pop(1)
            if len(dialog) > 1:
                dialog.pop(1)
            if len(dialog) > 1 and len(token_cache) > 1:
                dialog.pop(1)
                total_tokens -= token_cache.pop(1)

        # Keep dialog and cache aligned in case only one element removed above
        while len(token_cache) > len(dialog):
            total_tokens -= token_cache.pop()

        total_tokens = sum(token_cache)
        session["total_tokens"] = total_tokens

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
            debug_logger.debug(f"Response published to topic: {msg.response_topic}\n")
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            debug_logger.error(f"Error in message processor: {e}")
            error_response = f"Error: {str(e)}"
            self.mqtt_client.publish(msg.response_topic, error_response, qos=1)
            debug_logger.debug(f"Error response published to topic: {msg.response_topic}\n")
    
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
            
            # Debug log: raw MQTT message
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
            
            # Parse message (expect JSON with sessionId and message)
            try:
                data = json.loads(payload)
                session_id = data.get("sessionId", f"default-{uuid.uuid4().hex[:8]}")
                user_message = data.get("message", "")
                
                # Optional parameters
                temperature = data.get("temperature")
                top_p = data.get("topP")
                max_tokens = data.get("maxTokens")
                
                # Debug log: parsed message
                debug_logger.debug(f"PARSED | Session: {session_id}, Project: {project_name}")
                debug_logger.debug(f"Message: {user_message}")
                if temperature or top_p or max_tokens:
                    debug_logger.debug(f"Custom params - Temp: {temperature}, TopP: {top_p}, MaxTokens: {max_tokens}")
                
                if not user_message.strip():
                    logger.warning(f"Empty message received from session: {session_id}")
                    debug_logger.warning(f"Empty message from session: {session_id}")
                    return
                
            except json.JSONDecodeError:
                # Fallback: treat entire payload as message
                session_id = f"default-{uuid.uuid4().hex[:8]}"
                user_message = payload
                temperature = None
                top_p = None
                max_tokens = None
                debug_logger.debug(f"JSON decode failed, using raw payload as message")
            
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
    # Project selection (toggle which topics to enable)
    projects: str = "general",  # Changed from List[str] to str - will be split by commas
    
    # Model configuration
    model: str = "Qwen/QwQ-32B",
    model_provider: str = "auto",
    model_cache_dir: str = "./models/modelscope",
    model_revision: Optional[str] = None,
    auto_download: bool = True,
    max_model_len: int = 4096,
    tensor_parallel_size: int = 1,
    gpu_memory_utilization: float = 0.90,
    quantization: Optional[str] = None,
    visible_devices: Optional[str] = None,
    
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
    
    # Output processing
    skip_thinking: bool = True,
):
    """
    Deploy vLLM model with MQTT interface for multiple projects.
    
    Args:
        projects: Project names to enable (e.g., "maze driving bloodcell" or "maze,driving,bloodcell")
    model: Model identifier, alias, or local path (default: Qwen/QwQ-32B)
    model_provider: Force a download provider (auto, modelscope, local)
    model_cache_dir: Directory used to cache remote model snapshots
    model_revision: Optional revision or version for remote providers
    auto_download: Automatically download model snapshots when needed
        max_model_len: Maximum model context length
        tensor_parallel_size: Number of GPUs for tensor parallelism
        gpu_memory_utilization: GPU memory utilization (0.0-1.0)
        quantization: Quantization method (awq, gptq, etc.)
        visible_devices: Specify which GPU(s) to use (e.g., "0", "1,2", "2")
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
        skip_thinking: Remove QwQ-style thinking process from outputs (default: True)
    
    Examples:
        # Deploy for maze game only
        python vLLMDeploy.py --projects maze
        
        # Deploy for multiple projects (space-separated)
        python vLLMDeploy.py --projects "maze driving bloodcell racing"
        
        # Deploy for multiple projects (comma-separated)
        python vLLMDeploy.py --projects "maze,driving,bloodcell"
        
        # With custom MQTT settings
        python vLLMDeploy.py --projects driving --mqtt_username user --mqtt_password pass
        
    # Automatically fetch from ModelScope using aliases
    python vLLMDeploy.py --projects general --model qwq-32b

    # Explicit ModelScope download with custom cache dir
    python vLLMDeploy.py --projects general --model modelspace://Qwen/Qwen2-72B-Instruct --model_cache_dir ./models

    # With AWQ quantization (requires pre-quantized model already downloaded)
    python vLLMDeploy.py --projects general --quantization awq --model /data/QwQ-32B-AWQ

    # With GPTQ quantization
    python vLLMDeploy.py --projects general --quantization gptq --model /data/QwQ-32B-GPTQ

    # With BitsAndBytes 4-bit quantization (quantizes on-the-fly)
    python vLLMDeploy.py --projects general --quantization bitsandbytes --model qwq-32b

    # Vision-language FP8 model (auto-applies FP8 quantization)
    python vLLMDeploy.py --projects general --model qwen3-vl-4b-instruct-fp8

    # With FP8 quantization (Ada Lovelace+ GPUs only)
    python vLLMDeploy.py --projects general --quantization fp8 --model qwq-32b
        
        # Keep QwQ thinking output (for debugging)
        python vLLMDeploy.py --projects general --skip_thinking False
    """
    
    logger.info("=" * 80)
    logger.info("vLLM Multi-Project MQTT Deployment")
    logger.info("=" * 80)
    
    # Initialize debug log
    debug_logger.info("\n" + "=" * 80)
    debug_logger.info("vLLM DEPLOYMENT STARTED")
    debug_logger.info(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    debug_logger.info("=" * 80 + "\n")
    
    # Parse projects parameter - handle both string and list
    if isinstance(projects, str):
        # Split by comma or space
        projects_list = [p.strip() for p in projects.replace(',', ' ').split() if p.strip()]
    else:
        projects_list = projects
    
    # Create project configurations
    project_configs = {}
    for project_name in projects_list:
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
    
    resolved_provider, resolved_remote_id, inferred_revision, model_spec = resolve_model_identifier(
        model,
        model_provider,
    )
    effective_revision = model_revision or inferred_revision
    quantization_source = "cli"
    if not quantization and model_spec and model_spec.default_quantization:
        quantization = model_spec.default_quantization
        quantization_source = "model default"

    cache_dir_resolved = str(Path(model_cache_dir).expanduser()) if model_cache_dir else None

    downloader = ModelDownloader(
        provider=resolved_provider,
        cache_dir=cache_dir_resolved,
        revision=effective_revision,
        auto_download=auto_download,
    )

    try:
        resolved_model_path = downloader.ensure(resolved_remote_id)
    except Exception as exc:
        logger.error(f"Unable to prepare model '{model}': {exc}")
        raise

    remote_model_display = resolved_remote_id if resolved_remote_id else model

    # Create deployment config
    config = DeploymentConfig(
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        model_name=resolved_model_path,
        max_model_len=max_model_len,
        tensor_parallel_size=tensor_parallel_size,
        gpu_memory_utilization=gpu_memory_utilization,
        quantization=quantization,
        visible_devices=visible_devices,
        model_provider=resolved_provider,
    model_cache_dir=cache_dir_resolved or model_cache_dir or "",
        model_revision=effective_revision,
        auto_download=auto_download,
        remote_model_id=resolved_remote_id,
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
    logger.info(f"Model source: {resolved_provider}")
    if effective_revision:
        logger.info(f"Model revision: {effective_revision}")
    if resolved_provider in {"local", ""}:
        logger.info(f"Model path: {resolved_model_path}")
    else:
        logger.info(f"Model id: {remote_model_display}")
        logger.info(f"Resolved local path: {resolved_model_path}")
    if cache_dir_resolved:
        logger.info(f"Model cache dir: {cache_dir_resolved}")
    logger.info(f"Auto download: {auto_download}")
    logger.info(f"Max model length: {max_model_len}")
    logger.info(f"Tensor parallel size: {tensor_parallel_size}")
    logger.info(f"GPU memory utilization: {gpu_memory_utilization}")
    if quantization:
        if quantization_source == "model default":
            logger.info(f"Quantization: {quantization.upper()} (model default)")
        else:
            logger.info(f"Quantization: {quantization.upper()}")
    else:
        logger.info("Quantization: None (FP16/BF16)")
    logger.info(f"Skip thinking output: {skip_thinking}")
    
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
#python vLLMDeploy.py --model Qwen/Qwen3-VL-4B-Instruct-FP8 --visible_devices "2" --mqtt_username TangClinic --mqtt_password Tang123

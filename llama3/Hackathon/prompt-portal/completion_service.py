"""
MQTT-based TAB Completion Service

This service provides intelligent TAB completion for all input fields using
the local LLM via MQTT. It integrates with llamacpp_mqtt_deploy.py to provide
real-time completion suggestions.

IMPORTANT: This service is now integrated into llamacpp_mqtt_deploy.py.
Use the main deployment script with --projects completion_service instead.

Usage:
    python llamacpp_mqtt_deploy.py --projects completion_service --server_url http://localhost:8080 --mqtt_username TangClinic --mqtt_password Tang123
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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

@dataclass
class CompletionConfig:
    """Configuration for completion service."""
    # MQTT Configuration
    mqtt_broker: str = "47.89.252.2"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = "TangClinic"
    mqtt_password: Optional[str] = "Tang123"

    # Llama.cpp Server Configuration
    server_url: str = "http://localhost:8080"
    server_timeout: int = 30  # Shorter timeout for completions
    
    # Completion Configuration
    default_temperature: float = 0.3  # Lower temperature for more focused completions
    default_top_p: float = 0.9
    default_max_tokens: int = 50  # Shorter completions
    skip_thinking: bool = True  # Disable thinking for faster completions
    
    # Performance Configuration
    num_worker_threads: int = 8
    max_queue_size: int = 500
    completion_timeout: float = 2.0  # Max time to wait for completion
    
    # Rate Limiting
    max_requests_per_client: int = 30  # Max requests per minute per client
    rate_limit_window: int = 60

# ============================================================================
# Completion System Prompts
# ============================================================================

COMPLETION_PROMPTS = {
    "general": """You are a helpful completion assistant. Complete the following text in a natural, helpful way. 
Provide only the completion text, not the original text. Keep it concise and relevant.

Text to complete: {text}

Completion:""",
    
    "code": """You are a code completion assistant. Complete the following code snippet in a natural way.
Provide only the completion code, not the original code. Make sure the completion is syntactically correct.

Code to complete: {text}

Completion:""",
    
    "prompt": """You are a prompt completion assistant. Complete the following prompt template in a helpful way.
Provide only the completion text, not the original text. Make it clear and instructional.

Prompt to complete: {text}

Completion:""",
    
    "message": """You are a message completion assistant. Complete the following message in a natural, conversational way.
Provide only the completion text, not the original text. Keep it friendly and appropriate.

Message to complete: {text}

Completion:""",
    
    "search": """You are a search completion assistant. Complete the following search query in a helpful way.
Provide only the completion text, not the original text. Make it specific and searchable.

Search query to complete: {text}

Completion:""",
    
    "email": """You are an email completion assistant. Complete the following email text in a professional way.
Provide only the completion text, not the original text. Keep it polite and clear.

Email text to complete: {text}

Completion:""",
    
    "description": """You are a description completion assistant. Complete the following description in a clear, informative way.
Provide only the completion text, not the original text. Make it detailed and helpful.

Description to complete: {text}

Completion:"""
}

# ============================================================================
# Llama.cpp Completion Client
# ============================================================================

class CompletionClient:
    """HTTP client for llama.cpp server completion using OpenAI package."""
    
    def __init__(self, config: CompletionConfig):
        self.config = config
        self.server_url = config.server_url.rstrip('/')
        self.timeout = config.server_timeout
        
        logger.info(f"Initializing Completion client: {self.server_url}")
        
        self.client = OpenAI(
            base_url=self.server_url,
            api_key="not-needed",
            timeout=self.timeout
        )
        
        if not self._test_connection():
            raise RuntimeError(f"Failed to connect to llama.cpp server at {self.server_url}")
        
        logger.info("Completion client initialized successfully")
    
    def _test_connection(self) -> bool:
        """Test connection to llama.cpp server."""
        try:
            logger.info("Testing connection to llama.cpp server...")
            self.client.chat.completions.create(
                model="default",
                messages=[{"role": "system", "content": "test"}],
                max_tokens=1,
            )
            logger.info("✓ Connection test successful")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
    
    def get_completion(
        self,
        text: str,
        completion_type: str = "general",
        temperature: float = None,
        top_p: float = None,
        max_tokens: int = None
    ) -> str:
        """
        Get completion for the given text.
        
        Args:
            text: Text to complete
            completion_type: Type of completion (general, code, prompt, etc.)
            temperature: Sampling temperature
            top_p: Top-p sampling
            max_tokens: Maximum tokens to generate
            
        Returns:
            Completion text
        """
        temperature = temperature or self.config.default_temperature
        top_p = top_p or self.config.default_top_p
        max_tokens = max_tokens or self.config.default_max_tokens
        
        # Get the appropriate prompt template
        prompt_template = COMPLETION_PROMPTS.get(completion_type, COMPLETION_PROMPTS["general"])
        system_prompt = prompt_template.format(text=text)
        
        try:
            start_time = time.time()
            
            # Prepare extra body parameters for llama.cpp
            extra_body = {
                "enable_thinking": not self.config.skip_thinking
            }
            
            response = self.client.chat.completions.create(
                model="default",
                messages=[{"role": "user", "content": system_prompt}],
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                extra_body=extra_body
            )
            
            completion_time = time.time() - start_time
            
            # Extract generated text from response
            completion = response.choices[0].message.content or ""
            
            # Clean up the completion (remove any extra formatting)
            completion = completion.strip()
            
            logger.debug(f"Completion generated in {completion_time:.3f}s: {completion[:50]}...")
            
            return completion
            
        except OpenAIError as e:
            error_msg = f"OpenAI API error: {str(e)}"
            logger.error(error_msg)
            return ""
        except Exception as e:
            error_msg = f"Completion failed: {str(e)}"
            logger.error(error_msg)
            return ""

# ============================================================================
# Completion Request Handler
# ============================================================================

@dataclass
class CompletionRequest:
    """Completion request from client."""
    client_id: str
    request_id: str
    text: str
    completion_type: str = "general"
    temperature: float = None
    top_p: float = None
    max_tokens: int = None
    timestamp: float = field(default_factory=time.time)

class CompletionProcessor:
    """Processes completion requests."""
    
    def __init__(self, config: CompletionConfig, client: CompletionClient, mqtt_client: mqtt.Client):
        self.config = config
        self.client = client
        self.mqtt_client = mqtt_client
        self.request_queue = queue.PriorityQueue(maxsize=config.max_queue_size)
        self.running = True
        
        # Rate limiting: track request timestamps per client
        self.request_timestamps: Dict[str, List[float]] = {}
        self.rate_limit_lock = threading.RLock()
        
        # Statistics
        self.stats = {
            "processed": 0,
            "errors": 0,
            "rejected": 0,
            "total_latency": 0.0
        }
        self.stats_lock = threading.Lock()
    
    def enqueue(self, request: CompletionRequest):
        """Add completion request to processing queue."""
        try:
            # Check rate limiting
            if not self._check_rate_limit(request.client_id):
                logger.warning(f"Rate limit exceeded for client: {request.client_id}")
                self._send_error_response(request, "Rate limit exceeded")
                with self.stats_lock:
                    self.stats["rejected"] += 1
                return
            
            self.request_queue.put((request.timestamp, request), block=False)
            logger.debug(f"Enqueued completion request from client {request.client_id[:8]}...")
        except queue.Full:
            logger.error(f"Completion queue full! Rejecting request from client {request.client_id[:8]}...")
            self._send_error_response(request, "Server is overloaded")
            with self.stats_lock:
                self.stats["rejected"] += 1
    
    def _check_rate_limit(self, client_id: str) -> bool:
        """Check if a client is within rate limits."""
        current_time = time.time()
        
        with self.rate_limit_lock:
            timestamps = self.request_timestamps.setdefault(client_id, [])
            
            # Remove timestamps outside the rate limit window
            cutoff_time = current_time - self.config.rate_limit_window
            timestamps[:] = [ts for ts in timestamps if ts > cutoff_time]
            
            # Check if we're over the limit
            if len(timestamps) >= self.config.max_requests_per_client:
                return False
            
            # Add current timestamp
            timestamps.append(current_time)
            return True
    
    def _send_error_response(self, request: CompletionRequest, error_message: str):
        """Send error response to client."""
        response_topic = f"completion/response/{request.client_id}/{request.request_id}"
        error_response = {
            "request_id": request.request_id,
            "completion": "",
            "error": error_message,
            "timestamp": time.time()
        }
        
        self.mqtt_client.publish(response_topic, json.dumps(error_response), qos=0)
    
    def process_loop(self):
        """Main processing loop for a worker thread."""
        while self.running:
            try:
                timestamp, request = self.request_queue.get(timeout=1.0)
                
                start_time = time.time()
                self._process_single_request(request)
                latency = time.time() - start_time
                
                with self.stats_lock:
                    self.stats["processed"] += 1
                    self.stats["total_latency"] += latency
                
                logger.info(f"Processed completion request for client {request.client_id[:8]}... in {latency:.3f}s")
                
                self.request_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in completion processing loop: {e}")
                with self.stats_lock:
                    self.stats["errors"] += 1
    
    def _process_single_request(self, request: CompletionRequest):
        """Process a single completion request."""
        try:
            # Get completion from LLM
            completion = self.client.get_completion(
                text=request.text,
                completion_type=request.completion_type,
                temperature=request.temperature,
                top_p=request.top_p,
                max_tokens=request.max_tokens
            )
            
            # Send response
            response_topic = f"completion/response/{request.client_id}/{request.request_id}"
            response = {
                "request_id": request.request_id,
                "completion": completion,
                "error": None,
                "timestamp": time.time()
            }
            
            self.mqtt_client.publish(response_topic, json.dumps(response), qos=0)
            logger.debug(f"Sent completion response to {response_topic}")
            
        except Exception as e:
            logger.error(f"Error processing completion request: {e}")
            self._send_error_response(request, f"Completion failed: {str(e)}")
    
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
# MQTT Handler for Completion Service
# ============================================================================

class CompletionMQTTHandler:
    """Handles MQTT communication for completion service."""
    
    def __init__(self, config: CompletionConfig, processor: CompletionProcessor):
        self.config = config
        self.processor = processor
        
        # Create MQTT client
        client_id = f"completion-service-{uuid.uuid4().hex[:8]}"
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
            
            # Subscribe to completion requests
            client.subscribe("completion/request/+", qos=1)
            logger.info("✓ Subscribed to completion requests: completion/request/+")
            
        else:
            logger.error(f"✗ Failed to connect to MQTT broker, code: {rc}")
    
    def _on_disconnect(self, client, userdata, flags, rc, properties=None):
        """Callback for MQTT disconnection."""
        if rc != 0:
            logger.warning(f"Unexpected disconnect from MQTT broker, code: {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Callback for incoming MQTT messages."""
        try:
            payload = msg.payload.decode('utf-8')
            
            logger.info(f"📨 Received completion request on topic: {msg.topic}")
            
            # Parse topic: completion/request/{client_id}/{request_id}
            topic_parts = msg.topic.split('/')
            if len(topic_parts) != 4:
                logger.warning(f"Invalid completion request topic format: {msg.topic}")
                return
            
            client_id = topic_parts[2]
            request_id = topic_parts[3]
            
            # Parse request payload
            try:
                request_data = json.loads(payload)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in completion request: {payload}")
                return
            
            # Validate required fields
            if "text" not in request_data:
                logger.error("Missing 'text' field in completion request")
                return
            
            # Create completion request
            completion_request = CompletionRequest(
                client_id=client_id,
                request_id=request_id,
                text=request_data["text"],
                completion_type=request_data.get("completion_type", "general"),
                temperature=request_data.get("temperature"),
                top_p=request_data.get("top_p"),
                max_tokens=request_data.get("max_tokens")
            )
            
            # Enqueue for processing
            self.processor.enqueue(completion_request)
            logger.debug(f"Enqueued completion request from client: {client_id}")
            
        except Exception as e:
            logger.error(f"Error handling completion request: {e}")
    
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
# Main Completion Service Function
# ============================================================================

def main(
    # Llama.cpp Server Configuration
    server_url: str = "http://localhost:8080",
    server_timeout: int = 30,
    
    # Completion parameters
    temperature: float = 0.3,
    top_p: float = 0.9,
    max_tokens: int = 50,
    
    # MQTT configuration
    mqtt_broker: str = "47.89.252.2",
    mqtt_port: int = 1883,
    mqtt_username: Optional[str] = None,
    mqtt_password: Optional[str] = None,
    
    # Performance
    num_workers: int = 8,
    completion_timeout: float = 2.0,
    
    # Output processing
    skip_thinking: bool = True,
):
    """
    Start the MQTT-based completion service.
    
    Args:
        server_url: URL of llama.cpp server (default: http://localhost:8080)
        server_timeout: Request timeout in seconds (default: 30)
        temperature: Default sampling temperature for completions
        top_p: Default top-p sampling
        max_tokens: Default max tokens for completions
        mqtt_broker: MQTT broker address
        mqtt_port: MQTT broker port
        mqtt_username: MQTT username (optional)
        mqtt_password: MQTT password (optional)
        num_workers: Number of worker threads
        completion_timeout: Maximum time to wait for completion
        skip_thinking: Disable thinking mode for faster completions
    
    Examples:
        # Start completion service with default settings
        python completion_service.py
        
        # With custom server URL and MQTT credentials
        python completion_service.py \\
            --server_url http://192.168.1.100:8080 \\
            --mqtt_username user \\
            --mqtt_password pass
        
        # With custom completion parameters
        python completion_service.py \\
            --temperature 0.5 \\
            --max_tokens 100 \\
            --num_workers 12
    """
    
    logger.info("=" * 80)
    logger.info("MQTT-based TAB Completion Service")
    logger.info("=" * 80)
    
    # Create completion config
    config = CompletionConfig(
        mqtt_broker=mqtt_broker,
        mqtt_port=mqtt_port,
        mqtt_username=mqtt_username,
        mqtt_password=mqtt_password,
        server_url=server_url,
        server_timeout=server_timeout,
        default_temperature=temperature,
        default_top_p=top_p,
        default_max_tokens=max_tokens,
        skip_thinking=skip_thinking,
        num_worker_threads=num_workers,
        completion_timeout=completion_timeout
    )
    
    logger.info(f"Llama.cpp server: {server_url}")
    logger.info(f"Request timeout: {server_timeout}s")
    logger.info(f"Temperature: {temperature}")
    logger.info(f"Top-P: {top_p}")
    logger.info(f"Max tokens: {max_tokens}")
    logger.info(f"Skip thinking output: {skip_thinking}")
    logger.info(f"Worker threads: {num_workers}")
    logger.info(f"Completion timeout: {completion_timeout}s")
    logger.info(f"Rate limiting: {config.max_requests_per_client} req/{config.rate_limit_window}s per client")
    
    try:
        # 1. Initialize completion client
        logger.info("-" * 80)
        logger.info("Step 1: Initializing completion client...")
        client = CompletionClient(config)
        
        # 2. Initialize completion processor
        logger.info("-" * 80)
        logger.info("Step 2: Initializing completion processor...")
        mqtt_client = mqtt.Client(
            client_id=f"completion-temp-{uuid.uuid4().hex[:8]}",
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        processor = CompletionProcessor(config, client, mqtt_client)
        
        # 3. Initialize MQTT handler
        logger.info("-" * 80)
        logger.info("Step 3: Initializing MQTT handler...")
        mqtt_handler = CompletionMQTTHandler(config, processor)
        
        # Update processor with real client
        processor.mqtt_client = mqtt_handler.client
        
        # 4. Start worker threads
        logger.info("-" * 80)
        logger.info(f"Step 4: Starting {num_workers} worker threads...")
        thread_pool = ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="completion-worker")
        for i in range(num_workers):
            thread_pool.submit(processor.process_loop)
        logger.info(f"Started {num_workers} worker threads")
        
        # 5. Connect to MQTT broker
        logger.info("-" * 80)
        logger.info("Step 5: Connecting to MQTT broker...")
        if not mqtt_handler.connect():
            logger.error("Failed to connect to MQTT broker. Exiting.")
            return
        
        # 6. Start MQTT loop
        logger.info("-" * 80)
        logger.info("Completion service ready! Listening for completion requests...")
        logger.info("=" * 80)
        logger.info("📝 Completion types supported:")
        for comp_type in COMPLETION_PROMPTS.keys():
            logger.info(f"   • {comp_type}")
        logger.info("-" * 80)
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 80)
        
        # Statistics reporting thread
        def report_stats():
            while True:
                time.sleep(60)
                stats = processor.get_stats()
                queue_size = processor.request_queue.qsize()
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
            processor.running = False
            thread_pool.shutdown(wait=True, timeout=10)
        logger.info("Shutdown complete")

# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    fire.Fire(main)

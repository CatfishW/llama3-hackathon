import time
import uuid
import threading
import queue
import json
import torch
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Literal
from concurrent.futures import ThreadPoolExecutor
import fire
from llama import Dialog, Llama
import paho.mqtt.client as mqtt
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# MQTT Configuration
MQTT_BROKER = "47.89.252.2"
MQTT_PORT = 1883
MQTT_USER_TOPIC = "llama/user_input"
MQTT_ASSISTANT_TOPIC = "llama/assistant_response"
# Topic for session management
MQTT_SESSION_TOPIC = "llama/session"
# Max number of concurrent sessions
MAX_CONCURRENT_SESSIONS = 30

# Thread pool configuration
NUM_WORKER_THREADS = 4  # Adjust based on your hardware

# Batch processing configuration
BATCH_TIMEOUT = 0.05  # Seconds to wait to form a batch
BATCH_SIZE = 4       # Maximum batch size (should match max_batch_size)

# Priority queue for message processing
class PriorityMessage:
    def __init__(self, priority, item):
        self.priority = priority
        self.item = item
    
    def __lt__(self, other):
        return self.priority < other.priority

# Message processing queue
message_queue = queue.PriorityQueue(maxsize=100)

# Performance metrics tracking
class PerformanceMetrics:
    def __init__(self):
        self.request_count = 0
        self.response_times = []
        self.lock = threading.Lock()
        self.start_time = time.time()
        # Start metrics reporting thread
        self.reporting_thread = threading.Thread(target=self._report_metrics, daemon=True)
        self.reporting_thread.start()
    
    def record_request(self):
        with self.lock:
            self.request_count += 1
    
    def record_response_time(self, response_time_ms):
        with self.lock:
            self.response_times.append(response_time_ms)
            # Keep only the last 1000 response times to avoid memory issues
            if len(self.response_times) > 1000:
                self.response_times = self.response_times[-1000:]
    
    def _report_metrics(self):
        while True:
            time.sleep(60)  # Report every minute
            with self.lock:
                uptime = time.time() - self.start_time
                avg_response = sum(self.response_times) / len(self.response_times) if self.response_times else 0
                throughput = self.request_count / uptime if uptime > 0 else 0
                
                logger.info(f"Performance metrics - "
                           f"Requests: {self.request_count}, "
                           f"Avg response time: {avg_response:.2f}ms, "
                           f"Throughput: {throughput:.2f} req/sec, "
                           f"Queue size: {message_queue.qsize()}")

# Model interface and implementations
class ModelInterface(ABC):
    @abstractmethod
    def generate_response(self, dialog, max_gen_len, temperature, top_p):
        """Generate a response given a dialog history"""
        pass
    
    @abstractmethod
    def count_tokens(self, dialog):
        """Count tokens in the dialog"""
        pass

class LlamaModel(ModelInterface):
    def __init__(self, ckpt_dir, tokenizer_path, max_seq_len, max_batch_size):
        self.generator = Llama.build(
            ckpt_dir=ckpt_dir,
            tokenizer_path=tokenizer_path,
            max_seq_len=max_seq_len,
            max_batch_size=max_batch_size,
        )
    
    def generate_response(self, dialog, max_gen_len, temperature, top_p):
        results = self.generator.chat_completion(
            [dialog],
            max_gen_len=max_gen_len,
            temperature=temperature,
            top_p=top_p,
        )
        return results[0]['generation']['content']
    
    def count_tokens(self, dialog):
        """Count tokens in the dialog"""
        total_tokens = 0
        for message in dialog:
            role_token = self.generator.tokenizer.encode(message['role'], bos=False, eos=False)
            content_tokens = self.generator.tokenizer.encode(message['content'], bos=False, eos=False)
            total_tokens += len(role_token) + len(content_tokens)
        return total_tokens

class QwQModel(ModelInterface):
    def __init__(self, model_name, max_seq_len, quantization=None):
        """
        Initialize QwQ model with optional quantization
        
        Args:
            model_name: Name or path of the model
            max_seq_len: Maximum sequence length
            quantization: Quantization method ('4bit', '8bit', or None for FP16/32)
        """
        logger.info(f"Loading QwQ model: {model_name} with quantization: {quantization}")
        
        # Configure quantization
        quantization_config = None
        if quantization == '4bit':
            quantization_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True
            )
            logger.info("Using 4-bit quantization with bitsandbytes")
        elif quantization == '8bit':
            quantization_config = BitsAndBytesConfig(
                load_in_8bit=True
            )
            logger.info("Using 8-bit quantization with bitsandbytes")
        
        # Load model with appropriate configuration
        load_kwargs = {
            "device_map": "auto"
        }
        
        # Add quantization config if specified
        if quantization_config:
            load_kwargs["quantization_config"] = quantization_config
        else:
            # Use FP16 if no quantization is specified
            load_kwargs["torch_dtype"] = torch.float16
            
        self.model = AutoModelForCausalLM.from_pretrained(
            model_name,
            **load_kwargs
        )
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.max_seq_len = max_seq_len
        
        # Log memory usage
        if hasattr(torch.cuda, 'memory_allocated'):
            memory_used = torch.cuda.memory_allocated() / 1024**3  # GB
            logger.info(f"GPU memory used after model loading: {memory_used:.2f} GB")
    
    def generate_response(self, dialog, max_gen_len, temperature, top_p):
        # Convert dialog format to match QwQ's expected format
        messages = []
        for message in dialog:
            messages.append({"role": message["role"], "content": message["content"]})
        
        # Apply chat template
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        # Generate response
        model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
        
        generated_ids = self.model.generate(
            **model_inputs,
            max_new_tokens=max_gen_len if max_gen_len else 512,
            temperature=temperature,
            top_p=top_p
        )
        
        # Extract only the new tokens (remove the prompt)
        generated_ids = [
            output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
        ]
        
        response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
        return response
    
    def count_tokens(self, dialog):
        """Count tokens in the dialog"""
        messages = []
        for message in dialog:
            messages.append({"role": message["role"], "content": message["content"]})
        
        text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        tokens = self.tokenizer(text, return_tensors="pt").input_ids
        return tokens.shape[1]  # Number of tokens

class SessionManager:
    def __init__(self, model, system_prompt, max_seq_len):
        self.sessions = {}
        self.model = model  # Now using the model interface
        self.system_prompt = system_prompt
        self.max_seq_len = max_seq_len
        self.session_locks = {}  # Individual locks for each session
        self.global_lock = threading.RLock()  # Only used when modifying the sessions dict
        
    def get_or_create_session(self, session_id):
        # First check without lock for better performance
        if session_id in self.sessions:
            # Update last access outside of lock
            self.sessions[session_id]["last_access"] = time.time()
            return self.sessions[session_id]
        
        # Need to create a new session - acquire global lock
        with self.global_lock:
            if session_id not in self.sessions:
                if len(self.sessions) >= MAX_CONCURRENT_SESSIONS:
                    # Find the 5 least recently used sessions to remove
                    oldest_ids = sorted(self.sessions.items(), key=lambda x: x[1]["last_access"])[:5]
                    for oldest_id, _ in oldest_ids:
                        del self.sessions[oldest_id]
                        if oldest_id in self.session_locks:
                            del self.session_locks[oldest_id]
                        logger.info(f"Removed oldest session {oldest_id} due to limit")
                
                # Create new session
                self.sessions[session_id] = {
                    "dialog": [{"role": "assistant", "content": self.system_prompt}],
                    "last_access": time.time()
                }
                self.session_locks[session_id] = threading.RLock()  # Create per-session lock
                logger.info(f"Created new session: {session_id}")
            else:
                self.sessions[session_id]["last_access"] = time.time()
                
            return self.sessions[session_id]
    
    def process_message(self, session_id, user_input, temperature, top_p, max_gen_len):
        # Get session (creates if needed)
        session = self.get_or_create_session(session_id)
        
        # Use the session-specific lock
        with self.session_locks.get(session_id, threading.RLock()):
            if not user_input.strip():
                # Reset the dialog
                session["dialog"] = [{"role": "assistant", "content": self.system_prompt}]
                return "Dialog has been reset."
            
            # Append user message
            session["dialog"].append({"role": "user", "content": user_input})
            
            # Trim dialog if needed
            self.trim_dialog_to_fit_max_len(session["dialog"])
            
            # Generate response
            try:
                assistant_response = self.model.generate_response(
                    session["dialog"],
                    max_gen_len=max_gen_len,
                    temperature=temperature,
                    top_p=top_p
                )
                
                session["dialog"].append({"role": "assistant", "content": assistant_response})
                return assistant_response
                
            except Exception as e:
                error_msg = f"Error generating response: {str(e)}"
                logger.error(error_msg)
                return error_msg
    
    def trim_dialog_to_fit_max_len(self, dialog):
        """Trims the oldest messages from the dialog until the total token count is <= max_seq_len."""
        while self.model.count_tokens(dialog) > self.max_seq_len-5 and len(dialog) > 1:
            dialog.pop(0)

def message_processor(session_manager, client, temperature, top_p, max_gen_len, metrics):
    """Process individual messages from the queue"""
    while True:
        try:
            # Get message from queue with timeout
            msg_data = message_queue.get(timeout=1.0).item  # Get priority message item
            session_id = msg_data["session_id"]
            user_input = msg_data["message"]
            topic = msg_data["topic"]
            
            metrics.record_request()
            start_time = time.time()
            
            # Process message
            logger.info(f"Processing message for session {session_id}")
            response = session_manager.process_message(
                session_id, user_input, temperature, top_p, max_gen_len
            )
            
            # Record response time in milliseconds
            response_time = (time.time() - start_time) * 1000
            metrics.record_response_time(response_time)
            
            # Publish response with session ID
            response_topic = f"{MQTT_ASSISTANT_TOPIC}/{session_id}"
            client.publish(response_topic, response)
            logger.info(f"Published response to {response_topic} in {response_time:.2f}ms")
            
            # Mark task as done
            message_queue.task_done()
            
        except queue.Empty:
            # No messages in queue, just continue
            continue
        except Exception as e:
            logger.error(f"Error in message processor: {str(e)}")

def batch_message_processor(session_manager, client, temperature, top_p, max_gen_len, metrics):
    """Process messages in batches when possible for better throughput"""
    batch = []
    batch_sessions = []
    batch_topics = []
    
    while True:
        try:
            # Get first message with timeout
            priority_msg = message_queue.get(timeout=0.5)
            msg_data = priority_msg.item
            session_id = msg_data["session_id"]
            user_input = msg_data["message"]
            topic = msg_data["topic"]
            
            metrics.record_request()
            batch_start = time.time()
            
            # Add to current batch
            batch.append(user_input)
            batch_sessions.append(session_id)
            batch_topics.append(topic)
            
            # Try to fill batch up to batch size with a short timeout
            try:
                while len(batch) < BATCH_SIZE and time.time() - batch_start < BATCH_TIMEOUT:
                    priority_msg = message_queue.get(timeout=BATCH_TIMEOUT)
                    msg_data = priority_msg.item
                    batch.append(msg_data["message"])
                    batch_sessions.append(msg_data["session_id"])
                    batch_topics.append(msg_data["topic"])
                    metrics.record_request()
            except queue.Empty:
                # Batch timeout - process what we have
                pass
                
            logger.info(f"Processing batch of {len(batch)} messages")
            
            # Process each message in the batch
            for i, (user_input, session_id, topic) in enumerate(zip(batch, batch_sessions, batch_topics)):
                start_time = time.time()
                
                response = session_manager.process_message(
                    session_id, user_input, temperature, top_p, max_gen_len
                )
                
                # Record response time in milliseconds
                response_time = (time.time() - start_time) * 1000
                metrics.record_response_time(response_time)
                
                # Publish response
                response_topic = f"{MQTT_ASSISTANT_TOPIC}/{session_id}"
                client.publish(response_topic, response)
                logger.info(f"Published response to {response_topic} in {response_time:.2f}ms")
                
                # Mark task as done
                message_queue.task_done()
            
            # Clear the batch
            batch = []
            batch_sessions = []
            batch_topics = []
            
        except queue.Empty:
            # No messages in queue, just continue
            continue
        except Exception as e:
            logger.error(f"Error in batch message processor: {str(e)}")
            # Mark failed tasks as done to avoid queue blockage
            for _ in range(len(batch)):
                try:
                    message_queue.task_done()
                except:
                    pass

def main(
    model_type: str = "llama",  # "llama" or "qwq"
    # Llama model parameters
    ckpt_dir: Optional[str] = None,
    tokenizer_path: Optional[str] = None,
    # QwQ model parameters
    model_name: Optional[str] = "Qwen/QwQ-32B",
    quantization: Optional[str] = None,  # '4bit', '8bit' or None for FP16/32
    # Common parameters
    temperature: float = 0.6,
    top_p: float = 0.9,
    max_seq_len: int = 2048,
    max_batch_size: int = 4,
    max_gen_len: Optional[int] = None,
    delay: float = 0.001,
    mqtt_username: Optional[str] = None,
    mqtt_password: Optional[str] = None,
    num_workers: int = NUM_WORKER_THREADS,
    use_batching: bool = True
):
    try:
        # Initialize the appropriate model based on type
        logger.info(f"Initializing {model_type} model...")
        
        if model_type.lower() == "llama":
            if not ckpt_dir or not tokenizer_path:
                logger.error("For Llama model, ckpt_dir and tokenizer_path must be provided")
                return
                
            model = LlamaModel(
                ckpt_dir=ckpt_dir,
                tokenizer_path=tokenizer_path,
                max_seq_len=max_seq_len,
                max_batch_size=max_batch_size
            )
            
        elif model_type.lower() == "qwq":
            if not model_name:
                logger.error("For QwQ model, model_name must be provided")
                return
            
            # Validate quantization parameter    
            if quantization and quantization not in ['4bit', '8bit']:
                logger.error("Quantization must be '4bit', '8bit' or None")
                return
                
            model = QwQModel(
                model_name=model_name,
                max_seq_len=max_seq_len,
                quantization=quantization
            )
            
        else:
            logger.error(f"Unsupported model type: {model_type}")
            return
            
        logger.info(f"{model_type} model initialized successfully")

        # System prompt
        SETTING = "You are a peer agent live in heart who knows nothing about Red Blood Cells, lead players to learn more from the knowledge by letting players teach you properly.Goal: Try to understand the following question from player's answer, Note that your output contain 'I understand, I choose B' only when player has proper explaination for his answer. If the player don't have enough explanations to the question or the answer, don't output 'I understand, I choose B', try to ask the player more. Always use first person pronouns, and keep your responses short."
        LIMITATION = "LIMIT: You you can only learn from the player's answers, player's answers could be wrong but you can't correct them. You Answer should be no more than 20 words. No matter what,don't respond to player's irrelevant questions."
        QUESTION = "Question:Which of the following facts is true about me?A) Red blood cells contain a nucleus to store oxygen.B) Red blood cells do not contain a nucleus."
        EXTRA = "Make sure to provide players with emotional support and encouragement, and to ask them to explain their answers in detail."
        EXTRA_2 = "Speak like a junior high school student, you can use some cool gen-z slangs and be humorous."
        
        SYSTEM_PROMPT = SETTING + LIMITATION + QUESTION + EXTRA + EXTRA_2
        
        # Create session manager with our model
        session_manager = SessionManager(model, SYSTEM_PROMPT, max_seq_len)

        # Initialize performance metrics
        metrics = PerformanceMetrics()

        # MQTT client initialization with unique client ID to avoid conflicts
        client_id = f'llama-service-{uuid.uuid4().hex[:8]}'
        client = mqtt.Client(client_id=client_id)
        
        # Set up MQTT username and password if provided
        if mqtt_username and mqtt_password:
            client.username_pw_set(mqtt_username, mqtt_password)
            logger.info("MQTT username and password set")

        # Set up reconnection parameters
        client.reconnect_delay_set(min_delay=1, max_delay=120)

        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info("Connected to MQTT Broker!")
                # Subscribe to the user input topic with wildcard for session IDs
                client.subscribe(f"{MQTT_USER_TOPIC}/#")
                client.subscribe(MQTT_SESSION_TOPIC)
            else:
                logger.error(f"Failed to connect to MQTT broker with code {rc}")

        def on_disconnect(client, userdata, rc):
            if rc != 0:
                logger.warning(f"Unexpected disconnection from MQTT broker: {rc}")

        def on_message(client, userdata, msg):
            try:
                topic = msg.topic
                payload = msg.payload.decode("utf-8")
                
                # Handle session creation requests
                if topic == MQTT_SESSION_TOPIC:
                    # Client is requesting a new session
                    session_id = uuid.uuid4().hex[:10]
                    session_manager.get_or_create_session(session_id)
                    client.publish(f"{MQTT_SESSION_TOPIC}/response", session_id)
                    logger.info(f"New session created: {session_id}")
                    return
                
                # Handle user messages
                if topic.startswith(MQTT_USER_TOPIC):
                    # Extract session ID from topic
                    parts = topic.split('/')
                    if len(parts) >= 3:
                        session_id = parts[2]
                    else:
                        # Fallback for old clients without session ID
                        session_id = "default"
                    
                    logger.info(f"Received message from session {session_id}: {payload[:30]}...")
                    
                    # Set message priority (lower number = higher priority)
                    # Custom priority logic - shorter messages get higher priority
                    priority = 1  # Default priority
                    if len(payload) < 20:
                        priority = 0
                    
                    # Add message to processing queue
                    if message_queue.full():
                        logger.warning("Message queue is full, dropping oldest message")
                        try:
                            message_queue.get_nowait()
                            message_queue.task_done()
                        except queue.Empty:
                            pass
                    
                    message_queue.put(PriorityMessage(priority, {
                        "session_id": session_id,
                        "message": payload,
                        "topic": topic
                    }))
            except Exception as e:
                logger.error(f"Error handling message: {str(e)}")

        # Set up MQTT callbacks
        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect

        # Start worker threads
        processor_pool = ThreadPoolExecutor(max_workers=num_workers, thread_name_prefix="llama-worker")
        
        if use_batching:
            # Start batch processor threads
            logger.info(f"Starting {num_workers} batch processor threads")
            for _ in range(num_workers):
                processor_pool.submit(batch_message_processor, session_manager, client, temperature, top_p, max_gen_len, metrics)
        else:
            # Start individual message processor threads
            logger.info(f"Starting {num_workers} message processor threads")
            for _ in range(num_workers):
                processor_pool.submit(message_processor, session_manager, client, temperature, top_p, max_gen_len, metrics)
        
        # Connect to the MQTT broker with retry logic
        connected = False
        retry_count = 0
        max_retries = 5
        
        while not connected and retry_count < max_retries:
            try:
                logger.info(f"Connecting to MQTT broker {MQTT_BROKER}:{MQTT_PORT} (attempt {retry_count+1})")
                client.connect(MQTT_BROKER, MQTT_PORT, 60)
                connected = True
            except Exception as e:
                retry_count += 1
                wait_time = min(30, 2 ** retry_count)
                logger.error(f"Failed to connect: {str(e)}. Retrying in {wait_time} seconds...")
                time.sleep(wait_time)
        
        if not connected:
            logger.error("Failed to connect to MQTT broker after multiple attempts. Exiting.")
            return
            
        # Start the MQTT loop to handle incoming messages
        logger.info("Starting MQTT loop...")
        client.loop_forever()

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, shutting down...")
    except Exception as e:
        logger.error(f"Unhandled exception: {str(e)}")
    finally:
        if 'client' in locals() and client.is_connected():
            client.disconnect()
        if 'processor_pool' in locals():
            processor_pool.shutdown(wait=False)
        logger.info("Service stopped")

if __name__ == "__main__":
    fire.Fire(main)
    # Example commands:
    # Llama model:
    # torchrun --nproc_per_node 1 ./mqtt_deploy.py --model_type llama --ckpt_dir Llama3.1-8B-Instruct --tokenizer_path Llama3.1-8B-Instruct/tokenizer.model --max_batch_size 4 --mqtt_username TangClinic --mqtt_password Tang123
    
    # QwQ model (full precision):
    # python mqtt_deploy.py --model_type qwq --model_name Qwen/QwQ-32B --mqtt_username TangClinic --mqtt_password Tang123
    
    # QwQ model (4-bit quantized):
    # python mqtt_deploy.py --model_type qwq --model_name Qwen/QwQ-32B --quantization 4bit --mqtt_username TangClinic --mqtt_password Tang123
    
    # QwQ model (8-bit quantized):
    # python mqtt_deploy.py --model_type qwq --model_name Qwen/QwQ-32B --quantization 8bit --mqtt_username TangClinic --mqtt_password Tang123
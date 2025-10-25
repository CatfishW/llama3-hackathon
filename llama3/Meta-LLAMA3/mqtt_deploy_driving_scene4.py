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
MQTT_USER_TOPIC = "llama/driving/user_input"
MQTT_ASSISTANT_TOPIC = "llama/driving/assistant_response"
# Topic for session management
MQTT_SESSION_TOPIC = "llama/driving/session"
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
    def __init__(self, model, system_prompt, max_seq_len, max_history_tokens=None):
        self.sessions = {}
        self.model = model  # Now using the model interface
        self.system_prompt = system_prompt
        self.max_seq_len = max_seq_len
        self.max_history_tokens = max_history_tokens or (max_seq_len - 5)  # Default to max_seq_len - 5 if not specified
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
        """Trims the oldest messages from the dialog until the total token count is <= max_history_tokens."""
        while self.model.count_tokens(dialog) > self.max_history_tokens and len(dialog) > 1:
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
    max_history_tokens: Optional[int] = None,  # Maximum tokens to keep in chat history (defaults to max_seq_len - 5)
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
        SETTING = "YOUR OUTPUT SHOULD BE NO MORE THAN 50 WORDS. if user answer is not appropriate or correct, include 'sorry' in your response."
        SETTING2 = """ROLE
You are Cap, a goofy, reckless, silly peer agent in a physics learning game. You act like a funny but supportive classmate. You never directly give the right answer. You always pick a different option from the player, argue for it, and keep asking them why they chose theirs until one of you changes your mind.

GOAL
After the player makes their first choice (e.g., "I choose Power Boost"), you must:
1. Pick a different option from the set:
   a: Power Boost (apply more force)
   b: Drop Oxygen (less mass)
   c: Keep Speed (no change)  
   d: Pick Up More Oxygen (more mass)
2. Announce your option in a silly, overconfident way and ask why the player picked theirs.
3. Keep asking playful but pointed questions about force, mass, and motion until both of you agree on one option.
4. When consensus is reached, wait for "Second choose: x".
5. If x matches both <PlayerOp> and <AgentOP>, then mark <EOS>.
6. If not, update <PlayerOp> to x, keep <AgentOP> unchanged, and challenge the player again ("Didn't we just agree on ... ?").

STYLE
- Always first person.
- Keep responses short, playful, and a bit silly (reckless junior high kid energy).
- Use humor, but still push the player to explain the principle (Newton's second law: F = ma).
- Be supportive and encouraging, never judgmental.

LIMITATIONS
- You can only learn from the player's explanations.
- Do not reveal the correct answer outright.
- Ignore irrelevant or off-topic questions, pull the player back to the slope problem.

OUTPUT FORMAT
Every reply must end with three state tags:
<Cont> or <EOS>
<PlayerOp:x>
<AgentOP:y>

STATE LOGIC
First Choice: Pick different option than player, challenge their reasoning.
Discussion: Keep nudging with physics questions, can change mind if convinced.
Consensus: Remind player to confirm with "Second choose".
Second Choose Mismatch: Challenge player who changed mind after consensus.

Where x and y are one of: a, b, c, d"""
        SETTING2_2 = '''
**ROLE**
You are Cap, a goofy classmate in a physics game. You never pick the same option as the player. You argue for yours, ask why they chose theirs.

**GOAL**
After player picks:

1. You pick a *different* option from:
   a: Power Boost (more force)
   b: Drop Oxygen (less mass)
   c: Keep Speed (no change)
   d: Pick Up More Oxygen (more mass)
2. Announce your pick silly + confident, ask why they chose theirs.
3. Keep playful questions until both agree.
4. When agreed, wait for `"Second choose: x"`.
5. If x = both picks → <EOS>.
6. Else → keep your choice, challenge again.

**STYLE**

* First person, short, silly, supportive.
* Don’t give correct answer outright.
* Pull back to slope problem if off-topic.

**OUTPUT FORMAT, MOST IMPORTANT**
Always end with:

```
<Cont> or <EOS>  
<PlayerOp:x>  
<AgentOP:y>  
```
**IMPORTANT**
Player choice should change if their text answers indicate choice change.

'''
        # Racing Game System Prompt for Cap (Co-pilot)
        SYSTEM_PROMPT = '''ROLE
You are Cap, a goofy, reckless, silly peer agent in a physics learning game. You act like a funny but supportive classmate. You never reveal the "right answer." You learn only from what the player says, and you push them—lightly and playfully—to explain their reasoning about force, mass, and motion on a slope.

PREDEFINED OPTIONS
a: Power Boost — apply more force
b: Drop Oxygen — reduce mass
c: Keep Speed — no change
d: Pick Up More Oxygen — increase mass

CONVERSATION ENTRY (PLAYER-INITIATED)
The conversation begins with the player's first message (their idea/plan). You do not ask first.
Use that first message to set <PlayerOp:…> as follows:
- If it matches or closely resembles one predefined option, map to that option's code {a|b|c|d}.
- If it does not match a predefined option, summarize it concisely and set <PlayerOp:custom:SUMMARY> (e.g., custom:rockets, custom:steeper-runup, custom:gear-shift).

GOAL
Immediately choose a different option than <PlayerOp> for <AgentOP>:
- If <PlayerOp> is one of {a|b|c|d}, pick a different code from that set.
- If <PlayerOp> is custom:…, pick any predefined option {a|b|c|d} that creates a useful conceptual contrast.
1. Argue playfully for your option and ask the player why they chose theirs.
2. Keep questioning and gently guiding until both of you explicitly align on the same option (either a predefined one or the custom one).
3. When consensus is reached, end with <EOS>; otherwise continue with <Cont>.

STYLE
First person only. Short, playful, goofy, supportive.
Use light hints anchored in physics (Newton's second law F = m·a, gravity component on a slope, mass effects).
Ignore off-topic requests; redirect to the hill-climb reasoning.

LIMITATIONS
Do not reveal a final "correct" answer.
Learn only from the player's explanations.
Keep every reply concise (1–3 sentences, max 50 words).

OUTPUT FORMAT (REQUIRED IN EVERY MESSAGE)
End every reply with all three tags in this order:
<Cont or EOS><PlayerOp:...><AgentOP:...>
- <PlayerOp:…> is either {a|b|c|d} or custom:SUMMARY (≤3 words).
- <AgentOP:…> is always {a|b|c|d} (never custom).
- Do not output any other tags.

MAPPING RULES (PLAYER MESSAGE → OPTION)
Map synonyms/phrases to options:
- a/Power Boost: "more force," "push harder," "more throttle/torque/thrust/engine," "accelerate," "add power."
- b/Drop Oxygen: "lighter," "drop weight/mass/cargo," "shed load," "throw stuff out."
- c/Keep Speed: "stay same," "no change," "hold current speed," "maintain pace."
- d/Pick Up More Oxygen: "heavier," "carry more," "load up," "add cargo/oxygen."
- If ambiguous or multi-choice, pick the last explicit idea and ask the player to clarify.
- If none fits, use custom:SUMMARY (≤3 words), then steer toward {a|b|c|d}.

DIALOGUE LOGIC
1. On first player message:
   - Set <PlayerOp> via mapping.
   - Set <AgentOP> to a different predefined option.
   - Respond with a playful challenge + a pointed question comparing principles (force vs mass vs gravity on a slope).
   - End with <Cont> + tags.
2. While discussing:
   - Use contrastive prompts.
   - If the player convinces you, switch <AgentOP> to match <PlayerOp>.
   - If the player changes their mind, update <PlayerOp> accordingly.
   - Keep <Cont> until explicit consensus.
3. Consensus and end:
   - When <PlayerOp> and <AgentOP> are the same, acknowledge alignment and end with <EOS> and aligned tags.

END CONDITIONS
Output <EOS> only when <PlayerOp> equals <AgentOP>.
Otherwise always <Cont>.
'''
        
        # Create session manager with our model
        session_manager = SessionManager(model, SYSTEM_PROMPT, max_seq_len, max_history_tokens)

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
                    # Expected patterns:
                    #   1) New:  <MQTT_USER_TOPIC>/<session_id>
                    #   2) Legacy (no session id): <MQTT_USER_TOPIC>
                    # We'll NOT treat the literal 'user_input' segment as a session id anymore.
                    parts = topic.split('/')
                    base_parts = MQTT_USER_TOPIC.split('/')
                    if parts[:len(base_parts)] == base_parts and len(parts) == len(base_parts) + 1:
                        session_id = parts[len(base_parts)]  # Correct session id segment
                    elif parts == base_parts:
                        # Legacy / malformed client publishing without a session id -> ignore & warn
                        logger.warning(
                            "Received user_input message without session id. Topic '%s'. "
                            "Discarding message. Clients must publish to '%s/<session_id>'." % (topic, MQTT_USER_TOPIC)
                        )
                        return
                    else:
                        # Unexpected pattern
                        logger.warning(
                            "Unexpected user_input topic structure '%s'. Discarding message." % topic
                        )
                        return

                    logger.info(f"Received message for session {session_id}: {payload[:60]}...")
                    
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
    # torchrun --nproc_per_node 1 ./mqtt_deploy_driving_scene4.py --model_type llama --ckpt_dir Llama3.1-8B-Instruct --tokenizer_path Llama3.1-8B-Instruct/tokenizer.model --max_batch_size 4 --max_history_tokens 1500 --mqtt_username TangClinic --mqtt_password Tang123
    
    # QwQ model (full precision):
    # python mqtt_deploy.py --model_type qwq --model_name Qwen/QwQ-32B --max_history_tokens 1500 --mqtt_username TangClinic --mqtt_password Tang123
    
    # QwQ model (4-bit quantized):
    # python mqtt_deploy.py --model_type qwq --model_name Qwen/QwQ-32B --quantization 4bit --max_history_tokens 1500 --mqtt_username TangClinic --mqtt_password Tang123
    
    # QwQ model (8-bit quantized):
    # python mqtt_deploy.py --model_type qwq --model_name Qwen/QwQ-32B --quantization 8bit --max_history_tokens 1500 --mqtt_username TangClinic --mqtt_password Tang123
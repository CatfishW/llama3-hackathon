# LAM Agent Initialization - Slides Format

---

## SLIDE 1: Publishing & Starting Flow

```
Step 1: User clicks "Publish & Start" in UI
        ↓
Step 2: Frontend publishes template + game state via MQTT
        Topic: maze/state
        Payload: { session_id, template_id, game_state }
        ↓
Step 3: MQTT Handler receives message
        ↓
Step 4: MessageProcessor queues it
        ↓
Step 5: Worker thread processes
        ↓
Step 6: SessionManager creates NEW session
        ↓
Step 7: LlamaCppClient calls llama.cpp server
        ↓
Step 8: LAM generates hint with actions
        ↓
Step 9: Response published back via MQTT
```

---

## SLIDE 2: ProjectConfig - Define Project

```
ProjectConfig: Configuration for each game type

@dataclass
class ProjectConfig:
    name: str                       # "maze", "driving", etc.
    user_topic: str                 # MQTT input: "maze/user_input"
    response_topic: str             # MQTT output: "maze/response"
    system_prompt: str              # "You are a LAM guiding..."
    
    # Optional topics for game integration
    state_topic: str = None         # "maze/state"
    hint_topic: str = None          # "maze/hint/{sessionId}"
    template_topic: str = None      # Template updates
    
    # Function calling
    tools: List[Dict] = None        # Allowed actions
    tool_choice: str = None         # "auto" → let LAM choose
```

**Example for Maze:**
```python
ProjectConfig(
    name="maze",
    user_topic="maze/user_input",
    response_topic="maze/response",
    system_prompt="You are a LAM guiding players through mazes.",
    tools=MAZE_ACTION_TOOLS,
    tool_choice="auto"
)
```

---

## SLIDE 3: DeploymentConfig - Global Settings

```
DeploymentConfig: Global deployment setup

@dataclass
class DeploymentConfig:
    # MQTT Configuration
    mqtt_broker: str = "47.89.252.2"
    mqtt_port: int = 1883
    mqtt_username: str = "TangClinic"
    mqtt_password: str = "Tang123"
    
    # Llama.cpp Server
    server_url: str = "http://localhost:8080"
    server_timeout: int = 300        # 5 minutes
    
    # Generation Settings
    default_temperature: float = 1.0
    default_top_p: float = 0.9
    default_max_tokens: int = 256
    skip_thinking: bool = True
    
    # Session Management
    max_concurrent_sessions: int = 100
    session_timeout: int = 3600      # 1 hour
    num_worker_threads: int = 12     # Parallel processing
```

---

## SLIDE 4: LlamaCppClient - Initialize LLM

```
LlamaCppClient: HTTP client for llama.cpp server

class LlamaCppClient:
    def __init__(self, config: DeploymentConfig):
        # Create OpenAI client pointing to llama.cpp
        self.client = OpenAI(
            base_url="http://localhost:8080",
            api_key="not-needed",
            timeout=300,
            max_retries=3
        )
        
        # Test connection
        if not self._test_connection():
            raise RuntimeError("Failed to connect")
```

**Connection Test:**
```python
def _test_connection(self) -> bool:
    """Verify llama.cpp server is running."""
    try:
        response = self.client.models.list()
        logger.info("✓ Connected to llama.cpp server")
        return True
    except Exception as e:
        logger.error(f"✗ Connection failed: {e}")
        return False
```

---

## SLIDE 5: SessionManager - Create Session

```
SessionManager: Manages per-user conversation state

class SessionManager:
    def __init__(self, config, client):
        # All sessions: Dict[(project, session_id)] → dialog_history
        self.sessions = {}
        
        # Thread locks for safety
        self.session_locks = {}
        self.global_lock = RLock()
        
        # Rate limiting
        self.request_timestamps = {}
        
        # Limit concurrent LLM calls
        self.inference_semaphore = Semaphore(8)  # Max 8 parallel
```

**Key: Thread-safe with per-session locks!**

---

## SLIDE 6: Get or Create Session

```
def get_or_create_session(
    session_id: str,
    project_name: str,
    system_prompt: str
) -> Dict:
    """Get existing session or create new one."""
    
    session_key = (project_name, session_id)
    
    # Check if exists
    if session_key in self.sessions:
        return self.sessions[session_key]
    
    # CREATE NEW SESSION
    session = {
        "dialog": [
            {
                "role": "system",
                "content": system_prompt  # ← System prompt loaded here!
            }
        ],
        "project": project_name,
        "session_id": session_id,
        "created_at": time.time(),
        "last_access": time.time(),
        "message_count": 0
    }
    
    # Store it
    self.sessions[session_key] = session
    self.session_locks[session_key] = RLock()
    
    return session
```

---

## SLIDE 7: Session Data Structure

```
Session object created and stored in memory:

session = {
    "dialog": [
        {
            "role": "system",
            "content": "You are a LAM guiding players..."
        }
    ],
    "project": "maze",
    "session_id": "session-abc123",
    "created_at": 1699275800.123,
    "last_access": 1699275800.123,
    "message_count": 0,
    "repeat_count": 0,
    "assistant_repeat_count": 0
}

This session stays in memory throughout the game!
Messages accumulate in "dialog" list.
```

---

## SLIDE 8: MessageProcessor - Queue & Dispatch

```
MessageProcessor: Handles message queueing and processing

class MessageProcessor:
    def __init__(self, config, session_manager, mqtt_client):
        # Main processing queue
        self.message_queue = PriorityQueue(maxsize=1000)
        
        # Response publishing queue
        self.publish_queue = Queue()
        
        # Statistics
        self.stats = {
            "processed": 0,
            "errors": 0,
            "rejected": 0
        }

def enqueue(self, message: QueuedMessage):
    """Add message to processing queue."""
    self.message_queue.put(
        (priority, timestamp, message),
        block=False
    )
```

**Non-blocking queue ensures messages don't pile up!**

---

## SLIDE 9: Worker Thread - Process Loop

```
Worker threads continuously process messages:

def process_loop(self):
    while self.running:
        try:
            # Get next message (blocks if empty)
            priority, timestamp, msg = \
                self.message_queue.get(timeout=1)
            
            # Process this message
            self._process_single_message(msg)
            
        except queue.Empty:
            continue  # No messages, loop again
```

**12 worker threads run in parallel (configurable)**
**Each thread processes messages sequentially**

---

## SLIDE 10: Process Single Message

```
def _process_single_message(self, msg: QueuedMessage):
    """Process message through LAM."""
    
    # 1. Get system prompt for project
    project_config = self.config.projects[msg.project_name]
    system_prompt = project_config.system_prompt
    
    # 2. THIS IS WHERE SESSION IS CREATED/RETRIEVED!
    response = self.session_manager.process_message(
        session_id=msg.session_id,
        project_name=msg.project_name,
        system_prompt=system_prompt,
        user_message=msg.user_message,
        temperature=1.0,
        top_p=0.9,
        max_tokens=256,
        client_id=None
    )
    
    # 3. Queue response for publishing
    self.publish_queue.put((msg.response_topic, response))
```

---

## SLIDE 11: MQTTHandler - Connect & Subscribe

```
MQTTHandler: MQTT communication

class MQTTHandler:
    def __init__(self, config, message_processor):
        # Create MQTT client
        self.client = mqtt.Client(client_id="...")
        
        # Set authentication
        self.client.username_pw_set("TangClinic", "Tang123")
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

def connect(self):
    """Connect to MQTT broker."""
    self.client.connect(
        "47.89.252.2",      # Broker IP
        1883,               # Port
        keepalive=60
    )
```

---

## SLIDE 12: On Connect - Subscribe to Topics

```
def _on_connect(self, client, userdata, flags, rc):
    """When connected, subscribe to all project topics."""
    
    if rc == 0:
        logger.info("✓ Connected to MQTT")
        
        # Subscribe to all enabled projects
        for project_name, config in self.config.projects.items():
            if not config.enabled:
                continue
            
            # Subscribe to topics
            topics = [
                (config.user_topic, 1),          # QoS 1
                (config.state_topic or "", 1),
                (config.template_topic or "", 1)
            ]
            
            for topic, qos in topics:
                if topic:
                    client.subscribe(topic, qos=qos)
                    logger.info(f"✓ Subscribed: {topic}")

Examples:
- "maze/user_input" (QoS 1)
- "maze/state" (QoS 1)
- "maze/template" (QoS 1)
```

---

## SLIDE 13: On Message - Route & Queue

```
def _on_message(self, client, userdata, msg):
    """MQTT callback - received message on topic."""
    
    topic = msg.topic                    # "maze/state"
    payload = json.loads(msg.payload)    # Parse JSON
    
    # Extract information
    session_id = payload.get("session_id")
    project_name = self._find_project_for_topic(topic)
    state = payload.get("state")         # Game state
    
    # Convert state to user message
    user_message = self._convert_state_to_message(state)
    # Result: "Player at (1,1), exit (2,2), 1 oxygen, 1 germ..."
    
    # Queue for processing
    msg_to_queue = QueuedMessage(
        session_id=session_id,
        project_name=project_name,
        user_message=user_message,
        response_topic="maze/hint/session-abc123",
        priority=0,
        timestamp=time.time()
    )
    
    self.message_processor.enqueue(msg_to_queue)
```

---

## SLIDE 14: ProcessMessage - Add to Session

```
def process_message(
    session_id: str,
    project_name: str,
    system_prompt: str,
    user_message: str
) -> str:
    """Process user message through session."""
    
    # 1. CREATE OR GET SESSION
    session = self.get_or_create_session(
        session_id,
        project_name,
        system_prompt
    )
    
    # 2. ADD USER MESSAGE TO DIALOG
    session["dialog"].append({
        "role": "user",
        "content": user_message
    })
    session["message_count"] += 1
    
    # 3. TRIM HISTORY (keep last 6 messages)
    if len(session["dialog"]) > 6:
        session["dialog"] = \
            [session["dialog"][0]] + session["dialog"][-5:]
```

---

## SLIDE 15: Call LLM - Generate Response

```
# 4. CALL LLM WITH SESSION HISTORY
response = self.client.generate(
    messages=session["dialog"],
    temperature=1.0,
    top_p=0.9,
    max_tokens=256,
    tools=MAZE_ACTION_TOOLS,
    tool_choice="auto"  # ← Let LAM choose which action
)

# Result might include tool calls:
# {
#     "hint": "Breaking wall...",
#     "break_wall": {"x": 2, "y": 2}
# }

# 5. ADD RESPONSE TO DIALOG
session["dialog"].append({
    "role": "assistant",
    "content": response
})

# 6. RETURN RESPONSE
return response
```

---

## SLIDE 16: LlamaCppClient - Generate

```
class LlamaCppClient:
    def generate(
        self,
        messages: List[Dict],
        tools: List[Dict] = None,
        tool_choice: str = None,
        **kwargs
    ) -> str:
        """Call llama.cpp server for inference."""
        
        request = {
            "model": "default",
            "messages": messages,        # Full conversation history
            "temperature": 1.0,
            "top_p": 0.9,
            "max_tokens": 256,
            "extra_body": {
                "enable_thinking": False,
                "cache_prompt": True      # Reuse tokens
            }
        }
        
        # Add tools if provided
        if tools:
            request["tools"] = tools
            request["tool_choice"] = tool_choice
        
        # Call server
        response = self.client.chat.completions.create(**request)
        
        return response.choices[0].message.content
```

---

## SLIDE 17: Complete Initialization Sequence

```
⏱ Timeline (milliseconds):

T=0ms:    Frontend sends "Publish & Start"
T=5ms:    MQTT publishes game state
T=10ms:   MQTT Handler receives on_message()
T=15ms:   Message queued to MessageProcessor
T=20ms:   Worker thread picks from queue
T=25ms:   SessionManager.get_or_create_session()
          → NEW SESSION CREATED ✓
T=30ms:   Session initialized with system prompt
T=35ms:   User message added to dialog
T=40ms:   LlamaCppClient.generate() called
T=40-2600ms: Llama.cpp server processing
          (~2560ms for LLM inference)
T=2600ms: Response received from server
T=2610ms: Response added to session dialog
T=2620ms: Response published back via MQTT
T=2625ms: Frontend receives and displays hint
          TOTAL: ~2.6 seconds
```

---

## SLIDE 18: Session Lifecycle During Game

```
Game Start:
├─ Session created with system prompt
├─ dialog = [{"role": "system", ...}]

First State Update:
├─ User message added
├─ LLM generates response
├─ Response added to dialog
├─ dialog = [system, user, assistant]

Subsequent Updates:
├─ More user messages queued
├─ History trimmed to last 6 messages
├─ Each maintains context from previous
├─ dialog stays in memory

Game End:
├─ Session may be cleared (optional)
├─ Or kept for next game session

Auto-cleanup (after 1 hour):
├─ Sessions with last_access > 3600s removed
├─ Memory freed
```

---

## SLIDE 19: Tools for Maze Game

```
MAZE_ACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "break_wall",
            "description": "Break wall at coordinates"
        }
    },
    {
        "type": "function",
        "function": {
            "name": "speed_boost",
            "description": "Give player speed boost"
        }
    },
    {
        "type": "function",
        "function": {
            "name": "freeze_germs",
            "description": "Freeze germs temporarily"
        }
    },
    # ... more tools
]

When LAM generates response:
tool_choice="auto"  ← LAM picks best tool
            ↓
Response includes tool calls
            ↓
Frontend applies actions
            ↓
Game updates state
```

---

## SLIDE 20: Debugging - Check Active Sessions

```
# View all active sessions
print("Active sessions:", session_manager.sessions.keys())
Output: dict_keys([('maze', 'session-abc123')])

# View specific session
session = session_manager.sessions.get(('maze', 'session-abc123'))

print("Dialog history:")
for msg in session['dialog']:
    print(f"  {msg['role']}: {msg['content'][:50]}...")

Output:
  system: You are a LAM guiding players...
  user: Player at (1,1), exit at (2,2)...
  assistant: Breaking wall at (2,2)...
  user: Player moved to (2,1)...
  assistant: Good move! Boost speed...

# Session metadata
print(f"Created: {session['created_at']}")
print(f"Messages: {session['message_count']}")
print(f"Project: {session['project']}")
```

---

## SLIDE 21: Key Components - Summary

```
┌─────────────────────────────────────────────────────┐
│ 1. ProjectConfig                                    │
│    - Per-project configuration                      │
│    - System prompt, tools, MQTT topics              │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 2. DeploymentConfig                                 │
│    - Global settings                                │
│    - MQTT broker, llama.cpp server, threading       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 3. LlamaCppClient                                   │
│    - HTTP client to llama.cpp server                │
│    - Generates responses with tools                 │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 4. SessionManager                                   │
│    - Creates/manages per-user sessions              │
│    - Maintains conversation history                 │
│    - Thread-safe with locks                         │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 5. MessageProcessor                                 │
│    - Queues and processes messages                  │
│    - Dispatches to worker threads                   │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│ 6. MQTTHandler                                      │
│    - Connects to MQTT broker                        │
│    - Routes messages to processor                   │
│    - Publishes responses back                       │
└─────────────────────────────────────────────────────┘
```

---

## SLIDE 22: Initialization Checklist

```
BEFORE GAME STARTS:
✓ ProjectConfig for "maze" defined with tools
✓ DeploymentConfig with MQTT and server URLs
✓ LlamaCppClient created and connected
✓ SessionManager initialized
✓ MessageProcessor created with queues
✓ MQTTHandler connected to broker
✓ 12 worker threads started
✓ Subscribed to all project topics
✓ System ready to receive messages

AFTER "PUBLISH & START":
✓ MQTT receives state message
✓ MessageProcessor.enqueue() called
✓ Worker thread picks message up
✓ SessionManager.get_or_create_session() → NEW SESSION
✓ System prompt loaded into session.dialog
✓ User message added to session.dialog
✓ LlamaCppClient.generate() calls server
✓ Response added to session.dialog
✓ Response published back via MQTT
✓ Frontend displays hint

Session is now PERSISTENT in memory!
```

---

## SLIDE 23: Memory Management

```
Sessions stored in memory:
self.sessions = {
    ("maze", "session-abc"): {...},
    ("maze", "session-def"): {...},
    ("driving", "session-ghi"): {...}
}

Each session object:
- Contains full conversation history
- Takes ~1-10KB per session (depends on history)

With 100 concurrent sessions:
- ~100KB to 1MB memory usage
- Configurable max_concurrent_sessions

Session Cleanup:
- Auto-delete if last_access > 3600 seconds (1 hour)
- Oldest sessions removed first (LRU eviction)
- Prevents memory leaks in long-running deployments
```

---

## SLIDE 24: Rate Limiting Protection

```
Per-Session Rate Limiting:
- Sliding window over 60 seconds
- Track timestamps of requests
- Reject if too many requests

SessionManager._check_rate_limit():
if len(request_timestamps) > max_requests_per_session:
    if oldest_timestamp > current_time - 60:
        REJECT request  # Too many in 60 seconds
    else:
        ALLOW request   # Old requests expired
        Remove old timestamps

Protection against:
- Spam/abuse
- Accidental infinite loops
- DDoS attacks
```

---

## SLIDE 25: Concurrent Inference Limiting

```
Global Inference Semaphore:
self.inference_semaphore = Semaphore(8)

Limits LLM calls to 8 parallel:

Request 1 ──→ Acquire semaphore ──→ Call llama.cpp
Request 2 ──→ Acquire semaphore ──→ Call llama.cpp
Request 3 ──→ Acquire semaphore ──→ Call llama.cpp
...
Request 8 ──→ Acquire semaphore ──→ Call llama.cpp
Request 9 ──→ WAIT (semaphore full)
Request 10 → WAIT (semaphore full)

When Request 1 finishes:
Request 9 ──→ Acquire semaphore ──→ Call llama.cpp

Benefits:
- Prevents server overload
- Manages GPU memory
- Maintains response quality
```

---

## KEY TAKEAWAYS

✓ **ProjectConfig** defines per-project behavior (system prompt, tools)

✓ **DeploymentConfig** defines global infrastructure (MQTT, llama.cpp)

✓ **LlamaCppClient** creates HTTP connection to llama.cpp server

✓ **SessionManager** creates/manages per-user conversation sessions

✓ **MessageProcessor** queues and dispatches to worker threads

✓ **MQTTHandler** connects to MQTT and routes messages

✓ **Session Created** on first user message, persisted in memory

✓ **System Prompt** initialized in session.dialog on creation

✓ **Thread-Safe** with RLock per session

✓ **Scalable** with 12 worker threads and inference semaphore

---

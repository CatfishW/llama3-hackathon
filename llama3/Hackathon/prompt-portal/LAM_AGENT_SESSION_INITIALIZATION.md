# LAM Agent & Session Initialization

## 📚 Overview

After clicking "Publish & Start", here's how the LAM (Large Action Model) agent and session are initialized:

```
User clicks "Publish & Start"
      ↓
Frontend publishes template via MQTT
      ↓
Backend MQTT Handler receives message
      ↓
MessageProcessor queues it
      ↓
Worker thread picks it up
      ↓
SessionManager creates NEW session (or reuses existing)
      ↓
LlamaCppClient initializes inference
      ↓
LAM generates hint/response
      ↓
Response published back via MQTT
```

---

## 🎯 Key Initialization Points

### 1️⃣ ProjectConfig - Define Project Behavior

**File:** `llamacpp_mqtt_deploy.py`, Lines 46-63

```python
@dataclass
class ProjectConfig:
    """Configuration for a single project/topic."""
    name: str                              # "maze", "driving", etc.
    user_topic: str                        # MQTT topic to listen on
    response_topic: str                    # MQTT topic to publish to
    system_prompt: str                     # System prompt for LAM
    enabled: bool = True
    
    # Optional state/hint topics for game integration
    state_topic: str = None                # e.g., "maze/state"
    hint_topic: str = None                 # e.g., "maze/hint/{sessionId}"
    template_topic: str = None             # For template updates
    clear_topic: str = None                # For session clearing
    delete_topic: str = None               # For session deletion
    
    # Function calling / tools
    tools: Optional[List[Dict]] = None     # Available actions (break_wall, etc.)
    tool_choice: Optional[str] = None      # "auto", "none", or specific tool
```

**Example for Maze:**
```python
ProjectConfig(
    name="maze",
    user_topic="maze/user_input",
    response_topic="maze/response",
    hint_topic="maze/hint/{session_id}",
    state_topic="maze/state",
    system_prompt="""You are a LAM guiding players through a maze...
                     Always respond in JSON format with keys: "hint", "suggestion"
                  """,
    tools=MAZE_ACTION_TOOLS,  # break_wall, speed_boost, etc.
    tool_choice="auto"        # Let LAM choose which action to take
)
```

---

### 2️⃣ DeploymentConfig - Global Settings

**File:** `llamacpp_mqtt_deploy.py`, Lines 66-94

```python
@dataclass
class DeploymentConfig:
    """Global deployment configuration."""
    
    # MQTT Configuration
    mqtt_broker: str = "47.89.252.2"
    mqtt_port: int = 1883
    mqtt_username: Optional[str] = "TangClinic"
    mqtt_password: Optional[str] = "Tang123"
    
    # Llama.cpp Server Configuration
    server_url: str = "http://localhost:8080"
    server_timeout: int = 300                    # 5 minutes
    
    # Generation Configuration
    default_temperature: float = 1.0             # Randomness
    default_top_p: float = 0.9                   # Diversity
    default_max_tokens: int = 256                # Max length
    skip_thinking: bool = True                   # Disable deep thinking
    
    # Session Management
    max_history_tokens: int = 10000              # Conversation history limit
    max_concurrent_sessions: int = 100           # Max sessions at once
    session_timeout: int = 3600                  # 1 hour
    
    # Performance
    num_worker_threads: int = 12                 # Process 12 messages in parallel
    batch_timeout: float = 0.1                   # Batching timeout
    max_queue_size: int = 1000                   # Max queued messages
    
    # Rate Limiting
    max_requests_per_session: int = 100000000    # Per-session limit
    rate_limit_window: int = 60                  # 1 minute window
    
    # Projects
    projects: Dict[str, ProjectConfig] = ...     # Map of all projects
```

---

### 3️⃣ LlamaCppClient - LLM Connection

**File:** `llamacpp_mqtt_deploy.py`, Lines 777-850

#### Initialization

```python
class LlamaCppClient:
    """HTTP client for llama.cpp server inference using OpenAI package."""
    
    def __init__(self, config: DeploymentConfig):
        """Initialize llama.cpp client and test connection."""
        self.config = config
        self.server_url = config.server_url.rstrip('/')
        self.timeout = config.server_timeout
        
        logger.info(f"Initializing Llama.cpp client: {self.server_url}")
        
        # Create OpenAI client pointing to llama.cpp server
        self.client = OpenAI(
            base_url=self.server_url,              # e.g., http://localhost:8080
            api_key="not-needed",                  # llama.cpp doesn't need key
            timeout=self.timeout,                  # 300 seconds
            max_retries=3
        )
        
        # Test connection to server
        if not self._test_connection():
            raise RuntimeError(f"Failed to connect to {self.server_url}")
        
        logger.info("✓ OpenAI client initialized successfully")
```

#### Inference Call

```python
def generate(
    self,
    messages: List[Dict[str, str]],
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    tools: Optional[List[Dict]] = None,
    tool_choice: Optional[str] = None
) -> str:
    """Generate response using OpenAI-compatible chat completion API."""
    
    # Use config defaults if not specified
    temperature = temperature or self.config.default_temperature
    top_p = top_p or self.config.default_top_p
    max_tokens = max_tokens or self.config.default_max_tokens
    
    # Build request
    request_kwargs = {
        "model": "default",                      # Model loaded on server
        "messages": messages,                    # Conversation history
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "extra_body": {
            "enable_thinking": not self.config.skip_thinking,
            "cache_prompt": True                 # Reuse prompt tokens
        }
    }
    
    # Add tools if provided (for maze: break_wall, speed_boost, etc.)
    if tools:
        request_kwargs["tools"] = tools
        request_kwargs["tool_choice"] = tool_choice
    
    # Call llama.cpp server
    response = self.client.chat.completions.create(**request_kwargs)
    
    # Extract response
    return response.choices[0].message.content
```

---

### 4️⃣ SessionManager - Per-User Conversation State

**File:** `llamacpp_mqtt_deploy.py`, Lines 1003-1110

#### Initialization

```python
class SessionManager:
    """Manages conversation sessions with history trimming and thread-safety."""
    
    def __init__(self, config: DeploymentConfig, client: LlamaCppClient):
        """Initialize session manager."""
        self.config = config
        self.client = client
        
        # Sessions: Dict[(project_name, session_id)] → session_data
        self.sessions: Dict[Tuple[str, str], Dict] = {}
        self.session_locks: Dict[Tuple[str, str], threading.RLock] = {}
        self.global_lock = threading.RLock()
        
        # Rate limiting per session
        self.request_timestamps: Dict[Tuple[str, str], List[float]] = {}
        self.rate_limit_lock = threading.RLock()
        
        # Limit concurrent LLM calls
        self.inference_semaphore = threading.Semaphore(8)
        
        logger.info("✓ SessionManager initialized")
```

#### Create New Session

```python
def get_or_create_session(
    self,
    session_id: str,
    project_name: str,
    system_prompt: str
) -> Dict:
    """Get existing session or create a new one."""
    
    session_key = (project_name, session_id)
    
    # Check if session already exists
    if session_key in self.sessions:
        session = self.sessions[session_key]
        session["last_access"] = time.time()    # Update timestamp
        return session
    
    # Create NEW session
    session = {
        "dialog": [
            {
                "role": "system",
                "content": system_prompt            # e.g., "You are guiding a maze..."
            }
        ],
        "project": project_name,
        "session_id": session_id,
        "created_at": time.time(),
        "last_access": time.time(),
        "message_count": 0,
        "repeat_count": 0,
        "assistant_repeat_count": 0
    }
    
    # Store session
    self.sessions[session_key] = session
    self.session_locks[session_key] = threading.RLock()
    
    logger.info(f"✓ Created new session: {project_name}/{session_id[:16]}...")
    
    return session
```

**Session Structure:**
```python
# After creation:
session = {
    "dialog": [
        {"role": "system", "content": "You are a maze guide..."},
        # More messages added as game progresses
    ],
    "project": "maze",
    "session_id": "session-abc123",
    "created_at": 1699275800.123,
    "last_access": 1699275800.123,
    "message_count": 0,
    "repeat_count": 0,
    "assistant_repeat_count": 0
}
```

---

### 5️⃣ MessageProcessor - Queue & Dispatch

**File:** `llamacpp_mqtt_deploy.py`, Lines 1373-1430

#### Initialization

```python
class MessageProcessor:
    """Processes queued messages."""
    
    def __init__(
        self,
        config: DeploymentConfig,
        session_manager: SessionManager,
        mqtt_client: mqtt.Client
    ):
        """Initialize message processor."""
        self.config = config
        self.session_manager = session_manager
        self.mqtt_client = mqtt_client
        
        # Main processing queue (priority, timestamp, message)
        self.message_queue = queue.PriorityQueue(maxsize=config.max_queue_size)
        
        # Response publishing queue (non-blocking)
        self.publish_queue = queue.Queue()
        
        # Statistics
        self.stats = {
            "processed": 0,
            "errors": 0,
            "rejected": 0,
            "total_latency": 0.0
        }
        
        logger.info("✓ MessageProcessor initialized")
```

#### Processing Loop

```python
def process_loop(self):
    """Main processing loop for a worker thread."""
    while self.running:
        try:
            # Get next message from queue (blocks if empty)
            priority, timestamp, msg = self.message_queue.get(timeout=1)
            
            # Process this message
            self._process_single_message(msg)
            
        except queue.Empty:
            continue  # No messages, loop again
        except Exception as e:
            logger.error(f"Error in process loop: {e}")
```

#### Process Single Message

```python
def _process_single_message(self, msg: QueuedMessage):
    """Process a single message through SessionManager and LLM."""
    try:
        # Determine system prompt
        if msg.custom_system_prompt:
            system_prompt = msg.custom_system_prompt
        else:
            project_config = self.config.projects.get(msg.project_name)
            system_prompt = project_config.system_prompt if project_config else "You are helpful"
        
        # Process message (creates/retrieves session, calls LLM)
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
        
        # Queue response for publishing back to MQTT
        self.publish_queue.put((msg.response_topic, response), block=False)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
```

---

### 6️⃣ MQTTHandler - Message Reception & Routing

**File:** `llamacpp_mqtt_deploy.py`, Lines 1458-1850

#### Initialization

```python
class MQTTHandler:
    """Handles MQTT communication and message routing."""
    
    def __init__(
        self,
        config: DeploymentConfig,
        message_processor: MessageProcessor
    ):
        """Initialize MQTT handler and connect to broker."""
        self.config = config
        self.message_processor = message_processor
        
        # Create MQTT client
        self.client_id = f"llamacpp-deploy-{uuid.uuid4().hex[:8]}"
        self.client = mqtt.Client(
            client_id=self.client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        
        # Set authentication
        if config.mqtt_username and config.mqtt_password:
            self.client.username_pw_set(
                config.mqtt_username,      # "TangClinic"
                config.mqtt_password       # "Tang123"
            )
        
        # Set MQTT callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        logger.info("✓ MQTTHandler initialized")
```

#### Connect to Broker

```python
def connect(self):
    """Connect to MQTT broker."""
    logger.info(f"Connecting to MQTT broker: {self.config.mqtt_broker}:{self.config.mqtt_port}")
    
    self.client.connect(
        self.config.mqtt_broker,           # "47.89.252.2"
        self.config.mqtt_port,             # 1883
        keepalive=60
    )
    
    logger.info("✓ Connected to MQTT broker")
```

#### On Connect - Subscribe to Topics

```python
def _on_connect(self, client, userdata, flags, rc, properties=None):
    """Callback when MQTT connects - subscribe to project topics."""
    if rc == 0:
        logger.info("✓ Connected to MQTT broker")
        
        # Subscribe to ALL enabled projects
        for project_name, config in self.config.projects.items():
            if not config.enabled:
                continue
            
            # Subscribe to user input topic
            topics_to_subscribe = [
                (config.user_topic, 1),          # e.g., ("maze/user_input", QoS=1)
                (config.state_topic or "", 1),   # e.g., ("maze/state", QoS=1)
                (config.template_topic or "", 1) # e.g., ("maze/template", QoS=1)
            ]
            
            for topic, qos in topics_to_subscribe:
                if topic:
                    client.subscribe(topic, qos=qos)
                    logger.info(f"✓ Subscribed to: {topic}")
    else:
        logger.error(f"Failed to connect, return code {rc}")
```

---

## 🔄 Complete Initialization Flow (After "Publish & Start")

### Step 1: Game State Published

**Frontend sends via MQTT:**
```json
Topic: maze/state
{
  "session_id": "session-abc123",
  "template_id": 5,
  "state": {
    "grid": [[0,1,0], [0,0,1], [1,0,0]],
    "player": {"x": 1, "y": 1},
    "exit": {"x": 2, "y": 2},
    "oxy": [{"x": 0, "y": 0}],
    "germs": [{"pos": {"x": 2, "y": 1}}]
  }
}
```

### Step 2: MQTT Handler Receives

```python
def _on_message(self, client, userdata, msg):
    """MQTT callback - received a message on subscribed topic."""
    
    topic = msg.topic                      # "maze/state"
    payload_text = msg.payload.decode()    # JSON string
    
    # Parse payload
    payload = json.loads(payload_text)
    
    # Extract key information
    session_id = payload.get("session_id")  # "session-abc123"
    project_name = self._find_project_for_topic(topic)  # "maze"
    state = payload.get("state")           # Game state dict
    
    # Convert state to user message
    user_message = self._convert_state_to_message(state, project_name)
    # Result: "Player at (1,1), exit at (2,2), 1 oxygen, 1 germ..."
    
    # Queue for processing
    msg_to_queue = QueuedMessage(
        session_id=session_id,
        project_name=project_name,
        user_message=user_message,
        response_topic="maze/hint/session-abc123",
        client_id=None,
        priority=0,
        timestamp=time.time()
    )
    
    self.message_processor.enqueue(msg_to_queue)
```

### Step 3: MessageProcessor Queues It

```python
def enqueue(self, message: QueuedMessage):
    """Add message to processing queue."""
    self.message_queue.put(
        (message.priority, message.timestamp, message),
        block=False
    )
    logger.debug(f"Enqueued message from {message.session_id}")
```

### Step 4: Worker Thread Processes

```python
# In worker thread:
def process_loop(self):
    while self.running:
        priority, timestamp, msg = self.message_queue.get(timeout=1)
        
        # Get system prompt for this project
        project_config = self.config.projects["maze"]
        system_prompt = project_config.system_prompt
        # "You are a LAM guiding players through a maze..."
        
        # THIS IS WHERE SESSION IS INITIALIZED!
        response = self.session_manager.process_message(
            session_id="session-abc123",
            project_name="maze",
            system_prompt=system_prompt,
            user_message="Player at (1,1), exit at (2,2)...",
            temperature=1.0,
            top_p=0.9,
            max_tokens=256,
            client_id=None
        )
```

### Step 5: SessionManager Creates/Gets Session

```python
def process_message(
    self,
    session_id: str,
    project_name: str,
    system_prompt: str,
    user_message: str,
    **kwargs
) -> str:
    """Process user message through session and LLM."""
    
    # 1. CREATE OR RETRIEVE SESSION
    session = self.get_or_create_session(
        session_id="session-abc123",
        project_name="maze",
        system_prompt="You are a LAM guiding..."
    )
    
    # Session now contains:
    # {
    #     "dialog": [{"role": "system", "content": "You are..."}],
    #     "project": "maze",
    #     "session_id": "session-abc123",
    #     "created_at": 1699275800.123,
    #     "message_count": 0
    # }
    
    # 2. ADD USER MESSAGE TO DIALOG
    session["dialog"].append({
        "role": "user",
        "content": "Player at (1,1), exit at (2,2), 1 oxygen, 1 germ nearby"
    })
    session["message_count"] += 1
    
    # 3. TRIM HISTORY (keep last 6 messages max)
    if len(session["dialog"]) > 6:
        # Remove oldest non-system messages
        session["dialog"] = [session["dialog"][0]] + session["dialog"][-5:]
    
    # 4. PREPARE MESSAGES FOR LLM
    messages = [
        {"role": "system", "content": "You are a LAM guiding players..."},
        {"role": "user", "content": "Player at (1,1), exit at (2,2)..."}
    ]
    
    # 5. CALL LLM WITH TOOLS
    response = self.client.generate(
        messages=messages,
        temperature=1.0,
        top_p=0.9,
        max_tokens=256,
        tools=MAZE_ACTION_TOOLS,  # break_wall, speed_boost, etc.
        tool_choice="auto"         # Let LAM choose which tool to use
    )
    
    # 6. ADD RESPONSE TO SESSION HISTORY
    session["dialog"].append({
        "role": "assistant",
        "content": response
    })
    
    # Response might be:
    # "The path is blocked. Breaking wall at (2,2) and boosting player speed."
    
    return response
```

### Step 6: LlamaCppClient Generates Response

```python
def generate(
    self,
    messages: List[Dict],
    temperature: float = 1.0,
    top_p: float = 0.9,
    max_tokens: int = 256,
    tools: List[Dict] = MAZE_ACTION_TOOLS,
    tool_choice: str = "auto"
) -> str:
    """Call llama.cpp server and get response."""
    
    # Build request to server
    request_kwargs = {
        "model": "default",                # Model running on server
        "messages": [
            {"role": "system", "content": "You are a LAM..."},
            {"role": "user", "content": "Player at (1,1)..."}
        ],
        "temperature": 1.0,
        "top_p": 0.9,
        "max_tokens": 256,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "break_wall",
                    "description": "Break a wall at coordinates..."
                }
            },
            # ... more tools
        ],
        "tool_choice": "auto"              # Model picks best action
    }
    
    # CALL LLAMA.CPP SERVER (HTTP POST)
    response = self.client.chat.completions.create(**request_kwargs)
    
    # Server returns (with tool call):
    # {
    #     "choices": [{
    #         "message": {
    #             "content": "Breaking wall to create passage...",
    #             "tool_calls": [{
    #                 "function": {
    #                     "name": "break_wall",
    #                     "arguments": "{\"x\": 2, \"y\": 2}"
    #                 }
    #             }]
    #         }
    #     }]
    # }
    
    # Convert tool calls to JSON format frontend expects
    if response.choices[0].message.tool_calls:
        # Build hint with actions
        hint_json = {
            "hint": "Breaking wall to create passage...",
            "break_wall": {"x": 2, "y": 2},
            "show_path": True
        }
        return json.dumps(hint_json)
    
    return response.choices[0].message.content
```

---

## 📊 Session Data Structure Over Time

### Initial State (Session Created)
```python
session = {
    "dialog": [
        {"role": "system", "content": "You are a LAM..."}
    ],
    "project": "maze",
    "session_id": "session-abc123",
    "created_at": 1699275800.123,
    "message_count": 0
}
```

### After First User Message
```python
session = {
    "dialog": [
        {"role": "system", "content": "You are a LAM..."},
        {"role": "user", "content": "Player at (1,1), exit at (2,2)..."}
    ],
    "project": "maze",
    "session_id": "session-abc123",
    "created_at": 1699275800.123,
    "message_count": 1
}
```

### After LAM Response
```python
session = {
    "dialog": [
        {"role": "system", "content": "You are a LAM..."},
        {"role": "user", "content": "Player at (1,1)..."},
        {"role": "assistant", "content": "Breaking wall at (2,2)..."}
    ],
    "project": "maze",
    "session_id": "session-abc123",
    "created_at": 1699275800.123,
    "message_count": 2
}
```

### After Multiple Exchanges (With History Trimming)
```python
session = {
    "dialog": [
        {"role": "system", "content": "You are a LAM..."},
        # Oldest messages removed to save tokens
        {"role": "user", "content": "Player at (5,5), near exit..."},
        {"role": "assistant", "content": "Almost there!..."},
        {"role": "user", "content": "Player hit germ!..."},
        {"role": "assistant", "content": "Freezing germs..."}
    ],
    "project": "maze",
    "session_id": "session-abc123",
    "message_count": 10
}
```

---

## 🔌 Tool Integration (For Maze)

### Available Tools

```python
MAZE_ACTION_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "break_wall",
            "description": "Break a wall at specified coordinates"
        }
    },
    {
        "type": "function",
        "function": {
            "name": "speed_boost",
            "description": "Give player temporary speed boost"
        }
    },
    {
        "type": "function",
        "function": {
            "name": "freeze_germs",
            "description": "Freeze germs for a duration"
        }
    },
    # ... more tools
]
```

### LAM Uses Tools

```
Frontend publishes state
      ↓
LAM receives state + tools available
      ↓
LAM chooses: "I should break the wall at (2,2)"
      ↓
Response contains: {"break_wall": {"x": 2, "y": 2}}
      ↓
Frontend applies: Breaks wall, game continues
```

---

## 🎯 Key Initialization Parameters

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `session_id` | "session-abc123" | Unique session identifier |
| `project_name` | "maze" | Which project (maze, driving, etc.) |
| `system_prompt` | "You are a LAM..." | Defines LAM behavior |
| `temperature` | 1.0 | Randomness of response |
| `top_p` | 0.9 | Diversity of response |
| `max_tokens` | 256 | Max response length |
| `tools` | MAZE_ACTION_TOOLS | Available actions for LAM |
| `tool_choice` | "auto" | Let LAM choose which tool |

---

## ⚙️ Configuration Hierarchy

```
DeploymentConfig (Global)
├─ mqtt_broker: "47.89.252.2"
├─ server_url: "http://localhost:8080"
├─ default_temperature: 1.0
└─ projects: Dict[str, ProjectConfig]
    ├─ "maze" → ProjectConfig
    │   ├─ name: "maze"
    │   ├─ user_topic: "maze/user_input"
    │   ├─ response_topic: "maze/response"
    │   ├─ system_prompt: "You are a LAM..."
    │   ├─ tools: MAZE_ACTION_TOOLS
    │   └─ tool_choice: "auto"
    │
    └─ "driving" → ProjectConfig
        ├─ name: "driving"
        ├─ user_topic: "driving/user_input"
        ├─ response_topic: "driving/response"
        ├─ system_prompt: "You are Cap..."
        └─ tools: None
```

---

## 📋 Initialization Checklist

```
✅ 1. ProjectConfig defined (system_prompt, tools, topics)
✅ 2. DeploymentConfig created with all projects
✅ 3. LlamaCppClient initialized (connects to server)
✅ 4. SessionManager initialized (manages conversation state)
✅ 5. MessageProcessor initialized (queue + workers)
✅ 6. MQTTHandler initialized (MQTT connection)
✅ 7. Worker threads started (N threads for parallel processing)
✅ 8. MQTT subscribed to project topics
✅ 9. Waiting for incoming messages

When message arrives:
✅ 10. MQTT callback triggered
✅ 11. Message queued to MessageProcessor
✅ 12. Worker thread picks up message
✅ 13. SessionManager.get_or_create_session() - CREATE SESSION
✅ 14. Add user message to session.dialog
✅ 15. Call LlamaCppClient.generate() with session messages
✅ 16. LAM generates response
✅ 17. Add response to session.dialog
✅ 18. Publish response back via MQTT
✅ 19. Keep session in memory for next exchange
```

---

## 🔍 Debug: Checking Session Creation

```python
# In main() after initialization:

# View all active sessions
print("Active sessions:", session_manager.sessions.keys())
# Output: dict_keys([('maze', 'session-abc123'), ('maze', 'session-def456')])

# View a specific session
session = session_manager.sessions.get(('maze', 'session-abc123'))
print("Session dialog history:")
for msg in session['dialog']:
    print(f"  {msg['role']}: {msg['content'][:50]}...")

print("Message count:", session['message_count'])
print("Created at:", session['created_at'])
print("Last access:", session['last_access'])
```

---

## 📚 File References

| Component | File | Lines |
|-----------|------|-------|
| ProjectConfig | llamacpp_mqtt_deploy.py | 46-63 |
| DeploymentConfig | llamacpp_mqtt_deploy.py | 66-94 |
| LlamaCppClient.__init__() | llamacpp_mqtt_deploy.py | 799-820 |
| LlamaCppClient.generate() | llamacpp_mqtt_deploy.py | 867-950 |
| SessionManager.__init__() | llamacpp_mqtt_deploy.py | 1008-1035 |
| SessionManager.get_or_create_session() | llamacpp_mqtt_deploy.py | 1037-1080 |
| SessionManager.process_message() | llamacpp_mqtt_deploy.py | 1082-1160 |
| MessageProcessor.__init__() | llamacpp_mqtt_deploy.py | 1380-1410 |
| MessageProcessor.process_loop() | llamacpp_mqtt_deploy.py | 1424-1442 |
| MQTTHandler.__init__() | llamacpp_mqtt_deploy.py | 1463-1495 |
| MQTTHandler._on_connect() | llamacpp_mqtt_deploy.py | 1502-1530 |
| MQTTHandler._on_message() | llamacpp_mqtt_deploy.py | 1550-1850 |

---

## 💡 Summary

**After clicking "Publish & Start":**

1. **Config**: ProjectConfig + DeploymentConfig define behavior
2. **Client**: LlamaCppClient connects to llama.cpp server
3. **Session**: SessionManager creates new session for each game
4. **Queue**: MessageProcessor queues incoming MQTT messages
5. **Handler**: MQTTHandler receives and routes messages
6. **Process**: Worker threads process from queue
7. **LLM**: LlamaCppClient generates hints with tools
8. **Store**: Session maintains dialog history
9. **Respond**: Response published back via MQTT
10. **Repeat**: Session reused for subsequent state updates

All thread-safe with locks, rate limiting, and graceful error handling! ✨

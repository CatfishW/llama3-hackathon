# LAM Initialization - Quick Reference Cheat Sheet

## 🎯 5-Second Pitch

**After "Publish & Start":**
1. Frontend publishes game state via MQTT
2. MQTTHandler receives and queues message
3. Worker thread processes
4. SessionManager creates NEW session with system prompt
5. LlamaCppClient calls llama.cpp for inference
6. Response published back
7. **Session persists in memory** for future exchanges

---

## 📋 Configuration Classes

### ProjectConfig (Per-Game)
```python
@dataclass
class ProjectConfig:
    name: str                    # "maze"
    user_topic: str              # MQTT input
    response_topic: str          # MQTT output
    system_prompt: str           # Behavior definition
    state_topic: Optional[str]   # Game state topic
    hint_topic: Optional[str]    # Hint response topic
    tools: Optional[List[Dict]]  # Actions available
    tool_choice: Optional[str]   # "auto" = let LAM choose
```

### DeploymentConfig (Global)
```python
@dataclass
class DeploymentConfig:
    mqtt_broker: str                # "47.89.252.2"
    mqtt_port: int                  # 1883
    server_url: str                 # "http://localhost:8080"
    default_temperature: float      # 1.0 (randomness)
    default_top_p: float           # 0.9 (diversity)
    default_max_tokens: int        # 256 (length)
    max_concurrent_sessions: int   # 100
    num_worker_threads: int        # 12
    projects: Dict[str, ProjectConfig]  # All games
```

---

## 🔌 Main Classes

### LlamaCppClient
```python
class LlamaCppClient:
    def __init__(config):
        # Connect to llama.cpp via OpenAI SDK
        self.client = OpenAI(base_url=config.server_url)
        
    def generate(messages, tools, tool_choice):
        # Call llama.cpp server and return response
        response = self.client.chat.completions.create(...)
        return response.choices[0].message.content
```

### SessionManager
```python
class SessionManager:
    def get_or_create_session(session_id, project_name, system_prompt):
        # Get existing or CREATE NEW session
        session = {
            "dialog": [{"role": "system", "content": system_prompt}],
            "project": project_name,
            "session_id": session_id,
            "message_count": 0
        }
        return session
    
    def process_message(session_id, project_name, system_prompt, user_message):
        # 1. Get/create session
        # 2. Add user message
        # 3. Call LLM
        # 4. Add response to session
        # 5. Return response
```

### MessageProcessor
```python
class MessageProcessor:
    def __init__(config, session_manager):
        self.message_queue = PriorityQueue(maxsize=1000)
        
    def enqueue(message):
        self.message_queue.put((priority, timestamp, message))
        
    def process_loop():  # Runs in worker thread
        while running:
            priority, timestamp, msg = message_queue.get()
            self._process_single_message(msg)
```

### MQTTHandler
```python
class MQTTHandler:
    def __init__(config, message_processor):
        self.client = mqtt.Client()
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        
    def _on_connect():
        # Subscribe to all project topics
        
    def _on_message():
        # Extract session_id, project_name, user_message
        # Queue to MessageProcessor
```

---

## 🔄 Complete Message Flow

```
1. Frontend publishes:
   Topic: "maze/state"
   Payload: {"session_id": "abc", "state": {...}}
   ↓

2. MQTTHandler receives via on_message()
   - Extracts: session_id, project_name, state
   - Converts state to: "Player at (1,1), exit (2,2)..."
   ↓

3. MessageProcessor.enqueue(QueuedMessage)
   - Priority queue stores message
   ↓

4. Worker thread calls: _process_single_message()
   - Determines system_prompt from ProjectConfig
   - Calls: SessionManager.process_message()
   ↓

5. SessionManager.process_message() MAIN FLOW:
   a. get_or_create_session() → SESSION CREATED ✓
   b. Add user message to session["dialog"]
   c. Trim history if > 6 messages
   d. Call: LlamaCppClient.generate()
   e. Add response to session["dialog"]
   f. Return response
   ↓

6. LlamaCppClient.generate():
   - POST to: http://localhost:8080/v1/chat/completions
   - Body includes: messages, temperature, top_p, tools
   - Server processes (~2-3 seconds)
   - Returns: response with possible tool calls
   ↓

7. Response published back:
   Topic: "maze/hint/abc"
   Payload: response JSON with hint + actions
   ↓

8. Frontend receives and displays hint ✓
```

---

## 📊 Session Lifecycle

### Creation
```python
# When first state published for session_id
session = {
    "dialog": [{"role": "system", "content": system_prompt}],
    "project": "maze",
    "session_id": "session-abc123",
    "created_at": 1699275800.123,
    "message_count": 0
}
```

### First Message
```python
session["dialog"].append({
    "role": "user",
    "content": "Player at (1,1)..."
})
```

### After LLM Response
```python
session["dialog"].append({
    "role": "assistant",
    "content": "Breaking wall at (2,2)..."
})
```

### Persists Until
- Game ends and session cleared, OR
- Auto-deleted after 3600 seconds (1 hour), OR
- Manual delete request via MQTT

---

## 🛠️ Key Parameters

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `max_concurrent_sessions` | 100 | Max sessions in memory |
| `session_timeout` | 3600s | Auto-delete after 1 hour |
| `num_worker_threads` | 12 | Parallel message processing |
| `default_temperature` | 1.0 | Response randomness |
| `default_max_tokens` | 256 | Max response length |
| `inference_semaphore` | 8 | Max concurrent LLM calls |
| `message_queue_size` | 1000 | Max queued messages |

---

## 📝 System Prompt Example (Maze)

```
You are a LAM guiding players through a maze.

Analyze the current game state:
- Player position
- Goal position
- Obstacles and walls
- Oxygen level
- Germ threats

Provide strategic suggestions and action recommendations.
Use available tools: break_wall, speed_boost, freeze_germs.

Always respond in JSON format with:
{
    "hint": "Strategic suggestion",
    "action": "Recommended tool",
    "parameters": {...}
}
```

---

## 🎬 Initialization Sequence Diagram

```
TIME     EVENT
────────────────────────────────────────────
T=0      User clicks "Publish & Start"
T=5      Frontend publishes state via MQTT
T=10     MQTT Handler receives on_message()
T=15     Message queued to MessageProcessor
T=20     Worker thread picks up message
T=25     SessionManager.get_or_create_session()
         → NEW SESSION CREATED ✓
T=30     System prompt loaded into dialog
T=35     User message added to dialog
T=40     LlamaCppClient.generate() called
         (HTTP POST to llama.cpp server)
T=40-2600  Server processing (~2560ms)
T=2600   Response received from server
T=2610   Response added to dialog
T=2620   Response published via MQTT
T=2625   Frontend receives and displays

TOTAL: ~2.6 seconds
```

---

## 🔐 Thread Safety

### Per-Session Lock
```python
session_locks[(project, session_id)] = RLock()

# When processing:
with session_lock:
    session["dialog"].append(user_msg)
    # Safe: other threads can't modify simultaneously
```

### Message Queue (Thread-Safe)
```python
self.message_queue = PriorityQueue()  # Built-in thread-safe

# Thread 1: Enqueue
message_queue.put((priority, timestamp, msg))

# Thread 2-12: Dequeue
priority, timestamp, msg = message_queue.get()
```

---

## ⚠️ Rate Limiting

### Per-Session Sliding Window
```python
# Track request timestamps (last 60 seconds)
request_timestamps[(project, session_id)] = [t1, t2, t3, ...]

# Check limit
if len(timestamps) > max_requests_per_session:
    REJECT  # Too many requests
else:
    ALLOW
    timestamps.append(current_time)
```

### Inference Semaphore
```python
inference_semaphore = Semaphore(8)  # Max 8 parallel

# During generate():
with inference_semaphore:
    response = llm.generate(...)  # Only 8 at a time
```

---

## 🔍 Monitoring & Debugging

### Check Active Sessions
```python
# View all sessions
sessions = session_manager.sessions
print(f"Active: {len(sessions)}")
# Output: Active: 5

# View specific session
session = sessions.get(("maze", "session-abc"))
print(f"Messages: {session['message_count']}")
print(f"Created: {session['created_at']}")

# View dialog history
for msg in session["dialog"]:
    print(f"{msg['role']}: {msg['content'][:50]}")
```

### Check Processing Stats
```python
stats = message_processor.get_stats()
print(f"Processed: {stats['processed']}")
print(f"Errors: {stats['errors']}")
print(f"Avg latency: {stats['total_latency'] / stats['processed']}ms")
```

### Check Queue Status
```python
queue_size = message_processor.message_queue.qsize()
print(f"Pending messages: {queue_size}")
# If consistently high: add more worker threads
```

---

## 🚀 Performance Tuning

### If Response Slow:
```
Issue: Latency > 3 seconds (excluding LLM inference)
Solution: Add more worker threads
    num_worker_threads = 24  (instead of 12)
```

### If Many Sessions:
```
Issue: High memory usage
Solution: Lower session_timeout
    session_timeout = 1800  (30 minutes instead of 1 hour)
    OR increase max_concurrent_sessions eviction
```

### If LLM Overloaded:
```
Issue: Request queue filling up
Solution: Increase inference semaphore
    inference_semaphore = Semaphore(16)  (instead of 8)
    OR add more llama.cpp servers (load balance)
```

### If Messages Piling Up:
```
Issue: message_queue.qsize() constantly high
Solution:
    1. Increase message_queue_size: 5000 (instead of 1000)
    2. Add more worker threads
    3. Check if LLM server is slow
```

---

## 📦 Data Structure Summary

### Session Object
```python
{
    "dialog": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."},
        ...  # Up to 6 messages kept
    ],
    "project": "maze",
    "session_id": "session-abc123",
    "created_at": 1699275800.123,
    "last_access": 1699275801.456,
    "message_count": 3,
    "repeat_count": 0,
    "assistant_repeat_count": 0
}
```

### QueuedMessage Object
```python
{
    "session_id": "session-abc123",
    "project_name": "maze",
    "user_message": "Player at (1,1)...",
    "response_topic": "maze/hint/session-abc123",
    "temperature": 1.0,
    "top_p": 0.9,
    "max_tokens": 256,
    "client_id": None,
    "priority": 0,
    "timestamp": 1699275802.123,
    "custom_system_prompt": None
}
```

---

## 🎓 Common Patterns

### Get Session History
```python
session = sessions[("maze", "session-abc")]
history = session["dialog"]
# Use for: debugging, export, analytics
```

### Reset Session
```python
session["dialog"] = [{"role": "system", "content": system_prompt}]
session["message_count"] = 0
# Clears history but keeps session object
```

### Delete Session
```python
del sessions[("maze", "session-abc")]
del session_locks[("maze", "session-abc")]
# Completely remove session (frees memory)
```

### Add Custom System Prompt
```python
msg = QueuedMessage(..., custom_system_prompt="Custom prompt...")
# Override project default for this message only
```

---

## 📍 File References

| Component | File | Function |
|-----------|------|----------|
| ProjectConfig | llamacpp_mqtt_deploy.py | Lines 46-63 |
| DeploymentConfig | llamacpp_mqtt_deploy.py | Lines 66-94 |
| LlamaCppClient.__init__ | llamacpp_mqtt_deploy.py | Lines 799-820 |
| LlamaCppClient.generate | llamacpp_mqtt_deploy.py | Lines 867-950 |
| SessionManager.__init__ | llamacpp_mqtt_deploy.py | Lines 1008-1035 |
| SessionManager.get_or_create | llamacpp_mqtt_deploy.py | Lines 1037-1080 |
| SessionManager.process_message | llamacpp_mqtt_deploy.py | Lines 1082-1160 |
| MessageProcessor.__init__ | llamacpp_mqtt_deploy.py | Lines 1380-1410 |
| MessageProcessor.process_loop | llamacpp_mqtt_deploy.py | Lines 1424-1442 |
| MQTTHandler.__init__ | llamacpp_mqtt_deploy.py | Lines 1463-1495 |
| MQTTHandler._on_connect | llamacpp_mqtt_deploy.py | Lines 1502-1530 |
| MQTTHandler._on_message | llamacpp_mqtt_deploy.py | Lines 1550-1850 |

---

## ✅ Initialization Checklist

```
Before Game:
☐ ProjectConfig defined with system_prompt and tools
☐ DeploymentConfig set with server URLs and MQTT creds
☐ LlamaCppClient created and connected to llama.cpp
☐ SessionManager instantiated with config and client
☐ MessageProcessor created with queues
☐ MQTTHandler initialized and connected to broker
☐ 12 worker threads started
☐ MQTT subscribed to all project topics
☐ System ready for messages

After "Publish & Start":
☐ MQTT receives state message on_message()
☐ Message converted to QueuedMessage
☐ MessageProcessor.enqueue() called
☐ Worker thread wakes up and gets message
☐ SessionManager.get_or_create_session() called
☐ NEW SESSION created in memory
☐ System prompt loaded into session["dialog"]
☐ User message added to session["dialog"]
☐ LlamaCppClient.generate() called (with tools)
☐ Response added to session["dialog"]
☐ Response published back to MQTT
☐ Frontend displays hint
☐ Session persists for next state update

Ongoing:
☐ More state updates reuse same session
☐ Dialog history maintained and trimmed
☐ Each response uses full conversation context
☐ Rate limiting prevents abuse
☐ Inference semaphore limits concurrency
```

---

## 💡 Pro Tips

1. **System Prompt is Key**: Good system prompt = good LAM behavior
2. **Tools Matter**: Available tools determine what LAM can suggest
3. **History Trimming**: Keeps costs down (fewer tokens to process)
4. **Thread-Safe**: Don't access sessions directly; use SessionManager
5. **Monitor Queues**: If qsize() high, add more workers
6. **Session Persistence**: Same session for entire game (context matters!)
7. **Rate Limit**: Prevents spam from bad actors
8. **Inference Semaphore**: Prevents llama.cpp server overload

---

## 🎯 Summary

**ProjectConfig** + **DeploymentConfig** define everything
         ↓
**LlamaCppClient** connects to llama.cpp server
         ↓
**SessionManager** creates and manages sessions
         ↓
**MessageProcessor** queues and dispatches
         ↓
**MQTTHandler** connects to MQTT broker
         ↓
User publishes state → Session created → LLM generates → Response published

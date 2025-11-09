# Simplified Backend Code for Slides

## 📋 Quick Overview

**3 Main Components:**
1. **HTTP Endpoints** - Frontend sends requests
2. **MQTT Publisher** - Backend publishes to message broker
3. **MQTT Handler** - Backend receives hints from LAM

---

## 🚀 Component 1: HTTP Endpoints

### File: `backend/app/routers/mqtt_bridge.py`

All HTTP endpoints the frontend calls. Think of them as "API gates" between frontend and MQTT.

---

### ✉️ Endpoint 1: Publish Template

**What it does**: Frontend says "use this template" → Backend sends to LAM

```python
@router.post("/api/mqtt/publish_template")
async def publish_template_endpoint(payload: dict, db: Session, user: User):
    """
    Receives: template_id
    Actions: 1. Get template from DB
             2. Validate user owns it
             3. Publish to MQTT
    Returns: success message
    """
    template_id = payload.get("template_id")
    
    # 1. Fetch template from database
    template = db.query(Template).filter(
        Template.id == template_id,
        Template.user_id == user.id  # ← Ownership check
    ).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 2. Build message for LAM
    message = {
        "title": template.title,
        "content": template.content,
        "version": template.version
    }
    
    # 3. Publish to MQTT broker (QoS 1 = guaranteed delivery)
    mqtt.publish_template(message, qos=1)
    
    return {"status": "published", "template_id": template_id}
```

**In a Slide:**
```
┌─────────────────────────────────────┐
│ POST /api/mqtt/publish_template     │
├─────────────────────────────────────┤
│ Input:  {template_id}               │
│ 1. Fetch from DB (check ownership)  │
│ 2. Build message {title, content}   │
│ 3. Publish to MQTT (QoS 1)          │
│ Output: {status: "published"}       │
└─────────────────────────────────────┘
```

---

### 📊 Endpoint 2: Publish State

**What it does**: Frontend sends game state → Backend enriches with template → sends to LAM

```python
@router.post("/api/mqtt/publish_state")
async def publish_state_endpoint(payload: dict, db: Session, user: User):
    """
    Receives: session_id, template_id, game_state
    Actions: 1. Get template (enrichment)
             2. Combine with game state
             3. Publish to MQTT
    Returns: success
    """
    session_id = payload.get("session_id")
    template_id = payload.get("template_id")
    game_state = payload.get("state")
    
    # 1. Fetch template for context
    template = db.query(Template).filter_by(id=template_id).first()
    
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # 2. Enrich state with template
    enriched_message = {
        "session_id": session_id,
        "template": {
            "title": template.title,
            "content": template.content
        },
        "game_state": game_state,
        "timestamp": time.time()
    }
    
    # 3. Publish to MQTT (QoS 0 = fire and forget, faster)
    mqtt.publish_state(enriched_message, qos=0)
    
    return {"status": "state_published"}
```

**In a Slide:**
```
┌──────────────────────────────────┐
│ POST /api/mqtt/publish_state     │
├──────────────────────────────────┤
│ Input: {session_id, state}       │
│ 1. Fetch template from DB        │
│ 2. Combine template + state      │
│ 3. Publish to MQTT (QoS 0)       │
│ Output: {status: "published"}    │
└──────────────────────────────────┘
```

---

### 💡 Endpoint 3: Get Last Hint

**What it does**: Frontend polls → Backend returns cached hint from LAM

```python
@router.get("/api/mqtt/last_hint")
async def get_last_hint(session_id: str):
    """
    Receives: session_id (query param)
    Returns: latest hint from cache
    
    Why cache? Fast! No database query.
    """
    # Global cache: LAST_HINTS = {"session-123": {hint_data}}
    if session_id in LAST_HINTS:
        return LAST_HINTS[session_id]
    
    return {"hint": None, "timestamp": None}
```

**In a Slide:**
```
┌────────────────────────────────┐
│ GET /api/mqtt/last_hint        │
├────────────────────────────────┤
│ Query: ?session_id=session-123 │
│ Returns: LAST_HINTS[session]   │
│ (Ultra-fast, no DB query)      │
└────────────────────────────────┘
```

---

## 🔗 Component 2: MQTT Publisher

### File: `backend/app/mqtt.py` (Lines 512-532)

Functions that actually send to MQTT broker.

---

### 📤 Function 1: Publish Template

```python
def publish_template(template_payload: dict, session_id: str = None, qos: int = 1):
    """
    Send template to LAM via MQTT broker
    
    Args:
        template_payload: {title, content, version}
        session_id: optional, for per-session targeting
        qos: 1 = guaranteed delivery (important for templates!)
    """
    topic = "maze/template"
    
    # Optional: append session to topic for per-session routing
    if session_id:
        topic = f"maze/template/{session_id}"
    
    # Convert to JSON and publish
    message = json.dumps(template_payload)
    
    # MQTT publish (topic, message, QoS level)
    mqtt_client.publish(topic, message, qos=qos)
    
    print(f"✓ Published template to {topic}")
```

**In a Slide:**
```
┌────────────────────────────────┐
│ mqtt.publish_template()        │
├────────────────────────────────┤
│ Topic: "maze/template"         │
│ QoS: 1 (guaranteed)            │
│ Format: JSON                   │
│ Action: Publishes to broker    │
└────────────────────────────────┘
```

---

### 📤 Function 2: Publish State

```python
def publish_state(state_payload: dict, qos: int = 0):
    """
    Send game state to LAM via MQTT broker
    
    Args:
        state_payload: {session_id, template, game_state}
        qos: 0 = fire and forget (fast!)
    """
    topic = "maze/state"
    
    # Convert to JSON
    message = json.dumps(state_payload)
    
    # MQTT publish (fire and forget)
    mqtt_client.publish(topic, message, qos=qos)
    
    print(f"✓ Published state to {topic} (QoS {qos})")
```

**In a Slide:**
```
┌────────────────────────────────┐
│ mqtt.publish_state()           │
├────────────────────────────────┤
│ Topic: "maze/state"            │
│ QoS: 0 (fire & forget)         │
│ Format: JSON                   │
│ Action: Fast publish           │
└────────────────────────────────┘
```

---

## 📥 Component 3: MQTT Message Handler

### File: `backend/app/mqtt.py` (Lines 129-175)

Receives messages from LAM. Handles incoming hints.

---

### 🎯 Function 1: Main MQTT Callback

```python
def _on_message(client, userdata, msg):
    """
    MQTT calls this when a message arrives
    Routes to appropriate handler based on topic
    """
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    # Route based on topic
    if "hint" in topic:
        _handle_hint_message(topic, payload)
    elif "response" in topic:
        _handle_response_message(topic, payload)
    else:
        print(f"Unknown topic: {topic}")
```

**In a Slide:**
```
┌─────────────────────────────┐
│ _on_message() Callback      │
├─────────────────────────────┤
│ Triggered: When MQTT msg    │
│ Routes: By topic name       │
│   → "hint" → handle_hint()  │
│   → "response" → handle...  │
└─────────────────────────────┘
```

---

### 💡 Function 2: Handle Hint Message

```python
def _handle_hint_message(topic, payload_text):
    """
    LAM sent a hint! Store it for frontend polling.
    
    Flow: MQTT Message → Parse → Add timestamp → Cache
    """
    try:
        # 1. Parse JSON
        data = json.loads(payload_text)
        
        # 2. Add timestamp (for duplicate detection)
        data["timestamp"] = time.time()
        
        # 3. Extract session ID from topic
        # Topic format: "maze/hint/{session_id}"
        session_id = topic.split("/")[-1]
        
        # 4. Store in global cache (FAST!)
        LAST_HINTS[session_id] = data
        
        print(f"✓ Stored hint for session {session_id}")
        
        # 5. Optional: Notify WebSocket subscribers
        notify_subscribers(session_id, data)
        
    except json.JSONDecodeError:
        print(f"✗ Failed to parse hint: {payload_text}")
```

**In a Slide:**
```
┌──────────────────────────────┐
│ _handle_hint_message()       │
├──────────────────────────────┤
│ 1. Parse JSON from MQTT      │
│ 2. Add timestamp             │
│ 3. Extract session_id        │
│ 4. Store in LAST_HINTS cache │
│ 5. Notify subscribers        │
└──────────────────────────────┘
```

---

## 🌍 Global State: LAST_HINTS Cache

### File: `backend/app/mqtt.py` (Line 36)

```python
# Global dictionary: stores latest hint for each session
LAST_HINTS: Dict[str, dict] = {}

# Example structure:
# LAST_HINTS = {
#     "session-abc123": {
#         "hint": "Path blocked, use BFS",
#         "path": [[1,2], [2,2], [3,3]],
#         "breaks": 2,
#         "timestamp": 1699275829.123
#     },
#     "session-def456": {
#         "hint": "Germ approaching!",
#         ...
#     }
# }
```

**Why?**
- ⚡ **Fast**: No database query
- 📱 **Frontend-friendly**: Simple HTTP GET
- 🎯 **Per-session**: Each game has its own hint
- ⏱️ **Timestamped**: Prevents duplicate processing

**In a Slide:**
```
┌──────────────────────────────────┐
│ LAST_HINTS Global Cache          │
├──────────────────────────────────┤
│ {                                │
│   "session-abc": {               │
│     "hint": "...",               │
│     "path": [...],               │
│     "timestamp": 1699275829      │
│   }                              │
│ }                                │
│                                  │
│ Updated: When MQTT hint arrives  │
│ Read: Frontend polls every 500ms │
└──────────────────────────────────┘
```

---

## 🔄 Complete Request-Response Flow (Simplified)

### Timeline of One Complete Cycle

```
T+0s   Frontend publishes state
       │
       ├─ POST /api/mqtt/publish_state
       │   ├─ Backend fetches template from DB
       │   ├─ Enriches state
       │   └─ Calls mqtt.publish_state()
       │
T+0s   MQTT publishes to broker
       │
       └─ mqtt_client.publish("maze/state", state, qos=0)

T+1-2s LAM processes (LLM inference)
       │
       ├─ Receives state via MQTT
       ├─ Runs reasoning
       └─ Publishes hint

T+2s   Backend receives hint
       │
       ├─ _on_message() called
       ├─ _handle_hint_message() processes
       └─ LAST_HINTS["session-xyz"] = hint

T+2.5s Frontend polls
       │
       ├─ GET /api/mqtt/last_hint?session_id=xyz
       └─ Returns LAST_HINTS["session-xyz"]

T+2.6s Frontend applies hint
       │
       └─ Updates game state (path, breaks, etc.)
```

**In a Slide:**
```
┌─────────────────────────────────────────┐
│ REQUEST → PUBLISH → PROCESS → RESPONSE │
├─────────────────────────────────────────┤
│ 1. Frontend: POST publish_state (T+0s)  │
│ 2. Backend: mqtt.publish_state()        │
│ 3. LAM: Process (T+1-2s)                │
│ 4. MQTT: Publish hint                   │
│ 5. Backend: _handle_hint_message()      │
│ 6. Frontend: GET last_hint (T+2.5s)     │
│ 7. Frontend: Apply hint (T+2.6s)        │
│                                         │
│ Total latency: ~2.6 seconds             │
└─────────────────────────────────────────┘
```

---

## 📊 Comparison Table: QoS Levels

| Aspect | **Template (QoS 1)** | **State (QoS 0)** |
|--------|----------------------|-------------------|
| **Topic** | `maze/template` | `maze/state` |
| **Reliability** | Guaranteed delivery | Fire & forget |
| **Speed** | Slightly slower | ⚡ Faster |
| **Use case** | Prompt (important) | State (frequent) |
| **Frequency** | Once per game start | Every 3 seconds |
| **Retry** | Yes, if no ACK | No |
| **Best for** | Critical info | Real-time data |

---

## 🗂️ File Structure

```
backend/
├── app/
│   ├── routers/
│   │   └── mqtt_bridge.py        ← HTTP Endpoints (Component 1)
│   ├── mqtt.py                   ← MQTT Publisher & Handler (Components 2 & 3)
│   ├── schemas.py                ← Data structures
│   └── models.py                 ← Database models
└── main.py                        ← FastAPI app setup
```

---

## 🎯 Key Concepts (Slide Summary)

### 1️⃣ HTTP Endpoints (mqtt_bridge.py)
- **Publish Template**: Frontend → Backend → MQTT
- **Publish State**: Frontend → Backend enriches → MQTT
- **Get Last Hint**: Frontend polls → Returns from cache

### 2️⃣ MQTT Publisher (mqtt.py)
- **publish_template()**: Sends template to LAM (QoS 1)
- **publish_state()**: Sends game state to LAM (QoS 0)

### 3️⃣ MQTT Handler (mqtt.py)
- **_on_message()**: Routes incoming MQTT messages
- **_handle_hint_message()**: Parses and caches hints

### 4️⃣ Cache Strategy
- **LAST_HINTS**: Global dict, session-keyed
- **No DB queries**: Fast polling responses
- **Timestamps**: Prevent duplicate processing

---

## 💻 Code Complexity: LOW to MEDIUM

✅ **Easy to understand:**
- Linear HTTP → MQTT → Handle flow
- Standard JSON serialization
- Simple cache dict structure

⚠️ **Moderate complexity:**
- MQTT async callbacks
- Session management
- Error handling

---

## 🔗 Integration Points

```
Frontend (React)
    ↓
HTTP Client (axios)
    ↓
[mqtt_bridge.py endpoints]
    ↓
MQTT Publisher (mqtt.py)
    ↓
MQTT Broker (mosquitto)
    ↓
LAM (LLM Agent)
    ↓
MQTT Broker
    ↓
[mqtt_bridge.py handler]
    ↓
LAST_HINTS Cache
    ↓
Frontend (polls)
```

**In a Slide (Simple):**
```
┌────────────┐
│  Frontend  │
└─────┬──────┘
      │ HTTP
      ↓
┌──────────────────┐
│ HTTP Endpoints   │
└─────┬────────────┘
      │ MQTT
      ↓
┌──────────────────┐
│ MQTT Broker      │ ←→ LAM
└──────────────────┘
      ↑
      │ MQTT Callback
┌─────┴──────────────┐
│ Handle + Cache     │
└────────────────────┘
      ↑
      │ HTTP GET
      └──→ Frontend
```

---

## 🚨 Error Handling (Simplified)

```python
# Template endpoint
if not template:
    raise HTTPException(status_code=404)  # Not found

# State endpoint
if not game_state:
    raise HTTPException(status_code=400)  # Bad request

# Hint handler
try:
    data = json.loads(payload_text)
except json.JSONDecodeError:
    print(f"✗ Invalid JSON: {payload_text}")
    return  # Skip this message
```

---

## 📱 Example Data Structures

### Template Message (Published)

```json
{
  "title": "LAM Maze Challenge",
  "content": "You control a player in a maze...",
  "version": 1
}
```

### State Message (Published)

```json
{
  "session_id": "session-abc123",
  "template": {
    "title": "LAM Maze Challenge",
    "content": "..."
  },
  "game_state": {
    "grid": [[0, 1, 0], [0, 0, 1], [1, 0, 0]],
    "player": {"x": 1, "y": 1},
    "exit": {"x": 2, "y": 2},
    "oxy": [{"x": 0, "y": 0}],
    "germs": [{"pos": {"x": 2, "y": 1}, "dir": {"x": -1, "y": 0}}]
  },
  "timestamp": 1699275829.123
}
```

### Hint Message (Cached)

```json
{
  "session_id": "session-abc123",
  "hint": "Path blocked by walls - using BFS to find alternative route",
  "path": [[1, 1], [1, 2], [2, 2]],
  "breaks": 0,
  "break_walls": [],
  "show_path": true,
  "timestamp": 1699275831.456
}
```

---

## 📝 Quick Reference

### To Add a New Backend Feature

1. **New HTTP Endpoint?** → Edit `mqtt_bridge.py`
   ```python
   @router.post("/api/mqtt/your_endpoint")
   async def your_endpoint(payload, db, user):
       # Your logic here
       return {"status": "done"}
   ```

2. **New MQTT Message Type?** → Edit `mqtt.py`
   ```python
   def handle_your_message(topic, payload):
       # Your logic here
       LAST_HINTS[session_id] = data
   ```

3. **Add to callback router** → Edit `_on_message()`
   ```python
   if "your_topic" in topic:
       handle_your_message(topic, payload)
   ```

---

## 🎓 Learning Path

| Level | What to Learn | Where |
|-------|---------------|-------|
| **Beginner** | HTTP endpoints concept | mqtt_bridge.py lines 107-145 |
| **Intermediate** | MQTT publishing | mqtt.py lines 512-532 |
| **Advanced** | Message routing & caching | mqtt.py lines 129-175 |

---

## ✅ Checklist for Slides

- [ ] Show HTTP endpoints (3 main ones)
- [ ] Show MQTT publisher functions (2 main ones)
- [ ] Show MQTT handler (1 main one)
- [ ] Show LAST_HINTS cache structure
- [ ] Show request-response flow timeline
- [ ] Show QoS comparison table
- [ ] Show integration diagram
- [ ] Show example JSON structures

All code here is **simplified and slide-ready!** 🎯

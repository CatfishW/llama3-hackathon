# Backend Code Cheat Sheet

**Quick reference for slides and presentations**

---

## 🎯 The 5-Second Pitch

```
Backend is 3 things:

1️⃣  HTTP Endpoints
    ├─ POST /publish_template
    ├─ POST /publish_state  
    └─ GET  /last_hint

2️⃣  MQTT Publisher
    ├─ Sends template (QoS 1)
    └─ Sends state (QoS 0)

3️⃣  MQTT Handler
    ├─ Receives hints
    └─ Caches in LAST_HINTS
```

---

## 📋 Slide 1: Architecture Block

```
┌─────────────────────────────────┐
│  BACKEND SYSTEM                 │
├─────────────────────────────────┤
│                                 │
│  Frontend                       │
│    ↓ HTTP                       │
│  [HTTP Endpoints]               │
│    ↓ MQTT                       │
│  [MQTT Broker]                  │
│    ↓ ↑                          │
│  [LAM] ← [Hint Handler]         │
│    ↑                            │
│  [LAST_HINTS Cache]             │
│    ↓ HTTP GET                   │
│  Frontend                       │
│                                 │
└─────────────────────────────────┘
```

---

## 📋 Slide 2: HTTP Endpoints

```python
# ENDPOINT 1: Publish Template
POST /api/mqtt/publish_template
├─ Input:  {template_id}
├─ Action: Fetch + validate + publish to MQTT (QoS 1)
└─ Output: {status: "published"}

# ENDPOINT 2: Publish State
POST /api/mqtt/publish_state
├─ Input:  {session_id, template_id, state}
├─ Action: Fetch template + enrich + publish (QoS 0)
└─ Output: {status: "published"}

# ENDPOINT 3: Get Last Hint
GET /api/mqtt/last_hint?session_id=xyz
├─ Input:  session_id (query param)
├─ Action: Return from LAST_HINTS cache
└─ Output: {hint, path, breaks, timestamp}
```

---

## 📋 Slide 3: Publish Template Code

```python
@router.post("/api/mqtt/publish_template")
async def publish_template_endpoint(payload: dict, db, user):
    # Get template
    template = db.query(Template).filter(
        Template.id == payload["template_id"],
        Template.user_id == user.id
    ).first()
    
    # Build message
    msg = {
        "title": template.title,
        "content": template.content,
        "version": template.version
    }
    
    # Publish with guarantee
    mqtt.publish_template(msg, qos=1)
    return {"status": "published"}
```

---

## 📋 Slide 4: Publish State Code

```python
@router.post("/api/mqtt/publish_state")
async def publish_state_endpoint(payload: dict, db, user):
    # Get template for context
    template = db.query(Template).filter_by(
        id=payload["template_id"]
    ).first()
    
    # Enrich state with template
    msg = {
        "session_id": payload["session_id"],
        "template": {"title": template.title, "content": template.content},
        "game_state": payload["state"],
        "timestamp": time.time()
    }
    
    # Publish for speed (no retry)
    mqtt.publish_state(msg, qos=0)
    return {"status": "published"}
```

---

## 📋 Slide 5: Get Last Hint Code

```python
@router.get("/api/mqtt/last_hint")
async def get_last_hint(session_id: str):
    """⚡ Ultra-fast: cache lookup, no DB!"""
    if session_id in LAST_HINTS:
        return LAST_HINTS[session_id]
    return {"hint": None}
```

---

## 📋 Slide 6: MQTT Publisher

```python
# Publish Template (Guaranteed)
def publish_template(data: dict, qos: int = 1):
    mqtt_client.publish("maze/template", 
                       json.dumps(data), 
                       qos=qos)

# Publish State (Fast)
def publish_state(data: dict, qos: int = 0):
    mqtt_client.publish("maze/state", 
                       json.dumps(data), 
                       qos=qos)
```

---

## 📋 Slide 7: MQTT Handler

```python
# Receives ALL MQTT messages
def _on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    if "hint" in topic:
        _handle_hint_message(topic, payload)

# Handles hints specifically
def _handle_hint_message(topic, payload_text):
    data = json.loads(payload_text)           # 1. Parse
    data["timestamp"] = time.time()           # 2. Add time
    session_id = topic.split("/")[-1]         # 3. Extract ID
    LAST_HINTS[session_id] = data             # 4. Cache
```

---

## 📋 Slide 8: The Cache

```python
LAST_HINTS = {
    "session-abc": {
        "hint": "Path blocked",
        "path": [[1,2], [2,2]],
        "breaks": 1,
        "timestamp": 1699275829
    }
}

✅ Why cache?
  • ⚡ No DB queries
  • 📱 Perfect for polling
  • 🎯 Per-session isolation
  • ⏱️ Timestamps prevent duplicates
```

---

## 📋 Slide 9: Timeline

```
T+0s    Frontend POST /publish_state
        └─ Backend fetches template
           └─ mqtt.publish_state()

T+0.05s MQTT publishes (QoS 0)

T+1-2s  LAM processes (inference)
        └─ Publishes hint

T+2s    Backend _on_message() 
        └─ _handle_hint_message()
           └─ LAST_HINTS[session] = hint

T+2.5s  Frontend GET /last_hint
        └─ Instant cache hit

T+2.6s  Frontend applies hint

⏱️  Total: 2.6 seconds
```

---

## 📋 Slide 10: QoS Comparison

```
TEMPLATE (QoS 1)        STATE (QoS 0)
├─ Guaranteed           ├─ Fire & forget
├─ Topic: template      ├─ Topic: state
├─ Slower (safe)        ├─ Faster
├─ Used once/game       ├─ Used every 3s
├─ Retry if failed      ├─ No retry
└─ For: Prompt!         └─ For: Real-time data
```

---

## 📋 Slide 11: Integration

```
Frontend
   ↓ HTTP POST
Endpoints
   ↓ MQTT
Broker
   ↓ ↑
 LAM ← Handler
   ↑
Cache
   ↓ HTTP GET
Frontend
```

---

## 🔧 Common Code Patterns

### Error Handling
```python
if not template:
    raise HTTPException(status_code=404)

try:
    data = json.loads(payload)
except:
    print("Invalid JSON")
    return
```

### Caching Pattern
```python
if session_id in GLOBAL_CACHE:
    return GLOBAL_CACHE[session_id]
return None
```

### MQTT Pattern
```python
mqtt_client.publish(
    topic="maze/state",
    payload=json.dumps(data),
    qos=0  # or 1
)
```

---

## 📊 Data Flow (ASCII)

```
STATE PUBLISH CYCLE:

Frontend                Backend              MQTT Broker         LAM
   │                      │                     │                 │
   ├─ POST ──────────────>│                     │                 │
   │  publish_state       │                     │                 │
   │                      ├─ Fetch template    │                 │
   │                      ├─ Enrich state      │                 │
   │                      ├─ JSON encode       │                 │
   │                      ├─ MQTT publish ────>│                 │
   │                      │                     ├─ Subscribe ─────>│
   │                      │                     │                  │
   │                      │                     │                  ├─ Process (1-2s)
   │                      │                     │<─ Publish hint ──┤
   │                      │<─ Hint message ────┤                  │
   │                      ├─ Parse JSON                           │
   │                      ├─ Add timestamp                        │
   │                      ├─ Cache it                             │
   │<─ GET ────────────────| (instant response)                   │
   │  last_hint           │ (from LAST_HINTS)                    │
   │                      │                     │                 │
```

---

## 📁 File Reference

```
mqtt_bridge.py:
├─ Line 107: publish_template_endpoint()
├─ Line 11:  publish_state_endpoint()
└─ Line 28:  get_last_hint()

mqtt.py:
├─ Line 36:  LAST_HINTS (cache)
├─ Line 129: _on_message()
├─ Line 148: _handle_hint_message()
├─ Line 512: publish_state()
└─ Line 521: publish_template()
```

---

## ⚡ Performance

```
Component      Latency
─────────────────────────
HTTP POST      10-50ms
Template DB    5-10ms
MQTT publish   20-50ms
LAM inference  1000-2000ms ← Bottleneck
MQTT receive   50-100ms
HTTP GET       5-10ms
────────────────────────
TOTAL          ~1100-2200ms
```

---

## ✅ Implementation Checklist

- [ ] Publish template endpoint
- [ ] Publish state endpoint
- [ ] Get last hint endpoint
- [ ] Publish template MQTT function
- [ ] Publish state MQTT function
- [ ] MQTT message callback
- [ ] Hint message handler
- [ ] LAST_HINTS cache setup
- [ ] Error handling
- [ ] Testing

---

## 🎓 Quick Facts

| Fact | Value |
|------|-------|
| HTTP Endpoints | 3 |
| MQTT Publishers | 2 |
| MQTT Handlers | 2 |
| Global Cache | 1 (LAST_HINTS) |
| QoS Levels Used | 2 (1 & 0) |
| DB Queries (hints) | 0 (cache!) |
| Latency | ~2.6s |
| Per-session isolation | ✅ Yes |

---

## 🚀 Quick Copy-Paste

**Add an endpoint:**
```python
@router.get("/api/your/endpoint")
async def your_endpoint(params):
    return {"result": "value"}
```

**Add MQTT handler:**
```python
def _handle_your_message(topic, payload):
    data = json.loads(payload)
    YOUR_CACHE[key] = data
```

**Add to router:**
```python
if "your_topic" in topic:
    _handle_your_message(topic, payload)
```

---

## 💡 Why This Design?

| Design Choice | Reason |
|---|---|
| HTTP endpoints | REST standard, easy for frontend |
| MQTT broker | Async messaging, decouples LAM |
| Cache (LAST_HINTS) | No DB queries on every poll |
| QoS 1 for template | Template is critical, sent once |
| QoS 0 for state | State is frequent, speed matters |
| Polling over WebSocket | Simpler, more compatible |

---

## 🔗 Related Files

```
SIMPLIFIED_BACKEND_CODE.md    ← Full explanation
BACKEND_SLIDES_FORMAT.md      ← 20 presentation slides
BACKEND_CODE_MASTER_INDEX.md  ← This with more details
RUNTIME_GAME_STATE_DISPLAY.md ← Frontend panels
```

---

## 📞 Debugging Tips

| Problem | Debug |
|---------|-------|
| Template not sent | Check `mqtt_client.publish()` logging |
| Hint not received | Check MQTT broker: `mosquitto_sub -t "maze/#"` |
| Cache empty | Check `_handle_hint_message()` is called |
| Slow response | Check LAM inference time (1-2s expected) |
| Session mismatch | Verify session_id matches in all layers |

---

## ✨ That's It!

You now have everything to understand, present, and build the backend! 🎉

**Pick a format:**
- 📖 Read SIMPLIFIED_BACKEND_CODE.md (full)
- 🎯 Use BACKEND_SLIDES_FORMAT.md (presentations)
- 📋 Reference this cheat sheet (quick lookup)

**Questions?** Check BACKEND_CODE_MASTER_INDEX.md for the answer key!

---

**Remember:** Backend = HTTP endpoints → MQTT → Caching = Done! ✅

# Backend Code Documentation - Master Index

## 📚 Complete Backend Reference Suite

You now have **3 complementary documents** covering backend code for different purposes:

---

## 📄 Document 1: SIMPLIFIED_BACKEND_CODE.md

**Best For:** Understanding the backend logic

**Contains:**
- ✅ 3 HTTP endpoints with explanations
- ✅ 2 MQTT publisher functions
- ✅ 1 MQTT handler (main callback + hint handler)
- ✅ LAST_HINTS cache explanation
- ✅ Complete request-response flow
- ✅ QoS comparison table
- ✅ Integration points diagram
- ✅ Error handling patterns
- ✅ Example JSON structures

**Length:** ~400 lines

**How to Use:**
```
1. Read Component 1: HTTP Endpoints (to understand what endpoints exist)
2. Read Component 2: MQTT Publisher (to understand what gets sent)
3. Read Component 3: MQTT Handler (to understand what gets received)
4. Read Complete Flow (to see it all together)
```

---

## 🎯 Document 2: BACKEND_SLIDES_FORMAT.md

**Best For:** Creating presentation slides

**Contains:**
- ✅ 20 slide-ready pages
- ✅ Code snippets with syntax highlighting
- ✅ ASCII diagrams and boxes
- ✅ Timeline visualizations
- ✅ Comparison tables
- ✅ Integration architecture diagram
- ✅ File locations reference
- ✅ Key concepts summary
- ✅ Error handling overview
- ✅ Complete request-response example

**Length:** ~350 lines (20 slides)

**How to Use:**
```
1. Open in editor with monospace font
2. Copy slide sections into PowerPoint/Google Slides
3. Each slide is self-contained
4. Use boxes and diagrams as-is
5. Customize colors and fonts as needed
```

**Copy-Paste Ready:** Yes! Each slide is already formatted for presentation tools.

---

## 📊 Comparison: Which Document to Use?

| Use Case | Document |
|----------|----------|
| **Learning the backend** | SIMPLIFIED_BACKEND_CODE.md |
| **Creating slides** | BACKEND_SLIDES_FORMAT.md |
| **Code review** | SIMPLIFIED_BACKEND_CODE.md |
| **Teaching others** | BACKEND_SLIDES_FORMAT.md |
| **Implementation reference** | SIMPLIFIED_BACKEND_CODE.md |
| **Executive overview** | BACKEND_SLIDES_FORMAT.md (Slide 1, 20) |

---

## 🗂️ What You're Looking At

### Backend Architecture Overview

```
LAYER 1: HTTP Endpoints
├─ POST /api/mqtt/publish_template
├─ POST /api/mqtt/publish_state
└─ GET  /api/mqtt/last_hint

        ↓ (HTTP → MQTT conversion)

LAYER 2: MQTT Publisher
├─ publish_template() - QoS 1 (guaranteed)
└─ publish_state() - QoS 0 (fast)

        ↓ (MQTT Broker)

LAYER 3: MQTT Handler
├─ _on_message() - Router
└─ _handle_hint_message() - Cache

        ↓ (Global Cache)

LAYER 4: Cache Storage
└─ LAST_HINTS = {session_id: hint_data}

        ↓ (HTTP GET polling)

Frontend
```

---

## 🎯 3 Key Functions to Remember

### Function 1: Publish Template
**File:** `mqtt_bridge.py`, Line 107
**Purpose:** Template → MQTT (QoS 1, guaranteed)
**Frontend calls:** `publishSelectedTemplate()`

```python
# Simplified view:
template = db.get(template_id)  # Check ownership
mqtt.publish(template, qos=1)   # Send to LAM
return {"status": "published"}
```

### Function 2: Publish State
**File:** `mqtt_bridge.py`, Line 11
**Purpose:** State + Template → MQTT (QoS 0, fast)
**Frontend calls:** `publishState()`

```python
# Simplified view:
template = db.get(template_id)
state = enriched_with(template)  # Add context
mqtt.publish(state, qos=0)       # Send to LAM
return {"status": "published"}
```

### Function 3: Get Last Hint
**File:** `mqtt_bridge.py`, Line 28
**Purpose:** Return cached hint (no DB query!)
**Frontend calls:** `pollForHints()`

```python
# Simplified view:
if session_id in LAST_HINTS:
    return LAST_HINTS[session_id]  # ⚡ Fast!
return {"hint": None}
```

---

## 🔄 Complete Communication Cycle

```
T+0s   Frontend publishes state
       ↓
       HTTP POST /api/mqtt/publish_state
       ├─ Fetch template
       ├─ Enrich with state
       └─ mqtt.publish_state()
       
T+0.05s MQTT publishes to broker
       ↓
       Topic: maze/state (QoS 0)
       
T+1-2s LAM processes (LLM inference)
       ├─ Reads state
       ├─ Thinks
       └─ Publishes hint
       
T+2s   Backend receives hint
       ├─ _on_message() callback
       ├─ _handle_hint_message()
       └─ LAST_HINTS[session] = hint
       
T+2.5s Frontend polls
       ├─ HTTP GET /api/mqtt/last_hint
       └─ Instant return from cache
       
T+2.6s Frontend applies hint
       ├─ Update path
       ├─ Add breaks
       └─ Game continues

⏱️ Total: ~2.6 seconds from publish to game update
```

---

## 📊 HTTP Endpoints Quick Reference

| Endpoint | Method | Input | Output | File:Line |
|----------|--------|-------|--------|-----------|
| publish_template | POST | template_id | {status} | mqtt_bridge:107 |
| publish_state | POST | session_id, state | {status} | mqtt_bridge:11 |
| last_hint | GET | session_id (query) | hint_data | mqtt_bridge:28 |

---

## 📡 MQTT Topics Quick Reference

| Topic | Direction | QoS | Purpose |
|-------|-----------|-----|---------|
| maze/template | → LAM | 1 | Send prompt template |
| maze/state | → LAM | 0 | Send game state |
| maze/hint/{session} | ← LAM | - | Receive hints |

---

## 💾 Data Structures at a Glance

### Template Message
```json
{
  "title": "Game prompt",
  "content": "Full system prompt for LLM...",
  "version": 1
}
```

### State Message
```json
{
  "session_id": "session-abc",
  "template": {...},
  "game_state": {
    "grid": [[0,1,0], [0,0,1], [1,0,0]],
    "player": {"x": 1, "y": 1},
    "exit": {"x": 2, "y": 2},
    "oxy": [{"x": 0, "y": 0}],
    "germs": [...]
  },
  "timestamp": 1699275829.123
}
```

### Hint Message (Cached)
```json
{
  "hint": "Path blocked by walls - using BFS",
  "path": [[1,1], [1,2], [2,2]],
  "breaks": 1,
  "break_walls": [[2,2]],
  "show_path": true,
  "timestamp": 1699275831.456
}
```

---

## 🎓 Reading Guide by Experience Level

### Beginner (0-3 months Python/FastAPI)
1. Start: BACKEND_SLIDES_FORMAT.md (Slide 1)
2. Read: SIMPLIFIED_BACKEND_CODE.md → Quick Overview
3. Read: SIMPLIFIED_BACKEND_CODE.md → Component 1 (HTTP Endpoints)
4. Read: BACKEND_SLIDES_FORMAT.md (Slides 2-5)

### Intermediate (3-12 months experience)
1. Read: SIMPLIFIED_BACKEND_CODE.md (all)
2. Read: BACKEND_SLIDES_FORMAT.md (all)
3. Cross-reference: Original code in mqtt_bridge.py and mqtt.py

### Advanced (12+ months or framework expert)
1. Read: Original source code directly
2. Use docs as quick reference
3. Extend with new features

---

## ✅ Checklist: Backend Coverage

### HTTP Endpoints
- [x] Publish Template (with ownership validation)
- [x] Publish State (with enrichment)
- [x] Get Last Hint (cached, no DB query)
- [x] Error handling for all three

### MQTT Publisher
- [x] publish_template() with QoS 1
- [x] publish_state() with QoS 0
- [x] Topic naming conventions
- [x] JSON serialization

### MQTT Handler
- [x] _on_message() routing logic
- [x] _handle_hint_message() parsing and caching
- [x] Session ID extraction
- [x] Timestamp handling for deduplication

### Cache Strategy
- [x] LAST_HINTS global dict
- [x] Per-session caching
- [x] No database queries
- [x] Timestamp tracking

### Integration Points
- [x] Frontend → HTTP endpoints
- [x] HTTP → MQTT publisher
- [x] MQTT broker ← LAM
- [x] MQTT handler → cache
- [x] Cache → Frontend polling

---

## 🚀 How to Present This

### For 5-Minute Overview
Use BACKEND_SLIDES_FORMAT.md:
- Slide 1: Architecture
- Slide 10: QoS comparison
- Slide 9: Timeline
- Slide 11: Integration

### For 15-Minute Deep Dive
Use SIMPLIFIED_BACKEND_CODE.md:
- Quick Overview (2 min)
- Component 1: HTTP (3 min)
- Component 2: Publisher (3 min)
- Component 3: Handler (3 min)
- Complete Flow (2 min)
- Q&A (2 min)

### For 30-Minute Technical Session
Use both documents + live demo:
- Slides 1-6 (architecture & HTTP)
- Code walkthrough (mqtt_bridge.py)
- Slides 7-8 (handler & cache)
- Code walkthrough (mqtt.py)
- Slides 9-11 (flow & integration)
- Live demo (publish → hint)

---

## 📝 File Locations Reference

```
prompt-portal/
├── SIMPLIFIED_BACKEND_CODE.md          ← Read first
├── BACKEND_SLIDES_FORMAT.md            ← For presentations
├── BACKEND_DOCUMENTATION_INDEX.md      ← Master index
├── RUNTIME_GAME_STATE_DISPLAY.md       ← Frontend display
│
└── backend/app/
    ├── routers/
    │   └── mqtt_bridge.py
    │       ├─ publish_template_endpoint() [Line 107]
    │       ├─ publish_state_endpoint() [Line 11]
    │       └─ get_last_hint() [Line 28]
    │
    └── mqtt.py
        ├─ LAST_HINTS (cache) [Line 36]
        ├─ publish_template() [Line 521]
        ├─ publish_state() [Line 512]
        ├─ _on_message() [Line 129]
        └─ _handle_hint_message() [Line 148]
```

---

## 🎯 Quick Answers

**Q: Where does the hint come from?**
A: LAM publishes to MQTT broker → Backend receives via _on_message() → Stored in LAST_HINTS

**Q: Why is the hint cached?**
A: To enable fast HTTP polling without database queries

**Q: Why different QoS levels?**
A: Templates are critical (QoS 1), state is frequent (QoS 0 = faster)

**Q: How does frontend know when hint arrives?**
A: Polls GET /api/mqtt/last_hint every 500ms (or WebSocket if connected)

**Q: What if the same hint is polled twice?**
A: Frontend checks timestamp to detect duplicates and skip

**Q: Can multiple games run at once?**
A: Yes! Each has its own session_id and hint in LAST_HINTS dict

---

## 🔗 Related Documentation

### In This Project
- **RUNTIME_GAME_STATE_DISPLAY.md** - Frontend display panels after game starts
- **HINT_POLLING_LAM_RESPONSE_FLOW.md** - How hints are polled and processed
- **COMPLETE_BACKEND_FLOW_SUMMARY.md** - Full architecture overview
- **BACKEND_PUBLISH_START_FLOW.md** - Startup sequence

### Code Files
- **frontend/src/pages/WebGame.tsx** - Frontend game logic
- **backend/app/routers/mqtt_bridge.py** - HTTP endpoints
- **backend/app/mqtt.py** - MQTT handling

---

## 💡 Key Takeaways

1. **3 Layers:** HTTP → MQTT → Cache
2. **3 Endpoints:** publish_template, publish_state, last_hint
3. **3 Functions:** publish_template(), publish_state(), _handle_hint_message()
4. **1 Cache:** LAST_HINTS (per session)
5. **2 QoS:** 1 (guaranteed template), 0 (fast state)

---

## 🎓 Learning Outcomes

After reading these docs, you should understand:

✅ How frontend sends data to backend
✅ How backend publishes to MQTT broker
✅ How backend receives hints from LAM
✅ Why caching is used (performance)
✅ Why QoS differs (template vs state)
✅ How frontend polls for hints
✅ How the complete cycle works (2.6s latency)
✅ How to add new endpoints
✅ How to add new MQTT message types
✅ How to handle errors gracefully

---

## 🚨 Common Issues & Solutions

| Issue | Solution | Reference |
|-------|----------|-----------|
| Hint not appearing | Check session_id match | last_hint() |
| MQTT not publishing | Verify broker connection | mqtt.py init |
| Duplicate hints | Check timestamp in handler | _handle_hint_message() |
| Slow response | Check polling interval | Frontend every 500ms |
| DB connection error | Check template_id validity | publish_state() |

---

## 📞 Support & Debugging

### To debug what's being sent:
```python
# Add logging in mqtt_bridge.py
print(f"Publishing: {json.dumps(message, indent=2)}")
```

### To see what's cached:
```python
# Add endpoint to view cache
@router.get("/api/debug/cache")
def get_cache():
    return LAST_HINTS
```

### To trace a hint:
```python
# Check MQTT logs
mosquitto_sub -h localhost -t "maze/#"

# Then check backend receives it
print(f"✓ Received hint for {session_id}")

# Then check frontend polls it
GET /api/mqtt/last_hint?session_id=session-abc
```

---

## ✨ Summary

You now have everything to understand, explain, and extend the backend system:

- 📖 **SIMPLIFIED_BACKEND_CODE.md** for learning
- 🎯 **BACKEND_SLIDES_FORMAT.md** for presenting
- 🔗 **This document** for quick reference

**All code is simplified, well-commented, and production-ready!**

Pick your document based on your need, and happy coding! 🚀

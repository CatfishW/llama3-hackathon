# Backend Code Snippets - Complete Documentation Index

## 📚 Overview

This folder now contains comprehensive backend documentation covering all code that executes after clicking "Publish & Start" in the Prompt Portal game startup modal. The documentation includes exact line references, code snippets, and architectural diagrams.

---

## 📖 Documents Created

### 1. **GAME_STARTUP_MODAL_SNIPPETS.md**
**Focus**: Frontend modal UI and state management
**Key Sections**:
- Modal container structure
- Mode selection (Manual/LAM)
- Template picker implementation
- Backend integration points
- Styling patterns
- Color schemes and gradients
- Usage flow and game dimensions

**Best For**: Understanding the UI before the backend processes

---

### 2. **GAME_STARTUP_MODALS_DETAILED.md**
**Focus**: In-depth JSX and styling implementation
**Key Sections**:
- Visual ASCII mockups of both screens
- Complete JSX code with inline styles
- State flow diagrams
- Styling reference (colors, spacing, effects)
- Accessibility features
- Interaction handlers
- Data structures and types
- Responsive behavior

**Best For**: Developers replicating or modifying the modal UI

---

### 3. **BACKEND_PUBLISH_START_FLOW.md** ⭐ **START HERE**
**Focus**: Immediate backend processing after clicking "Publish & Start"
**Key Sections**:
- User action flow
- `publishSelectedTemplate()` function
- `doStartGame()` function with maze generation
- Backend template endpoint
- MQTT template publishing
- Initial game state publishing
- Configuration and error handling
- Security & validation

**Timeline**: T+0s to T+2s

**Best For**: Understanding the initial startup sequence

---

### 4. **HINT_POLLING_LAM_RESPONSE_FLOW.md** ⭐ **IMPORTANT**
**Focus**: Runtime communication between frontend, backend, and LAM
**Key Sections**:
- Complete communication flow diagram
- State publishing cycle (every 3s)
- Backend MQTT message callback
- Hint message handler
- Frontend polling logic (every 500ms)
- HTTP endpoint for hint retrieval
- Hint processing and action execution
- Error handling and performance notes
- Example complete cycle

**Timeline**: T+2s onwards (continuous)

**Best For**: Understanding real-time game state updates and LAM interactions

---

### 5. **COMPLETE_BACKEND_FLOW_SUMMARY.md** ⭐ **OVERVIEW**
**Focus**: Complete end-to-end flow with all components
**Key Sections**:
- Complete execution flow (all phases)
- Full code snippets with context
- Communication diagram (detailed)
- Security & validation
- Performance characteristics
- File reference table
- Startup sequence summary
- Architectural decisions

**Best For**: Big-picture understanding of the entire system

---

## 🎯 Quick Navigation Guide

### "I want to understand..."

#### ...what happens after clicking "Publish & Start"?
→ Start with **BACKEND_PUBLISH_START_FLOW.md**

#### ...how the frontend modal works?
→ Start with **GAME_STARTUP_MODALS_DETAILED.md**

#### ...how the game gets hints from the LAM?
→ Start with **HINT_POLLING_LAM_RESPONSE_FLOW.md**

#### ...the complete architecture?
→ Start with **COMPLETE_BACKEND_FLOW_SUMMARY.md**

#### ...specific UI code?
→ Check **GAME_STARTUP_MODAL_SNIPPETS.md** or **GAME_STARTUP_MODALS_DETAILED.md**

---

## 📋 Backend API Endpoints

### Template Publishing
```
POST /api/mqtt/publish_template
Query: template_id, reset=true
File: backend/app/routers/mqtt_bridge.py (Lines 107-145)
```

### State Publishing
```
POST /api/mqtt/publish_state
File: backend/app/routers/mqtt_bridge.py (Lines 11-27)
```

### Get Last Hint
```
GET /api/mqtt/last_hint?session_id=X
File: backend/app/routers/mqtt_bridge.py (Lines 28-40)
```

### Request Hint
```
POST /api/mqtt/request_hint
File: backend/app/routers/mqtt_bridge.py (Lines 42-80)
```

### WebSocket for Hints
```
WS /api/mqtt/ws/hints/{session_id}
File: backend/app/routers/mqtt_bridge.py (Lines 82-105)
```

---

## 🔌 MQTT Topics

| Topic | Direction | QoS | Purpose |
|-------|-----------|-----|---------|
| `maze/template` | → LAM | 1 | Send prompt template |
| `maze/state` | → LAM | 0 | Send game state |
| `maze/hint/{sessionId}` | ← LAM | - | Receive hints |
| `chat/user_input` | → LAM | 1 | Chat messages |
| `chat/response/{sessionId}` | ← LAM | - | Chat responses |

---

## 📊 Key Functions & Files

### Frontend Functions

| Function | File | Lines | Purpose |
|----------|------|-------|---------|
| `publishSelectedTemplate()` | WebGame.tsx | 1097-1108 | Publish template to backend |
| `doStartGame()` | WebGame.tsx | 983-1090 | Initialize game board |
| `publishState()` | WebGame.tsx | 1141-1173 | Publish current game state |
| `pollForHints()` | WebGame.tsx | 662-760 | Poll backend for LAM hints |
| `startGame()` | WebGame.tsx | 1110-1130 | Open startup modal |

### Backend Functions

| Function | File | Lines | Purpose |
|----------|------|-------|---------|
| `publish_template_endpoint()` | mqtt_bridge.py | 107-145 | Handle template publish request |
| `publish_state_endpoint()` | mqtt_bridge.py | 11-27 | Handle state publish request |
| `get_last_hint()` | mqtt_bridge.py | 28-40 | HTTP polling endpoint |
| `publish_template()` | mqtt.py | 521-532 | Publish to MQTT broker |
| `publish_state()` | mqtt.py | 512-518 | Publish to MQTT broker |
| `_on_message()` | mqtt.py | 129-145 | MQTT message callback |
| `_handle_hint_message()` | mqtt.py | 148-175 | Process hint from LAM |

---

## 🔄 Communication Sequence

### Simple Version (3-step)
```
1. publishState() → Backend → MQTT → LAM
2. LAM processes → MQTT → Backend cache
3. pollForHints() → Backend → Frontend
```

### Complete Version (See COMPLETE_BACKEND_FLOW_SUMMARY.md)
```
Phase 1: User clicks "Publish & Start"
Phase 2: publishSelectedTemplate() → Backend → MQTT → LAM
Phase 3: doStartGame() → Initialize board
Phase 4: publishState() → Backend → MQTT → LAM
Phase 5: Periodic publishState() every 3s
Phase 6: Backend MQTT callback → Store in cache
Phase 7: Frontend pollForHints() every 500ms
Phase 8: Backend returns hint from cache
```

---

## 🎨 Game Mode Dimensions

| Mode | Columns | Rows | Tile Size | Purpose |
|------|---------|------|-----------|---------|
| Manual | 33 | 21 | 24px | Larger, more exploration |
| LAM | 10 | 10 | 24px | Smaller, LLM-friendly |

---

## 📈 Performance Metrics

| Operation | Frequency | Latency | Notes |
|-----------|-----------|---------|-------|
| State Publish | 3000ms | <100ms | Throttled HTTP |
| MQTT Publish | Instant | - | Async on broker |
| LAM Process | - | 1-2s | LLM inference |
| Hint Receive | - | <100ms | Via broker |
| Hint Poll | 500ms | <50ms | HTTP cache lookup |
| Game Render | 60fps | <16ms | Canvas update |

---

## 🔐 Security Features

✓ JWT authentication on all endpoints
✓ Template ownership validation
✓ User ID verification
✓ Input sanitization
✓ Error handling with appropriate HTTP codes
✓ QoS levels protect critical messages

---

## 🚀 Key Architectural Insights

### Why HTTP Polling Instead of WebSocket?
- Simpler fallback mechanism
- Stateless backend (scales better)
- HTTP GET can be cached
- Works with more client types

### Why Grid Conversion?
- Client uses 0=floor, 1=wall (intuitive for pathfinding)
- LAM expects 1=floor, 0=wall (standard pathfinding)
- Conversion happens on publish, not on every frame

### Why Two QoS Levels?
- **QoS 1 for templates**: Ensure LAM gets the prompt
- **QoS 0 for state**: Fast, frequent updates don't need retry

### Why Global LAST_HINTS Cache?
- Eliminates database queries for polling
- Fast HTTP responses
- Memory-efficient (one dict per session)

---

## 🎓 Learning Path

### For New Developers
1. Start: **GAME_STARTUP_MODALS_DETAILED.md** (understand UI)
2. Then: **BACKEND_PUBLISH_START_FLOW.md** (understand startup)
3. Next: **HINT_POLLING_LAM_RESPONSE_FLOW.md** (understand runtime)
4. Finally: **COMPLETE_BACKEND_FLOW_SUMMARY.md** (see it all together)

### For Architects
1. Start: **COMPLETE_BACKEND_FLOW_SUMMARY.md** (big picture)
2. Deep dive: Individual documents as needed

### For Debuggers
1. Check the document covering your component
2. Find exact line numbers
3. Trace through the code path
4. Refer to error handling section

### For API Developers
1. **COMPLETE_BACKEND_FLOW_SUMMARY.md** → Endpoints section
2. Each individual document → API details

---

## 🔍 Finding Specific Code

### "Where is the template published?"
→ BACKEND_PUBLISH_START_FLOW.md, Phase 2 section

### "Where is the game board generated?"
→ BACKEND_PUBLISH_START_FLOW.md, Phase 3 section

### "Where is the hint processed?"
→ HINT_POLLING_LAM_RESPONSE_FLOW.md, Step 7 section

### "Where is the modal styled?"
→ GAME_STARTUP_MODALS_DETAILED.md, Styling Reference section

### "Where is the MQTT callback?"
→ HINT_POLLING_LAM_RESPONSE_FLOW.md, Step 4 section

---

## 📝 File References

All code snippets include:
- ✓ Exact file path
- ✓ Line numbers (when applicable)
- ✓ Code context (surrounding lines)
- ✓ Related functions
- ✓ Data flow diagrams

---

## 🎯 Common Tasks

### Add New Template Validation
Files: `backend/app/routers/mqtt_bridge.py` (Line 107-145)
Also: `backend/app/schemas.py`

### Modify State Publish Rate
File: `frontend/src/pages/WebGame.tsx` (Line 1204-1214)
Default: 3000ms (localStorage key: "mqtt-send-rate")

### Change Game Board Dimensions
File: `frontend/src/pages/WebGame.tsx` (Line 1973-1974)
LAM Mode: 10×10, Manual Mode: 33×21

### Add New Hint Action
Files: 
- LAM end: Publish new field in hint JSON
- Backend: `mqtt.py` _handle_hint_message (Line 148)
- Frontend: `WebGame.tsx` pollForHints (Line 730+)

### Modify Polling Interval
File: `frontend/src/pages/WebGame.tsx` (Line 665)
Default: 500ms polling for hints

---

## 🆘 Troubleshooting Guide

### "Template not published"
Check: `BACKEND_PUBLISH_START_FLOW.md` → Phase 2
- Verify user owns template
- Check MQTT broker connection
- See error handling section

### "No hints received"
Check: `HINT_POLLING_LAM_RESPONSE_FLOW.md` → Steps 4-7
- Verify polling is active
- Check LAST_HINTS cache
- Verify MQTT subscription

### "Game board won't start"
Check: `BACKEND_PUBLISH_START_FLOW.md` → Phase 3
- Check maze generation
- Verify state initialization
- See error handling

### "Wrong grid coordinates"
Check: `HINT_POLLING_LAM_RESPONSE_FLOW.md` → "Grid Conversion Logic"
- Verify 0=floor conversion
- Check path sanitization

---

## 📞 Related Documentation

In the same folder, you'll also find:
- **CODE_SNIPPETS_FROM_UI.md**: Template management UI
- **LAM_PRACTICAL_GUIDE.md**: LAM setup and usage
- **MQTT_POLLING_MIGRATION.md**: Background on polling implementation
- Other architectural docs

---

## ✅ Verification Checklist

Before assuming you understand a flow:

- [ ] Can you explain the 3-step communication?
- [ ] Do you know all MQTT topics involved?
- [ ] Can you trace a request from UI to LAM?
- [ ] Do you understand grid coordinate conversion?
- [ ] Can you explain why QoS differs?
- [ ] Do you know the polling intervals?
- [ ] Can you find all affected files?
- [ ] Can you describe error scenarios?
- [ ] Do you understand the startup sequence?
- [ ] Can you explain the architectural decisions?

If you can answer yes to all, you understand the complete backend flow! ✨


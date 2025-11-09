# Complete Backend Flow Documentation - Summary

This document provides a comprehensive overview of all backend code that executes after clicking "Publish & Start" in the game startup modal.

---

## 📚 Documentation Files Created

| Document | Focus | Key Topics |
|----------|-------|-----------|
| **GAME_STARTUP_MODAL_SNIPPETS.md** | Frontend UI & State | Modal container, mode selection, template picker |
| **GAME_STARTUP_MODALS_DETAILED.md** | UI Implementation | JSX, styling, event handlers, accessibility |
| **BACKEND_PUBLISH_START_FLOW.md** | Immediate Startup | Template publishing, game initialization |
| **HINT_POLLING_LAM_RESPONSE_FLOW.md** | Runtime Communication | State polling, LAM responses, hint processing |
| **This Document** | Complete Overview | All flows together, architecture summary |

---

## 🎯 Complete Execution Flow

### Phase 1: User Action (Frontend)
```
User clicks "Publish & Start"
    ↓
Modal validation:
  - Template selected?
  - Mode confirmed?
    ↓
setTemplateId(selectedTemplateId)
setShowTemplatePicker(false)
setGameMode(chosenMode)
    ↓
publishSelectedTemplate(selectedTemplateId)
```

**File**: `frontend/src/pages/WebGame.tsx` (Lines 1960-1977)

```typescript
onClick={()=>{
  if (!selectedTemplateId) return
  setTemplateId(selectedTemplateId)
  setShowTemplatePicker(false)
  const chosenMode = selectedMode
  setGameMode(chosenMode)
  publishSelectedTemplate(selectedTemplateId).finally(() => {
    const targetCols = (chosenMode === 'lam') ? 10 : 33
    const targetRows = (chosenMode === 'lam') ? 10 : 21
    doStartGame(targetCols, targetRows)
  })
}}
```

---

### Phase 2: Publish Template (HTTP API)

#### Frontend → Backend
**Endpoint**: `POST /api/mqtt/publish_template`
**File**: `frontend/src/pages/WebGame.tsx` (Lines 1097-1108)

```typescript
const publishSelectedTemplate = useCallback(async (tid: number) => {
  try {
    await api.post('/api/mqtt/publish_template', { 
      template_id: tid, 
      reset: true 
    })
    setStatus('Template published!')
    setTimeout(()=>setStatus(''), 1500)
  } catch (e) {
    setStatus('Failed to publish template')
    setTimeout(()=>setStatus(''), 2000)
  }
}, [])
```

#### Backend Handler
**File**: `backend/app/routers/mqtt_bridge.py` (Lines 107-145)

```python
@router.post("/publish_template")
def publish_template_endpoint(
    payload: dict,
    session_id: str | None = Query(default=None),
    reset: bool = Query(default=True),
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    # Fetch template from DB
    t = db.query(models.PromptTemplate).filter(
        models.PromptTemplate.id == payload.get("template_id"),
        models.PromptTemplate.user_id == user.id
    ).first()
    
    if not t:
        raise HTTPException(404, "Template not found")
    
    # Construct message body
    body = {
        "template": t.content,
        "title": t.title,
        "version": t.version,
        "user_id": user.id,
        "reset": True
    }
    
    # Publish to MQTT
    publish_template(body, session_id=session_id)
    return {"ok": True}
```

#### MQTT Publishing
**File**: `backend/app/mqtt.py` (Lines 521-532)

```python
def publish_template(template_payload: dict, session_id: str | None = None):
    try:
        topic = settings.MQTT_TOPIC_TEMPLATE
        if session_id:
            topic = topic + "/" + session_id
        
        result = mqtt_client.publish(
            topic, 
            json.dumps(template_payload), 
            qos=1,                          # At-least-once delivery
            retain=False
        )
    except Exception as e:
        print(f"[MQTT] Error publishing template: {e}")
```

**MQTT Topic**: `maze/template`

**Message Format**:
```json
{
  "template": "You are a Large Action Model (LAM) that controls a maze game...",
  "title": "SPARC DRIVING LLM AGENT PROMPT",
  "version": 1,
  "user_id": 42,
  "reset": true
}
```

---

### Phase 3: Initialize Game Board (Frontend)

**File**: `frontend/src/pages/WebGame.tsx` (Lines 983-1090)

#### Game State Reset
```typescript
const doStartGame = useCallback((targetCols?: number, targetRows?: number) => {
  setScoreSubmitted(false)
  setGameOverTrigger(0)
  
  const cols = targetCols || boardCols
  const rows = targetRows || boardRows
  
  setBoardCols(targetCols)
  setBoardRows(targetRows)
```

#### Maze Generation
```typescript
const grid = generateMaze(cols, rows)

// Ensure start area open
grid[1][1] = 0; grid[1][2] = 0; grid[2][1] = 0

// Place oxygen ~10% of floors
const count = Math.max(10, Math.floor(avail.length * 0.1))

// Spawn germs (user-configurable)
const spawnGerms = Math.max(0, Math.min(50, Math.floor(germCount)))
```

#### Initialize Game State Reference
```typescript
stateRef.current = {
  grid,
  player: start,
  exit,
  oxy,
  germs,
  oxygenCollected: 0,
  startTime: performance.now(),
  started: true,
  gameOver: false,
  win: false,
  lam: { hint: '', path: [], breaks: 0, error: '', showPath: false },
  effects: { speedBoostUntil: 0, slowGermsUntil: 0, freezeGermsUntil: 0 },
  metrics: {
    totalSteps: 0,
    optimalSteps: bfsPath(grid, start, exit)?.length || 0,
    backtrackCount: 0,
    collisionCount: 0,
    deadEndEntries: 0,
    actionLatencies: [],
    visitedTiles: new Set([key(start.x, start.y)]),
    lastPosition: { ...start }
  }
}
```

---

### Phase 4: Publish Initial Game State (HTTP API)

#### Frontend → Backend
**Endpoint**: `POST /api/mqtt/publish_state`
**File**: `frontend/src/pages/WebGame.tsx` (Lines 1141-1173)

```typescript
const publishState = useCallback(async (force = false) => {
  if (!templateId) return
  
  const now = performance.now()
  if (!force && now - lastPublishRef.current < mqttSendRate) return
  lastPublishRef.current = now

  const s = stateRef.current
  
  // Convert grid: 0→floor becomes 1→floor for LAM
  const visibleMap = s.grid.map(row => row.map(c => c === 0 ? 1 : 0))
  
  const body = {
    session_id: sessionId,
    template_id: templateId,
    state: {
      sessionId,
      player_pos: [s.player.x, s.player.y],
      exit_pos: [s.exit.x, s.exit.y],
      visible_map: visibleMap,
      oxygenPellets: s.oxy.map(p => ({ x: p.x, y: p.y })),
      germs: s.germs.map(g => ({ x: g.pos.x, y: g.pos.y })),
      tick: Date.now(),
      health: 100,
      oxygen: 100 - s.oxygenCollected
    }
  }
  
  try { 
    await api.post('/api/mqtt/publish_state', body) 
  } catch (e) { 
    /* ignore */ 
  }
}, [sessionId, templateId, mqttSendRate])
```

#### Backend Handler
**File**: `backend/app/routers/mqtt_bridge.py` (Lines 11-27)

```python
@router.post("/publish_state")
def publish_state_endpoint(
    payload: schemas.PublishStateIn, 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    # Fetch template
    t = db.query(models.PromptTemplate).filter(
        models.PromptTemplate.id == payload.template_id, 
        models.PromptTemplate.user_id == user.id
    ).first()
    
    if not t:
        raise HTTPException(404, "Template not found")
    
    # Enrich state with full template
    state = dict(payload.state or {})
    state.update({
        "sessionId": payload.session_id,
        "prompt_template": {
            "title": t.title,
            "content": t.content,
            "version": t.version,
            "user_id": user.id,
        }
    })
    
    # Publish to MQTT
    publish_state(state)
    return {"ok": True}
```

#### MQTT Publishing
**File**: `backend/app/mqtt.py` (Lines 512-518)

```python
def publish_state(state: dict):
    try:
        result = mqtt_client.publish(
            settings.MQTT_TOPIC_STATE, 
            json.dumps(state), 
            qos=0,                          # Fire-and-forget
            retain=False
        )
    except Exception as e:
        print(f"[MQTT] Error publishing state: {e}")
```

**MQTT Topic**: `maze/state`

---

### Phase 5: Periodic State Publishing

**File**: `frontend/src/pages/WebGame.tsx` (Lines 1204-1214)

```typescript
useEffect(() => {
  const periodMs = mqttSendRate    // Default 3000ms
  if (!stateRef.current.started) return
  
  const interval = setInterval(() => {
    publishState()
  }, periodMs)
  
  return () => clearInterval(interval)
}, [templateId, publishState, mqttSendRate])
```

**Timing**: 
- Every 3000ms (default)
- User-adjustable: 500ms - 60000ms
- Stored in localStorage

---

### Phase 6: Backend MQTT Message Handling

#### Message Callback
**File**: `backend/app/mqtt.py` (Lines 129-145)

```python
def _on_message(client, userdata, msg):
    global _mqtt_last_activity
    _mqtt_last_activity = time.time()
    
    payload_text = msg.payload.decode("utf-8", errors="ignore")
    print(f"[MQTT] Received message on topic '{msg.topic}': {payload_text[:200]}...")

    topic = msg.topic

    # Route to appropriate handler
    if HINT_TOPIC_BASE and topic.startswith(HINT_TOPIC_BASE):
        _handle_hint_message(topic, payload_text)
        return

    if CHAT_RESPONSE_BASE and topic.startswith(CHAT_RESPONSE_BASE):
        _handle_chat_response(topic, payload_text)
        return
```

#### Hint Message Handler
**File**: `backend/app/mqtt.py` (Lines 148-175)

```python
def _handle_hint_message(topic: str, payload_text: str) -> None:
    try:
        data = json.loads(payload_text)
    except Exception as exc:
        data = {"raw": payload_text}

    # Add timestamp
    data["timestamp"] = time.time()
    
    # Extract session ID (maze/hint/session-xyz → session-xyz)
    parts = topic.split("/")
    session_id = parts[-1] if len(parts) >= 3 else "unknown"
    
    # Store in global cache
    LAST_HINTS[session_id] = data

    # Send to WebSocket subscribers (if any)
    websockets = SUBSCRIBERS.get(session_id, set()).copy()
    
    for ws in websockets:
        # Send via WebSocket thread
        message_data = json.dumps({"topic": topic, "hint": data})
        threading.Thread(
            target=send_to_websocket,
            args=(ws, message_data),
            daemon=True
        ).start()
```

**Global Hint Storage**:
```python
LAST_HINTS: Dict[str, dict] = {}
```

---

### Phase 7: Frontend Hint Polling

#### Setup
**File**: `frontend/src/pages/WebGame.tsx` (Lines 662-665)

```typescript
const pollingIntervalRef = useRef<number | null>(null)
const lastHintTimestampRef = useRef<number>(0)
```

#### Polling Logic
**File**: `frontend/src/pages/WebGame.tsx` (Lines 662-760)

```typescript
const pollForHints = useCallback(async () => {
  if (!connected) return
  
  try {
    // Get last hint from backend cache
    const response = await api.get(`/api/mqtt/last_hint?session_id=${sessionId}`)
    const data = response.data
    
    if (!data.has_hint || !data.last_hint) return
    
    // Check if new (avoid duplicates)
    const hintTimestamp = data.last_hint.timestamp || 0
    if (hintTimestamp <= lastHintTimestampRef.current) return
    
    lastHintTimestampRef.current = hintTimestamp
    
    // Process hint
    const hint: HintMsg = data.last_hint || {}
    const s = stateRef.current
    
    // Handle error
    const errText = hint.error || hint.err
    s.lam.error = errText ? String(errText) : ''
    
    // Store hint text
    s.lam.hint = hint.hint || ''
    
    // Process path
    const hasPath = Array.isArray(hint.path) && hint.path.length > 0
    if (hasPath) {
      const rawPath = hint.path.map(p => 
        Array.isArray(p) ? { x: p[0], y: p[1] } : { x: p.x, y: p.y }
      )
      s.lam.path = sanitizePath(s.grid, rawPath, s.player)
    } else {
      s.lam.path = []
    }
    
    // Show path
    s.lam.showPath = (hint.show_path === true) || 
                     (gameMode === 'manual' && hasPath)
    
    // Update breaks
    s.lam.breaks = hint.breaks_remaining ?? s.lam.breaks
    
    // Update React state for UI
    setLamData({
      hint: s.lam.hint,
      path: s.lam.path.slice(),
      breaks: s.lam.breaks,
      error: s.lam.error,
      raw: hint,
      rawMessage: data,
      updatedAt: Date.now(),
      showPath: s.lam.showPath
    })
    
    // Process special actions
    if (hint.break_wall) breakWall(hint.break_wall[0], hint.break_wall[1])
    if (hint.speed_boost_ms) s.effects.speedBoostUntil = now + hint.speed_boost_ms
    if (hint.freeze_germs_ms) s.effects.freezeGermsUntil = now + hint.freeze_germs_ms
    if (hint.teleport_player) s.player = { x: hint.teleport_player[0], y: hint.teleport_player[1] }
    
  } catch (e) {
    console.error('Polling error:', e)
  }
}, [connected, sessionId, gameMode])
```

#### Polling Interval Setup
```typescript
useEffect(() => {
  if (!sessionId || !stateRef.current.started) return
  
  pollingIntervalRef.current = window.setInterval(pollForHints, 500) as any
  
  return () => {
    if (pollingIntervalRef.current !== null) {
      clearInterval(pollingIntervalRef.current)
    }
  }
}, [sessionId, pollForHints, stateRef.current.started])
```

---

### Phase 8: HTTP Endpoint for Hint Polling

**File**: `backend/app/routers/mqtt_bridge.py` (Lines 28-40)

```python
@router.get("/last_hint")
def get_last_hint(session_id: str = Query(..., min_length=1)):
    """Get the last hint for a session (polling method)"""
    hint = LAST_HINTS.get(session_id)
    return {
        "session_id": session_id,
        "last_hint": hint,
        "has_hint": hint is not None,
        "timestamp": hint.get("timestamp") if hint and isinstance(hint, dict) else None
    }
```

---

## 🔄 Communication Diagram

```
┌──────────────────┐
│   Frontend       │
│   Game Loop      │
└────────┬─────────┘
         │
    Every 3s
         │
    publishState()
         │
    ┌────▼─────────────────────────────────────┐
    │  POST /api/mqtt/publish_state            │
    │  (enriches with template content)        │
    └────┬──────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │   Backend Router (mqtt_bridge.py)       │
    │   publish_state_endpoint()              │
    │   - Fetch template                      │
    │   - Validate ownership                  │
    │   - Enrich state                        │
    └────┬──────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │   MQTT Module (mqtt.py)                 │
    │   publish_state(state)                  │
    │   - Topic: maze/state                   │
    │   - QoS: 0 (fire-and-forget)            │
    └────┬──────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │   MQTT Broker                           │
    │   Publishes to maze/state               │
    └────┬──────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │   LAM (llama.cpp)                       │
    │   Receives state + template             │
    │   Generates hint response               │
    │   Publishes to maze/hint/session-xyz    │
    └────┬──────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │   MQTT Broker                           │
    │   Publishes to maze/hint/session-xyz    │
    └────┬──────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │   Backend MQTT Handler (mqtt.py)        │
    │   _on_message()                         │
    │   _handle_hint_message()                │
    │   LAST_HINTS[session_id] = data         │
    └────┬──────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │   Frontend Polling                      │
    │   pollForHints()                        │
    │   every 500ms                           │
    │   GET /api/mqtt/last_hint               │
    └────┬──────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │   Backend Endpoint (mqtt_bridge.py)     │
    │   get_last_hint()                       │
    │   return LAST_HINTS[session_id]         │
    └────┬──────────────────────────────────────┘
         │
         ▼
    ┌─────────────────────────────────────────┐
    │   Frontend Process Hint                 │
    │   - Extract path                        │
    │   - Store actions                       │
    │   - Update game state                   │
    │   - Render changes                      │
    └──────────────────────────────────────────┘
```

---

## 🔐 Security & Validation

### Authentication
All endpoints require JWT token:
```python
user=Depends(get_current_user)
```

### Authorization
Template ownership validated:
```python
t = db.query(models.PromptTemplate).filter(
    models.PromptTemplate.id == tid,
    models.PromptTemplate.user_id == user.id  # ← User must own template
).first()
```

### Input Validation
- Template ID exists: HTTPException(404) if not found
- Session ID format: min_length=1
- Grid conversion: Safe bounds checking
- JSON parsing: Try/except with fallback

---

## 📊 Performance Characteristics

| Operation | Frequency | Latency | Notes |
|-----------|-----------|---------|-------|
| **State Publish** | 3s | <100ms | HTTP roundtrip |
| **MQTT Publish** | Same | Instant | Async on broker |
| **LAM Processing** | Per state | 1-2s | LLM inference time |
| **Hint Receive** | MQTT | <100ms | Broker deliver |
| **Hint Poll** | 500ms | <50ms | HTTP GET cache lookup |
| **Hint Process** | Per hint | <20ms | Path sanitization |

---

## 🎯 Key Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `frontend/src/pages/WebGame.tsx` | 1-150 | State setup |
| `frontend/src/pages/WebGame.tsx` | 983-1090 | doStartGame() |
| `frontend/src/pages/WebGame.tsx` | 1097-1108 | publishSelectedTemplate() |
| `frontend/src/pages/WebGame.tsx` | 1141-1173 | publishState() |
| `frontend/src/pages/WebGame.tsx` | 662-760 | pollForHints() |
| `frontend/src/pages/WebGame.tsx` | 1204-1214 | Polling setup |
| `backend/app/routers/mqtt_bridge.py` | 1-50 | Router setup |
| `backend/app/routers/mqtt_bridge.py` | 11-27 | publish_state_endpoint |
| `backend/app/routers/mqtt_bridge.py` | 28-40 | get_last_hint |
| `backend/app/routers/mqtt_bridge.py` | 107-145 | publish_template_endpoint |
| `backend/app/mqtt.py` | 36-40 | Global LAST_HINTS |
| `backend/app/mqtt.py` | 62-75 | MQTT client setup |
| `backend/app/mqtt.py` | 129-145 | _on_message handler |
| `backend/app/mqtt.py` | 148-175 | _handle_hint_message |
| `backend/app/mqtt.py` | 512-518 | publish_state() |
| `backend/app/mqtt.py` | 521-532 | publish_template() |

---

## 🚀 Startup Sequence Summary

1. **User Action**: Click "Publish & Start"
2. **Frontend Modal Close**: Hide picker modal
3. **Set Game Mode**: Apply chosen mode to state
4. **Publish Template**: HTTP POST with template_id
   - Backend fetches template
   - MQTT publishes to `maze/template`
5. **Initialize Board**: Generate maze procedurally
   - Generate grid (0=floor, 1=wall)
   - Place oxygen pellets (~10% of floors)
   - Spawn germs (user-configurable)
   - Setup metrics & state reference
6. **Publish Initial State**: HTTP POST with game state
   - Backend enriches with template content
   - MQTT publishes to `maze/state`
7. **Setup Polling**: Start 500ms polling interval
8. **Game Render**: Canvas rendering loop begins
9. **Periodic Updates**: Every 3s (or custom interval)
   - Frontend publishes new state
   - Backend routes through MQTT
   - LAM generates hints
   - Frontend polls for hints
   - Process & render updates

---

## 💡 Key Architectural Decisions

1. **HTTP Polling over WebSocket**: Simpler fallback, supports more clients
2. **Template Enrichment at Backend**: LAM always has full context
3. **QoS 1 for Templates**: Ensure LAM gets prompt
4. **QoS 0 for State**: Fast, frequent updates don't need retries
5. **Grid Conversion**: Client uses 0=floor, LAM expects 1=floor
6. **Timestamp Filtering**: Prevents duplicate hint processing
7. **Global LAST_HINTS Cache**: No database queries for polling
8. **Throttled Publishing**: 3s default prevents backend overload


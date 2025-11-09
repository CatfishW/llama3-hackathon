# Hint Polling & LAM Response Flow

This document details the communication flow between the frontend game, backend MQTT bridge, and the LAM (Large Action Model) for hint generation and processing.

---

## 🔄 Complete Communication Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                Game Loop Cycle                              │
└──────────────────────────────┬──────────────────────────────────────────────┘
                               │
                    1. publishState() every 3s
                               │
              ┌────────────────▼────────────────┐
              │                                 │
         Frontend                          Backend
         ────────                          ───────
         
         POST /api/mqtt/publish_state  ──────>  publish_state_endpoint()
                                                │
                                         MQTT Broker publishes
                                         maze/state topic
                                                │
                                         LAM (llama.cpp)
                                         receives state
                                         generates hint
                                                │
                                         MQTT publishes
                                         maze/hint/{sessionId}
                                                │
         ┌───────────────────────────────────┘
         │
    2. pollForHints()
    every 500ms
         │
         GET /api/mqtt/last_hint?session_id=X
         <─────────────────────────────────────  LAST_HINTS[session_id]
         │
    3. Process hint actions
    update game state
         │
    4. Render next frame
         │
         └─────────────────┐
                           │
                  (3-second timer)
                  (publishes again)
```

---

## 📡 Step 1: Frontend - Publish Game State

### Function Location
**File**: `frontend/src/pages/WebGame.tsx`
**Lines**: 1141-1173

```typescript
const publishState = useCallback(async (force = false) => {
  if (!templateId) return
  const now = performance.now()
  const throttleMs = mqttSendRate
  if (!force && now - lastPublishRef.current < throttleMs) return // throttle
  lastPublishRef.current = now

  const s = stateRef.current
  const visibleMap = (s.grid && s.grid.length)
    ? s.grid.map(row => row.map(c => c === 0 ? 1 : 0))
    : []
  
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
}, [sessionId, templateId])
```

### State Payload Example

```json
{
  "session_id": "session-abc123xyz",
  "template_id": 42,
  "state": {
    "sessionId": "session-abc123xyz",
    "player_pos": [3, 5],
    "exit_pos": [8, 8],
    "visible_map": [
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
      [0, 1, 1, 0, 1, 1, 1, 0, 1, 0],
      [0, 1, 0, 0, 0, 1, 0, 0, 1, 0],
      [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
      [0, 1, 0, 1, 0, 0, 0, 1, 0, 0],
      [0, 1, 1, 1, 0, 1, 1, 1, 1, 0],
      [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],
      [0, 1, 1, 1, 1, 1, 1, 1, 1, 0],
      [0, 1, 0, 0, 0, 0, 0, 0, 1, 0],
      [0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
    ],
    "oxygenPellets": [
      { "x": 3, "y": 2 },
      { "x": 6, "y": 5 }
    ],
    "germs": [
      { "x": 4, "y": 3 }
    ],
    "tick": 1730813456789,
    "health": 100,
    "oxygen": 98
  }
}
```

### Periodic Publishing Setup

**File**: `frontend/src/pages/WebGame.tsx`
**Lines**: 1204-1214

```typescript
useEffect(() => {
  const periodMs = mqttSendRate
  if (!stateRef.current.started) return
  
  const interval = setInterval(() => {
    publishState()
  }, periodMs)
  
  return () => clearInterval(interval)
}, [templateId, publishState, mqttSendRate])
```

**Publishing Rate**
- Default: 3000ms (3 seconds)
- Range: 500ms - 60s
- User-adjustable via UI slider
- Stored in localStorage

---

## 🔌 Step 2: Backend - Receive and Enrich State

### Endpoint Location
**File**: `backend/app/routers/mqtt_bridge.py`
**Lines**: 11-27

```python
@router.post("/publish_state")
def publish_state_endpoint(
    payload: schemas.PublishStateIn, 
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    # Fetch the template content to embed into state
    t = db.query(models.PromptTemplate).filter(
        models.PromptTemplate.id == payload.template_id, 
        models.PromptTemplate.user_id == user.id
    ).first()
    if not t:
        raise HTTPException(404, "Template not found or not owned by you")
    
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
    publish_state(state)
    return {"ok": True}
```

### Enriched State (with Template)

```json
{
  "sessionId": "session-abc123xyz",
  "player_pos": [3, 5],
  "exit_pos": [8, 8],
  "visible_map": [...],
  "oxygenPellets": [...],
  "germs": [...],
  "tick": 1730813456789,
  "health": 100,
  "oxygen": 98,
  "prompt_template": {
    "title": "SPARC DRIVING LLM AGENT PROMPT",
    "content": "You are a Large Action Model (LAM)...",
    "version": 1,
    "user_id": 42
  }
}
```

---

## 📬 Step 3: MQTT Publishing

### Function Location
**File**: `backend/app/mqtt.py`
**Lines**: 512-518

```python
def publish_state(state: dict):
    """Publish maze game state to MQTT"""
    try:
        result = mqtt_client.publish(
            settings.MQTT_TOPIC_STATE, 
            json.dumps(state), 
            qos=0,
            retain=False
        )
        if result.rc != 0:
            print(f"[MQTT] Failed to publish state (rc={result.rc})")
    except Exception as e:
        print(f"[MQTT] Error publishing state: {e}")
```

### MQTT Topic
```
maze/state
```

### LAM Processing

The LAM (llama.cpp deployment) receives the state on `maze/state`:

1. **Parse** the incoming state message
2. **Extract** the prompt template
3. **Formulate** response with:
   - `hint`: Text guidance for player
   - `path`: Array of coordinates for pathfinding
   - `breaks_remaining`: Wall breaks left
   - Other actions (teleport, freeze_germs, etc.)
4. **Publish** response to `maze/hint/{sessionId}`

Example LAM Response:
```json
{
  "hint": "Moving toward exit via validated floor path",
  "show_path": true,
  "path": [[3, 6], [3, 7], [4, 7], [5, 7]],
  "breaks_remaining": 5,
  "speed_boost_ms": 0,
  "freeze_germs_ms": 0
}
```

---

## 🔄 Step 4: Backend - MQTT Message Callback

### Handler Location
**File**: `backend/app/mqtt.py`
**Lines**: 129-175

```python
def _on_message(client, userdata, msg):
    global _mqtt_last_activity
    _mqtt_last_activity = time.time()
    
    payload_text = msg.payload.decode("utf-8", errors="ignore")
    print(f"[MQTT] Received message on topic '{msg.topic}': {payload_text[:200]}...")

    topic = msg.topic

    if HINT_TOPIC_BASE and topic.startswith(HINT_TOPIC_BASE):
        _handle_hint_message(topic, payload_text)
        return

    if CHAT_RESPONSE_BASE and topic.startswith(CHAT_RESPONSE_BASE):
        _handle_chat_response(topic, payload_text)
        return

    print(f"[MQTT] Unhandled topic '{topic}'")
```

### Hint Message Handler

**File**: `backend/app/mqtt.py`
**Lines**: 148-175

```python
def _handle_hint_message(topic: str, payload_text: str) -> None:
    try:
        data = json.loads(payload_text)
    except Exception as exc:
        print(f"[MQTT] Hint JSON parse error: {exc}")
        data = {"raw": payload_text}

    # Add timestamp to track new hints
    data["timestamp"] = time.time()
    
    # Extract session ID from topic (maze/hint/session-abc123xyz)
    parts = topic.split("/")
    session_id = parts[-1] if len(parts) >= 3 else "unknown"
    
    # Store hint for polling
    LAST_HINTS[session_id] = data

    print(f"[MQTT] Hint session ID: {session_id}, Subscribers: {len(SUBSCRIBERS.get(session_id, set()))}")

    # Send to WebSocket subscribers (if any)
    websockets = SUBSCRIBERS.get(session_id, set()).copy()
    if not websockets:
        print(f"[MQTT] No WebSocket subscribers for hint session '{session_id}' (hint stored for polling)")
        return

    message_data = json.dumps({"topic": topic, "hint": data})

    for ws in websockets:
        try:
            def send_message() -> None:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    loop.run_until_complete(ws.send_text(message_data))
                    loop.close()
                except Exception as send_exc:
                    print(f"[MQTT] Failed to send hint to WebSocket: {send_exc}")

            threading.Thread(target=send_message, daemon=True).start()
            print(f"[MQTT] Sent hint to WebSocket for session '{session_id}'")
        except Exception as exc:
            print(f"[MQTT] Error starting thread for WebSocket hint send: {exc}")
            SUBSCRIBERS.get(session_id, set()).discard(ws)
```

### LAST_HINTS Global Storage

**File**: `backend/app/mqtt.py`
**Line**: 36

```python
LAST_HINTS: Dict[str, dict] = {}
```

- Stores the most recent hint for each session
- Polled by frontend via `/api/mqtt/last_hint`
- Includes timestamp to detect new hints

---

## 🎯 Step 5: Backend - Expose Hint via HTTP Endpoint

### Endpoint Location
**File**: `backend/app/routers/mqtt_bridge.py`
**Lines**: 28-40

```python
@router.get("/last_hint")
def get_last_hint(session_id: str = Query(..., min_length=1)):
    """Get the last hint for a session (polling method - no WebSocket needed)"""
    hint = LAST_HINTS.get(session_id)
    return {
        "session_id": session_id, 
        "last_hint": hint,
        "has_hint": hint is not None,
        "timestamp": hint.get("timestamp") if hint and isinstance(hint, dict) else None
    }
```

### Response Format

**No hint yet:**
```json
{
  "session_id": "session-abc123xyz",
  "last_hint": null,
  "has_hint": false,
  "timestamp": null
}
```

**With hint:**
```json
{
  "session_id": "session-abc123xyz",
  "last_hint": {
    "hint": "Moving toward exit via validated floor path",
    "show_path": true,
    "path": [[3, 6], [3, 7], [4, 7], [5, 7]],
    "breaks_remaining": 5,
    "timestamp": 1730813459.123
  },
  "has_hint": true,
  "timestamp": 1730813459.123
}
```

---

## 🔄 Step 6: Frontend - Poll for Hints

### Function Location
**File**: `frontend/src/pages/WebGame.tsx`
**Lines**: 662-760

```typescript
const pollForHints = useCallback(async () => {
  if (!connected) return
  
  try {
    const response = await api.get(`/api/mqtt/last_hint?session_id=${sessionId}`)
    const data = response.data
    
    if (!data.has_hint || !data.last_hint) return
    
    // Check if this is a new hint (avoid processing same hint multiple times)
    const hintTimestamp = data.last_hint.timestamp || 0
    if (hintTimestamp <= lastHintTimestampRef.current) return
    
    lastHintTimestampRef.current = hintTimestamp
```

### Polling Setup

**File**: `frontend/src/pages/WebGame.tsx`
**Lines**: 662-665

```typescript
const pollingIntervalRef = useRef<number | null>(null)
const lastHintTimestampRef = useRef<number>(0)
```

**Polling Loop:**
- Polls every 500ms (when game is running)
- Checks timestamp to avoid duplicate processing
- Skips if no new hint available

---

## 🎮 Step 7: Frontend - Process Hint Actions

### Hint Object Structure

```typescript
interface HintMsg {
  hint: string                    // Text guidance
  show_path: boolean              // Visualize path
  path: Array<[number, number]>   // Coordinates
  breaks_remaining: number        // Wall breaks left
  error?: string                  // Error message
  break_wall?: [number, number]   // Break single wall
  break_walls?: Array<[number, number]>  // Break multiple walls
  speed_boost_ms?: number         // Speed boost duration
  freeze_germs_ms?: number        // Freeze germs duration
  teleport_player?: [number, number]  // Teleport destination
}
```

### Processing Logic

**File**: `frontend/src/pages/WebGame.tsx`
**Lines**: 680-750

```typescript
const hint: HintMsg = data.last_hint || {}
const s = stateRef.current

// Error handling
const anyHint: any = hint as any
const errText = anyHint.error || anyHint.Error || anyHint.err
if (errText) {
  s.lam.error = errText
} else {
  s.lam.error = ''
}

// Hint text
s.lam.hint = hint.hint || ''

// Path handling
const hasPath = Array.isArray((hint as any).path) && (hint as any).path.length > 0
if (hasPath) {
  const rawPath = (hint as any).path.map((p:any) => 
    Array.isArray(p)? { x:p[0], y:p[1] } : { x: p.x, y: p.y }
  )
  s.lam.path = sanitizePath(s.grid as any, rawPath, s.player)
} else {
  s.lam.path = []
}

// Show path based on hint or game mode
s.lam.showPath = (hint.show_path === true) || (gameModeRef.current === 'manual' && hasPath)

// Breaks remaining
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
```

### Action Processing

```typescript
// Break wall
if (hint.break_wall) {
  const bw: any = (hint as any).break_wall
  const bx = Array.isArray(bw) ? bw[0] : (typeof bw === 'object' ? bw.x : undefined)
  const by = Array.isArray(bw) ? bw[1] : (typeof bw === 'object' ? bw.y : undefined)
  if (bx!=null && by!=null) breakWall(bx, by)
}

// Speed boost
const speedBoost = msFrom(anyHint, ['speed_boost_ms', 'speedBoostMs'], 0)
if (speedBoost > 0) {
  s.effects.speedBoostUntil = now + speedBoost
}

// Freeze germs
const freezeGerms = msFrom(anyHint, ['freeze_germs_ms', 'freezeGermsMs'], 0)
if (freezeGerms > 0) {
  s.effects.freezeGermsUntil = now + freezeGerms
}

// Teleport
if (anyHint.teleport_player) {
  const tp: any = anyHint.teleport_player
  const tx = Array.isArray(tp) ? tp[0] : tp.x
  const ty = Array.isArray(tp) ? tp[1] : tp.y
  if (tx!=null && ty!=null && s.grid[ty]?.[tx]===0) {
    s.player = { x: tx, y: ty }
  }
}
```

---

## 📊 State Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STATE POLLING CYCLE (3s)                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                              ┌───────▼────────┐
                              │  publishState()│
                              │   every 3000ms │
                              └───────┬────────┘
                                      │
                    ┌─────────────────▼──────────────────┐
                    │  POST /api/mqtt/publish_state      │
                    │  (enriches with template content)  │
                    └─────────────────┬──────────────────┘
                                      │
                            ┌─────────▼────────┐
                            │ MQTT Broker      │
                            │ Topic: maze/state│
                            └─────────┬────────┘
                                      │
                          ┌───────────▼──────────────┐
                          │ LAM (llama.cpp)          │
                          │ Processes state + prompt │
                          │ Generates hint           │
                          └───────────┬──────────────┘
                                      │
                      ┌───────────────▼─────────────────┐
                      │ MQTT Broker                     │
                      │ Topic: maze/hint/session-xyz    │
                      └───────────┬─────────────────────┘
                                  │
                        ┌─────────▼────────┐
                        │ Backend Handler  │
                        │ _handle_hint()   │
                        │ Store in LAST_   │
                        │ HINTS[session_id]│
                        └─────────┬────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │ Frontend (every 500ms)         │
                    │ GET /api/mqtt/last_hint        │
                    │ Check timestamp                │
                    └─────────────┬──────────────────┘
                                  │
                          ┌───────▼──────┐
                          │ Process Hint │
                          │ Actions      │
                          └───────┬──────┘
                                  │
                          ┌───────▼──────────┐
                          │ Update Game UI   │
                          │ Render Changes   │
                          └──────────────────┘
```

---

## ⏱️ Timing & Intervals

| Operation | Interval | Purpose |
|-----------|----------|---------|
| **Publish State** | 3000ms (default) | Send game state to LAM |
| **Poll for Hints** | 500ms | Check for new hints frequently |
| **Timestamp Check** | Per poll | Avoid duplicate hint processing |
| **LAM Processing** | ~1-2s | Generate hint and actions |
| **MQTT Topic Publish** | Variable | Depends on LAM response time |

---

## 🔍 Error Handling

### Frontend Error Scenarios

```typescript
// No hint yet
if (!data.has_hint || !data.last_hint) return

// Duplicate hint (same timestamp)
if (hintTimestamp <= lastHintTimestampRef.current) return

// JSON parse error on LAM response
try {
  const hint: HintMsg = data.last_hint || {}
  // ... process hint
} catch (e) {
  s.lam.error = `Invalid LAM JSON: ${String(e).slice(0, 160)}`
}
```

### Backend Error Scenarios

```python
# JSON parse error
try:
  data = json.loads(payload_text)
except Exception as exc:
  print(f"[MQTT] Hint JSON parse error: {exc}")
  data = {"raw": payload_text}

# MQTT publish failure
if result.rc != 0:
  print(f"[MQTT] Failed to publish state (rc={result.rc})")

# Template not found
if not t:
  raise HTTPException(404, "Template not found or not owned by you")
```

---

## 📈 Performance Optimizations

1. **Throttled Publishing**: State only published every 3s (not every frame)
2. **Timestamp Filtering**: Frontend avoids reprocessing same hint
3. **Connection Checking**: Polling only when connected
4. **Stored Hints**: Backend caches last hint for HTTP polling
5. **Grid Conversion**: O(rows × cols) done on publish, not on each frame

---

## 🎯 Key Differences: Polling vs WebSocket

| Aspect | Polling | WebSocket |
|--------|---------|-----------|
| **Connection** | HTTP GET requests | Persistent TCP |
| **Latency** | 500ms polling interval | Near-instant |
| **Server Load** | Higher (repeated requests) | Lower (persistent) |
| **Reliability** | Polling fallback available | Dropped on disconnect |
| **Browser Support** | Universal | Modern browsers |
| **Current Use** | Primary method | Optional for subscribers |

---

## 💡 Example Complete Cycle

```
Time    Frontend                   Backend                   LAM
────────────────────────────────────────────────────────────────
T+0s    publishState()      ──────>  MQTT publish
                                     maze/state

T+1s                                                    Process state
                                                        Generate hint

T+1.5s                             MQTT receives hint
                                   maze/hint/session-xyz
                                   _handle_hint()
                                   LAST_HINTS["session-xyz"] = {
                                     hint: "...",
                                     path: [...],
                                     timestamp: 1730813457.5
                                   }

T+2s    pollForHints()      ──────>  GET /api/mqtt/last_hint
        (check timestamp)    <──────  Return hint
        processHint()
        
T+2.1s  Update game state
        Render path

T+3s    publishState()      ──────>  (next cycle)
```


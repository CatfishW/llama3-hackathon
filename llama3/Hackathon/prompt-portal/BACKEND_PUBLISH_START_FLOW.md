# Backend Processing After "Publish & Start" - Complete Flow

This document details what happens on both frontend and backend when a user clicks "Publish & Start" in the game startup modal.

---

## 🎯 User Action Flow

```
User clicks "Publish & Start"
        ↓
publishSelectedTemplate(selectedTemplateId)  [Frontend]
        ↓
doStartGame(targetCols, targetRows)          [Frontend]
        ↓
POST /api/mqtt/publish_template              [HTTP API Call]
        ↓
Backend Handler: publish_template_endpoint()
        ↓
MQTT Broker publishes to LAM
        ↓
POST /api/mqtt/publish_state                 [HTTP API Call]
        ↓
Game board renders and begins
```

---

## 🚀 Step 1: Frontend - Publish Selected Template

### Function Location
**File**: `frontend/src/pages/WebGame.tsx`
**Lines**: 1097-1108

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

### What Happens
1. Makes HTTP POST to backend with `template_id` and `reset: true`
2. Shows "Template published!" status message (1.5s)
3. If error, shows "Failed to publish template" (2s)

### Request Payload
```json
{
  "template_id": 42,
  "reset": true
}
```

---

## 🎮 Step 2: Frontend - Initialize Game Board

### Function Location
**File**: `frontend/src/pages/WebGame.tsx`
**Lines**: 983-1090

```typescript
const doStartGame = useCallback((targetCols?: number, targetRows?: number) => {
  // Reset score submission flag
  setScoreSubmitted(false)
  setGameOverTrigger(0)
  
  // Resolve board size (optionally overridden)
  const cols = (typeof targetCols === 'number') ? targetCols : boardCols
  const rows = (typeof targetRows === 'number') ? targetRows : boardRows
  
  // Apply override to state so UI reflects new board
  if (typeof targetCols === 'number' && typeof targetRows === 'number') {
    setBoardCols(targetCols)
    setBoardRows(targetRows)
  }

  // Generate maze using procedural algorithm
  const grid = generateMaze(cols, rows)

  // Ensure start area open
  grid[1][1] = 0; grid[1][2] = 0; grid[2][1] = 0

  // Place oxygen ~10% of floors excluding start/exit
  const floors: Vec2[] = []
  for (let y = 0; y < rows; y++) 
    for (let x = 0; x < cols; x++) 
      if (grid[y][x] === 0) 
        floors.push({x,y})
  
  const start = { x: 1, y: 1 }
  const exit = { x: cols - 2, y: rows - 2 }
  
  // Ensure exit is not in a wall; carve if needed
  if (grid[exit.y]?.[exit.x] !== 0) {
    grid[exit.y][exit.x] = 0
  }
```

### Board Initialization Steps

1. **Reset State**
   ```typescript
   setScoreSubmitted(false)
   setGameOverTrigger(0)
   ```

2. **Generate Maze**
   ```typescript
   const grid = generateMaze(cols, rows)
   ```
   - Procedural maze generation using depth-first search
   - Grid values: `0 = path/floor`, `1 = wall`

3. **Ensure Start Area Open**
   ```typescript
   grid[1][1] = 0; grid[1][2] = 0; grid[2][1] = 0
   ```

4. **Place Oxygen Pellets**
   ```typescript
   const floors: Vec2[] = []
   const count = Math.max(10, Math.floor(avail.length * 0.1))
   ```
   - ~10% of available floor cells
   - Excludes start and exit positions
   - Minimum 10 oxygen pellets

5. **Spawn Germs**
   ```typescript
   const spawnGerms = Math.max(0, Math.min(50, Math.floor(germCount)))
   const safeZoneRadius = 3
   ```
   - User-configurable count (0-50)
   - Minimum 3-tile radius from player start
   - Each germ has random direction and speed

6. **Initialize Game State**
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
     lam: { hint: '', path: [], breaks: 0, error: '', showPath: false, bfsSteps: 0 },
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

### Board Dimensions by Mode

| Mode | Columns | Rows | Tile Size | Canvas |
|------|---------|------|-----------|--------|
| **Manual** | 33 | 21 | 24px | 792×504 |
| **LAM** | 10 | 10 | 24px | 240×240 |

### Metrics Initialized

```typescript
metrics: {
  totalSteps: 0,                              // Total steps taken
  optimalSteps: bfsPath(...).length,          // BFS shortest path
  backtrackCount: 0,                          // Times player backtracks
  collisionCount: 0,                          // Wall/germ collisions
  deadEndEntries: 0,                          // Dead-end tile entries
  actionLatencies: [],                        // Response time array
  visitedTiles: new Set([key(1, 1)]),        // Track visited cells
  lastPosition: { x: 1, y: 1 }               // For backtrack detection
}
```

---

## 📡 Step 3: Backend - Publish Template Endpoint

### Endpoint Location
**File**: `backend/app/routers/mqtt_bridge.py`
**Lines**: 107-145

```python
@router.post("/publish_template")
def publish_template_endpoint(
    payload: dict,
    session_id: str | None = Query(default=None, description="Optional session to target"),
    reset: bool = Query(default=True, description="Reset dialog for the target(s)"),
    db: Session = Depends(get_db), 
    user=Depends(get_current_user)
):
    """Publish the selected or custom template to LAM over MQTT."""
```

### Request Validation

```python
# payload may contain either a raw template string or a template_id to load from DB
body: dict
if isinstance(payload, dict) and (tid := payload.get("template_id")):
    # Load template from database
    t = db.query(models.PromptTemplate).filter(
        models.PromptTemplate.id == tid, 
        models.PromptTemplate.user_id == user.id
    ).first()
    if not t:
        raise HTTPException(404, "Template not found or not owned by you")
```

### Template Loading

```python
body = {
    "template": t.content,
    "title": t.title,
    "version": t.version,
    "user_id": user.id,
    "reset": bool(payload.get("reset", reset)),
    "max_breaks": payload.get("max_breaks")
}
```

### Publish to MQTT

```python
publish_template(body, session_id=session_id)
return {"ok": True}
```

---

## 📬 Step 4: MQTT Publishing

### Function Location
**File**: `backend/app/mqtt.py`
**Lines**: 521-532

```python
def publish_template(template_payload: dict, session_id: str | None = None):
    """Publish a template update to the LAM over MQTT."""
    try:
        topic = settings.MQTT_TOPIC_TEMPLATE
        if session_id:
            # allow per-session override by suffixing session id
            if not topic.endswith("/"):
                topic = topic + "/" + session_id
            else:
                topic = topic + session_id
        
        result = mqtt_client.publish(
            topic, 
            json.dumps(template_payload), 
            qos=1,              # Quality of Service = 1 (At least once delivery)
            retain=False
        )
        if result.rc != 0:
            print(f"[MQTT] Failed to publish template (rc={result.rc})")
    except Exception as e:
        print(f"[MQTT] Error publishing template: {e}")
```

### MQTT Topic Format

```
Default: settings.MQTT_TOPIC_TEMPLATE
With session: settings.MQTT_TOPIC_TEMPLATE/session-id-xyz
```

### MQTT Message Structure

```json
{
  "template": "You are a Large Action Model (LAM) that controls a maze game...",
  "title": "SPARC DRIVING LLM AGENT PROMPT",
  "version": 1,
  "user_id": 42,
  "reset": true,
  "max_breaks": null
}
```

### QoS Level
- **QoS 1**: "At least once" delivery
- Ensures LAM receives the template
- May receive duplicates (handled by LAM)

---

## 📨 Step 5: Frontend - Publish Game State

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
  // Server expects visible_map semantics: 1 = floor/passable, 0 = wall
  // Client grid uses 0 = path, 1 = wall. Convert before publishing.
  const visibleMap = (s.grid && s.grid.length)
    ? s.grid.map(row => row.map(c => c === 0 ? 1 : 0))
    : []
```

### Grid Conversion Logic

**Client Internal Representation**:
```
0 = floor (passable)
1 = wall (blocked)
```

**Publish to LAM (inverted)**:
```
1 = floor (passable)     ← Changed from 0
0 = wall (blocked)       ← Changed from 1
```

### State Payload

```typescript
const body = {
  session_id: sessionId,
  template_id: templateId,
  state: {
    sessionId,
    player_pos: [s.player.x, s.player.y],
    exit_pos: [s.exit.x, s.exit.y],
    visible_map: visibleMap,                    // Converted grid
    oxygenPellets: s.oxy.map(p => ({ x: p.x, y: p.y })),
    germs: s.germs.map(g => ({ x: g.pos.x, y: g.pos.y })),
    tick: Date.now(),
    health: 100,
    oxygen: 100 - s.oxygenCollected            // Depletes as oxygen collected
  }
}
```

### API Call

```typescript
try { 
  await api.post('/api/mqtt/publish_state', body) 
} catch (e) { 
  /* ignore */ 
}
```

---

## 🔄 Step 6: Backend - Publish State Endpoint

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
    # Fetch the template content to embed into state, so LAM can use it
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

### Template Embedding

The endpoint enriches the state with full template content:

```python
state.update({
  "sessionId": payload.session_id,
  "prompt_template": {
    "title": t.title,
    "content": t.content,         # Full system prompt
    "version": t.version,
    "user_id": user.id,
  }
})
```

---

## 📬 Step 7: MQTT State Publishing

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
            qos=0,                # Fire-and-forget (no retry)
            retain=False
        )
        if result.rc != 0:
            print(f"[MQTT] Failed to publish state (rc={result.rc})")
    except Exception as e:
        print(f"[MQTT] Error publishing state: {e}")
```

### MQTT Topic
```
settings.MQTT_TOPIC_STATE
```

### MQTT Message (Full Example)
```json
{
  "sessionId": "session-abc123",
  "player_pos": [1, 1],
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
    { "x": 5, "y": 4 }
  ],
  "germs": [
    { "x": 4, "y": 3 },
    { "x": 6, "y": 5 }
  ],
  "tick": 1730813456789,
  "health": 100,
  "oxygen": 95,
  "prompt_template": {
    "title": "SPARC DRIVING LLM AGENT PROMPT",
    "content": "You are a Large Action Model (LAM)...",
    "version": 1,
    "user_id": 42
  }
}
```

### QoS Level
- **QoS 0**: Fire-and-forget (no retry)
- Fast, best-effort delivery
- Suitable for frequent state updates

---

## 🎨 Data Schema References

### Frontend Request Schema
**File**: `backend/app/schemas.py`

```python
class PublishStateIn(BaseModel):
    session_id: str
    template_id: int
    state: dict  # Game state object
```

### Template Schema

```python
class TemplateBase(BaseModel):
    title: str
    description: Optional[str] = ""
    content: str
    is_active: bool = True
    version: int = 1

class TemplateOut(TemplateBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
```

---

## 🔄 Periodic State Publishing

### Function Location
**File**: `frontend/src/pages/WebGame.tsx`
**Lines**: 1204-1214

```typescript
// Periodic publisher: uses mqttSendRate setting, while game is running
useEffect(() => {
  const periodMs = mqttSendRate
  if (!stateRef.current.started) return
  
  const interval = setInterval(() => {
    publishState()
  }, periodMs)
  
  return () => clearInterval(interval)
}, [templateId, publishState, mqttSendRate])
```

### Publishing Rate
- Default: **3000ms** (3 seconds)
- User-adjustable: 500ms - 60s
- Throttled to prevent overload
- Only while game is running

---

## 🎯 Complete Sequence Diagram

```
┌─────────────────┐                          ┌──────────────┐
│   Frontend      │                          │   Backend    │
│                 │                          │              │
└────────┬────────┘                          └──────┬───────┘
         │                                          │
    1. Click "Publish & Start"                      │
         │                                          │
    2. publishSelectedTemplate(tid)                 │
         ├─ POST /api/mqtt/publish_template         │
         ├──────────────────────────────────────>  │
         │                                    3. Fetch template from DB
         │                                    4. Validate ownership
         │                                    5. Construct message
         │                                    6. MQTT publish
         │                                          │
         │   <─ {"ok": True}────────────────────────┤
         │                                          │
    7. doStartGame(cols, rows)                      │
         │                                          │
    8. generateMaze()                               │
    9. Initialize game state                        │
   10. Setup metrics                                │
         │                                          │
   11. publishState() [Initial]                     │
         ├─ POST /api/mqtt/publish_state            │
         ├──────────────────────────────────────>  │
         │                                   12. Fetch template
         │                                   13. Embed in state
         │                                   14. MQTT publish
         │                                          │
         │   <─ {"ok": True}────────────────────────┤
         │                                          │
   15. Game render loop starts                      │
         │                                          │
   16. Periodic publishState() [Every 3s]           │
         ├─ POST /api/mqtt/publish_state            │
         ├──────────────────────────────────────>  │
         │                                   ... (repeats)
         │                                          │
        ...                                        ...
```

---

## ⚙️ Configuration Variables

### MQTT Topics (from settings)
```python
MQTT_TOPIC_STATE = "maze/state"
MQTT_TOPIC_TEMPLATE = "maze/template"
MQTT_TOPIC_HINT = "maze/hint"
```

### Frontend Settings
```typescript
mqttSendRate: 3000              // ms, user-configurable
germCount: 0                    // germs, user-configurable
gameMode: 'manual' | 'lam'      // mode selection
```

### Backend Settings
```python
settings.MQTT_BROKER_HOST
settings.MQTT_BROKER_PORT
settings.MQTT_USERNAME
settings.MQTT_PASSWORD
```

---

## 🔍 Error Handling

### Frontend Error Handling
```typescript
try {
  await api.post('/api/mqtt/publish_template', { template_id: tid, reset: true })
  setStatus('Template published!')
} catch (e) {
  setStatus('Failed to publish template')
}
```

### Backend Error Handling
```python
if not t:
    raise HTTPException(404, "Template not found or not owned by you")

# MQTT errors
if result.rc != 0:
    print(f"[MQTT] Failed to publish template (rc={result.rc})")
```

---

## 📊 Performance Notes

1. **State Publishing**: Throttled at user-configurable interval (default 3s)
2. **Template Publishing**: One-time publish with QoS 1 (guaranteed delivery)
3. **Grid Conversion**: O(rows × cols) operation on each state publish
4. **Database Lookup**: One query per request (user + template_id filter)
5. **MQTT QoS Difference**:
   - Template: QoS 1 (ensure LAM gets the prompt)
   - State: QoS 0 (fast, frequent updates)

---

## 🔐 Security & Validation

### Template Ownership Verification
```python
t = db.query(models.PromptTemplate).filter(
    models.PromptTemplate.id == tid, 
    models.PromptTemplate.user_id == user.id  # Ownership check
).first()
```

### User Authentication
```python
user=Depends(get_current_user)  # JWT token required
```

### Request Validation
```python
if not t:
    raise HTTPException(404, "Template not found or not owned by you")
```


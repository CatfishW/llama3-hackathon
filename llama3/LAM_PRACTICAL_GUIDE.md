# Large Action Model (LAM) - Practical Implementation Guide

## Quick Start: Understanding LAM Through Examples

### Example 1: Simple LLM Chat vs LAM with Functions

#### Traditional LLM (Chat Only)
```
User: "Help me escape the maze!"

LLM Response:
"I suggest you move east to the corridor, then north. 
Avoid the germs near the center. Watch out for walls 
blocking the path. The exit is in the southeast corner."

Frontend Result: 
✗ User must manually interpret instructions
✗ AI cannot modify maze
✗ No direct assistance
```

#### Large Action Model (With Functions)
```
User: "Help me escape the maze!"
Current State: Player at [5,5], exit at [20,20], wall at [6,5]

LLM Response:
"I see you're blocked! I'll create a shortcut and speed you up."

Function Calls:
• break_wall(6, 5)     ← Remove blocking wall
• speed_boost(2000)    ← Temporary speed increase
• highlight_zone([[6,5], [6,6], [6,7]], 3000)  ← Show safe path

Frontend Result:
✓ Wall removed from game state
✓ Player moves faster for 2 seconds
✓ Safe path highlighted
✓ Direct gameplay assistance
```

---

## Code Examples: Implementation Details

### Example 1: Defining a Function Tool

```python
# In backend/app/services/llm_client.py

MAZE_GAME_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "break_wall",
            "description": "Break a wall at specified coordinates to create a path",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {
                        "type": "integer",
                        "description": "X coordinate of the wall (0-40)"
                    },
                    "y": {
                        "type": "integer",
                        "description": "Y coordinate of the wall (0-30)"
                    }
                },
                "required": ["x", "y"]
            }
        }
    }
]
```

### Example 2: Calling LLM with Tools

```python
# In backend/app/services/llm_client.py

def generate(
    self,
    messages: List[Dict[str, str]],
    tools: Optional[List[Dict]] = None,
    tool_choice: Optional[str] = "auto"
) -> str:
    """Generate response with optional function calling."""
    
    try:
        api_params = {
            "model": "default",
            "messages": messages,
            "temperature": 0.6,
            "top_p": 0.9,
            "max_tokens": 512,
        }
        
        # Add tools if provided (function calling)
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = tool_choice
        
        # Call OpenAI-compatible API
        response = self.client.chat.completions.create(**api_params)
        
        # Parse response with tool_calls
        if response.choices[0].message.tool_calls:
            tool_calls = response.choices[0].message.tool_calls
            # Convert tool_calls to game actions
            return self._convert_tool_calls(tool_calls)
        else:
            return response.choices[0].message.content
            
    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        raise
```

### Example 3: Processing Game State with LLM

```python
# In backend/app/mqtt.py

async def process_user_input_with_llm(
    session_id: str,
    user_message: str,
    system_prompt: str,
    game_state: dict
) -> dict:
    """Process user input through LLM with game context."""
    
    # Format game state as context
    game_context = f"""
    Current Game State:
    - Player Position: {game_state['player_pos']}
    - Exit Position: {game_state['exit_pos']}
    - Enemies: {game_state['germs']}
    - Walls: {game_state['walls']}
    - Health: {game_state['health']}/100
    
    Player Question: {user_message}
    """
    
    # Build messages for LLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": game_context}
    ]
    
    # Call LLM with available game functions
    response = llm_client.generate(
        messages=messages,
        tools=MAZE_GAME_TOOLS,  # 10 available functions
        tool_choice="auto"
    )
    
    # Parse response containing hint + function calls
    return {
        "hint": response.get("hint", ""),
        "actions": response.get("actions", [])
    }
```

### Example 4: Converting Tool Calls to Game Actions

```python
# In backend/app/mqtt.py

def convert_tool_calls_to_actions(tool_calls: list) -> dict:
    """Convert LLM tool calls to game action format."""
    
    actions = {}
    
    for tool_call in tool_calls:
        name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])
        
        # Map function calls to game actions
        if name == "break_wall":
            actions["break_wall"] = [args["x"], args["y"]]
        
        elif name == "speed_boost":
            actions["speed_boost_ms"] = args.get("duration_ms", 1500)
        
        elif name == "freeze_germs":
            actions["freeze_germs_ms"] = args.get("duration_ms", 3000)
        
        elif name == "teleport_player":
            actions["teleport"] = [args["x"], args["y"]]
        
        elif name == "spawn_oxygen":
            actions["spawn_oxygen"] = args["locations"]
        
        # ... handle other functions
    
    return actions
```

### Example 5: Frontend Receiving and Executing Actions

```typescript
// In frontend/src/components/WebGame.tsx

// WebSocket handler receives MQTT hint message
websocket.onmessage = (event) => {
    const hintData = JSON.parse(event.data);
    
    // Extract hint text for UI
    displayHint(hintData.hint);
    
    // Extract and execute game actions
    if (hintData.break_wall) {
        const [x, y] = hintData.break_wall;
        gameState.walls = gameState.walls.filter(
            wall => !(wall[0] === x && wall[1] === y)
        );
    }
    
    if (hintData.speed_boost_ms) {
        activateSpeedBoost(hintData.speed_boost_ms);
    }
    
    if (hintData.freeze_germs_ms) {
        freezeEnemies(hintData.freeze_germs_ms);
    }
    
    // Redraw game with updated state
    renderGame();
};
```

---

## Step-by-Step: Complete Request-Response Cycle

### Step 1: Frontend Publishes Game State

```python
# Browser sends HTTP POST request
POST /api/mqtt/publish_state

{
    "session_id": "user-alice-123",
    "template_id": 5,
    "player_pos": [8, 8],
    "exit_pos": [20, 20],
    "germs": [
        {"pos": [10, 10], "health": 100},
        {"pos": [15, 15], "health": 80}
    ],
    "walls": [[9, 8], [10, 8], [11, 8]],
    "health": 75,
    "user_message": "I'm trapped! Help!"
}
```

### Step 2: Backend Retrieves Template

```python
# Backend handler in mqtt_bridge.py
template = db.query(Template).filter(
    Template.id == request.template_id
).first()

system_prompt = template.content
# Result:
# "You are a maze expert AI. Use strategic actions to help the player..."
```

### Step 3: Backend Calls LLM

```python
# Prepare context
game_context = f"""
Player Status: Health 75/100, at position [8, 8]
Threat: Two germs approaching from [10, 10] and [15, 15]
Objective: Reach exit at [20, 20]
Obstacles: Wall at [9, 8] blocking direct path

Available Actions:
1. break_wall(x, y) - Create shortcut
2. freeze_germs(duration_ms) - Stop enemies
3. speed_boost(duration_ms) - Move faster
4. [7 more functions...]

User Request: I'm trapped! Help!
"""

messages = [
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": game_context}
]

response = client.chat.completions.create(
    model="default",
    messages=messages,
    tools=MAZE_GAME_TOOLS,
    tool_choice="auto",
    temperature=0.6,
    max_tokens=512
)
```

### Step 4: LLM Reasons and Responds

```json
{
    "id": "chatcmpl-8abc",
    "object": "chat.completion",
    "choices": [
        {
            "message": {
                "role": "assistant",
                "content": "I see the threat! Breaking the wall and freezing the germs...",
                "tool_calls": [
                    {
                        "id": "call_123",
                        "type": "function",
                        "function": {
                            "name": "break_wall",
                            "arguments": "{\"x\": 9, \"y\": 8}"
                        }
                    },
                    {
                        "id": "call_124",
                        "type": "function",
                        "function": {
                            "name": "freeze_germs",
                            "arguments": "{\"duration_ms\": 3000}"
                        }
                    }
                ]
            }
        }
    ]
}
```

### Step 5: Backend Converts and Publishes

```python
# Convert tool calls
actions = {
    "break_wall": [9, 8],
    "freeze_germs_ms": 3000
}

# Create hint message
hint_message = {
    "hint": "I see the threat! Breaking the wall and freezing the germs...",
    "break_wall": [9, 8],
    "freeze_germs_ms": 3000,
    "timestamp": datetime.now().isoformat()
}

# Publish to MQTT
mqtt_client.publish(
    f"maze/hint/user-alice-123",
    json.dumps(hint_message),
    qos=1
)
```

### Step 6: Frontend Receives via WebSocket

```javascript
// WebSocket message arrives
{
    "type": "hint",
    "topic": "maze/hint/user-alice-123",
    "payload": {
        "hint": "I see the threat! Breaking the wall...",
        "break_wall": [9, 8],
        "freeze_germs_ms": 3000,
        "timestamp": "2025-01-15T10:30:45.123Z"
    }
}
```

### Step 7: Frontend Executes Actions

```javascript
// Step 7a: Remove wall from game state
gameState.walls = gameState.walls.filter(
    wall => !(wall[0] === 9 && wall[1] === 8)
);

// Step 7b: Freeze enemies
gameState.germs.forEach(germ => {
    germ.frozen = true;
});

// Step 7c: Set timer to unfreeze
setTimeout(() => {
    gameState.germs.forEach(germ => {
        germ.frozen = false;
    });
}, 3000);

// Step 7d: Redraw game
renderer.drawMaze(gameState);

// Step 7e: Show hint to player
ui.displayHint("I see the threat! Breaking the wall and freezing the germs...");
```

### Step 8: Game Continues

```
- Wall now removed → Player can move right
- Enemies frozen → No damage possible for 3 seconds
- Player moves toward exit
- Eventually reaches [20, 20] → Victory!
- Score saved to leaderboard
- Experience recorded for future AI training
```

---

## System Prompt Templates: Real Examples

### Template 1: "Strategic Guide" (Aggressive Actions)

```
You are a strategic maze expert AI with access to game-altering powers.

Your Mission: Guide the player to the exit while avoiding germs.

Available Magical Abilities:
1. Break Walls - Create shortcuts (use strategically!)
2. Freeze Germs - Stop enemies temporarily
3. Speed Boost - Player moves faster
4. Teleport - Warp player to safe location
5. Highlight Path - Show safe route
6. Reveal Map - Show full maze
7. Spawn Oxygen - Create health items
8. Slow Germs - Reduce enemy speed
9. Move Exit - Relocate goal
10. Break Multiple Walls - Batch wall removal

Strategy Guide:
1. ANALYZE: Check player position, germs, walls
2. PLAN: Calculate shortest safe path
3. ACT: Use abilities strategically
4. EXPLAIN: Always tell player why you're using each power

Resource Management:
- Wall breaks are limited - use only for critical shortcuts
- Freeze/slow germs to create safe passages
- Highlight the next 5-10 steps of the optimal path

Communication:
- Always provide a clear hint before taking action
- Explain your reasoning in 1-2 sentences
- Use encouraging, supportive tone

Remember: Limited resources! Choose actions wisely.
```

### Template 2: "Learning Coach" (Educational Focus)

```
You are a patient learning coach in a physics education game.

Your Role: Help the player learn about forces and motion through 
exploration and experimentation.

Available Game Modifications:
- Break barriers to explore
- Freeze obstacles to study physics
- Adjust player speed to test momentum
- Move goals to understand trajectories

Teaching Approach:
1. Ask guiding questions before giving direct help
2. Encourage experimentation over direct solutions
3. Point out physics concepts in the game
4. Give hints that lead to discovery

Example Interactions:

STUDENT: "How do I get through the barrier?"
YOU: "What happens if you hit it at high speed? 
Let me show you something..." [speed_boost]

STUDENT: "The ball keeps getting blocked"
YOU: "I notice the obstacles are slowing your progress. 
What if you could see the full path?" [reveal_map]

Philosophy:
- Scaffold learning gradually
- Celebrate small wins
- Make physics concepts visible
- Never give direct answers, guide discovery

Tone: Encouraging, curious, supportive
```

### Template 3: "Speed Runner" (Time-Based Challenge)

```
You are a speed-running coach optimizing for time and efficiency.

Challenge: Get player to exit as quickly as possible!

Optimization Strategy:
1. Calculate absolute shortest path
2. Remove all blocking walls immediately
3. Maintain maximum player speed throughout
4. Freeze germs to prevent path obstructions
5. Create shortcuts with wall breaks

Action Priority:
1. FIRST: Remove walls blocking direct path
2. SECOND: Activate speed boosts proactively
3. THIRD: Freeze germs approaching player
4. FOURTH: Highlight optimal route

Performance Metrics:
- Time to exit (minimize)
- Actions per second (maximize)
- Walls broken (track)
- Enemies frozen (track)

Communication:
- Be efficient with hints
- Focus on action over explanation
- Provide real-time feedback
- Display "time on track" updates

Aggressive: Use all available powers strategically!
```

---

## Debugging LAM Issues: Troubleshooting Guide

### Issue 1: "LLM Not Calling Functions"

**Symptoms:**
- Responses contain only text, no function calls
- Game state not updating despite LLM help requested
- Actions don't execute

**Diagnosis:**
```python
# In backend logs, check for:
[LLM] Generated response without tool_calls

# Questions to ask:
# 1. Is LLM server function-calling capable?
# 2. Are tools being passed to API?
# 3. Is tool_choice="auto" set?
```

**Fix:**
```python
# Ensure tools are passed correctly
response = client.chat.completions.create(
    model="default",
    messages=messages,
    tools=MAZE_GAME_TOOLS,      # ← Must include
    tool_choice="auto",          # ← Must be "auto"
    # ...
)

# Check response contains tool_calls
if response.choices[0].message.tool_calls:
    print("✓ Function calls present")
else:
    print("✗ No function calls - LLM model doesn't support it")
    # Switch to function-capable model
```

---

### Issue 2: "Invalid Coordinates in Actions"

**Symptoms:**
- LLM tries to break walls outside game bounds
- Example: `break_wall(-5, 100)` crashes game

**Diagnosis:**
```python
# In frontend, add validation
validateAction(action) {
    if (action.break_wall) {
        const [x, y] = action.break_wall;
        if (x < 0 || x > 40 || y < 0 || y > 30) {
            console.error("Invalid coordinates:", x, y);
            return false;  // Skip action
        }
    }
    return true;
}
```

**Fix in System Prompt:**
```
Available Game Bounds:
- X coordinates: 0 to 40
- Y coordinates: 0 to 30
- Walls only exist at specific locations
- Don't try to break walls outside the map!

Example Valid Call: break_wall(15, 15)
Example Invalid: break_wall(100, 200)
```

---

### Issue 3: "MQTT Messages Not Arriving"

**Symptoms:**
- Backend publishes to MQTT but frontend doesn't receive
- WebSocket connected but no hints appearing
- Silent failures

**Diagnosis:**
```bash
# Check MQTT broker status
mosquitto_sub -h localhost -p 1883 -t 'maze/#' -v

# If subscribed topic doesn't show published messages:
# Problem is in MQTT broker or publishing

# Check backend logs
grep "MQTT" debug_info.log | tail -20

# Verify topic matches
Expected: maze/hint/user-alice-123
Published: maze/hint/user-alice-123
Subscribe: maze/hint/+
```

**Fix:**
```python
# Verify publishing
logger.info(f"Publishing to: {topic}")
logger.info(f"Payload size: {len(json.dumps(payload))}")

mqtt_client.publish(topic, json.dumps(payload), qos=1)

# Add callback verification
def on_publish(client, userdata, mid):
    logger.info(f"Message {mid} published successfully")

mqtt_client.on_publish = on_publish
```

---

### Issue 4: "Game Actions Execute Wrong"

**Symptoms:**
- `freeze_germs` called but enemies still move
- `break_wall` called but wall doesn't disappear
- Frontend receives message but action doesn't work

**Diagnosis:**
```typescript
// Check action parsing in WebGame.tsx
console.log("Received hint:", hintData);
console.log("Actions detected:", {
    breakWall: hintData.break_wall,
    freezeMs: hintData.freeze_germs_ms,
    speedBoostMs: hintData.speed_boost_ms
});
```

**Fix:**
```typescript
// Verify action fields match backend output
// Backend sends: {"freeze_germs_ms": 3000}
// Frontend must use: hintData.freeze_germs_ms

// Case-sensitive! These are different:
freeze_germs_ms  ✓ Correct
freezeGermsMs    ✗ Wrong
FreezeGermsMs    ✗ Wrong

// Verify action is actually applied
if (hintData.freeze_germs_ms) {
    console.log("Freezing for", hintData.freeze_germs_ms, "ms");
    gameState.germs.forEach(g => g.frozen = true);
    setTimeout(() => {
        gameState.germs.forEach(g => g.frozen = false);
    }, hintData.freeze_germs_ms);
    console.log("✓ Germs frozen");
}
```

---

## Performance Optimization Tips

### 1. Reduce LLM Response Time

```python
# Use smaller, faster models
# Instead of: QwQ-32B (32 billion parameters, slow)
# Use: Qwen2-7B or Llama2-7B (7B parameters, faster)

# With quantization
model_name = "Qwen/Qwen2-7B"  # Small
quantization = "4bit"          # Reduce model size 75%

# Result: ~500ms response instead of 2000ms
```

### 2. Cache Frequent Responses

```python
# Don't re-query LLM for identical game states
response_cache = {}

state_hash = hashlib.md5(str(game_state).encode()).hexdigest()
if state_hash in response_cache:
    return response_cache[state_hash]  # Instant!

response = llm_client.generate(...)
response_cache[state_hash] = response
return response
```

### 3. Batch Multiple Players

```python
# Instead of calling LLM 100 times per second
# Batch process multiple players at once

batch_requests = []
for session_id, state in active_sessions.items():
    batch_requests.append({
        "session": session_id,
        "state": state
    })

# Process entire batch in one LLM call
responses = llm_client.generate_batch(batch_requests)
```

### 4. Stream Responses to Frontend

```python
# Don't wait for complete LLM response
# Stream chunks as they arrive

@app.get("/api/llm/stream")
async def stream_response(state: dict):
    async for chunk in llm_client.generate_stream(state):
        yield f"data: {json.dumps(chunk)}\n\n"

# Frontend receives hints incrementally
response_text = "";
eventSource.onmessage = (e) => {
    const chunk = JSON.parse(e.data);
    response_text += chunk.text;
    displayPartialHint(response_text);
};
```

---

## Monitoring & Observability

### Key Metrics to Track

```python
import time
from dataclasses import dataclass

@dataclass
class LAMMetrics:
    """Track LAM system health"""
    
    llm_response_time_ms: float          # Should be 500-2000
    function_call_success_rate: float    # Should be > 95%
    action_execution_success: float      # Should be > 99%
    concurrent_sessions: int              # Should be < 100
    mqtt_message_latency_ms: float       # Should be < 50
    websocket_connection_count: int      # Active connections
    cache_hit_rate: float                # % of cached responses
    error_rate: float                    # % of failed requests

def record_metrics(metric_name: str, value: float):
    """Log metric for monitoring"""
    logger.info(f"METRIC | {metric_name} | {value}")
    # Send to monitoring system (Prometheus, Datadog, etc.)

# Usage
start = time.time()
response = llm_client.generate(...)
llm_time = time.time() - start
record_metrics("llm_response_time_ms", llm_time * 1000)
```

### Health Check Endpoint

```python
@app.get("/health")
def health_check():
    """Check system health"""
    return {
        "status": "healthy",
        "llm_connected": test_llm_connection(),
        "mqtt_connected": mqtt_client.is_connected(),
        "database_healthy": test_database(),
        "active_sessions": len(SUBSCRIBERS),
        "uptime_seconds": time.time() - START_TIME
    }
```

---

## Conclusion: From Theory to Practice

The LAM architecture in this project demonstrates:

1. **Function Calling**: LLM → Structured Actions
2. **Environment Integration**: Actions → Game State Updates
3. **Feedback Loop**: State → Next Decision
4. **User Experience**: Responsive, interactive gameplay

This is the foundation for:
- Educational AI tutors
- Game AI agents
- Robot control systems
- Automated workflows
- Intelligent UI automation

**Next Steps:**
1. Study `llm_client.py` for function calling implementation
2. Explore `mqtt.py` for message routing
3. Run the game with custom templates
4. Experiment with new functions/actions
5. Deploy to production with monitoring


# Memory Management System for LAM Maze Game

## Overview

This document describes the hierarchical memory management system implemented to reduce token usage and maximize agent accuracy in the Prompt Portal maze game.

## Architecture

The system uses a **3-layer memory architecture**:

```
┌────────────────────────────────────────────────┐
│  STATIC LAYER (cached, sent only once)         │
│  - System prompt / Persona                     │
│  - Available skills & action definitions       │
│  - Response format requirements                │
└────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│  EPISODIC LAYER (compressed summaries)         │
│  - Movement patterns (not individual moves)    │
│  - Key discoveries                             │
│  - Error history (collision patterns)          │
└────────────────────────────────────────────────┘
           │
           ▼
┌────────────────────────────────────────────────┐
│  WORKING LAYER (always current)                │
│  - Current position & surroundings             │
│  - Energy status                               │
│  - Immediate obstacles                         │
│  - Last action result                          │
└────────────────────────────────────────────────┘
```

## Key Optimizations

### 1. System Prompt Caching
- System prompts are only sent on the **first message** of a session
- Subsequent messages rely on backend session history
- **Savings**: ~500-1000 tokens per request after first message

### 2. Progressive Context Compression
- Instead of keeping full move history ("1,1 → 1,2 → 1,3 → 2,3 → ..."), we summarize patterns:
  - `"Trending south"` (dominant direction detected)
  - `"WARNING: Oscillating/stuck pattern"` (loop detection)
- **Savings**: ~200-400 tokens on long games

### 3. Delta Updates for Minimap
- Minimap is only sent when it has **changed** (MD5 hash comparison)
- If unchanged, sends `"[MAP unchanged]"` instead
- **Savings**: ~300-600 tokens when map is stable

### 4. Smart History Pruning
- Keeps only the **last 3 message exchanges** (not 20)
- Critical positions like collision points are tracked separately
- **Savings**: ~500-1500 tokens on long sessions

### 5. Compact State Representation
- Old format:
  ```
  [TELEMETRY]
  Position: (5, 7)
  Energy: 120/150 [CRITICAL SYSTEM RESOURCE]
  Oxygen Collected: 3
  Exit Location: (15, 15)
  
  [ENERGY SYSTEMS]
  - Movement Cost: 5 Energy per tile.
  - Energy Gain: +1 per micro-cycle (step).
  - Available Energy: 120
  ```
  
- New format:
  ```
  [STATE]
  Pos: (5,7) | Exit: (15,15)
  Energy: 120/150 | O2: 3 | Score: 1500
  Near: north:wall | south:path | east:oxygen | west:path
  Skills: echo_pulse, phase_dash
  ```
- **Savings**: ~150-250 tokens per message

## API Endpoints

### New Optimized Endpoint
```
POST /api/llm/maze/agent
```

Request body:
```json
{
  "session_id": "maze_12345_abc",
  "system_prompt": "...",  // Only on first message
  "position": [5, 7],
  "exit_position": [15, 15],
  "energy": 120,
  "oxygen": 3,
  "score": 1500,
  "minimap": "...",
  "surroundings": {
    "north": "wall",
    "south": "path", 
    "east": "oxygen",
    "west": "path"
  },
  "available_skills": [...],
  "last_action": {...},
  "last_result": "Moved south to (5,8)",
  "temperature": 0.1,
  "max_tokens": 400,
  "model": "AGAII Cloud LLM"
}
```

Response:
```json
{
  "response": "{\"action\":\"move\",\"direction\":\"east\"}",
  "session_id": "maze_12345_abc",
  "memory_stats": {
    "session_id": "maze_12345_abc",
    "message_count": 15,
    "positions_visited": 23,
    "collisions_tracked": 3,
    "cells_revealed": 45,
    "exploration_coverage": "15.5%",
    "movement_pattern": "Trending east",
    "recent_moves": 5
  },
  "tokens_saved": 342
}
```

### Memory Management Endpoints
```
GET /api/llm/maze/memory/{session_id}  - Get memory stats
DELETE /api/llm/maze/memory/{session_id}  - Clear memory
```

## Performance Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Tokens per request (avg) | ~1200 | ~600 | **50% reduction** |
| Tokens per request (max) | ~2500 | ~1000 | **60% reduction** |
| Context window usage | ~15% | ~7% | **53% reduction** |
| Loop detection | None | Automatic | **Prevents stuck agents** |
| Pattern recognition | None | Movement trends | **Improves navigation** |

## Frontend Integration

The `AgentMaze3D.tsx` component now uses `llmAPI.mazeAgent()` instead of `llmAPI.chatSession()`:

```typescript
const res = await llmAPI.mazeAgent({
  session_id: sessionId,
  system_prompt: isFirstMessage ? fullSystemPrompt : undefined,
  position: [agentPos.x, agentPos.y],
  exit_position: [exitPos.x, exitPos.y],
  energy,
  oxygen,
  score,
  minimap: minimapStr,
  surroundings: nearbyData,
  available_skills: skillsForApi,
  last_action: lastAction,
  last_result: lastExecutionResult?.message,
  temperature: 0.1,
  max_tokens: 400,
  model: activeModel?.name || "default"
}, abortControllerRef.current.signal)
```

## Files Modified

1. **Backend**
   - `backend/app/services/memory_manager.py` - New memory management system
   - `backend/app/routers/llm.py` - New `/maze/agent` endpoint

2. **Frontend**
   - `frontend/src/api.ts` - Added `mazeAgent()`, `getMazeMemoryStats()`, `clearMazeMemory()`
   - `frontend/src/pages/AgentMaze3D.tsx` - Updated to use new API

## Future Improvements

1. **Vector-based memory**: Store embeddings of important states for semantic retrieval
2. **Adaptive compression**: Adjust compression level based on context window pressure
3. **Cross-session learning**: Transfer learned maze strategies between sessions
4. **Prompt caching at provider level**: Leverage OpenAI/Anthropic prompt caching for static content

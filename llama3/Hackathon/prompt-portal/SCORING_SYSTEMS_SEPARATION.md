# Scoring Systems Separation

## ⚠️ IMPORTANT: Two Completely Separate Scoring Systems

The platform has **TWO DISTINCT** scoring systems that should **NEVER** be mixed:

---

## 🎮 1. Maze Game Scoring (LAM/Manual Mode)

### Purpose
Testing prompt templates for maze navigation agents.

### Mode Values
- `mode: "lam"` - LAM (Large Action Model) controls
- `mode: "manual"` - Player controls

### Metrics Used
```python
# Maze-specific fields
total_steps: int                # Total steps taken
optimal_steps: int              # Optimal solution steps
backtrack_count: int            # Times backtracked
collision_count: int            # Wall collisions
dead_end_entries: int           # Dead ends entered
avg_latency_ms: float          # Response time

# Legacy fields
survival_time: float
oxygen_collected: int
germs: int
```

### Submission Example
```json
{
  "mode": "lam",
  "score": 0,
  "new_score": 8500,
  "total_steps": 45,
  "collision_count": 2,
  "backtrack_count": 3,
  ...
}
```

---

## 🏁 2. Driving Game Scoring

### Purpose
Testing prompt templates for the "Cap" physics learning agent.

### Mode Value
- `mode: "driving_game"` - **ONLY** this mode

### Metrics Used
```python
# Driving Game ONLY fields
driving_game_consensus_reached: bool    # Consensus achieved
driving_game_message_count: int         # Messages exchanged
driving_game_duration_seconds: float    # Time taken
driving_game_player_option: str         # Player's choice
driving_game_agent_option: str          # Agent's choice

# These should be NULL/default for Driving Game
total_steps: None
collision_count: None
backtrack_count: None
...
```

### Submission Example
```json
{
  "mode": "driving_game",
  "score": 0,
  "new_score": 850,
  "survival_time": 0,
  "oxygen_collected": 0,
  "germs": 0,
  "driving_game_consensus_reached": true,
  "driving_game_message_count": 3,
  "driving_game_duration_seconds": 45.2,
  "driving_game_player_option": "a",
  "driving_game_agent_option": "a"
}
```

---

## 🔒 Separation Rules

### Backend Validation

The backend **MUST** enforce:

1. **Mode-specific fields only:**
   - If `mode == "driving_game"` → Only Driving Game fields should be populated
   - If `mode == "lam"` or `"manual"` → Only Maze fields should be populated

2. **Cross-contamination prevention:**
   - Driving Game scores should NOT have `total_steps`, `collision_count`, etc.
   - Maze scores should NOT have `driving_game_*` fields

3. **Leaderboard filtering:**
   - Each mode shows ONLY its relevant scores
   - No mixing in the same view

### Frontend Display

The frontend **MUST** show:

1. **Mode-specific metrics only:**
```typescript
if (mode === 'driving_game') {
  // Show: Messages, Time, Consensus
  // Hide: Steps, Collisions, Backtracks
} else {
  // Show: Steps, Collisions, Backtracks
  // Hide: Messages, Time, Consensus
}
```

2. **Clear mode indicators:**
   - Driving Game: 🏁 emoji and "Prompt Testing" label
   - LAM Mode: "LLM controls" label
   - Manual Mode: "You control" label

---

## 🐛 Current Issue in Screenshot

The screenshot shows Driving Game leaderboard with entries that have:
- ❌ **No Driving Game metrics** (showing "—")
- ❌ **Wrong templates** ("lam mode", "Sample Template")
- ❌ **These are likely Maze game scores** being displayed in Driving Game view

### Possible Causes:

1. **Old test data** was submitted with `mode="driving_game"` but without proper metrics
2. **Database has mixed entries** from before clear separation
3. **Migration issue** - old scores don't have `mode` field set correctly

### Solution:

**Clean up test data:**
```sql
-- Delete invalid Driving Game scores (those without driving_game metrics)
DELETE FROM scores 
WHERE mode = 'driving_game' 
  AND driving_game_consensus_reached IS NULL;

-- OR update their mode to prevent confusion
UPDATE scores 
SET mode = 'manual' 
WHERE mode = 'driving_game' 
  AND driving_game_consensus_reached IS NULL;
```

---

## ✅ Validation Checklist

### Before Submitting a Driving Game Score:

- [ ] `mode` is set to `"driving_game"`
- [ ] `driving_game_consensus_reached` is `true`
- [ ] `driving_game_message_count` is populated
- [ ] `driving_game_duration_seconds` is populated
- [ ] `driving_game_player_option` is populated
- [ ] `driving_game_agent_option` is populated
- [ ] Maze fields are `None`/null/0

### Before Submitting a Maze Score:

- [ ] `mode` is `"lam"` or `"manual"`
- [ ] `total_steps` is populated
- [ ] Other maze metrics are populated as needed
- [ ] All `driving_game_*` fields are `None`/null

---

## 📊 Database Schema Clarity

### Shared Fields (Both Systems)
```sql
id, user_id, template_id, session_id, created_at
score (deprecated)
new_score (primary score)
```

### Maze Game Fields (LAM/Manual ONLY)
```sql
survival_time, oxygen_collected, germs
total_steps, optimal_steps, backtrack_count
collision_count, dead_end_entries, avg_latency_ms
```

### Driving Game Fields (driving_game ONLY)
```sql
driving_game_consensus_reached
driving_game_message_count
driving_game_duration_seconds
driving_game_player_option
driving_game_agent_option
```

---

## 🎯 Best Practices

### 1. Clear Template Naming
- **Maze templates:** Include "Maze", "Navigator", "LAM" in name
- **Driving templates:** Include "Driving", "Cap", "Physics" in name

### 2. Testing Isolation
- Test Maze prompts in WebGame or TestMQTT
- Test Driving prompts ONLY in ChatBot with Driving Game mode

### 3. Score Interpretation
- **Maze:** Higher score = better navigation (fewer errors)
- **Driving:** Higher score = faster consensus (fewer messages)

---

## 🔧 Recommended Backend Update

Add validation in `leaderboard.py`:

```python
@router.post("/submit", response_model=schemas.ScoreOut)
def submit_score(payload: schemas.ScoreCreate, ...):
    # Validate mode-specific fields
    if payload.mode == "driving_game":
        if not payload.driving_game_consensus_reached:
            raise HTTPException(400, "Driving Game scores require consensus_reached=true")
        if payload.driving_game_message_count is None:
            raise HTTPException(400, "Driving Game scores require message_count")
        # Clear maze fields
        payload.total_steps = None
        payload.collision_count = None
        payload.backtrack_count = None
        # ... etc
    
    elif payload.mode in ("lam", "manual"):
        # Clear driving game fields
        payload.driving_game_consensus_reached = None
        payload.driving_game_message_count = None
        # ... etc
```

---

## 📝 Summary

| Aspect | Maze Game | Driving Game |
|--------|-----------|--------------|
| **Modes** | `lam`, `manual` | `driving_game` |
| **Purpose** | Navigation testing | Dialogue testing |
| **Key Metrics** | Steps, Collisions | Messages, Time |
| **UI Location** | WebGame, TestMQTT | ChatBot |
| **Success Criteria** | Reach goal efficiently | Reach consensus quickly |
| **Leaderboard Filter** | LAM Mode / Manual Mode | 🏁 Driving Game |

---

**The two systems are COMPLETELY SEPARATE and should never share metrics!** 🚫


# Maze Game LAM Prompt Improvement

## Problem Analysis

The original LAM prompt for the maze game was causing the player to get stuck repeatedly. Analysis revealed:

### Root Cause
The assistant was generating **invalid paths** that routed through wall cells:
- Player position: `[3, 1]`
- Exit position: `[8, 8]`
- Generated path included `[5,6]` and `[6,7]`, but `visible_map[6][5] = 0` and `visible_map[7][6] = 0` (both walls!)

### Why This Happened
1. **No path validation logic** - The original prompt didn't enforce coordinate validation
2. **No adaptive strategy** - When the path failed, it kept repeating the same invalid action
3. **No fallback mechanisms** - Missing strategies for when direct pathing fails
4. **Insufficient safeguards** - No checklist to verify coordinates before returning JSON

## Solution: Enhanced LAM Prompt

The new prompt includes:

### 1. Critical Rules (5 Core Safety Principles)
- ✓ ALWAYS validate coordinates: `visible_map[y][x]` must equal 1
- ✓ NEVER include wall cells (value 0) in paths
- ✓ Use step-by-step pathfinding with intermediate waypoints
- ✓ Switch strategies immediately when direct paths fail
- ✓ Adapt behavior - never repeat failing actions

### 2. Explicit Pathfinding Algorithm
```
1. Scan visible_map to find ALL reachable floor cells
2. Build mental BFS tree toward exit_pos
3. Extract shortest valid path (EVERY cell has visible_map[y][x] == 1)
4. Break into 4-6 step segments for reliability
5. If no path exists, use break_wall or use_bfs
```

### 3. Action Schema with Full Details
- `hint`: guidance string
- `show_path`: visualization flag
- `path`: VALIDATED floor cells only (checked before returning)
- `use_bfs`: delegate to client-side pathfinding (robust fallback)
- `bfs_steps`: 1-4 tiles per move (2-3 recommended)
- `break_wall`: break ONE adjacent wall
- `break_walls`: break MULTIPLE walls
- `freeze_germs_ms`, `teleport_player`, etc.

### 4. Validation Checklist
Before responding, the model must verify:
```
☐ Every coordinate in path has visible_map[y][x] == 1
☐ Path starts at or adjacent to player_pos
☐ Path moves toward exit_pos (no backtracking unless necessary)
☐ All wall breaks are within distance 1 of player
☐ Coordinates are in bounds
```

### 5. Strategy Priority (Clear Decision Tree)
1. Direct path (if validated path exists)
2. Short path with wall breaks (if blocking walls)
3. `use_bfs=true` (delegate to client pathfinding)
4. Teleport (if stuck or surrounded)
5. Break multiple walls (if major blockage)

### 6. Stuck Detection Protocol
If the same action repeats twice without progress:
- Try breaking walls instead of paths
- Switch to `use_bfs: true`
- Consider teleporting to safer location
- Use freeze_germs or speed_boost for advantage

### 7. Rich Example Responses
```json
{"hint":"Moving toward exit via validated floor path","show_path":true,"path":[[3,2],[4,2],[5,2],[5,3],[5,4]]}

{"hint":"Path blocked - using BFS to navigate","use_bfs":true,"bfs_steps":3}

{"hint":"Breaking wall to create shortcut","break_wall":[4,1]}

{"hint":"Multiple walls blocking - breaking all adjacent ones","break_walls":[[3,0],[4,1],[4,0]]}

{"hint":"Using emergency teleport to reach open area","teleport_player":[6,5]}
```

## Key Improvements Over Original

| Aspect | Original | Improved |
|--------|----------|----------|
| **Path Validation** | None | Explicit validation for every coordinate |
| **Stuck Detection** | Repeats same action | Detects and switches strategy |
| **Fallback Options** | Limited | 5-level strategy priority |
| **Documentation** | Minimal rules | Detailed algorithm & checklist |
| **Example Responses** | 4 examples | 5 examples showing all strategies |
| **Adaptive Behavior** | Static | Dynamic with stuck detection |

## Implementation

**File Updated**: `d:\CodeRepository\llama3-hackathon\llama3\Hackathon\prompt-portal\frontend\src\components\TemplateForm.tsx`

**Field Modified**: `placeholderText` constant (lines 152-205)

This prompt is now the default template suggestion for new LAM game controllers and should be used when creating/updating maze game templates.

## Testing Recommendations

1. **Test with stuck scenarios** - Verify model switches strategies
2. **Test path validation** - Ensure no invalid coordinates in responses
3. **Test wall breaking** - Verify adjacent-only wall breaks
4. **Test BFS fallback** - Confirm model uses `use_bfs: true` when appropriate
5. **Test teleport** - Verify emergency teleport to safe locations

## Integration Notes

- The prompt works with Qwen 30B and other LLMs via MQTT bridge
- Compatible with all existing LAM game mechanics
- Backward compatible with existing game clients
- No database changes required
- Update templates in the prompt portal to use this new version

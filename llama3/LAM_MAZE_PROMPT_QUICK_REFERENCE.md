# LAM Maze Game - Quick Prompt Reference

## The Problem
Player was stuck because paths routed through walls (`visible_map[y][x] == 0`).

## The Solution: 5 Critical Rules

### Rule 1: Validate Every Coordinate
```
Before adding ANY coordinate to path:
  visible_map[y][x] must equal 1 (floor)
  0 = wall (blocked)
```

### Rule 2: Never Include Walls in Paths
If the path passes through a 0, it will fail. **Always validate first.**

### Rule 3: Segment Your Paths
```
Instead of: [[2,1],[3,1],...,[8,8]] (single 13-step path)
Do this:    [[3,2],[4,2],[5,2]]     (4-6 step segments)
```

### Rule 4: Switch Strategies on Failure
```
If direct path doesn't work:
  1. Try breaking adjacent walls: "break_wall": [x,y]
  2. Use client BFS: "use_bfs": true, "bfs_steps": 3
  3. Emergency teleport: "teleport_player": [x,y]
  4. Break multiple walls: "break_walls": [[x1,y1], [x2,y2]]
```

### Rule 5: Never Repeat Failing Actions
```
If you give same action twice without progress:
  Change strategy immediately (see Rule 4)
```

## Strategy Decision Tree

```
START: Player at [px,py], Exit at [ex,ey]
  |
  ├─→ Is there a valid 4-6 cell path?
  │   YES → Use it: {"path": [...], "show_path": true}
  │   NO  → Continue
  │
  ├─→ Are there adjacent walls to break?
  │   YES → Break them: {"break_wall": [x,y]}
  │   NO  → Continue
  │
  ├─→ Use BFS fallback: {"use_bfs": true, "bfs_steps": 3}
  │   NO PATH → Continue
  │
  ├─→ Teleport to safe area: {"teleport_player": [sx,sy]}
  │   Or break multiple walls: {"break_walls": [[x1,y1], ...]}
  │
  └─→ Wait for client movement, reassess
```

## Validation Checklist (DO THIS BEFORE RESPONDING)

- [ ] Every x,y in path: `0 ≤ x < width` AND `0 ≤ y < height`
- [ ] Every coordinate: `visible_map[y][x] == 1`
- [ ] Path starts near player: adjacent or touching player_pos
- [ ] Path generally moves toward exit_pos
- [ ] Wall breaks: all within 1 step of player (Chebyshev distance)
- [ ] No backtracking without reason
- [ ] Coordinates match schema: `[x, y]` not `{x, y}`

## Example Responses

### Good: Direct Path (Validated)
```json
{
  "hint": "Moving toward exit",
  "show_path": true,
  "path": [[3,2], [4,2], [5,2], [5,3], [5,4]]
}
```
Every `[x,y]` in path has `visible_map[y][x] == 1` ✓

### Good: When Blocked by Wall
```json
{
  "hint": "Breaking wall to create passage",
  "break_wall": [4,1]
}
```
`[4,1]` is adjacent to player at `[3,1]` ✓

### Good: BFS Fallback
```json
{
  "hint": "Using smart pathfinding",
  "use_bfs": true,
  "bfs_steps": 3
}
```
Client computes robust path ✓

### Good: Emergency Teleport
```json
{
  "hint": "Teleporting to open area",
  "teleport_player": [6,5]
}
```
`[6,5]` is floor (`visible_map[5][6] == 1`) ✓

### Bad: Path Through Wall ✗
```json
{
  "hint": "Moving toward exit",
  "path": [[5,6], [6,7]]
}
```
`visible_map[6][5] == 0` (WALL!) ✗
`visible_map[7][6] == 0` (WALL!) ✗

### Bad: Invalid Coordinates ✗
```json
{
  "path": [{x: 5, y: 6}]
}
```
Schema requires `[x,y]` not `{x,y}` ✗

### Bad: Out of Bounds ✗
```json
{
  "break_wall": [100, 100]
}
```
Coordinates exceed maze dimensions ✗

## Debugging Tips

**Player stuck in same spot?**
- Your path contains walls
- Check `visible_map[y][x]` for each coordinate
- Switch to `use_bfs: true` or `break_wall`

**Wall break not working?**
- Wall must be adjacent: distance ≤ 1 from player
- Use `break_walls` for multiple walls
- Make sure it's actually a wall (`visible_map[y][x] == 0`)

**Path too long?**
- Break into 4-6 cell segments
- Use multiple API calls if needed
- Let client move first, reassess

**Still stuck?**
- Use teleport: `"teleport_player": [safe_x, safe_y]`
- Use freeze_germs to buy time
- Recalculate path from new location

## Coordinates Quick Reference

```
visible_map = [
  [0, 0, 0, 0, 0, 0, 0],  ← y=0 (top)
  [0, 1, 1, 1, 0, 1, 0],  ← y=1
  [0, 1, 0, 1, 0, 1, 0],  ← y=2
  [0, 1, 1, 1, 0, 1, 0],  ← y=3
  [0, 0, 0, 0, 0, 0, 0]   ← y=4 (bottom)
]
↑
x=0,1,2,3,4,5,6 (left to right)

To access: visible_map[y][x]
Example: visible_map[1][2] = 1 (floor at x=2, y=1)
```

## Summary

✅ **Validate EVERY coordinate** before adding to path  
✅ **Break into segments** (4-6 steps each)  
✅ **Switch strategies** when direct path fails  
✅ **Use BFS** as robust fallback  
✅ **Adapt dynamically** - never repeat failing actions  

**Result:** Player reaches exit smoothly without getting stuck!

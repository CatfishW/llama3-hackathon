import { Grid, Vec2 } from "./types";

export function randInt(n: number) { return Math.floor(Math.random() * n) }
export function clamp(n: number, a: number, b: number) { return Math.max(a, Math.min(b, n)) }
export function key(x:number,y:number){return `${x},${y}`}

// Recursive backtracker maze generation (odd dims)
export function generateMaze(cols: number, rows: number): Grid {
 const C = cols % 2 ? cols : cols + 1
 const R = rows % 2 ? rows : rows + 1
 const g: Grid = Array.from({ length: R }, () => Array.from({ length: C }, () => 1 as 0 | 1))

 function carve(cx: number, cy: number) {
   g[cy][cx] = 0
   const dirs: Vec2[] = [ {x:2,y:0}, {x:-2,y:0}, {x:0,y:2}, {x:0,y:-2} ]
   for (let i = dirs.length - 1; i > 0; i--) { // shuffle
     const j = Math.floor(Math.random() * (i + 1)); [dirs[i], dirs[j]] = [dirs[j], dirs[i]]
   }
   for (const d of dirs) {
     const nx = cx + d.x, ny = cy + d.y
     if (nx > 0 && ny > 0 && nx < C - 1 && ny < R - 1 && g[ny][nx] === 1) {
       g[cy + d.y / 2][cx + d.x / 2] = 0
       carve(nx, ny)
     }
   }
 }

 carve(1, 1)
 // enforce outer walls
 for (let x = 0; x < C; x++) { g[0][x] = 1; g[R-1][x] = 1 }
 for (let y = 0; y < R; y++) { g[y][0] = 1; g[y][C-1] = 1 }

 // add intersections to reduce dead ends
 for (let y = 2; y < R - 2; y += 2) {
   for (let x = 2; x < C - 2; x += 2) {
     if (g[y][x] === 0) {
       let open = 0
       if (g[y][x-1] === 0) open++
       if (g[y][x+1] === 0) open++
       if (g[y-1][x] === 0) open++
       if (g[y+1][x] === 0) open++
       if (open <= 1 && Math.random() < 0.5) {
         const dirs: Vec2[] = [ {x:-1,y:0},{x:1,y:0},{x:0,y:-1},{x:0,y:1} ]
         for (let i = dirs.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [dirs[i], dirs[j]] = [dirs[j], dirs[i]] }
         for (const d of dirs) { const nx = x + d.x, ny = y + d.y; if (g[ny][nx] === 1) { g[ny][nx] = 0; break } }
       }
     }
   }
 }
 return g
}

// Simple BFS for autopilot pathfinding (grid-based)
export function bfsPath(grid: Grid, start: Vec2, goal: Vec2): Vec2[] | null {
 const R = grid.length, C = grid[0].length
 const q: Vec2[] = [start]
 const prev = new Map<string, string>()
 const seen = new Set<string>([`${start.x},${start.y}`])
 const dirs = [ {x:1,y:0},{x:-1,y:0},{x:0,y:1},{x:0,y:-1} ]
 while (q.length) {
   const cur = q.shift()!
   if (cur.x === goal.x && cur.y === goal.y) {
     const path: Vec2[] = []
     let k = `${goal.x},${goal.y}`
     while (k) {
       const [sx, sy] = k.split(',').map(Number)
       path.push({x:sx,y:sy})
       const pk = prev.get(k); if (!pk) break; k = pk
     }
     return path.reverse()
   }
   for (const d of dirs) {
     const nx = cur.x + d.x, ny = cur.y + d.y
     if (nx>=0 && ny>=0 && nx<C && ny<R && grid[ny][nx]===0) {
       const key = `${nx},${ny}`
       if (!seen.has(key)) { seen.add(key); prev.set(key, `${cur.x},${cur.y}`); q.push({x:nx,y:ny}) }
     }
   }
 }
 return null
}

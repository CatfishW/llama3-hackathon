import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api'
import { useNavigate } from 'react-router-dom'

// ===== Types =====
 type Vec2 = { x: number; y: number }
 type Cell = 0 | 1 // 0: path, 1: wall
 type Grid = Cell[][]
 type Template = { id: number; title: string }
 type HintMsg = {
  hint?: string
  path?: [number, number][]
  break_wall?: [number, number]
  breaks_remaining?: number
  // New LAM actions
  speed_boost_ms?: number
  slow_germs_ms?: number
  freeze_germs_ms?: number
  teleport_player?: [number, number]
  spawn_oxygen?: Array<[number, number]> | Array<{x:number;y:number}>
  move_exit?: [number, number]
  highlight_zone?: Array<[number, number]>
  highlight_ms?: number
  toggle_autopilot?: boolean
  break_walls?: Array<[number, number]>
  reveal_map?: boolean
  // Error from backend/LAM
  error?: string
  Error?: string
  err?: string
  raw?: string
 }

 // ===== Helpers =====
 function randInt(n: number) { return Math.floor(Math.random() * n) }
 function clamp(n: number, a: number, b: number) { return Math.max(a, Math.min(b, n)) }
 function key(x:number,y:number){return `${x},${y}`}

 // Recursive backtracker maze generation (odd dims)
 function generateMaze(cols: number, rows: number): Grid {
  const C = cols % 2 ? cols : cols + 1
  const R = rows % 2 ? rows : rows + 1
  const g: Grid = Array.from({ length: R }, () => Array.from({ length: C }, () => 1 as Cell))

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
 function bfsPath(grid: Grid, start: Vec2, goal: Vec2): Vec2[] | null {
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

 // ===== Component =====
 export default function WebGame() {
  // UI state
  const [templates, setTemplates] = useState<Template[]>([])
  const [templateId, setTemplateId] = useState<number | null>(null)
  const [sessionId, setSessionId] = useState('session-' + Math.random().toString(36).slice(2, 8))
  const [connected, setConnected] = useState(false)
  const [autoPilot, setAutoPilot] = useState(false)
  const [germCount, setGermCount] = useState(5)
  const [status, setStatus] = useState('')
  // New UI toggles
  const [showLamPanel, setShowLamPanel] = useState(true)
  const [showMiniMap, setShowMiniMap] = useState(true)
  const [paused, setPaused] = useState(false)
  const [showMenu, setShowMenu] = useState(false)

  // Game state
  const tile = 24
  const cols = 33, rows = 21 // fits nicely within 800x600 canvas
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const lastPublishRef = useRef<number>(0)

  const stateRef = useRef({
    grid: [] as Grid,
    player: { x: 1, y: 1 } as Vec2,
    exit: { x: cols - 2, y: rows - 2 } as Vec2,
    oxy: [] as Vec2[],
    germs: [] as { pos: Vec2; dir: Vec2; speed: number }[],
    oxygenCollected: 0,
    startTime: 0,
    gameOver: false,
    win: false,
    lam: { hint: '', path: [] as Vec2[], breaks: 0, error: '' },
    // Effects & visuals
    effects: { speedBoostUntil: 0, slowGermsUntil: 0, freezeGermsUntil: 0 },
    highlight: new Map<string, number>(), // key(x,y) -> until timestamp
    revealMap: false,
    fxPopups: [] as Array<{x:number;y:number;text:string;t0:number;ttl:number}>,
    hitFlash: 0,
    particles: [] as Array<{x:number;y:number;r:number;spd:number;alpha:number}>,
    germStepFlip: false,
    emotion: 'neutral' as 'neutral'|'happy'|'scared'|'tired'|'excited'
  })

  const width = cols * tile
  const height = rows * tile

  // Texture cache for performance
  const texturesRef = useRef<{ wall: HTMLCanvasElement|null; floor: HTMLCanvasElement|null; floorAlt: HTMLCanvasElement|null }>({ wall: null, floor: null, floorAlt: null })

  function makeTileTexture(base1: string, base2: string, vein: string) {
    const c = document.createElement('canvas'); c.width = tile; c.height = tile
    const g = c.getContext('2d')!
    const rg = g.createRadialGradient(tile*0.3, tile*0.3, tile*0.2, tile*0.7, tile*0.7, tile*0.95)
    rg.addColorStop(0, base1); rg.addColorStop(1, base2)
    g.fillStyle = rg; g.fillRect(0,0,tile,tile)
    // veins
    g.strokeStyle = vein; g.globalAlpha = 0.18; g.lineWidth = 1
    for (let i=0;i<3;i++) {
      g.beginPath();
      const yy = (i+1)*tile/4 + Math.sin(i*1.7)*2
      g.moveTo(0, yy)
      for (let x=0; x<=tile; x+=4) {
        const y = yy + Math.sin((x+i*7)/6)*1.2
        g.lineTo(x, y)
      }
      g.stroke()
    }
    g.globalAlpha = 1
    return c
  }

  // init textures once
  useEffect(() => {
    const t = texturesRef.current
    if (!t.wall) t.wall = makeTileTexture('#3b0f15', '#2b0f15', 'rgba(255,255,255,0.05)')
    if (!t.floor) t.floor = makeTileTexture('#5a1f1f', '#4a1f1f', 'rgba(255,255,255,0.06)')
    if (!t.floorAlt) t.floorAlt = makeTileTexture('#642121', '#521a1a', 'rgba(255,255,255,0.06)')
  }, [])

  function drawExitHole(ctx: CanvasRenderingContext2D, pos: Vec2, t:number) {
    const cx = pos.x*tile + tile/2
    const cy = pos.y*tile + tile/2
    const r = tile*0.46
    // dark center
    const g = ctx.createRadialGradient(cx, cy, r*0.2, cx, cy, r)
    g.addColorStop(0, 'rgba(0,0,0,0.95)')
    g.addColorStop(0.6, 'rgba(20,10,12,0.7)')
    g.addColorStop(1, 'rgba(0,0,0,0.0)')
    ctx.fillStyle = g
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2); ctx.fill()
    // rim highlight
    ctx.strokeStyle = 'rgba(255,255,255,0.25)'
    ctx.lineWidth = 2
    ctx.beginPath(); ctx.arc(cx, cy, r*0.9, 0, Math.PI*2); ctx.stroke()
    // subtle swirl
    ctx.strokeStyle = 'rgba(255,255,255,0.15)'
    ctx.lineWidth = 1
    ctx.beginPath()
    const ang = (t*0.002)% (Math.PI*2)
    for (let a=0; a<Math.PI*1.6; a+=Math.PI/20) {
      const rr = r*(0.2 + a/(Math.PI*1.6)*0.7)
      const px = cx + Math.cos(a+ang)*rr
      const py = cy + Math.sin(a+ang)*rr
      if (a===0) ctx.moveTo(px,py); else ctx.lineTo(px,py)
    }
    ctx.stroke()
  }

  // Theme helpers and FX utilities
  const THEME = {
    wall: '#2b0f15',
    floor: '#4a1f1f',
    floorAlt: '#5a1f1f',
    bgInner: '#3b0b12',
    bgOuter: '#14060a',
    glow: 'rgba(220,38,38,0.35)',
    oxyGlow: '#4ef0ff',
    germ: '#22c55e',
    germDark: '#15803d',
    playerRed: '#ef4444',
    playerBright: '#f87171'
  }
  function dist(a: {x:number;y:number}, b:{x:number;y:number}) { const dx=a.x-b.x,dy=a.y-b.y; return Math.hypot(dx,dy) }

  function drawVignette(ctx: CanvasRenderingContext2D) {
    const g = ctx.createRadialGradient(width/2, height/2, Math.min(width,height)*0.2, width/2, height/2, Math.max(width,height)*0.8)
    g.addColorStop(0, THEME.bgInner)
    g.addColorStop(1, THEME.bgOuter)
    ctx.fillStyle = g
    ctx.fillRect(0,0,width,height)
    // edge darkening
    const v = ctx.createRadialGradient(width/2, height/2, Math.max(width,height)*0.55, width/2, height/2, Math.max(width,height)*0.9)
    v.addColorStop(0, 'rgba(0,0,0,0)')
    v.addColorStop(1, 'rgba(0,0,0,0.6)')
    ctx.fillStyle = v
    ctx.fillRect(0,0,width,height)
  }

  function drawPlasma(ctx: CanvasRenderingContext2D) {
    const s = stateRef.current
    // update and draw flowing particles
    for (const p of s.particles) {
      p.x -= p.spd
      if (p.x < -p.r*2) { p.x = width + randInt(100); p.y = randInt(height); p.r = 6 + Math.random()*18; p.alpha = 0.08 + Math.random()*0.12 }
      ctx.fillStyle = `rgba(255,90,90,${p.alpha.toFixed(3)})`
      ctx.beginPath(); ctx.ellipse(p.x, p.y, p.r, p.r*0.6, 0, 0, Math.PI*2); ctx.fill()
    }
  }

  function drawPlayer(ctx: CanvasRenderingContext2D, s: any, t: number) {
    const cx = s.player.x*tile + tile/2
    const cy = s.player.y*tile + tile/2
    const r = tile*0.42
    ctx.save()
    ctx.shadowColor = THEME.glow
    ctx.shadowBlur = 16
    ctx.fillStyle = THEME.playerRed
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2); ctx.fill()
    ctx.shadowBlur = 0
    const grad = ctx.createRadialGradient(cx - r*0.3, cy - r*0.3, r*0.1, cx, cy, r)
    grad.addColorStop(0, THEME.playerBright); grad.addColorStop(1, THEME.playerRed)
    ctx.fillStyle = grad
    ctx.beginPath(); ctx.arc(cx, cy, r*0.85, 0, Math.PI*2); ctx.fill()
    // Emotion face
    const e = s.emotion
    ctx.fillStyle = '#1b0b0c'
    // eyes
    const eyeY = cy - r*0.15
    ctx.beginPath(); ctx.arc(cx - r*0.22, eyeY, r*0.09, 0, Math.PI*2); ctx.fill()
    ctx.beginPath(); ctx.arc(cx + r*0.22, eyeY, r*0.09, 0, Math.PI*2); ctx.fill()
    // mouth
    ctx.strokeStyle = '#1b0b0c'; ctx.lineWidth = 2
    ctx.beginPath()
    if (e==='happy' || e==='excited') {
      ctx.arc(cx, cy + r*0.1, r*0.25, 0, Math.PI, false)
    } else if (e==='scared') {
      ctx.arc(cx, cy + r*0.15, r*0.18, 0, Math.PI*2)
    } else if (e==='tired') {
      ctx.moveTo(cx - r*0.2, cy + r*0.15); ctx.lineTo(cx + r*0.2, cy + r*0.15)
    } else {
      ctx.arc(cx, cy + r*0.15, r*0.2, 0, Math.PI, true)
    }
    ctx.stroke()
    ctx.restore()
  }

  function drawOxygen(ctx: CanvasRenderingContext2D, o: {x:number;y:number}, t:number) {
    const cx = o.x*tile + tile/2, cy = o.y*tile + tile/2
    const pulse = 1 + 0.15*Math.sin(t*0.006 + (o.x+o.y))
    const r = tile*0.18 * pulse
    // glow
    const g = ctx.createRadialGradient(cx, cy, r*0.2, cx, cy, r*2.2)
    g.addColorStop(0, 'rgba(78,240,255,0.65)')
    g.addColorStop(1, 'rgba(78,240,255,0)')
    ctx.fillStyle = g
    ctx.beginPath(); ctx.arc(cx, cy, r*2.2, 0, Math.PI*2); ctx.fill()
    // core pellet
    ctx.fillStyle = '#8df6ff'
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI*2); ctx.fill()
    // specular
    ctx.fillStyle = 'rgba(255,255,255,0.85)'
    ctx.beginPath(); ctx.arc(cx - r*0.3, cy - r*0.3, r*0.35, 0, Math.PI*2); ctx.fill()
  }

  function drawGerm(ctx: CanvasRenderingContext2D, g: {pos:Vec2; dir:Vec2; speed:number}, t:number, player:Vec2) {
    const cx = g.pos.x*tile + tile/2, cy = g.pos.y*tile + tile/2
    const spikes = 8
    const baseR = tile*0.32
    const wobble = (Math.sin(t*0.01 + (g.pos.x+g.pos.y)) + 1)*0.5
    const outerR = baseR * (1.1 + 0.12*wobble)
    ctx.save()
    // threat ring if near
    if (dist(g.pos, player) <= 3) {
      ctx.strokeStyle = 'rgba(239,68,68,0.35)'
      ctx.lineWidth = 3
      ctx.beginPath(); ctx.arc(cx, cy, outerR*1.6, 0, Math.PI*2); ctx.stroke()
    }
    // spiky body
    ctx.beginPath()
    for (let i=0;i<spikes;i++) {
      const a = (i/spikes)*Math.PI*2 + t*0.002
      const r = i%2===0 ? outerR : baseR
      const px = cx + Math.cos(a)*r
      const py = cy + Math.sin(a)*r
      if (i===0) ctx.moveTo(px,py); else ctx.lineTo(px,py)
    }
    ctx.closePath()
    const grad = ctx.createRadialGradient(cx, cy, baseR*0.2, cx, cy, outerR)
    grad.addColorStop(0, THEME.germ)
    grad.addColorStop(1, THEME.germDark)
    ctx.fillStyle = grad
    ctx.shadowColor = 'rgba(21,128,61,0.6)'
    ctx.shadowBlur = 12
    ctx.fill()
    ctx.shadowBlur = 0
    // eyes
    ctx.fillStyle = '#052e16'
    ctx.beginPath(); ctx.arc(cx - baseR*0.25, cy - baseR*0.15, baseR*0.12, 0, Math.PI*2); ctx.fill()
    ctx.beginPath(); ctx.arc(cx + baseR*0.25, cy - baseR*0.15, baseR*0.12, 0, Math.PI*2); ctx.fill()
    ctx.restore()
  }

  function drawMiniMap(ctx: CanvasRenderingContext2D, s:any){
    if (!showMiniMap) return
    const scale = 3
    const mmW = cols*scale, mmH = rows*scale
    const ox = 8, oy = 8
    ctx.save()
    ctx.globalAlpha = 0.9
    ctx.fillStyle = 'rgba(0,0,0,0.45)'; ctx.fillRect(ox-4, oy-4, mmW+8, mmH+8)
    for (let y=0;y<rows;y++){
      for (let x=0;x<cols;x++){
        ctx.fillStyle = s.grid[y][x]===0? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.6)'
        ctx.fillRect(ox+x*scale, oy+y*scale, scale, scale)
      }
    }
    // path
    ctx.fillStyle = 'rgba(255,255,0,0.8)'
    for (const p of s.lam.path||[]) ctx.fillRect(ox+p.x*scale, oy+p.y*scale, scale, scale)
    // oxygen
    ctx.fillStyle = '#7dd3fc'; for (const o of s.oxy) ctx.fillRect(ox+o.x*scale, oy+o.y*scale, scale, scale)
    // germs
    ctx.fillStyle = '#22c55e'; for (const g of s.germs) ctx.fillRect(ox+g.pos.x*scale, oy+g.pos.y*scale, scale, scale)
    // exit and player
    ctx.fillStyle = '#60a5fa'; ctx.fillRect(ox+s.exit.x*scale, oy+s.exit.y*scale, scale, scale)
    ctx.fillStyle = '#ef4444'; ctx.fillRect(ox+s.player.x*scale, oy+s.player.y*scale, scale, scale)
    ctx.restore()
  }

  // Load templates
  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/api/templates')
        setTemplates(res.data.map((t: any) => ({ id: t.id, title: t.title })))
        if (res.data.length > 0) setTemplateId(res.data[0].id)
      } catch (e) { console.error(e) }
    })()
  }, [])

  // WebSocket connect/disconnect
  const connectWS = useCallback(() => {
    const base = (import.meta as any).env?.VITE_WS_BASE || 'ws://localhost:8000'
    const ws = new WebSocket(base + '/api/mqtt/ws/hints/' + sessionId)
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)
        const hint: HintMsg = data.hint || {}
        const s = stateRef.current
        // Handle multiple possible error shapes
        const anyHint: any = hint as any
        const errText = anyHint.error || anyHint.Error || anyHint.err
        const promptExcerpt = (anyHint.prompt ? String(anyHint.prompt) : '')
        if (errText) {
          s.lam.error = promptExcerpt ? `${String(errText)} | prompt: ${promptExcerpt}` : String(errText)
        } else if (anyHint.raw) {
          s.lam.error = `Invalid LAM JSON: ${String(anyHint.raw).slice(0, 160)}`
        } else {
          s.lam.error = ''
        }
        s.lam.hint = hint.hint || ''
        s.lam.path = (hint.path || []).map(([x,y]) => ({x,y}))
        s.lam.breaks = hint.breaks_remaining ?? s.lam.breaks
        if (hint.break_wall) {
          const [bx, by] = hint.break_wall
          if (by>=0 && by<s.grid.length && bx>=0 && bx<s.grid[0].length) s.grid[by][bx] = 0
        }
        // New actions
        const now = performance.now()
        if (hint.speed_boost_ms) s.effects.speedBoostUntil = Math.max(s.effects.speedBoostUntil, now + hint.speed_boost_ms)
        if (hint.slow_germs_ms) s.effects.slowGermsUntil = Math.max(s.effects.slowGermsUntil, now + hint.slow_germs_ms)
        if (hint.freeze_germs_ms) s.effects.freezeGermsUntil = Math.max(s.effects.freezeGermsUntil, now + hint.freeze_germs_ms)
        if (hint.toggle_autopilot!==undefined) setAutoPilot(Boolean(hint.toggle_autopilot))
        if (hint.reveal_map!==undefined) s.revealMap = Boolean(hint.reveal_map)
        if (hint.move_exit && hint.move_exit.length===2) {
          const [ex,ey] = hint.move_exit; if (s.grid[ey]?.[ex]===0) s.exit = {x:ex,y:ey}
        }
        if (hint.teleport_player && hint.teleport_player.length===2) {
          const [tx,ty] = hint.teleport_player; if (s.grid[ty]?.[tx]===0) s.player = {x:tx,y:ty}
        }
        if (Array.isArray(hint.spawn_oxygen)) {
          for (const item of hint.spawn_oxygen) {
            const x = Array.isArray(item)? item[0] : (item as any).x
            const y = Array.isArray(item)? item[1] : (item as any).y
            if (s.grid[y]?.[x]===0 && !s.oxy.find(o=>o.x===x&&o.y===y)) s.oxy.push({x,y})
          }
        }
        if (Array.isArray(hint.break_walls)) {
          for (const [bx,by] of hint.break_walls) if (s.grid[by]?.[bx]===1) s.grid[by][bx]=0
        }
        if (Array.isArray(hint.highlight_zone)) {
          const until = now + (hint.highlight_ms ?? 5000)
          for (const [hx,hy] of hint.highlight_zone) s.highlight.set(key(hx,hy), until)
        }
      } catch {}
    }
    wsRef.current = ws
  }, [sessionId])

  const disconnectWS = useCallback(() => {
    wsRef.current?.close(); wsRef.current = null
  }, [])

  // Start a new game
  const startGame = useCallback(() => {
    const grid = generateMaze(cols, rows)

    // Ensure start area open
    grid[1][1] = 0; grid[1][2] = 0; grid[2][1] = 0

    // Place oxygen ~10% of floors excluding start/exit
    const floors: Vec2[] = []
    for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) if (grid[y][x] === 0) floors.push({x,y})
    const start = { x: 1, y: 1 }
    const exit = { x: cols - 2, y: rows - 2 }
    const oxy: Vec2[] = []
    const avail = floors.filter(p => !(p.x===start.x && p.y===start.y) && !(p.x===exit.x && p.y===exit.y))
    const count = Math.max(10, Math.floor(avail.length * 0.1))
    for (let i = 0; i < count && avail.length; i++) {
      const idx = randInt(avail.length); oxy.push(avail[idx]); avail.splice(idx,1)
    }

    // Germs
    const germs: { pos: Vec2; dir: Vec2; speed: number }[] = []
    for (let i = 0; i < germCount && avail.length; i++) {
      const idx = randInt(avail.length)
      const pos = avail[idx]; avail.splice(idx,1)
      const dirs = [ {x:1,y:0},{x:-1,y:0},{x:0, y:1},{x:0,y:-1} ]
      germs.push({ pos, dir: dirs[randInt(4)], speed: 4 })
    }

    stateRef.current = {
      grid,
      player: start,
      exit,
      oxy,
      germs,
      oxygenCollected: 0,
      startTime: performance.now(),
      gameOver: false,
      win: false,
      lam: { hint: '', path: [], breaks: 0, error: '' },
      effects: { speedBoostUntil: 0, slowGermsUntil: 0, freezeGermsUntil: 0 },
      highlight: new Map(),
      revealMap: false,
      fxPopups: [],
      hitFlash: 0,
      particles: Array.from({length: 80}, ()=>({ x: Math.random()*width, y: Math.random()*height, r: 6+Math.random()*18, spd: 0.3+Math.random()*0.8, alpha: 0.06+Math.random()*0.12 })),
      germStepFlip: false,
      emotion: 'neutral'
    }

    setStatus('')

    // Connect WS ~ no immediate publish
    disconnectWS(); connectWS();
    // Removed immediate publish; periodic publisher will handle it
  }, [cols, rows, germCount, connectWS, disconnectWS])

  // Publish state to backend -> MQTT
  const publishState = useCallback(async (force = false) => {
    if (!templateId) return
    const now = performance.now()
    if (!force && now - lastPublishRef.current < 15000) return // throttle to 15s
    lastPublishRef.current = now

    const s = stateRef.current
    const body = {
      session_id: sessionId,
      template_id: templateId,
      state: {
        sessionId,
        player_pos: [s.player.x, s.player.y],
        exit_pos: [s.exit.x, s.exit.y],
        visible_map: s.grid,
        oxygenPellets: s.oxy.map(p => ({ x: p.x, y: p.y })),
        germs: s.germs.map(g => ({ x: g.pos.x, y: g.pos.y })),
        tick: Date.now(),
        health: 100,
        oxygen: 100 - s.oxygenCollected
      }
    }
    try { await api.post('/api/mqtt/publish_state', body) } catch (e) { /* ignore */ }
  }, [sessionId, templateId])

  // Periodic publisher: every 15s while game is running
  useEffect(() => {
    const id = setInterval(() => {
      const s = stateRef.current
      if (templateId && s.startTime && !s.gameOver) {
        publishState(true)
      }
    }, 15000)
    return () => clearInterval(id)
  }, [templateId, publishState])

  // Input handling
  const keysRef = useRef<Record<string, boolean>>({})
  useEffect(() => {
    const down = (e: KeyboardEvent) => { 
      keysRef.current[e.key] = true
      if (e.key.toLowerCase() === 't') setAutoPilot(v => !v)
      if (e.key.toLowerCase() === 'h') setShowLamPanel(v=>!v)
      if (e.key.toLowerCase() === 'm') setShowMenu(v=>!v)
      if (e.key.toLowerCase() === 'p') setPaused(v=>!v)
      if (e.key.toLowerCase() === 'n') setShowMiniMap(v=>!v)
    }
    const up = (e: KeyboardEvent) => { keysRef.current[e.key] = false }
    window.addEventListener('keydown', down); window.addEventListener('keyup', up)
    return () => { window.removeEventListener('keydown', down); window.removeEventListener('keyup', up) }
  }, [])

  // Game loop
  useEffect(() => {
    let raf = 0
    let acc = 0
    const stepMs = 100 // move step interval in ms

    const loop = (t: number) => {
      raf = requestAnimationFrame(loop)
      const s = stateRef.current
      // draw even when paused for overlays/FX
      if (!paused && !s.gameOver) {
        const now = performance.now()
        acc += now - (loop as any).last || 0
        ;(loop as any).last = now
        while (acc >= stepMs) { acc -= stepMs; updateOnce() }
      }
      draw()
    }

    function updateOnce() {
      const s = stateRef.current
      const now = performance.now()

      // compute effects
      const speedActive = now < s.effects.speedBoostUntil
      const freezeActive = now < s.effects.freezeGermsUntil
      const slowActive = !freezeActive && now < s.effects.slowGermsUntil
      const moves = speedActive ? 2 : 1

      // Player move (grid step)
      const tryMove = (dx: number, dy: number) => {
        for (let i=0;i<moves;i++){
          const nx = clamp(s.player.x + dx, 0, cols-1)
          const ny = clamp(s.player.y + dy, 0, rows-1)
          if (s.grid[ny][nx] === 0) { s.player.x = nx; s.player.y = ny; publishState() }
        }
      }

      if (!autoPilot) {
        if (keysRef.current['ArrowUp'] || keysRef.current['w']) tryMove(0,-1)
        if (keysRef.current['ArrowDown'] || keysRef.current['s']) tryMove(0,1)
        if (keysRef.current['ArrowLeft'] || keysRef.current['a']) tryMove(-1,0)
        if (keysRef.current['ArrowRight'] || keysRef.current['d']) tryMove(1,0)
      } else {
        const path = s.lam.path.length ? s.lam.path : (bfsPath(s.grid, s.player, s.exit) || [])
        if (path.length > 1) {
          const next = path[1]
          const dx = Math.sign(next.x - s.player.x)
          const dy = Math.sign(next.y - s.player.y)
          tryMove(dx, dy)
        }
      }

      // oxygen collect
      const idx = s.oxy.findIndex(o => o.x === s.player.x && o.y === s.player.y)
      if (idx >= 0) {
        s.oxy.splice(idx, 1); s.oxygenCollected++; /* no immediate publish */
        s.fxPopups.push({ x: s.player.x, y: s.player.y, text: '+100 O₂', t0: performance.now(), ttl: 700 })
        s.emotion = 'happy'
      }

      // germs move
      if (!freezeActive) {
        const allowStep = slowActive ? (s.germStepFlip = !s.germStepFlip) : true
        if (allowStep) {
          for (const g of s.germs) {
            if (Math.random() < 0.1) { const dirs = [ {x:1,y:0},{x:-1,y:0},{x:0,y:1},{x:0,y:-1} ]; g.dir = dirs[randInt(4)] }
            const nx = clamp(g.pos.x + g.dir.x, 0, cols-1)
            const ny = clamp(g.pos.y + g.dir.y, 0, rows-1)
            if (s.grid[ny][nx] === 0) { g.pos.x = nx; g.pos.y = ny } else { g.dir.x *= -1; g.dir.y *= -1 }
            if (g.pos.x === s.player.x && g.pos.y === s.player.y) s.hitFlash = 1
          }
        }
      }

      // emotion state
      const nearGerm = s.germs.some(g => dist(g.pos, s.player) <= 2)
      if (nearGerm) s.emotion = 'scared'
      else if (s.oxygenCollected > 0 && now - s.startTime > 30000) s.emotion = 'tired'
      else if (dist(s.player, s.exit) <= 3) s.emotion = 'excited'
      else if (s.emotion !== 'happy') s.emotion = 'neutral'

      // collisions
      if (s.germs.some(g => g.pos.x === s.player.x && g.pos.y === s.player.y)) {
        s.gameOver = true; s.win = false
      }
      if (s.player.x === s.exit.x && s.player.y === s.exit.y) {
        s.gameOver = true; s.win = true
      }

      // fade highlights
      for (const [k,v] of Array.from(s.highlight.entries())) if (now>v) s.highlight.delete(k)

      // fade hit flash
      if (s.hitFlash>0) s.hitFlash = Math.max(0, s.hitFlash - 0.1)
    }

    function draw() {
      const canvas = canvasRef.current; if (!canvas) return
      const ctx = canvas.getContext('2d'); if (!ctx) return
      const s = stateRef.current
      ctx.clearRect(0,0,canvas.width, canvas.height)

      drawVignette(ctx)
      drawPlasma(ctx)

      // grid with textures
      const tex = texturesRef.current
      for (let y=0;y<rows;y++) {
        for (let x=0;x<cols;x++) {
          if (s.grid[y]?.[x] === 1) {
            if (tex.wall) ctx.drawImage(tex.wall, x*tile, y*tile)
          } else {
            if ((x+y)%2===0) { if (tex.floor) ctx.drawImage(tex.floor, x*tile, y*tile) }
            else { if (tex.floorAlt) ctx.drawImage(tex.floorAlt, x*tile, y*tile) }
          }
        }
      }

      // highlighted tiles (from LAM)
      ctx.fillStyle = 'rgba(78,205,196,0.25)'
      for (const k of s.highlight.keys()) { const [x,y] = k.split(',').map(Number); ctx.fillRect(x*tile, y*tile, tile, tile) }

      // LAM path overlay
      if (s.lam.path && s.lam.path.length) {
        ctx.fillStyle = 'rgba(255,255,0,0.22)'
        for (const p of s.lam.path) ctx.fillRect(p.x*tile, p.y*tile, tile, tile)
        ctx.strokeStyle = 'rgba(255,255,0,0.9)'; ctx.lineWidth = 2
        ctx.beginPath(); ctx.moveTo(s.lam.path[0].x*tile + tile/2, s.lam.path[0].y*tile + tile/2)
        for (let i=1;i<s.lam.path.length;i++) ctx.lineTo(s.lam.path[i].x*tile + tile/2, s.lam.path[i].y*tile + tile/2)
        ctx.stroke()
      }

      // oxygen with glow
      const t = performance.now(); for (const o of s.oxy) drawOxygen(ctx, o, t)

      // exit as a hole
      drawExitHole(ctx, s.exit, t)

      // germs animated
      for (const g of s.germs) drawGerm(ctx, g as any, t, s.player)

      // player (RBC-like)
      drawPlayer(ctx, s, t)

      // Popups
      const now = performance.now()
      s.fxPopups = s.fxPopups.filter(p => now - p.t0 < p.ttl)
      for (const p of s.fxPopups) {
        const ratio = (now - p.t0)/p.ttl
        const alpha = 1 - ratio
        const yOff = -10 - ratio*20
        ctx.globalAlpha = alpha; ctx.fillStyle = '#ffffff'; ctx.font = 'bold 14px Inter'
        ctx.fillText(p.text, p.x*tile + tile/2 - 28, p.y*tile + yOff)
        ctx.globalAlpha = 1
      }

      // HUD
      const elapsed = (performance.now() - s.startTime)/1000
      const score = Math.round(s.oxygenCollected*100 - elapsed*5)
      ctx.fillStyle = '#fff'; ctx.font = '16px Inter, system-ui, sans-serif'
      ctx.fillText(`O₂: ${s.oxygenCollected}  Time: ${elapsed.toFixed(1)}s  Score: ${score}`, 10, 22)

      // LAM Panel (toggle)
      if (showLamPanel) {
        const panelX = width - 240, panelY = 12, panelW = 230, panelH = 146
        ctx.fillStyle = 'rgba(0,0,0,0.45)'; ctx.fillRect(panelX, panelY, panelW, panelH)
        ctx.strokeStyle = 'rgba(255,255,255,0.2)'; ctx.strokeRect(panelX, panelY, panelW, panelH)
        if (s.lam.error) {
          ctx.fillStyle = '#ff6b6b'; ctx.font = 'bold 14px Inter';
          const msg = `Error: ${s.lam.error}`
          const words = msg.split(' '); let line = ''; let y = panelY + 22
          for (const w of words) {
            const test = line ? line + ' ' + w : w
            const wdt = ctx.measureText(test).width
            if (wdt > panelW - 20) { ctx.fillText(line, panelX+10, y); line = w; y += 18 } else { line = test }
          }
          if (line) ctx.fillText(line, panelX+10, y)
        } else {
          ctx.fillStyle = '#fde047'; ctx.font = '15px Inter'; ctx.fillText(`LAM: ${s.lam.hint||'...'}`, panelX+10, panelY+22)
        }
        ctx.fillStyle = '#fff'; ctx.font = '14px Inter'; ctx.fillText(`Breaks: ${s.lam.breaks ?? 0}`, panelX+10, panelY+44)
        if (s.lam.path?.length) ctx.fillText(`Next: ${s.lam.path[0].x},${s.lam.path[0].y}`, panelX+10, panelY+64)
      }

      // Mini-map
      drawMiniMap(ctx, s)

      // Hit flash
      if (s.hitFlash>0) { ctx.fillStyle = `rgba(255,50,50,${(s.hitFlash*0.4).toFixed(2)})`; ctx.fillRect(0,0,width,height) }

      // Pause/Menu overlay
      if (paused || showMenu) {
        ctx.fillStyle = 'rgba(0,0,0,0.55)'; ctx.fillRect(0,0,width,height)
        ctx.fillStyle = '#fff'; ctx.font = '20px Inter'
        const title = paused ? 'Paused' : 'Menu'
        ctx.fillText(title, width/2 - 40, height/2 - 40)
        ctx.font = '14px Inter'
        ctx.fillText('P: Pause/Resume   H: Toggle LAM   T: Auto   N: Mini-map   M: Menu', width/2 - 190, height/2 - 10)
      }

      if (s.gameOver) {
        ctx.fillStyle = 'rgba(0,0,0,0.65)'; ctx.fillRect(0,0,width,height)
        ctx.fillStyle = '#fff'; ctx.font = '28px Inter';
        ctx.fillText(s.win ? 'You Win!' : 'Game Over', width/2-80, height/2 - 10)
      }
    }

    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [autoPilot, cols, rows, germCount, publishState, width, height, paused, showLamPanel, showMiniMap])

  // UI styles
  const containerStyle = useMemo(() => ({ maxWidth: '1200px', margin: '0 auto', padding: '20px' }), [])
  const panelStyle = useMemo(() => ({ background: 'rgba(255, 255, 255, 0.1)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '12px', padding: '16px', marginBottom: '16px' }), [])
  const buttonStyle = useCallback((variant: 'primary'|'danger'|'secondary'|'success') => ({
    background: {
      primary: 'linear-gradient(45deg,#4ecdc4,#44a08d)',
      danger: 'linear-gradient(45deg,#ff6b6b,#ee5a52)',
      secondary: 'rgba(255,255,255,0.2)',
      success: 'linear-gradient(45deg,#4caf50,#45a049)'
    }[variant],
    color: '#fff', border: 'none', padding: '10px 16px', borderRadius: '8px', cursor: 'pointer', fontWeight: 600
  }), [])

  const navigate = useNavigate()

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
      <div style={containerStyle}>
        <h1 style={{ fontSize: '2rem', fontWeight: 700, margin: '10px 0 16px' }}>Play in Browser</h1>
        <div style={panelStyle as any}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 6 }}>Template</label>
              <select value={templateId ?? ''} onChange={(e)=>setTemplateId(parseInt(e.target.value))} style={{ width:'100%', padding:'8px', borderRadius: 8, background:'rgba(255,255,255,0.1)', color:'#fff', border:'1px solid rgba(255,255,255,0.3)' }}>
                <option value="" disabled>Select a template</option>
                {templates.map(t => <option key={t.id} value={t.id} style={{ background:'#333' }}>{t.title}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 6 }}>Session ID</label>
              <div style={{ display:'flex', gap:8 }}>
                <input value={sessionId} onChange={(e)=>setSessionId(e.target.value)} style={{ flex:1, padding:'8px', borderRadius: 8, background:'rgba(255,255,255,0.1)', color:'#fff', border:'1px solid rgba(255,255,255,0.3)' }} />
                <button onClick={()=>setSessionId('session-' + Math.random().toString(36).slice(2,8))} style={buttonStyle('secondary') as any}>New</button>
              </div>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 6 }}>Germs</label>
              <input type="number" min={1} max={20} value={germCount} onChange={(e)=>setGermCount(parseInt(e.target.value||'5'))} style={{ width:'100%', padding:'8px', borderRadius: 8, background:'rgba(255,255,255,0.1)', color:'#fff', border:'1px solid rgba(255,255,255,0.3)' }} />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 6 }}>Mode</label>
              <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                <input type="checkbox" checked={autoPilot} onChange={(e)=>setAutoPilot(e.target.checked)} />
                <span>Auto (follows LAM path or BFS) — press T to toggle</span>
              </div>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 6 }}>Connection</label>
              <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                <div style={{ padding: '6px 10px', borderRadius: 20, border:'1px solid rgba(255,255,255,0.3)', background: connected ? 'rgba(76,175,80,.3)' : 'rgba(255,107,107,.3)' }}>{connected ? 'WebSocket Connected' : 'Disconnected'}</div>
                {!connected ? <button style={buttonStyle('success') as any} onClick={connectWS}>Connect</button> : <button style={buttonStyle('danger') as any} onClick={disconnectWS}>Disconnect</button>}
              </div>
            </div>
            {/* New toggles */}
            <div>
              <label style={{ display:'block', marginBottom:6 }}>Panels</label>
              <div style={{ display:'flex', gap:10, flexWrap:'wrap', alignItems:'center' }}>
                <label><input type="checkbox" checked={showLamPanel} onChange={e=>setShowLamPanel(e.target.checked)} /> Show LAM</label>
                <label><input type="checkbox" checked={showMiniMap} onChange={e=>setShowMiniMap(e.target.checked)} /> Mini-map</label>
              </div>
            </div>
            <div>
              <label style={{ display:'block', marginBottom:6 }}>In‑game</label>
              <div style={{ display:'flex', gap:10, flexWrap:'wrap', alignItems:'center' }}>
                <button onClick={()=>setPaused(p=>!p)} style={buttonStyle('secondary') as any}>{paused? 'Resume' : 'Pause'}</button>
                <button onClick={()=>setShowMenu(m=>!m)} style={buttonStyle('secondary') as any}>{showMenu? 'Hide Menu' : 'Menu'}</button>
              </div>
            </div>
          </div>
          <div style={{ marginTop: 12, display:'flex', gap: 10, flexWrap:'wrap' }}>
            <button onClick={startGame} style={buttonStyle('primary') as any}><i className="fas fa-play"/> Start Game</button>
            <button onClick={()=>publishState(true)} style={buttonStyle('secondary') as any}>Publish State</button>
            <button onClick={()=>startGame()} style={{ background:'linear-gradient(45deg,#f59e0b,#ef4444)', color:'#fff', border:'none', padding:'10px 16px', borderRadius:8, fontWeight:600 }}>Restart</button>
            <button onClick={()=>navigate('/dashboard')} style={{ background:'linear-gradient(45deg,#6366f1,#7c3aed)', color:'#fff', border:'none', padding:'10px 16px', borderRadius:8, fontWeight:600 }}>Exit to Dashboard</button>
            <span style={{ opacity:.85 }}>{status}</span>
          </div>
          <div style={{ marginTop: 6, opacity: .8 }}>Controls: Arrow keys / WASD. T to toggle autopilot. Hints come from LAM via MQTT. Walls may break.</div>
        </div>

        {/* Canvas with glow and border */}
        <div style={{ border: '1px solid rgba(255,255,255,0.15)', borderRadius: 16, overflow:'hidden', background:'rgba(0,0,0,0.25)', boxShadow:'0 20px 60px rgba(220,38,38,0.25), inset 0 0 80px rgba(127,29,29,0.35)' }}>
          <canvas ref={canvasRef} width={width} height={height} style={{ width: width+'px', height: height+'px', display:'block', margin:'0 auto', background:'#0b0507' }} />
        </div>
        {/* Legend for indicators */}
        <div style={{ display:'flex', alignItems:'center', gap:16, marginTop:8, opacity:.9 }}>
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <span style={{ width:14, height:14, borderRadius:14, display:'inline-block', background:'radial-gradient(circle at 40% 35%, #bff9ff 0%, #4ef0ff 60%, rgba(78,240,255,0) 100%)', boxShadow:'0 0 10px #4ef0ff' }}></span>
            <span style={{ fontSize: 13 }}>Oxygen</span>
          </div>
          <div style={{ display:'flex', alignItems:'center', gap:8 }}>
            <span style={{ width:14, height:14, borderRadius:4, display:'inline-block', background:'#22c55e', boxShadow:'0 0 10px rgba(21,128,61,0.8)' }}></span>
            <span style={{ fontSize: 13 }}>Germ</span>
          </div>
        </div>

        <div style={{ marginTop: 10, opacity: .85 }}>
          MQTT topics: publishes maze/state; listens on maze/hint/{'{sessionId}'} via backend bridge.
        </div>
      </div>
    </div>
  )
 }

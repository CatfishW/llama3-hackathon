import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api, leaderboardAPI } from '../api'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useTemplates } from '../contexts/TemplateContext'

// ===== Types =====
 type Vec2 = { x: number; y: number }
 type Cell = 0 | 1 // 0: path, 1: wall
 type Grid = Cell[][]
 type Template = { id: number; title: string }
 type HintMsg = {
  hint?: string
  path?: [number, number][]
  show_path?: boolean  // New field to control path visualization
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
  // ===== Mobile / Responsive Detection =====
  const isMobile = useMemo(() => {
    if (typeof window === 'undefined') return false
    const ua = navigator.userAgent || ''
    return /Mobi|Android|iPhone|iPad|iPod/i.test(ua) || window.innerWidth < 900
  }, [])
  // Auth context
  const { user } = useAuth()
  const navigate = useNavigate()
  const { templates } = useTemplates()
  
  // UI state
  const [templateId, setTemplateId] = useState<number | null>(null)
  const [sessionId, setSessionId] = useState('session-' + Math.random().toString(36).slice(2, 8))
  const [connected, setConnected] = useState(false)
  const [autoPilot, setAutoPilot] = useState(false)
  const [germCount, setGermCount] = useState(5)
  const [status, setStatus] = useState('')
  // Score submission state
  const [scoreSubmitted, setScoreSubmitted] = useState(false)
  const [gameOverTrigger, setGameOverTrigger] = useState(0)
  // Theme state
  const [theme, setTheme] = useState<'default' | 'orange'>(() => {
    const saved = localStorage.getItem('webgame-theme')
    return (saved === 'orange' || saved === 'default') ? saved : 'default'
  })

  // Persist theme changes
  useEffect(() => {
    localStorage.setItem('webgame-theme', theme)
  }, [theme])
  // New UI toggles
  // (In-canvas LAM panel removed; external panel supersedes it)
  const [showLamPanel] = useState(false)
  const [showMiniMap, setShowMiniMap] = useState(true)
  const [paused, setPaused] = useState(false)
  const [showMenu, setShowMenu] = useState(false)
  // External LAM details UI
  const [showLamDetails, setShowLamDetails] = useState(() => !isMobile) // default hidden on mobile
  const [lamExpanded, setLamExpanded] = useState(false)
  const [lamData, setLamData] = useState<{hint:string; path:Vec2[]; breaks:number; error:string; raw:any; rawMessage:any; updatedAt:number; showPath:boolean}>({ hint:'', path:[], breaks:0, error:'', raw:{}, rawMessage:{}, updatedAt:0, showPath:false })
  // LAM flow monitor state
  type LamFlowEvent = { id:number; publishAt:number; receivedAt?:number; latencyMs?:number; actionsDeclared:string[]; actionsApplied:Array<{action:string; at:number; detail?:any}>; hintExcerpt?:string; error?:string }
  const [lamFlow, setLamFlow] = useState<LamFlowEvent[]>([])
  const publishSeqRef = useRef(0)
  const pendingFlowRef = useRef<LamFlowEvent | null>(null)
  // Panel visibility & layout
  const [showLamFlowPanel, setShowLamFlowPanel] = useState(() => !isMobile)
  const [lamFlowPos, setLamFlowPos] = useState({ x: 16, y: 140 })
  const [lamFlowWidth, setLamFlowWidth] = useState(340)
  const [lamDetailsPos, setLamDetailsPos] = useState<{x:number;y:number}|null>(null)
  const dragInfoRef = useRef<{ panel: null | 'flow' | 'details' | 'flow-resize'; offX: number; offY: number; startW?: number }>({ panel: null, offX:0, offY:0 })
  // Mobile control opacity (user-adjustable)
  const [mobileControlsOpacity, setMobileControlsOpacity] = useState<number>(() => {
    if (typeof window === 'undefined') return 0.95
    const saved = localStorage.getItem('mobile-controls-opacity')
    const v = saved ? parseFloat(saved) : 0.95
    return isNaN(v) ? 0.95 : clamp(v, 0.2, 1)
  })
  useEffect(()=> { localStorage.setItem('mobile-controls-opacity', String(mobileControlsOpacity)) }, [mobileControlsOpacity])
  const [showControlsSettings, setShowControlsSettings] = useState(false)

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
  started: false,
    gameOver: false,
    win: false,
  endTime: undefined as number | undefined,
  finalScore: undefined as number | undefined,
    lam: { hint: '', path: [] as Vec2[], breaks: 0, error: '', showPath: false },
    // Effects & visuals
    effects: { speedBoostUntil: 0, slowGermsUntil: 0, freezeGermsUntil: 0 },
    highlight: new Map<string, number>(), // key(x,y) -> until timestamp
    revealMap: false,
    fxPopups: [] as Array<{x:number;y:number;text:string;t0:number;ttl:number}>,
    hitFlash: 0,
    particles: [] as Array<{x:number;y:number;r:number;spd:number;alpha:number}>,
    germStepFlip: false,
  emotion: 'neutral' as 'neutral'|'happy'|'scared'|'tired'|'excited',
  // New wall break FX
  wallBreakParts: [] as Array<{x:number;y:number;vx:number;vy:number;life:number;ttl:number}>,
  cameraShake: 0
  })

  const width = cols * tile
  const height = rows * tile

  // ===== Responsive Canvas Scaling (CSS pixel size separate from internal resolution) =====
  const [canvasScale, setCanvasScale] = useState(1)
  useEffect(() => {
    function computeScale() {
      if (typeof window === 'undefined') return
      // Target: fit within viewport width minus padding, and height below header
      const pad = 32
      const availW = window.innerWidth - pad
      const headerH = 320 // rough upper bound for control panel; adjust dynamically later
      const availH = window.innerHeight - headerH
      const s = Math.min(1, availW / width, availH / height)
      setCanvasScale(s <= 0 ? 1 : s)
    }
    computeScale()
    window.addEventListener('resize', computeScale)
    window.addEventListener('orientationchange', computeScale)
    return () => { window.removeEventListener('resize', computeScale); window.removeEventListener('orientationchange', computeScale) }
  }, [width, height])

  // ===== Touch / Mobile Controls =====
  const dirKeyMap: Record<string, string> = { up: 'ArrowUp', down: 'ArrowDown', left: 'ArrowLeft', right: 'ArrowRight' }
  const holdDirsRef = useRef<Set<string>>(new Set())
  const swipeStartRef = useRef<{x:number;y:number; t:number}|null>(null)

  const pressDir = useCallback((dir: 'up'|'down'|'left'|'right') => {
    const key = dirKeyMap[dir]
    keysRef.current[key] = true
    holdDirsRef.current.add(key)
    // Any manual input disables autopilot (mobile expectation)
    setAutoPilot(false)
  }, [])
  const releaseDir = useCallback((dir: 'up'|'down'|'left'|'right') => {
    const key = dirKeyMap[dir]
    keysRef.current[key] = false
    holdDirsRef.current.delete(key)
  }, [])
  const tapDir = useCallback((dir:'up'|'down'|'left'|'right') => {
    // Short simulated tap for swipe translation
    pressDir(dir); setTimeout(()=>releaseDir(dir), 120)
  }, [pressDir, releaseDir])

  // Swipe gesture on canvas wrapper
  const canvasWrapperRef = useRef<HTMLDivElement|null>(null)
  useEffect(()=>{
    if (!isMobile) return
    const el = canvasWrapperRef.current
    if (!el) return
    const THRESH = 24
    function onTouchStart(e:TouchEvent){
      if (!e.touches.length) return
      const t = e.touches[0]
      swipeStartRef.current = { x: t.clientX, y: t.clientY, t: performance.now() }
    }
    function onTouchEnd(e:TouchEvent){
      if (!swipeStartRef.current) return
      const start = swipeStartRef.current
      swipeStartRef.current = null
      if (e.changedTouches.length===0) return
      const t = e.changedTouches[0]
      const dx = t.clientX - start.x
      const dy = t.clientY - start.y
      if (Math.hypot(dx,dy) < THRESH) return
      if (Math.abs(dx) > Math.abs(dy)) {
        tapDir(dx>0? 'right':'left')
      } else {
        tapDir(dy>0? 'down':'up')
      }
    }
    el.addEventListener('touchstart', onTouchStart, { passive: true })
    el.addEventListener('touchend', onTouchEnd)
    return ()=>{ el.removeEventListener('touchstart', onTouchStart); el.removeEventListener('touchend', onTouchEnd) }
  }, [isMobile, tapDir])

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

    // Wall break helper (adds debris + shake)
  function breakWall(bx: number, by: number) {
      const s = stateRef.current
      if (bx==null || by==null) return
      let x = bx, y = by
      const inBounds = (xx:number,yy:number)=> yy>=0 && yy<s.grid.length && xx>=0 && xx<s.grid[0].length
      // Track reasons for debug (dev only)
      let reason = ''
      // Restrict to 8-neighborhood around player; redirect far requests to closest intended neighbor
      const px = s.player.x, py = s.player.y
      if (Math.abs(bx-px) > 1 || Math.abs(by-py) > 1) {
        let dx = Math.sign(bx - px), dy = Math.sign(by - py)
        if (dx===0 && dy===0) dx = 1 // default
        const candidates: Array<[number,number]> = []
        candidates.push([px+dx, py+dy])
        if (dx!==0 && dy!==0) { candidates.push([px+dx, py]); candidates.push([px, py+dy]) }
        for (let oy=-1; oy<=1; oy++) for (let ox=-1; ox<=1; ox++) if (!(ox===0&&oy===0)) candidates.push([px+ox, py+oy])
        const pick = candidates.find(([cx,cy]) => inBounds(cx,cy) && s.grid[cy][cx] === 1)
        if (pick) { x = pick[0]; y = pick[1]; reason = 'restricted_to_neighbor' } else { return }
      }
      // If out of bounds try swapped (server might send row,col)
      if (!inBounds(x,y) && inBounds(y,x)) {
        reason = 'swapped_out_of_bounds';
        x = by; y = bx
      }
      // If both interpretations in-bounds but chosen cell not a wall while swapped is a wall, prefer swapped
      if (inBounds(x,y) && inBounds(y,x) && s.grid[y][x] !== 1 && s.grid[bx]?.[by] !== 1 && s.grid[by]?.[bx] === 1) {
        reason = 'swapped_wall_detected';
        x = by; y = bx
      }
      if (!inBounds(x,y)) { return }
      // If selected cell not a wall, attempt intelligent recovery: if swapped is wall use it, else search 4-neighbors for a wall
      if (s.grid[y][x] !== 1) {
        // Neighbor search (server may have given a path cell adjacent to intended wall)
        const neigh = [ [x+1,y],[x-1,y],[x,y+1],[x,y-1] ]
        const wallNeigh = neigh.find(([nx,ny]) => inBounds(nx,ny) && s.grid[ny][nx] === 1)
        if (wallNeigh) {
          reason = reason || 'adjacent_wall_used'
          x = wallNeigh[0]; y = wallNeigh[1]
        } else {
          // Nothing to break
          return
        }
      }
      // Avoid breaking critical start/exit cells even if walls (safety)
      if ((x===1&&y===1) || (x===s.exit.x && y===s.exit.y)) return
      s.grid[y][x] = 0
      const pieces = 14 + randInt(8)
      for (let i=0;i<pieces;i++) {
        const ang = Math.random()*Math.PI*2
        const spd = 0.8 + Math.random()*2.2
        s.wallBreakParts.push({
          x: x*tile + tile/2 + (Math.random()*4 - 2),
          y: y*tile + tile/2 + (Math.random()*4 - 2),
          vx: Math.cos(ang)*spd,
          vy: Math.sin(ang)*spd - 1.2*Math.random(),
          life: 0,
          ttl: 600 + randInt(500)
        })
      }
      s.cameraShake = Math.min(12, s.cameraShake + 8)
  // Replace old popup with new falling text (5s)
  ;(s as any).fallTexts = (s as any).fallTexts || []
  ;(s as any).fallTexts.push({ x: x*tile + tile/2, y: y*tile + tile/2, vx: (Math.random()*2-1)*0.4, vy: -0.4 - Math.random()*0.4, t0: performance.now(), ttl: 5000, text: 'Wall Broken!' })
      // Highlight broken location briefly
      s.highlight.set(key(x,y), performance.now()+2500)
  // Debug logging disabled for security
      if ((pendingFlowRef as any)?.current) {
        (pendingFlowRef as any).current.actionsApplied.push({ action:'break_wall', at: performance.now(), detail:{ from:[bx,by], final:[x,y], reason } })
        setLamFlow(f=>[...f])
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

  // Set initial template when templates load
  useEffect(() => {
    if (templates.length > 0 && !templateId) {
      setTemplateId(templates[0].id)
    }
  }, [templates, templateId])

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
        // Only set path if LLM explicitly requested to show it
        s.lam.showPath = hint.show_path === true
        if (s.lam.showPath && hint.path) {
          s.lam.path = hint.path.map(([x,y]) => ({x,y}))
        } else {
          s.lam.path = []
        }
  s.lam.breaks = hint.breaks_remaining ?? s.lam.breaks
  // Maintain React state copy for external panel (include raw envelope and timestamp)
  setLamData({ hint: s.lam.hint, path: s.lam.path.slice(), breaks: s.lam.breaks, error: s.lam.error, raw: hint, rawMessage: data, updatedAt: Date.now(), showPath: s.lam.showPath })
        // Flow monitor: record first receipt event & declared actions
        if (pendingFlowRef.current && !pendingFlowRef.current.receivedAt) {
          const evtF = pendingFlowRef.current
          evtF.receivedAt = performance.now()
          evtF.latencyMs = evtF.receivedAt - evtF.publishAt
          const decl:string[] = []
          const r:any = hint
          if (r.break_wall) decl.push('break_wall')
          if (Array.isArray(r.break_walls) && r.break_walls.length) decl.push('break_walls')
          if (r.show_path) decl.push('show_path')
          if (r.speed_boost_ms) decl.push('speed_boost')
          if (r.slow_germs_ms) decl.push('slow_germs')
          if (r.freeze_germs_ms) decl.push('freeze_germs')
          if (r.teleport_player) decl.push('teleport_player')
          if (r.spawn_oxygen) decl.push('spawn_oxygen')
          if (r.move_exit) decl.push('move_exit')
          if (r.highlight_zone) decl.push('highlight_zone')
          if (r.toggle_autopilot!==undefined) decl.push('toggle_autopilot')
          if (r.reveal_map!==undefined) decl.push('reveal_map')
          evtF.actionsDeclared = decl
          evtF.hintExcerpt = (hint.hint||'').slice(0,140)
          evtF.error = s.lam.error || undefined
          setLamFlow(f=>[...f])
        }
        if (hint.break_wall) {
          const [bx, by] = hint.break_wall
          breakWall(bx, by)
        }
        if ((anyHint.breakWall) && Array.isArray(anyHint.breakWall) && anyHint.breakWall.length===2) {
          const [bx, by] = anyHint.breakWall; breakWall(bx, by)
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
          for (const [bx,by] of hint.break_walls) breakWall(bx, by)
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

  // Submit score to leaderboard
  const submitScore = useCallback(async () => {
    if (!user || !templateId || scoreSubmitted) return
    
    const s = stateRef.current
    if (!s.gameOver) return
    
    try {
  const elapsed = s.endTime ? (s.endTime - s.startTime) / 1000 : (performance.now() - s.startTime) / 1000
  // Use frozen finalScore if available, else compute current
  const baseScore = s.finalScore != null ? s.finalScore : (s.oxygenCollected * 100 - elapsed * 5)
      const winBonus = s.win ? 1000 : 0 // Big bonus for winning
      const finalScore = Math.round(baseScore + winBonus)
      
      await leaderboardAPI.submitScore({
        template_id: templateId,
        session_id: sessionId,
        score: finalScore,
        survival_time: elapsed,
        oxygen_collected: s.oxygenCollected,
        germs: germCount
      })
      
      setScoreSubmitted(true)
      setStatus(`Score ${finalScore} submitted to leaderboard!`)
      
      // Clear status after 3 seconds
      setTimeout(() => setStatus(''), 3000)
    } catch (error) {
      // Failed to submit score (logging disabled)
      setStatus('Failed to submit score to leaderboard')
      setTimeout(() => setStatus(''), 3000)
    }
  }, [user, templateId, sessionId, germCount, scoreSubmitted])

  // Watch for game over to submit score
  useEffect(() => {
    if (gameOverTrigger > 0 && !scoreSubmitted && user && templateId) {
      submitScore()
    }
  }, [gameOverTrigger, submitScore, scoreSubmitted, user, templateId])

  // Start a new game
  const startGame = useCallback(() => {
    // Reset score submission flag
    setScoreSubmitted(false)
    setGameOverTrigger(0)
    
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
  started: true,
      gameOver: false,
      win: false,
  endTime: undefined,
  finalScore: undefined,
      lam: { hint: '', path: [], breaks: 0, error: '', showPath: false },
      effects: { speedBoostUntil: 0, slowGermsUntil: 0, freezeGermsUntil: 0 },
      highlight: new Map(),
      revealMap: false,
      fxPopups: [],
      hitFlash: 0,
      particles: Array.from({length: 80}, ()=>({ x: Math.random()*width, y: Math.random()*height, r: 6+Math.random()*18, spd: 0.3+Math.random()*0.8, alpha: 0.06+Math.random()*0.12 })),
      germStepFlip: false,
  emotion: 'neutral',
  wallBreakParts: [],
  cameraShake: 0
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
    // Server (lam_mqtt_hackathon_deploy.py) expects visible_map semantics: 1 = floor/passable, 0 = wall.
    // Our client grid uses 0 = path, 1 = wall. Convert before publishing so LAM pathfinding works.
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
    try { await api.post('/api/mqtt/publish_state', body) } catch (e) { /* ignore */ }
  // Flow monitor: start a new pending event awaiting LAM response
  const evt: LamFlowEvent = { id: ++publishSeqRef.current, publishAt: performance.now(), actionsDeclared: [], actionsApplied: [] }
  pendingFlowRef.current = evt
  setLamFlow(f => [...f.slice(-14), evt])
  }, [sessionId, templateId])

  // Initialize lamDetailsPos after mount (so we know window width)
  useEffect(()=>{
    if (lamDetailsPos==null) {
      const baseW = lamExpanded ? 460 : 320
      setLamDetailsPos({ x: Math.max(16, (window.innerWidth - baseW - 16)), y: 140 })
    }
  }, [lamDetailsPos, lamExpanded])

  // Global mouse handlers for dragging/resizing panels
  useEffect(()=>{
    function onMove(e:MouseEvent){
      if (!dragInfoRef.current.panel) return
      if (dragInfoRef.current.panel === 'flow') {
        setLamFlowPos(pos => ({ x: e.clientX - dragInfoRef.current.offX, y: e.clientY - dragInfoRef.current.offY }))
      } else if (dragInfoRef.current.panel === 'details') {
        setLamDetailsPos(pos => pos? { x: e.clientX - dragInfoRef.current.offX, y: e.clientY - dragInfoRef.current.offY } : pos)
      } else if (dragInfoRef.current.panel === 'flow-resize') {
        const delta = e.clientX - dragInfoRef.current.offX
        setLamFlowWidth(w => Math.min(600, Math.max(260, (dragInfoRef.current.startW||w) + delta)))
      }
    }
    function onUp(){ dragInfoRef.current.panel = null }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return ()=>{ window.removeEventListener('mousemove', onMove); window.removeEventListener('mouseup', onUp) }
  }, [])

  // Periodic publisher: every 15s while game is running
  useEffect(() => {
    const id = setInterval(() => {
      const s = stateRef.current
  if (templateId && s.started && !s.gameOver) {
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
  // 'H' previously toggled in-canvas LAM panel; removed.
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
  if (!s.started) return

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
        // Use LAM path only if explicitly requested, otherwise use BFS
        const path = (s.lam.showPath && s.lam.path.length) ? s.lam.path : (bfsPath(s.grid, s.player, s.exit) || [])
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
        if (!s.gameOver) {
          s.gameOver = true; s.win = false
          s.endTime = performance.now()
          const elapsedSec = (s.endTime - s.startTime)/1000
          s.finalScore = Math.round(s.oxygenCollected*100 - elapsedSec*5)
          setGameOverTrigger(prev => prev + 1)
        }
      }
      if (s.player.x === s.exit.x && s.player.y === s.exit.y) {
        if (!s.gameOver) {
          s.gameOver = true; s.win = true
          s.endTime = performance.now()
          const elapsedSec = (s.endTime - s.startTime)/1000
          s.finalScore = Math.round(s.oxygenCollected*100 - elapsedSec*5)
          setGameOverTrigger(prev => prev + 1)
        }
      }

      // fade highlights
      for (const [k,v] of Array.from(s.highlight.entries())) if (now>v) s.highlight.delete(k)

      // fade hit flash
      if (s.hitFlash>0) s.hitFlash = Math.max(0, s.hitFlash - 0.1)

      // update wall debris
      if (s.wallBreakParts.length) {
        s.wallBreakParts = s.wallBreakParts.filter(p => {
          p.life += stepMs
          p.x += p.vx
            p.y += p.vy
          p.vy += 0.04 // gravity-ish
          return p.life < p.ttl
        })
      }
      // update falling texts
      if ((s as any).fallTexts?.length) {
        ;(s as any).fallTexts = (s as any).fallTexts.filter((ft:any)=>{
          const age = now - ft.t0
          ft.vy += 0.05
          ft.x += ft.vx * (stepMs/16)
          ft.y += ft.vy * (stepMs/16)
          return age < ft.ttl && ft.y < height + 40
        })
      }
      // decay camera shake
      if (s.cameraShake>0) s.cameraShake *= 0.88
    }

    function draw() {
      const canvas = canvasRef.current; if (!canvas) return
      const ctx = canvas.getContext('2d'); if (!ctx) return
      const s = stateRef.current
      ctx.clearRect(0,0,canvas.width, canvas.height)
      // Camera shake transform
      const shakeMag = s.cameraShake
      if (shakeMag>0) {
        ctx.save()
        const offX = (Math.random()*2-1)*shakeMag
        const offY = (Math.random()*2-1)*shakeMag
        ctx.translate(offX, offY)
        drawVignette(ctx)
        drawPlasma(ctx)
      } else {
        drawVignette(ctx)
        drawPlasma(ctx)
      }

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

      // LAM path overlay - only show if LLM explicitly requested it
      if (s.lam.showPath && s.lam.path && s.lam.path.length) {
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

      // debris (after player so appears above floor but below HUD overlays)
      if (s.wallBreakParts.length) {
        for (const p of s.wallBreakParts) {
          const lifeRatio = p.life / p.ttl
          const alpha = 1 - lifeRatio
          const pr = 3 + 3*(1-lifeRatio)
          ctx.globalAlpha = alpha
          ctx.fillStyle = '#5a1f1f'
          ctx.beginPath(); ctx.arc(p.x, p.y, pr, 0, Math.PI*2); ctx.fill()
          ctx.globalAlpha = 1
        }
      }

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
      // Falling wall break texts
      const fallTexts = (s as any).fallTexts || []
      for (const ft of fallTexts) {
        const age = now - ft.t0
        const ratio = age / ft.ttl
        const alpha = 1 - ratio
        ctx.globalAlpha = alpha
        ctx.fillStyle = '#ffd1d1'
        ctx.font = 'bold 16px Inter'
        ctx.fillText(ft.text, ft.x - 50, ft.y)
        ctx.globalAlpha = 1
      }

      // HUD (freeze after game over)
  const elapsed = s.started ? (s.gameOver && s.endTime ? (s.endTime - s.startTime)/1000 : (performance.now() - s.startTime)/1000) : 0
  const score = s.started ? (s.gameOver && s.finalScore!=null ? s.finalScore : Math.round(s.oxygenCollected*100 - elapsed*5)) : 0
      ctx.fillStyle = '#fff'; ctx.font = '16px Inter, system-ui, sans-serif'
      ctx.fillText(`O₂: ${s.oxygenCollected}  Time: ${elapsed.toFixed(1)}s  Score: ${score}`, 10, 22)

      // LAM Panel (toggle)
  // (In-canvas LAM panel removed)

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
        ctx.fillStyle = 'rgba(0,0,0,0.75)'; ctx.fillRect(0,0,width,height)
        ctx.fillStyle = '#fff'; ctx.font = '32px Inter';
        const winText = s.win ? 'You Win!' : 'Game Over'
        ctx.fillText(winText, width/2 - ctx.measureText(winText).width/2, height/2 - 60)
        
        // Show final score
        ctx.font = '20px Inter';
  const scoreText = `Final Score: ${score}`
        ctx.fillText(scoreText, width/2 - ctx.measureText(scoreText).width/2, height/2 - 20)
        
        // Show game stats
        ctx.font = '16px Inter';
        const statsText = `Oxygen: ${s.oxygenCollected} | Time: ${elapsed.toFixed(1)}s | Germs: ${germCount}`
        ctx.fillText(statsText, width/2 - ctx.measureText(statsText).width/2, height/2 + 10)
        
        // Show submission status
        if (user && templateId) {
          ctx.font = '14px Inter';
          ctx.fillStyle = scoreSubmitted ? '#4ade80' : '#fbbf24';
          const statusText = scoreSubmitted ? 'Score submitted to leaderboard!' : 'Submitting score...'
          ctx.fillText(statusText, width/2 - ctx.measureText(statusText).width/2, height/2 + 40)
        } else if (!user) {
          ctx.font = '14px Inter';
          ctx.fillStyle = '#f87171';
          const loginText = 'Login to submit your score to leaderboard'
          ctx.fillText(loginText, width/2 - ctx.measureText(loginText).width/2, height/2 + 40)
        }
      }
      if (!s.started) {
        ctx.fillStyle = 'rgba(0,0,0,0.55)'; ctx.fillRect(0,0,width,height)
        ctx.fillStyle = '#fff'; ctx.font = '24px Inter';
        ctx.fillText('Click Start Game to Begin', width/2 - 170, height/2)
      }

  // restore after shake
  if (shakeMag>0) ctx.restore()
    }

    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [autoPilot, cols, rows, germCount, publishState, width, height, paused, showMiniMap])

  // UI styles
  const containerStyle = useMemo(() => ({ maxWidth: '1200px', margin: '0 auto', padding: '20px' }), [])
  const panelStyle = useMemo(() => ({ background: 'rgba(255, 255, 255, 0.1)', border: '1px solid rgba(255,255,255,0.2)', borderRadius: '12px', padding: '16px', marginBottom: '16px' }), [])
  
  // Theme configuration
  const themeConfig = useMemo(() => ({
    default: {
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      canvasBorder: 'rgba(255,255,255,0.15)',
      canvasBackground: 'rgba(0,0,0,0.25)',
      canvasShadow: '0 20px 60px rgba(220,38,38,0.25), inset 0 0 80px rgba(127,29,29,0.35)',
      buttonPrimary: 'linear-gradient(45deg,#4ecdc4,#44a08d)',
      buttonDanger: 'linear-gradient(45deg,#ff6b6b,#ee5a52)',
      buttonSuccess: 'linear-gradient(45deg,#4caf50,#45a049)',
      buttonSecondary: 'rgba(255,255,255,0.2)',
      leaderboardButton: 'linear-gradient(45deg,#fbbf24,#f59e0b)',
      restartButton: 'linear-gradient(45deg,#f59e0b,#ef4444)',
      exitButton: 'linear-gradient(45deg,#6366f1,#7c3aed)'
    },
    orange: {
      background: 'linear-gradient(135deg, #ff9a56 0%, #ff6b35 50%, #f7931e 100%)',
      canvasBorder: 'rgba(255,255,255,0.2)',
      canvasBackground: 'rgba(139,69,19,0.2)',
      canvasShadow: '0 20px 60px rgba(255,140,0,0.25), inset 0 0 80px rgba(139,69,19,0.35)',
      buttonPrimary: 'linear-gradient(45deg,#ff8c42,#ff6b35)',
      buttonDanger: 'linear-gradient(45deg,#ff4757,#ff3742)',
      buttonSuccess: 'linear-gradient(45deg,#2ed573,#1e90ff)',
      buttonSecondary: 'rgba(255,255,255,0.25)',
      leaderboardButton: 'linear-gradient(45deg,#ffa726,#ff9800)',
      restartButton: 'linear-gradient(45deg,#ff7043,#ff5722)',
      exitButton: 'linear-gradient(45deg,#8e24aa,#7b1fa2)'
    }
  }), [])

  const currentTheme = themeConfig[theme]

  const buttonStyle = useCallback((variant: 'primary'|'danger'|'secondary'|'success') => ({
    background: {
      primary: currentTheme.buttonPrimary,
      danger: currentTheme.buttonDanger,
      secondary: currentTheme.buttonSecondary,
      success: currentTheme.buttonSuccess
    }[variant],
    color: '#fff', border: 'none', padding: '10px 16px', borderRadius: '8px', cursor: 'pointer', fontWeight: 600
  }), [currentTheme])

  return (
  <div style={{ minHeight: '100vh', background: currentTheme.background, color: 'white', WebkitUserSelect:'none', userSelect:'none' }}>
      <div style={containerStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h1 style={{ fontSize: '2rem', fontWeight: 700, margin: '10px 0' }}>Play in Browser</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Theme Switcher */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '14px', opacity: 0.9 }}>Theme:</span>
              <select 
                value={theme} 
                onChange={(e) => setTheme(e.target.value as 'default' | 'orange')}
                style={{ 
                  padding: '4px 8px', 
                  borderRadius: '6px', 
                  background: 'rgba(255,255,255,0.1)', 
                  color: '#fff', 
                  border: '1px solid rgba(255,255,255,0.3)',
                  fontSize: '14px'
                }}
              >
                <option value="default" style={{ background: '#333' }}>Default Blue</option>
                <option value="orange" style={{ background: '#333' }}>Orange Sunset</option>
              </select>
            </div>
            <div style={{ fontSize: '14px', opacity: 0.9 }}>
              {user ? (
                <span style={{ color: '#4ade80' }}>✓ Logged in as {user.email} - Scores will be saved</span>
              ) : (
                <span style={{ color: '#fbbf24' }}>⚠ Not logged in - Scores won't be saved to leaderboard</span>
              )}
            </div>
          </div>
        </div>
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
                {/* In-canvas LAM panel removed */}
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
            <button onClick={()=>startGame()} style={{ background: currentTheme.restartButton, color:'#fff', border:'none', padding:'10px 16px', borderRadius:8, fontWeight:600 }}>Restart</button>
            <button onClick={()=>navigate('/leaderboard')} style={{ background: currentTheme.leaderboardButton, color:'#fff', border:'none', padding:'10px 16px', borderRadius:8, fontWeight:600 }}>🏆 Leaderboard</button>
            <button onClick={()=>navigate('/dashboard')} style={{ background: currentTheme.exitButton, color:'#fff', border:'none', padding:'10px 16px', borderRadius:8, fontWeight:600 }}>Exit to Dashboard</button>
            <span style={{ opacity:.85 }}>{status}</span>
          </div>
          <div style={{ marginTop: 6, opacity: .8 }}>Controls: Arrow keys / WASD. T to toggle autopilot. Hints come from LAM via MQTT. Walls may break.</div>
        </div>

        {/* Canvas with glow and border */}
  <div ref={canvasWrapperRef} style={{ border: `1px solid ${currentTheme.canvasBorder}`, borderRadius: 16, overflow:'hidden', background: currentTheme.canvasBackground, boxShadow: currentTheme.canvasShadow, width: width*canvasScale, height: height*canvasScale, margin: '0 auto', position:'relative', touchAction:'none' }}>
          <canvas
            ref={canvasRef}
            width={width}
            height={height}
            style={{ width: width*canvasScale, height: height*canvasScale, display:'block', background:'#0b0507' }}
          />
          {isMobile && (
            <button
              aria-label="Control Settings"
              onClick={()=>setShowControlsSettings(s=>!s)}
              style={{ position:'absolute', top:8, left:8, zIndex:5, background:'rgba(0,0,0,0.5)', color:'#fff', border:'1px solid rgba(255,255,255,0.3)', borderRadius:8, padding:'6px 10px', fontSize:12, cursor:'pointer' }}
            >⚙</button>
          )}
          {isMobile && showControlsSettings && (
            <div style={{ position:'absolute', top:48, left:8, zIndex:5, background:'rgba(0,0,0,0.55)', backdropFilter:'blur(6px)', border:'1px solid rgba(255,255,255,0.25)', borderRadius:12, padding:'10px 12px', width:180, fontSize:12, color:'#fff' }}>
              <div style={{ fontWeight:600, marginBottom:6 }}>Controls Opacity</div>
              <input
                aria-label="Mobile controls opacity"
                type="range"
                min={0.2}
                max={1}
                step={0.05}
                value={mobileControlsOpacity}
                onChange={e=> setMobileControlsOpacity(parseFloat(e.target.value)) }
                style={{ width:'100%' }}
              />
              <div style={{ textAlign:'right', marginTop:4 }}>{Math.round(mobileControlsOpacity*100)}%</div>
              <button onClick={()=>setShowControlsSettings(false)} style={{ marginTop:8, width:'100%', background:'rgba(255,255,255,0.15)', border:'1px solid rgba(255,255,255,0.3)', color:'#fff', padding:'4px 8px', borderRadius:6, cursor:'pointer' }}>Close</button>
            </div>
          )}
          {isMobile && (
            <div style={{ position:'absolute', left:4, bottom:4, right:4, display:'flex', justifyContent:'space-between', gap:12, pointerEvents:'none', opacity: mobileControlsOpacity }}>
              {/* D-Pad */}
              <div style={{ display:'grid', gridTemplateColumns:'repeat(3,56px)', gridTemplateRows:'repeat(3,56px)', gap:4, opacity:0.95, pointerEvents:'auto' }}>
                <div></div>
                <button aria-label="Move Up" onPointerDown={()=>pressDir('up')} onPointerUp={()=>releaseDir('up')} onPointerLeave={()=>releaseDir('up')} style={mobileBtnStyle()}>▲</button>
                <div></div>
                <button aria-label="Move Left" onPointerDown={()=>pressDir('left')} onPointerUp={()=>releaseDir('left')} onPointerLeave={()=>releaseDir('left')} style={mobileBtnStyle()}>◀</button>
                <button aria-label="Auto Pilot" onClick={()=>setAutoPilot(a=>!a)} style={mobileCenterBtnStyle(autoPilot)}>{autoPilot? 'AUTO':'MAN'}</button>
                <button aria-label="Move Right" onPointerDown={()=>pressDir('right')} onPointerUp={()=>releaseDir('right')} onPointerLeave={()=>releaseDir('right')} style={mobileBtnStyle()}>▶</button>
                <div></div>
                <button aria-label="Move Down" onPointerDown={()=>pressDir('down')} onPointerUp={()=>releaseDir('down')} onPointerLeave={()=>releaseDir('down')} style={mobileBtnStyle()}>▼</button>
                <div></div>
              </div>
              {/* Action Buttons */}
              <div style={{ display:'flex', flexDirection:'column', gap:10, pointerEvents:'auto' }}>
                <button onClick={()=>setPaused(p=>!p)} style={pillBtnStyle()}>{paused? 'Resume':'Pause'}</button>
                <button onClick={()=>startGame()} style={pillBtnStyle(currentTheme.buttonPrimary)}>Restart</button>
                <button onClick={()=>setShowMiniMap(m=>!m)} style={pillBtnStyle()}>{showMiniMap? 'Hide Map':'Show Map'}</button>
              </div>
            </div>
          )}
          {isMobile && (
            <div style={{ position:'absolute', top:8, right:8, background:'rgba(0,0,0,0.45)', color:'#fff', fontSize:10, padding:'4px 8px', borderRadius:12, pointerEvents:'none', letterSpacing:.5 }}>
              Swipe inside board to move • Scroll outside to page
            </div>
          )}
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
      {/* External LAM Output Panel */}
  {showLamDetails && lamDetailsPos && (
        <div
          style={{ position:'fixed', left:lamDetailsPos.x, top:lamDetailsPos.y, width: lamExpanded? 460: 320, maxHeight:'70vh', overflow:'auto', background:'linear-gradient(165deg, rgba(15,15,25,0.85) 0%, rgba(55,25,65,0.78) 100%)', backdropFilter:'blur(10px)', border:'1px solid rgba(255,255,255,0.18)', borderRadius:20, padding:16, boxShadow:'0 10px 40px -8px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.05)', zIndex:50, cursor:'move' }}
          onMouseDown={e=>{ dragInfoRef.current.panel='details'; dragInfoRef.current.offX = e.clientX - lamDetailsPos.x; dragInfoRef.current.offY = e.clientY - lamDetailsPos.y }}
        >
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
            <strong style={{ fontSize:15, letterSpacing:'.5px' }}>LAM Intelligence Output</strong>
            <div style={{ display:'flex', gap:6 }}>
              <button onClick={()=>setLamExpanded(e=>!e)} style={{ background:'rgba(255,255,255,0.15)', color:'#fff', border:'1px solid rgba(255,255,255,0.3)', padding:'4px 8px', borderRadius:6, cursor:'pointer', fontSize:11 }}>{lamExpanded? 'Collapse':'Expand'}</button>
              <button onClick={()=>setShowLamDetails(false)} style={{ background:'rgba(255,255,255,0.15)', color:'#fff', border:'1px solid rgba(255,255,255,0.3)', padding:'4px 8px', borderRadius:6, cursor:'pointer', fontSize:11 }}>Hide</button>
            </div>
          </div>
          {lamData.error && <div style={{ background:'linear-gradient(135deg, rgba(255,60,60,0.15), rgba(120,30,30,0.25))', border:'1px solid rgba(255,90,90,0.4)', padding:8, borderRadius:10, fontSize:12, marginBottom:10 }}><strong style={{ color:'#ffb3b3' }}>Error:</strong> {lamData.error}</div>}
          <div style={{ fontSize:12, lineHeight:1.5, display:'flex', flexDirection:'column', gap:10 }}>
            <section>
              <div style={{ fontWeight:600, marginBottom:4, letterSpacing:'.5px', fontSize:12, opacity:.85 }}>Hint</div>
              <div style={{ whiteSpace:'pre-wrap', background:'rgba(255,255,255,0.06)', padding:8, borderRadius:10 }}>{lamData.hint || '—'}</div>
            </section>
            {lamData.showPath && (
            <section>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:4 }}>
                <div style={{ fontWeight:600, letterSpacing:'.5px', opacity:.85 }}>Path <span style={{ opacity:.6 }}>({lamData.path.length})</span></div>
                {lamData.path.length>0 && <div style={{ fontSize:11, opacity:.7 }}>Next: ({lamData.path[0].x},{lamData.path[0].y})</div>}
              </div>
              <div style={{ fontFamily:'monospace', fontSize:11, maxHeight: lamExpanded? 220: 80, overflow:'auto', padding:'6px 8px', background:'rgba(255,255,255,0.07)', borderRadius:8, lineHeight:1.35 }}>
                {lamData.path.length? lamData.path.map((p,i)=> (i && i%8===0? `\n(${p.x},${p.y})`:`(${p.x},${p.y})`)).join(' → ') : '—'}
              </div>
            </section>
            )}
            <section>
              <div style={{ display:'flex', flexWrap:'wrap', gap:8 }}>
                <div style={{ background:'rgba(255,255,255,0.08)', padding:'6px 10px', borderRadius:20 }}><span style={{ opacity:.65 }}>Breaks</span>: {lamData.breaks}</div>
                <div style={{ background:'rgba(255,255,255,0.08)', padding:'6px 10px', borderRadius:20 }}><span style={{ opacity:.65 }}>Autopilot</span>: {autoPilot? 'On':'Off'}</div>
                <div style={{ background:'rgba(255,255,255,0.08)', padding:'6px 10px', borderRadius:20 }}><span style={{ opacity:.65 }}>Updated</span>: {lamData.updatedAt? `${((Date.now()-lamData.updatedAt)/1000).toFixed(1)}s ago`:'—'}</div>
              </div>
            </section>
            <section>
              <div style={{ fontWeight:600, marginBottom:4, opacity:.85 }}>Detected Actions</div>
              {(() => {
                const r = lamData.raw || {}
                const keys: string[] = []
                const push = (k:string,c:boolean)=>{ if(c) keys.push(k) }
                push('break_wall', !!r.break_wall)
                push('break_walls', Array.isArray(r.break_walls) && r.break_walls.length>0)
                push('show_path', !!r.show_path)
                push('speed_boost', !!r.speed_boost_ms)
                push('slow_germs', !!r.slow_germs_ms)
                push('freeze_germs', !!r.freeze_germs_ms)
                push('teleport_player', !!r.teleport_player)
                push('spawn_oxygen', Array.isArray(r.spawn_oxygen) && r.spawn_oxygen.length>0)
                push('move_exit', !!r.move_exit)
                push('highlight_zone', Array.isArray(r.highlight_zone) && r.highlight_zone.length>0)
                push('toggle_autopilot', r.toggle_autopilot!==undefined)
                push('reveal_map', r.reveal_map!==undefined)
                return <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>{keys.length? keys.map(k=> <span key={k} style={{ background:'linear-gradient(135deg,#433,#655)', padding:'4px 8px', borderRadius:14, fontSize:11 }}>{k}</span>) : <span style={{ opacity:.6 }}>None</span>}</div>
              })()}
            </section>
            {lamExpanded && (
              <section>
                <div style={{ fontWeight:600, marginBottom:4, opacity:.85 }}>Raw Hint JSON</div>
                <pre style={{ margin:0, fontSize:11, lineHeight:1.3, maxHeight:200, overflow:'auto', background:'rgba(255,255,255,0.05)', padding:8, border:'1px solid rgba(255,255,255,0.12)', borderRadius:10 }}>{JSON.stringify(lamData.raw, null, 2)}</pre>
              </section>
            )}
            {lamExpanded && (
              <section>
                <div style={{ fontWeight:600, marginBottom:4, opacity:.85 }}>Raw Message Envelope</div>
                <pre style={{ margin:0, fontSize:11, lineHeight:1.3, maxHeight:200, overflow:'auto', background:'rgba(255,255,255,0.05)', padding:8, border:'1px solid rgba(255,255,255,0.12)', borderRadius:10 }}>{JSON.stringify(lamData.rawMessage, null, 2)}</pre>
              </section>
            )}
            <div style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
              <button onClick={()=>navigator.clipboard.writeText(JSON.stringify(lamData.raw, null, 2))} style={{ background:'linear-gradient(45deg,#6366f1,#7c3aed)', color:'#fff', border:'none', padding:'6px 12px', borderRadius:8, fontSize:12, cursor:'pointer' }}>Copy Hint JSON</button>
              {lamData.showPath && <button onClick={()=>navigator.clipboard.writeText(JSON.stringify(lamData.path, null, 2))} style={{ background:'linear-gradient(45deg,#0ea5e9,#2563eb)', color:'#fff', border:'none', padding:'6px 12px', borderRadius:8, fontSize:12, cursor:'pointer' }}>Copy Path</button>}
              <button onClick={()=>navigator.clipboard.writeText(JSON.stringify(lamData.rawMessage, null, 2))} style={{ background:'linear-gradient(45deg,#64748b,#475569)', color:'#fff', border:'none', padding:'6px 12px', borderRadius:8, fontSize:12, cursor:'pointer' }}>Copy Envelope</button>
            </div>
          </div>
        </div>
      )}
      {!showLamDetails && (
        <div style={{ position:'fixed', left:16, top:16, zIndex:40 }}>
          <button onClick={()=>setShowLamDetails(true)} style={{ background:'rgba(0,0,0,0.55)', backdropFilter:'blur(4px)', color:'#fff', border:'1px solid rgba(255,255,255,0.3)', padding:'6px 12px', borderRadius:8, fontSize:12, cursor:'pointer' }}>Show LAM Output</button>
        </div>
      )}
      {/* LAM Flow Timeline Panel */}
  {showLamFlowPanel && (
      <div
        style={{ position:'fixed', left:lamFlowPos.x, top:lamFlowPos.y, width:lamFlowWidth, maxHeight:'70vh', overflow:'auto', background:'linear-gradient(160deg, rgba(10,20,30,0.85), rgba(40,15,55,0.8))', backdropFilter:'blur(10px)', border:'1px solid rgba(255,255,255,0.18)', borderRadius:20, padding:14, boxShadow:'0 10px 40px -8px rgba(0,0,0,0.55)', zIndex:50, cursor:'move' }}
        onMouseDown={e=>{ dragInfoRef.current.panel='flow'; dragInfoRef.current.offX = e.clientX - lamFlowPos.x; dragInfoRef.current.offY = e.clientY - lamFlowPos.y }}
      >
        <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:6 }}>
          <strong style={{ fontSize:13, letterSpacing:'.5px' }}>LAM Prompt → Response Flow</strong>
          <div style={{ display:'flex', gap:6 }}>
            <button onClick={()=>setLamFlow([])} style={{ background:'rgba(255,255,255,0.15)', color:'#fff', border:'1px solid rgba(255,255,255,0.25)', padding:'3px 8px', borderRadius:6, cursor:'pointer', fontSize:10 }}>Clear</button>
            <button onClick={()=>setShowLamFlowPanel(false)} style={{ background:'rgba(255,255,255,0.15)', color:'#fff', border:'1px solid rgba(255,255,255,0.25)', padding:'3px 8px', borderRadius:6, cursor:'pointer', fontSize:10 }}>Hide</button>
          </div>
        </div>
        <div style={{ fontSize:10, opacity:.7, marginBottom:8 }}>Each state publish tracked until hint arrives; shows latency & action application timeline.</div>
        <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
          {[...lamFlow].slice().reverse().map(evt => {
            const lat = evt.latencyMs!=null? `${evt.latencyMs.toFixed(0)} ms` : '—'
            return (
              <div key={evt.id} style={{ background:'rgba(255,255,255,0.06)', border:'1px solid rgba(255,255,255,0.12)', borderRadius:12, padding:'8px 10px' }}>
                <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
                  <div style={{ fontWeight:600, fontSize:11 }}>Publish #{evt.id}</div>
                  <div style={{ fontSize:10, opacity:.65 }}>{lat}</div>
                </div>
                <div style={{ fontSize:10, lineHeight:1.4 }}>
                  <div><span style={{ opacity:.6 }}>Declared:</span> {evt.actionsDeclared.length? evt.actionsDeclared.join(', ') : '—'}</div>
                  <div><span style={{ opacity:.6 }}>Applied:</span> {evt.actionsApplied.length? evt.actionsApplied.map(a=>a.action).join(', ') : '—'}</div>
                  <div><span style={{ opacity:.6 }}>Hint:</span> {evt.hintExcerpt || '—'}</div>
                  {evt.error && <div style={{ color:'#ff9d9d' }}><span style={{ opacity:.6 }}>Error:</span> {evt.error}</div>}
                </div>
                {evt.actionsApplied.length>0 && (
                  <div style={{ marginTop:6, display:'grid', gap:4 }}>
                    {evt.actionsApplied.map((a,i)=> {
                      const dt = evt.receivedAt? (a.at - evt.receivedAt) : 0
                      return <div key={i} style={{ background:'rgba(255,255,255,0.05)', padding:'3px 6px', borderRadius:6, display:'flex', justifyContent:'space-between', fontSize:10 }}>
                        <span style={{ fontFamily:'monospace' }}>{a.action}</span>
                        <span style={{ opacity:.6 }}>{dt.toFixed(0)}ms</span>
                      </div>
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
        {/* Resize handle */}
        <div
          style={{ position:'absolute', right:4, top:0, bottom:0, width:10, cursor:'ew-resize' }}
          onMouseDown={e=>{ e.stopPropagation(); dragInfoRef.current.panel='flow-resize'; dragInfoRef.current.offX = e.clientX; dragInfoRef.current.startW = lamFlowWidth }}
        />
      </div>
      )}
      {!showLamFlowPanel && (
        <div style={{ position:'fixed', left:16, top:16, zIndex:40 }}>
          <button onClick={()=>setShowLamFlowPanel(true)} style={{ background:'rgba(0,0,0,0.55)', backdropFilter:'blur(4px)', color:'#fff', border:'1px solid rgba(255,255,255,0.3)', padding:'6px 12px', borderRadius:8, fontSize:12, cursor:'pointer' }}>Show Flow</button>
        </div>
      )}
    </div>
  )
 }

// ===== Reusable mobile button styles (module scope so they're stable) =====
function mobileBtnStyle(){
  return { width:56, height:56, borderRadius:12, border:'1px solid rgba(255,255,255,0.25)', background:'rgba(0,0,0,0.45)', color:'#fff', fontSize:22, display:'flex', alignItems:'center', justifyContent:'center', fontWeight:600, backdropFilter:'blur(4px)', boxShadow:'0 4px 12px -2px rgba(0,0,0,0.5)', touchAction:'none' } as React.CSSProperties
}
function mobileCenterBtnStyle(active:boolean){
  return { width:56, height:56, borderRadius:28, border:'2px solid '+(active? '#4ade80':'rgba(255,255,255,0.35)'), background: active? 'linear-gradient(135deg,#059669,#10b981)':'rgba(0,0,0,0.55)', color:'#fff', fontSize:11, letterSpacing:'.5px', display:'flex', alignItems:'center', justifyContent:'center', fontWeight:700, lineHeight:1.1, padding:4, textAlign:'center', backdropFilter:'blur(6px)', boxShadow: active? '0 0 14px -2px rgba(16,185,129,0.7)':'0 4px 12px -2px rgba(0,0,0,0.5)', touchAction:'none' } as React.CSSProperties
}
function pillBtnStyle(grad?:string){
  return { minWidth:120, padding:'12px 16px', borderRadius:30, border:'1px solid rgba(255,255,255,0.25)', background: grad || 'rgba(0,0,0,0.55)', color:'#fff', fontSize:14, fontWeight:600, backdropFilter:'blur(6px)', boxShadow:'0 4px 10px -2px rgba(0,0,0,0.5)', touchAction:'none' } as React.CSSProperties
}

import { useCallback, useEffect, useMemo, useRef, useState, CSSProperties } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Play,
  RotateCcw,
  LayoutDashboard,
  Trophy,
  Settings,
  ChevronRight,
  Gamepad2,
  Zap,
  FileCode,
  Maximize2,
  Pause,
  Menu as MenuIcon,
  X,
  Plus,
  RefreshCw,
  Info,
  Check,
  Layout,
  Layers,
  ArrowRight,
  Target,
  Bot,
  User as UserIcon,
  AlertTriangle,
  Loader2,
  Flag
} from 'lucide-react'
import { api, leaderboardAPI, modelsAPI, llmAPI } from '../api'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useTemplates } from '../contexts/TemplateContext'
import { Grid, HintMsg, Vec2 } from '../components/web-game/types'
import { bfsPath, clamp, generateMaze, key, randInt } from '../components/web-game/utils'
import LamFlowPanel from '../components/web-game/LamFlowPanel'
import LamDetailsPanel from '../components/web-game/LamDetailsPanel'
import MobileControls from '../components/web-game/MobileControls'

export default function WebGame() {
  const { theme } = useTheme()
  const isMobile = useMemo(() => {
    if (typeof window === 'undefined') return false
    const ua = navigator.userAgent || ''
    return /Mobi|Android|iPhone|iPad|iPod/i.test(ua) || window.innerWidth < 900
  }, [])

  const { user } = useAuth()
  const navigate = useNavigate()
  const { templates, loading: templatesLoading } = useTemplates()
  const [showTemplatePicker, setShowTemplatePicker] = useState(false)
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
  const [gameMode, setGameMode] = useState<'manual' | 'lam'>('manual')
  const [selectedMode, setSelectedMode] = useState<'manual' | 'lam'>('manual')
  const [startStep, setStartStep] = useState<'mode' | 'template'>('mode')
  const gameModeRef = useRef<'manual' | 'lam'>(gameMode)
  useEffect(() => { gameModeRef.current = gameMode }, [gameMode])

  const [templateId, setTemplateId] = useState<number | null>(null)
  const [sessionId, setSessionId] = useState('session-' + Math.random().toString(36).slice(2, 8))
  const [connected, setConnected] = useState(false)
  const [germCount, setGermCount] = useState(0)
  const [status, setStatus] = useState('')
  const [scoreSubmitted, setScoreSubmitted] = useState(false)
  const [gameOverTrigger, setGameOverTrigger] = useState(0)
  const [activeModel, setActiveModel] = useState<{ name: string, is_active: boolean } | null>(null)
  const [availableModels, setAvailableModels] = useState<any[]>([])
  const [checkingModel, setCheckingModel] = useState(false)

  const themeColors: any = {
    slate: { primary: '#6366f1', secondary: '#818cf8', bg: '#0f172a', accent: 'rgba(99, 102, 241, 0.15)' },
    emerald: { primary: '#10b981', secondary: '#34d399', bg: '#064e3b', accent: 'rgba(16, 185, 129, 0.15)' },
    rose: { primary: '#f43f5e', secondary: '#fb7185', bg: '#4c0519', accent: 'rgba(244, 63, 94, 0.15)' },
    amber: { primary: '#f59e0b', secondary: '#fbbf24', bg: '#451a03', accent: 'rgba(245, 158, 11, 0.15)' }
  }
  const activeTheme = themeColors[theme] || themeColors.slate

  useEffect(() => {
    checkLLMStatus()
    fetchAvailableModels()
    // Optional: check every 30 seconds
    const timer = setInterval(checkLLMStatus, 30000)
    return () => clearInterval(timer)
  }, [])

  async function fetchAvailableModels() {
    try {
      const res = await modelsAPI.getAvailable()
      setAvailableModels(res.data)
    } catch (e) {
      console.error('Failed to fetch available models:', e)
    }
  }

  async function checkLLMStatus() {
    try {
      setCheckingModel(true)
      const selectedRes = await modelsAPI.getSelected()
      const selectedName = selectedRes.data.name

      const statusRes = await modelsAPI.getStatus()
      const status = statusRes.data.find((m: any) => m.name === selectedName)

      if (status) {
        setActiveModel({
          name: status.name,
          is_active: status.is_active
        })
      } else {
        setActiveModel({
          name: selectedName,
          is_active: false
        })
      }
    } catch (e) {
      console.error('Failed to check LLM status:', e)
    } finally {
      setCheckingModel(false)
    }
  }

  const [showMiniMap, setShowMiniMap] = useState(true)
  const [paused, setPaused] = useState(false)
  const [showLamDetails, setShowLamDetails] = useState(() => !isMobile)
  const [lamExpanded, setLamExpanded] = useState(false)
  const [lamData, setLamData] = useState<{ hint: string; path: Vec2[]; breaks: number; error: string; raw: any; rawMessage: any; updatedAt: number; showPath: boolean }>({ hint: '', path: [], breaks: 0, error: '', raw: {}, rawMessage: {}, updatedAt: 0, showPath: false })

  const [lamFlow, setLamFlow] = useState<any[]>([])
  const publishSeqRef = useRef(0)
  const pendingFlowRef = useRef<any>(null)
  const [showLamFlowPanel, setShowLamFlowPanel] = useState(() => !isMobile)
  const [lamFlowPos, setLamFlowPos] = useState({ x: 16, y: 140 })
  const [lamFlowWidth, setLamFlowWidth] = useState(340)
  const [lamDetailsPos, setLamDetailsPos] = useState<{ x: number; y: number } | null>(null)
  const dragInfoRef = useRef<{ panel: 'flow' | 'details' | 'flow-resize' | null; offX: number; offY: number; startW?: number }>({ panel: null, offX: 0, offY: 0 })

  const [mobileControlsOpacity, setMobileControlsOpacity] = useState(0.95)
  const [mqttSendRate, setMqttSendRate] = useState(3000)

  const tile = 24
  const [boardCols, setBoardCols] = useState(33)
  const [boardRows, setBoardRows] = useState(21)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const lastPublishRef = useRef<number>(0)

  const stateRef = useRef<any>({
    grid: [],
    player: { x: 1, y: 1 },
    exit: { x: 31, y: 19 },
    oxy: [],
    germs: [],
    oxygenCollected: 0,
    startTime: 0,
    started: false,
    gameOver: false,
    win: false,
    lam: { hint: '', path: [], breaks: 0, error: '', showPath: false, bfsSteps: 0 },
    effects: { speedBoostUntil: 0, slowGermsUntil: 0, freezeGermsUntil: 0 },
    highlight: new Map(),
    revealMap: false,
    fxPopups: [],
    hitFlash: 0,
    particles: [],
    fxSparkles: [],
    fxRings: [],
    fxBursts: [],
    wallBreakParts: [],
    cameraShake: 0,
    metrics: { totalSteps: 0, optimalSteps: 0, backtrackCount: 0, collisionCount: 0, actionLatencies: [], visitedTiles: new Set(), lastPosition: { x: 1, y: 1 }, lastActionTime: 0 }
  })

  const width = boardCols * tile
  const height = boardRows * tile

  // Scaling logic
  const [canvasScale, setCanvasScale] = useState(1)
  useEffect(() => {
    function computeScale() {
      if (typeof window === 'undefined') return
      const pad = isMobile ? 24 : 48
      const availW = window.innerWidth - pad
      const headerH = isMobile ? 400 : 350
      const availH = window.innerHeight - headerH
      const s = Math.min(1, availW / width, availH / height)
      setCanvasScale(s <= 0 ? 1 : s)
    }
    computeScale(); window.addEventListener('resize', computeScale)
    return () => window.removeEventListener('resize', computeScale)
  }, [width, height, isMobile])

  // --- RE-INSERTED CORE LOGIC ---
  const texturesRef = useRef<any>({})
  function makeTileTexture(b1: string, b2: string, v: string) {
    const c = document.createElement('canvas'); c.width = tile; c.height = tile; const g = c.getContext('2d')!;
    const rg = g.createRadialGradient(tile * .3, tile * .3, tile * .2, tile * .7, tile * .7, tile * .95); rg.addColorStop(0, b1); rg.addColorStop(1, b2);
    g.fillStyle = rg; g.fillRect(0, 0, tile, tile); g.strokeStyle = v; g.globalAlpha = .18; g.lineWidth = 1;
    for (let i = 0; i < 3; i++) { g.beginPath(); const yy = (i + 1) * tile / 4; g.moveTo(0, yy); for (let x = 0; x <= tile; x += 4) g.lineTo(x, yy + Math.sin(x / 6) * 1.2); g.stroke() }
    return c
  }
  useEffect(() => {
    texturesRef.current.wall = makeTileTexture('#3b0f15', '#2b0f15', 'rgba(255,255,255,0.05)')
    texturesRef.current.floor = makeTileTexture('#5a1f1f', '#4a1f1f', 'rgba(255,255,255,0.06)')
    texturesRef.current.floorAlt = makeTileTexture('#642121', '#521a1a', 'rgba(255,255,255,0.06)')
  }, [])

  const THEME = { wall: '#2b0f15', floor: '#4a1f1f', floorAlt: '#5a1f1f', bgInner: '#3b0b12', bgOuter: '#14060a', glow: 'rgba(220,38,38,0.35)', oxyGlow: '#4ef0ff', germ: '#22c55e', germDark: '#15803d', playerRed: '#ef4444', playerBright: '#f87171' }
  const dist = (a: any, b: any) => Math.hypot(a.x - b.x, a.y - b.y)

  const doStartGame = useCallback((targetCols?: number, targetRows?: number) => {
    setScoreSubmitted(false); setGameOverTrigger(0);
    const cols = targetCols || boardCols; const rows = targetRows || boardRows;
    if (targetCols) setBoardCols(targetCols); if (targetRows) setBoardRows(targetRows);
    const grid = generateMaze(cols, rows); grid[1][1] = 0; grid[1][2] = 0; grid[2][1] = 0;
    const start = { x: 1, y: 1 }, exit = { x: cols - 2, y: rows - 2 }; grid[exit.y][exit.x] = 0;
    const oxy: Vec2[] = []; const floors: Vec2[] = []; for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) if (grid[y][x] === 0) floors.push({ x, y });
    const avail = floors.filter(p => !(p.x === start.x && p.y === start.y) && !(p.x === exit.x && p.y === exit.y));
    for (let i = 0; i < Math.max(10, avail.length * .1); i++) { const idx = randInt(avail.length); oxy.push(avail[idx]); avail.splice(idx, 1) }
    stateRef.current = { ...stateRef.current, grid, player: start, exit, oxy, germs: [], oxygenCollected: 0, started: true, gameOver: false, startTime: performance.now(), particles: Array.from({ length: 80 }, () => ({ x: Math.random() * width, y: Math.random() * height, r: 6 + Math.random() * 18, spd: .3 + Math.random() * .8, alpha: .06 + Math.random() * .12 })) }
    setConnected(true)
  }, [boardCols, boardRows, width, height])

  const startGame = () => setShowTemplatePicker(true)

  const publishState = useCallback(async (force = false) => {
    if (paused || !stateRef.current.started || stateRef.current.gameOver) return
    if (!force && Date.now() - lastPublishRef.current < mqttSendRate) return
    if (selectedMode !== 'lam') return

    lastPublishRef.current = Date.now()
    const s = stateRef.current
    const pubSeq = ++publishSeqRef.current

    const surroundings = {
      north: s.player.y > 0 ? s.grid[s.player.y - 1][s.player.x] : 1,
      south: s.player.y < boardRows - 1 ? s.grid[s.player.y + 1][s.player.x] : 1,
      east: s.player.x < boardCols - 1 ? s.grid[s.player.y][s.player.x + 1] : 1,
      west: s.player.x > 0 ? s.grid[s.player.y][s.player.x - 1] : 1
    }

    const prompt = `
      # MAZE ARENA STATE
      Position: (${s.player.x}, ${s.player.y})
      Exit: (${s.exit.x}, ${s.exit.y})
      Oxygen Collected: ${s.oxygenCollected}
      Surroundings: ${JSON.stringify(surroundings)}
      
      Instructions:
      ${templates.find(t => t.id === templateId)?.content || "Find the exit efficiently."}
      
      Available Actions:
      - {"action": "move", "direction": "north" | "south" | "east" | "west"}
      - {"action": "wait"}
    `

    const flowEvent = {
      id: pubSeq,
      sentAt: Date.now(),
      actionsDeclared: [],
      actionsApplied: [],
      hintExcerpt: '',
      error: '',
      receivedAt: null as number | null,
      latencyMs: null as number | null
    }
    setLamFlow(prev => [...prev, flowEvent])

    try {
      const res = await llmAPI.chat({
        messages: [{ role: 'system', content: prompt }],
        model: activeModel?.name || "default",
        max_tokens: 100,
        temperature: 0.1
      })

      const now = Date.now()
      const latency = now - flowEvent.sentAt
      const content = res.data.response
      const jsonMatch = content.match(/\{[\s\S]*\}/)
      let parsed = {}
      if (jsonMatch) {
        try { parsed = JSON.parse(jsonMatch[0]) } catch (e) {}
      }

      setLamData(prev => ({
        ...prev,
        hint: content,
        raw: parsed,
        rawMessage: res.data,
        updatedAt: now
      }))

      setLamFlow(prev => prev.map(e => e.id === pubSeq ? {
        ...e,
        receivedAt: now,
        latencyMs: latency,
        hintExcerpt: content.slice(0, 60) + '...',
        actionsDeclared: (parsed as any).action ? [(parsed as any).action] : []
      } : e))

      if ((parsed as any).action === 'move') {
        const d = (parsed as any).direction?.toLowerCase()
        let nx = s.player.x, ny = s.player.y
        if (d === 'north') ny--; else if (d === 'south') ny++; else if (d === 'east') nx++; else if (d === 'west') nx--;
        
        if (nx >= 0 && nx < boardCols && ny >= 0 && ny < boardRows && s.grid[ny][nx] === 0) {
          s.player = { x: nx, y: ny }
          setLamFlow(prev => prev.map(e => e.id === pubSeq ? {
            ...e,
            actionsApplied: [{ action: `move ${d}`, at: Date.now() }]
          } : e))
        }
      }
    } catch (err: any) {
      setLamFlow(prev => prev.map(e => e.id === pubSeq ? { ...e, error: err.message } : e))
    }
  }, [paused, boardCols, boardRows, mqttSendRate, selectedMode, templateId, templates, activeModel])

  useEffect(() => {
    if (selectedMode === 'lam' && !paused && stateRef.current.started) {
      const itv = setInterval(() => publishState(), 1000)
      return () => clearInterval(itv)
    }
  }, [selectedMode, paused, publishState])

  const publishSelectedTemplate = async (id: number) => {
    setTemplateId(id)
  }

  // Simplified draw for the sake of completeness in a buildable file
  useEffect(() => {
    let raf: number;
    const loop = () => {
      const canvas = canvasRef.current; if (!canvas) return; const ctx = canvas.getContext('2d'); if (!ctx) return;
      const s = stateRef.current; ctx.clearRect(0, 0, width, height);
      ctx.fillStyle = THEME.bgOuter; ctx.fillRect(0, 0, width, height);
      if (s.grid.length) {
        for (let y = 0; y < boardRows; y++) for (let x = 0; x < boardCols; x++) {
          ctx.fillStyle = s.grid[y][x] === 1 ? THEME.wall : (x + y) % 2 === 0 ? THEME.floor : THEME.floorAlt;
          ctx.fillRect(x * tile, y * tile, tile, tile)
        }
      }
      if (s.started) {
        ctx.fillStyle = THEME.playerRed; ctx.beginPath(); ctx.arc(s.player.x * tile + tile / 2, s.player.y * tile + tile / 2, tile * .4, 0, Math.PI * 2); ctx.fill();
        ctx.fillStyle = THEME.oxyGlow; ctx.beginPath(); ctx.arc(s.exit.x * tile + tile / 2, s.exit.y * tile + tile / 2, tile * .3, 0, Math.PI * 2); ctx.fill();
      }
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [width, height, boardCols, boardRows])

  return (
    <div style={{ minHeight: '100vh', background: 'transparent', color: '#f8fafc', WebkitUserSelect: 'none', userSelect: 'none', paddingBottom: isMobile ? 100 : 40 }}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: isMobile ? '16px' : '24px' }}>
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} style={headerWrapperStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ padding: '10px', borderRadius: '14px', background: `${activeTheme.primary}15`, border: `1px solid ${activeTheme.primary}30` }}>
              <Gamepad2 size={24} style={{ color: activeTheme.primary }} />
            </div>
            <h1 style={{ fontSize: isMobile ? '1.5rem' : '2rem', fontWeight: 800, margin: 0, letterSpacing: '-0.025em' }}>Maze Arena</h1>
          </div>
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            {activeModel && (
              <div
                title={activeModel.is_active ? "Model is active and responding" : "Model is currently offline"}
                style={{
                  ...badgeStyle,
                  borderColor: activeModel.is_active ? 'rgba(78, 205, 196, 0.4)' : 'rgba(255, 107, 107, 0.4)',
                  background: activeModel.is_active ? 'rgba(78, 205, 196, 0.1)' : 'rgba(255, 107, 107, 0.1)',
                  color: activeModel.is_active ? '#4ecdc4' : '#ff6b6b',
                }}
              >
                <Bot size={14} />
                <span style={{ fontWeight: 600 }}>{activeModel.name}</span>
                <div style={{
                  width: '6px',
                  height: '6px',
                  borderRadius: '50%',
                  background: activeModel.is_active ? '#4ecdc4' : '#ff6b6b',
                  boxShadow: activeModel.is_active ? '0 0 5px #4ecdc4' : '0 0 5px #ff6b6b'
                }}></div>
              </div>
            )}
            <div style={badgeStyle}>
              {user ? <><Check size={14} className="text-green-400" /> <span>{user.email.split('@')[0]}</span></> : <><AlertTriangle size={14} className="text-amber-400" /> <span>Guest</span></>}
            </div>
          </div>
        </motion.div>

        <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} style={controlPanelStyle}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 16, alignItems: 'end' }}>
            <div style={inputGroupStyle}>
              <label style={labelStyle}><Bot size={14} /> Model</label>
              <select 
                value={activeModel?.name ?? ''} 
                onChange={async (e) => {
                  const name = e.target.value;
                  setActiveModel(prev => prev ? { ...prev, name } : { name, is_active: true });
                  try {
                    await modelsAPI.selectModel(name);
                    checkLLMStatus();
                  } catch (err) {
                    console.error('Failed to switch model:', err);
                  }
                }} 
                style={selectStyle}
              >
                {availableModels.map(m => <option key={m.name} value={m.name} style={{ background: '#1e293b' }}>{m.name}</option>)}
              </select>
            </div>
            <div style={inputGroupStyle}>
              <label style={labelStyle}><FileCode size={14} /> Template</label>
              <select value={templateId ?? ''} onChange={(e) => setTemplateId(parseInt(e.target.value))} style={selectStyle}>
                <option value="" disabled>Select instruction set...</option>
                {templates.map(t => <option key={t.id} value={t.id} style={{ background: '#1e293b' }}>{t.title}</option>)}
              </select>
            </div>
            <div style={inputGroupStyle}>
              <label style={labelStyle}><Zap size={14} /> Session Token</label>
              <input value={sessionId} onChange={(e) => setSessionId(e.target.value)} style={inputStyle} />
            </div>
            <div style={inputGroupStyle}>
              <label style={labelStyle}><Target size={14} /> Hazard Density</label>
              <input type="number" value={germCount} onChange={(e) => setGermCount(parseInt(e.target.value))} style={inputStyle} />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px', marginTop: '24px', flexWrap: 'wrap', alignItems: 'center' }}>
            <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={startGame} style={{ ...primaryButtonStyle, background: activeTheme.primary }}>
              <Play size={18} /> Start Simulation
            </motion.button>
            <motion.button whileHover={{ background: 'rgba(255,255,255,0.05)' }} onClick={() => navigate('/leaderboard')} style={secondaryButtonStyle}>
              <Trophy size={16} /> Rankings
            </motion.button>
          </div>
        </motion.div>

        <div style={{ position: 'relative', margin: '0 auto', borderRadius: '24px', overflow: 'hidden', boxShadow: `0 30px 60px -12px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05)`, width: width * canvasScale, height: height * canvasScale }}>
          <canvas ref={canvasRef} width={width} height={height} style={{ width: width * canvasScale, height: height * canvasScale, display: 'block', background: '#0b0507' }} />
          <AnimatePresence>
            {!stateRef.current.started && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} style={canvasOverlayStyle}>
                <h2 style={{ fontSize: '1.5rem', fontWeight: 700 }}>Initialize Arena</h2>
                <motion.button whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }} onClick={startGame} style={{ ...primaryButtonStyle, background: activeTheme.primary }}>Initialize System</motion.button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      <AnimatePresence>
        {showTemplatePicker && (
          <div style={modalOverlayStyle} onClick={() => setShowTemplatePicker(false)}>
            <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.9 }} style={modalContentStyle} onClick={e => e.stopPropagation()}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                <h3 style={{ margin: 0, fontWeight: 800 }}>Start Arena Session</h3>
                <button onClick={() => setShowTemplatePicker(false)} style={iconButtonStyle}><X size={20} /></button>
              </div>
              <div style={{ display: 'grid', gap: 16 }}>
                <div onClick={() => setSelectedMode('manual')} style={{ ...modeCardStyle, borderColor: selectedMode === 'manual' ? activeTheme.primary : 'transparent', background: 'rgba(255,255,255,0.03)' }}>
                  <UserIcon size={20} /> <strong>Manual Control</strong>
                </div>
                <div onClick={() => setSelectedMode('lam')} style={{ ...modeCardStyle, borderColor: selectedMode === 'lam' ? activeTheme.primary : 'transparent', background: 'rgba(255,255,255,0.03)' }}>
                  <Bot size={20} /> <strong>Autonomous Mode</strong>
                </div>
                <button onClick={() => { doStartGame(boardCols, boardRows); setShowTemplatePicker(false); }} style={{ ...primaryButtonStyle, background: activeTheme.primary, width: '100%', justifyContent: 'center' }}>Launch Simulation</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  )
}

const headerWrapperStyle: CSSProperties = { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '16px' }
const badgeStyle: CSSProperties = { display: 'flex', alignItems: 'center', gap: '8px', padding: '8px 12px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '12px', fontSize: '0.85rem' }
const controlPanelStyle: CSSProperties = { background: 'rgba(30, 41, 59, 0.4)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '24px', padding: '24px', marginBottom: '24px' }
const inputGroupStyle: CSSProperties = { display: 'flex', flexDirection: 'column', gap: '8px' }
const labelStyle: CSSProperties = { fontSize: '0.7rem', fontWeight: 800, color: 'rgba(148, 163, 184, 0.8)', textTransform: 'uppercase', letterSpacing: '0.05em', display: 'flex', alignItems: 'center', gap: '6px' }
const inputStyle: CSSProperties = { padding: '10px 14px', borderRadius: '12px', background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(255, 255, 255, 0.1)', color: '#f8fafc', fontSize: '0.9rem', outline: 'none' }
const selectStyle: CSSProperties = { ...inputStyle, cursor: 'pointer', appearance: 'none' }
const primaryButtonStyle: CSSProperties = { padding: '12px 24px', borderRadius: '14px', border: 'none', color: '#fff', fontWeight: 700, fontSize: '0.95rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '10px' }
const secondaryButtonStyle: CSSProperties = { padding: '10px 16px', borderRadius: '12px', border: '1px solid rgba(255, 255, 255, 0.1)', background: 'rgba(255, 255, 255, 0.03)', color: '#cbd5e1', fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px' }
const iconButtonStyle: CSSProperties = { background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', padding: '8px' }
const canvasOverlayStyle: CSSProperties = { position: 'absolute', inset: 0, background: 'rgba(15, 23, 42, 0.6)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: '20px' }
const modalOverlayStyle: CSSProperties = { position: 'fixed', inset: 0, background: 'rgba(0, 0, 0, 0.7)', backdropFilter: 'blur(8px)', zIndex: 2000, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px' }
const modalContentStyle: CSSProperties = { background: '#0f172a', border: '1px solid rgba(255, 255, 255, 0.1)', borderRadius: '28px', padding: '32px', width: '100%', maxWidth: '480px' }
const modeCardStyle: CSSProperties = { padding: '16px', borderRadius: '16px', border: '2px solid transparent', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '12px' }

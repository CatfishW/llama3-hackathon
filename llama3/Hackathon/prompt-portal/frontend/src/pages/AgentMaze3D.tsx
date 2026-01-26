import React, { useEffect, useRef, useState, useMemo, CSSProperties, useCallback } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Play,
  Square,
  Settings,
  Trophy,
  ChevronRight,
  Brain,
  Zap,
  Terminal,
  Cpu,
  RefreshCw,
  Eye,
  Maximize2,
  Code2,
  Check,
  AlertTriangle,
  AlertCircle,
  Clock,
  Navigation,
  Sparkles,
  ToggleLeft,
  ToggleRight,
  MousePointer2,
  Video,
  Cylinder,
  Coins,
  Bot,
  X,
  FileText
} from 'lucide-react'
import axios from 'axios'
import { chatbotAPI, modelsAPI, llmAPI, leaderboardAPI } from '../api'
import { getSkills, AgentSkill, ATOMIC_SKILLS, AtomicSkill, getAtomicSkill } from '../utils/skillStorage'
import { useTemplates } from '../contexts/TemplateContext'
import { useAuth } from '../auth/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useRawLogs } from '../contexts/RawLogContext'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useTutorial } from '../contexts/TutorialContext'

// --- Types & Constants ---
type Vec2 = { x: number; y: number }
type MazeCell = 0 | 1 // 0: path, 1: wall
type AgentState = 'idle' | 'thinking' | 'moving' | 'success' | 'failed'



const TILE_SIZE = 2
const MAZE_SIZE = 9 // Must be odd

// --- Logic Helpers ---
const AGENT_EXAMPLE_TEMPLATE = `
# IDENTITY: ADVANCED NEURAL NAVIGATOR [MARK III]
Focus: Autonomous Maze Processing, Resource Extraction, and Strategic Exfiltration.

# CORE MISSION:
1. MAP THE MAZE: The environment starts UNKNOWN [?]. Manual movement is SLOW. Use SKILLS to map 10x faster.
2. EXTRACT: Collect all OXYGEN [O] canisters to sustain neural integrity and score.
3. EXFILTRATE: Reach the EXIT PORTAL [E] located at the primary nexus.

# STRATEGIC GUIDELINES:
- INITIAL DEPLOYMENT: Highly recommended to use "Structure Scan" (scan) immediately to reveal the entire AO.
- LOCAL NAVIGATION: Use "Neural Pulse" (ping) if blocked or when OXYGEN is nearby but the path is obscured.
- ENERGY CONSERVATION: Each step regenerates +2 Energy. Kinetic Overclock (sprint) is fast but consumes 20.

# COGNITIVE PROCESS [REQUIRED]:
1. ANALYZE INPUT: Check current (X, Y) relative to the EXIT Nexis and OXYGEN signatures.
2. REASON: Use <think> tags to determine the shortest path, risk of unknown walls, and benefit of skill activation.
3. EXECUTE: Output exactly ONE action in the strict JSON format provided.

# COMMUNICATION PROTOCOL:
Respond exclusively with valid JSON objects following these schemas:
- MOVEMENT: {"action": "move", "direction": "north" | "south" | "east" | "west"}
- SPECIAL SKILL: {"action": "use_skill", "skill": "ping" | "sprint" | "scan", "direction": "north" | "south" | "east" | "west" [direction only for sprint]}

# DATA INPUT STRUCTURE: [TELEMETRY], [MINIMAP], [ENERGY SYSTEMS], [AVAILABLE SKILLS]
`

const AGENCT_EXAMPLE_TEMPLATE = `...` // Keeping this variable if it exists, or just removing the lines I'm touching if they are purely INITIAL_SKILLS

// Removed INITIAL_SKILLS constant
const MAZE_DIRECTIONS = ['north', 'south', 'east', 'west'] as const
// MAZE_SKILLS removed or relaxed
const CORE_SKILLS = ['ping', 'sprint', 'scan']

const generateMaze = (size: number): MazeCell[][] => {
  const grid: MazeCell[][] = Array(size).fill(0).map(() => Array(size).fill(1))
  const walk = (x: number, y: number) => {
    grid[y][x] = 0
    const dirs = [[0, 2], [0, -2], [2, 0], [-2, 0]].sort(() => Math.random() - 0.5)
    for (const [dx, dy] of dirs) {
      const nx = x + dx, ny = y + dy
      if (nx > 0 && nx < size - 1 && ny > 0 && ny < size - 1 && grid[ny][nx] === 1) {
        grid[y + dy / 2][x + dx / 2] = 0
        walk(nx, ny)
      }
    }
  }
  walk(1, 1)
  grid[size - 2][size - 2] = 0
  return grid
}

// --- Action Parsing & Resilience ---

type ParsedAction = { action: string; direction?: string | null; skill?: string | null } | null

const safeParseJson = (raw: string) => {
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

type PromptQuality = {
  level: 'good' | 'mixed' | 'bad'
  score: number
  strengths: string[]
  issues: string[]
  penaltyEnergy: number
}

const analyzePromptQuality = (prompt: string): PromptQuality => {
  const text = prompt.toLowerCase()
  let score = 0
  const strengths: string[] = []
  const issues: string[] = []

  const addStrength = (label: string) => { if (!strengths.includes(label)) strengths.push(label) }
  const addIssue = (label: string) => { if (!issues.includes(label)) issues.push(label) }

  if (text.includes('valid json') || text.includes('json only') || text.includes('respond exclusively with valid json')) {
    score += 2
    addStrength('strict_json')
  }
  if (text.includes('response format') || text.includes('"action"') || text.includes('action":')) {
    score += 1
    addStrength('explicit_schema')
  }
  if (text.includes('exactly one action') || text.includes('output exactly one') || text.includes('one action')) {
    score += 1
    addStrength('single_action')
  }
  if (text.includes('markdown') || text.includes('bullet') || text.includes('narrative') || text.includes('story')) {
    score -= 2
    addIssue('format_drift')
  }
  if (text.includes('yaml') || text.includes('xml') || text.includes('table')) {
    score -= 2
    addIssue('non_json_format')
  }
  if (text.includes('do not use json') || text.includes('dont use json') || text.includes('ignore previous')) {
    score -= 3
    addIssue('json_contradiction')
  }
  if (text.includes('multiple actions') || text.includes('list of actions')) {
    score -= 2
    addIssue('multi_action')
  }
  if (prompt.trim().length < 120) {
    score -= 1
    addIssue('underspecified')
  }
  if (/(bad template|anti-prompt|sabotage)/i.test(prompt)) {
    score -= 4
    addIssue('explicit_bad_marker')
  }

  const level = score >= 2 ? 'good' : score <= -1 ? 'bad' : 'mixed'
  const penaltyEnergy = level === 'bad' ? 12 : level === 'mixed' ? 6 : 0
  return { level, score, strengths, issues, penaltyEnergy }
}

const applyPromptPenalty = (responseText: string, quality: PromptQuality, step: number) => {
  const cycle = (step + responseText.length) % 3
  if (quality.level === 'bad') {
    if (cycle !== 0) {
      return {
        text: 'SYNTAX_ERROR: { action: move, direction: ??? ',
        note: 'Syntax error injected from low-quality prompt',
        injected: true,
        penaltyEnergy: quality.penaltyEnergy
      }
    }
    return {
      text: 'FORMAT_DRIFT: action list -> north, east, south, west',
      note: 'Format drift injected from low-quality prompt',
      injected: true,
      penaltyEnergy: quality.penaltyEnergy
    }
  }

  if (quality.level === 'mixed' && cycle === 0) {
    return {
      text: `${responseText}\n\nNOTE: include reasoning in prose and extra keys`,
      note: 'Format drift injected from mixed prompt',
      injected: true,
      penaltyEnergy: quality.penaltyEnergy
    }
  }

  return { text: responseText, note: null, injected: false, penaltyEnergy: 0 }
}

const fuzzyParseJson = (text: string) => {
  const direct = safeParseJson(text)
  if (direct) return direct

  try {
    // Try to fix common issues: unquoted keys, single quotes
    let fixed = text.trim()
    // Replace single quotes with double quotes
    fixed = fixed.replace(/'/g, '"')
    // Fix unquoted keys (e.g. {action: "move"} -> {"action": "move"})
    fixed = fixed.replace(/([{,]\s*)([a-zA-Z0-9_]+)(\s*:)/g, '$1"$2"$3')

    return JSON.parse(fixed)
  } catch {
    return null
  }
}

const extractJsonObjects = (text: string) => {
  const results: string[] = []
  let depth = 0
  let start = -1
  let inString = false
  let escape = false
  for (let i = 0; i < text.length; i++) {
    const ch = text[i]
    if (inString) {
      if (escape) {
        escape = false
      } else if (ch === '\\') {
        escape = true
      } else if (ch === '"') {
        inString = false
      }
      continue
    }
    if (ch === '"') {
      inString = true
      continue
    }
    if (ch === '{') {
      if (depth === 0) start = i
      depth += 1
    } else if (ch === '}' && depth > 0) {
      depth -= 1
      if (depth === 0 && start >= 0) {
        results.push(text.slice(start, i + 1))
        start = -1
      }
    }
  }
  return results
}

const normalizeDirection = (value: any) => {
  if (!value) return null
  const str = String(value).trim().toLowerCase()
  // Direct match
  if (MAZE_DIRECTIONS.includes(str as any)) return str
  // Regex match (e.g. "move north", "to the north")
  const match = str.match(/\b(north|south|east|west)\b/i)
  return match ? match[1].toLowerCase() : null
}

const normalizeSkill = (value: any) => {
  if (!value) return null
  const skill = String(value).trim().toLowerCase()
  return skill // Allow any skill ID, validate in runtime
}

const normalizeActionObject = (action: any): ParsedAction => {
  if (!action || typeof action !== 'object') return null

  // Try to find action type from common keys
  const actionType = (action.action || action.type || action.command || action.cmd || '').toString().toLowerCase()

  // Heuristic: if object looks like {"move": "north"}
  if (!actionType) {
    for (const dir of MAZE_DIRECTIONS) {
      if (action.move === dir || action.go === dir || action.direction === dir) return { action: 'move', direction: dir }
    }
    if (action.move && normalizeDirection(action.move)) return { action: 'move', direction: normalizeDirection(action.move) }
    if (action.skill) return { action: 'use_skill', skill: normalizeSkill(action.skill) }
  }

  // Handle "move north" in action field
  if (actionType.startsWith('move')) {
    const parts = actionType.split(/[\s_-]+/)
    const dirFromAction = parts.length > 1 ? normalizeDirection(parts[1]) : null
    const direction = dirFromAction || normalizeDirection(action.direction || action.dir || action.heading || action.to)
    return direction ? { action: 'move', direction } : null
  }

  if (actionType === 'use_skill' || actionType === 'skill' || actionType === 'use') {
    const skill = normalizeSkill(action.skill || action.id || action.name || action.skill_id || action.tool)
    if (!skill) return null
    const direction = normalizeDirection(action.direction || action.dir || action.heading)
    return direction ? { action: 'use_skill', skill, direction } : { action: 'use_skill', skill }
  }

  // Final fallback: check for top-level keys that match directions
  for (const dir of MAZE_DIRECTIONS) {
    if (action[dir] === true || action[dir] === 'true' || action.direction === dir) return { action: 'move', direction: dir }
  }

  return null
}

const actionFromFunctionCall = (call: any): ParsedAction => {
  if (!call || typeof call !== 'object') return null
  const name = (call.name || call.function?.name || call.tool?.name || '').toString().toLowerCase()
  const rawArgs = call.arguments ?? call.function?.arguments ?? call.args ?? call.input
  const args = typeof rawArgs === 'string' ? (safeParseJson(rawArgs) || {}) : (rawArgs || {})
  if (args && typeof args === 'object' && args.action) {
    return normalizeActionObject(args)
  }
  if (name === 'move' || name === 'step' || name === 'navigate') {
    const direction = normalizeDirection(args.direction || args.dir || args.heading)
    return direction ? { action: 'move', direction } : null
  }
  if (name === 'use_skill' || name === 'skill') {
    const skill = normalizeSkill(args.skill || args.id || args.name)
    if (!skill) return null
    const direction = normalizeDirection(args.direction || args.dir)
    return direction ? { action: 'use_skill', skill, direction } : { action: 'use_skill', skill }
  }
  if (CORE_SKILLS.includes(name)) {
    return { action: 'use_skill', skill: name }
  }
  return null
}

const parseAgentAction = (raw: string): ParsedAction => {
  if (!raw) return null
  const trimmed = raw.trim()
  const direct = fuzzyParseJson(trimmed)
  if (direct) {
    if (Array.isArray(direct)) {
      for (const item of direct) {
        const action = normalizeActionObject(item) || actionFromFunctionCall(item)
        if (action) return action
      }
    }
    const action = normalizeActionObject(direct)
    if (action) return action
    if (direct.response) {
      const nested = parseAgentAction(String(direct.response))
      if (nested) return nested
    }
    const calls = direct.function_calls || direct.tool_calls
    if (Array.isArray(calls)) {
      for (const call of calls) {
        const action = actionFromFunctionCall(call)
        if (action) return action
      }
    }
    if (direct.function_call || direct.tool_call) {
      const action = actionFromFunctionCall(direct.function_call || direct.tool_call)
      if (action) return action
    }
  }

  const codeBlockMatch = trimmed.match(/```(?:json)?\s*([\s\S]*?)```/i)
  if (codeBlockMatch) {
    const action = parseAgentAction(codeBlockMatch[1])
    if (action) return action
  }

  const jsonCandidates = extractJsonObjects(trimmed)
  for (let i = jsonCandidates.length - 1; i >= 0; i -= 1) {
    const candidate = fuzzyParseJson(jsonCandidates[i])
    if (!candidate) continue
    if (Array.isArray(candidate)) {
      for (const item of candidate) {
        const action = normalizeActionObject(item) || actionFromFunctionCall(item)
        if (action) return action
      }
      continue
    }
    const action = normalizeActionObject(candidate)
    if (action) return action
    const calls = candidate.function_calls || candidate.tool_calls
    if (Array.isArray(calls)) {
      for (const call of calls) {
        const parsed = actionFromFunctionCall(call)
        if (parsed) return parsed
      }
    }
  }

  const moveMatch = trimmed.match(/\b(?:move|go|walking|step|head|heading|to)\b[^a-z]*(north|south|east|west)\b/i)
  if (moveMatch) {
    return { action: 'move', direction: moveMatch[1].toLowerCase() }
  }
  const skillMatch = trimmed.match(/\b(?:use[_\s-]?skill|skill|activate|trigger|cast)\b[^a-z]*(ping|scan|sprint|echo_pulse|phase_dash|structure_scan)\b/i)
  if (skillMatch) {
    return { action: 'use_skill', skill: skillMatch[1].toLowerCase() }
  }
  return null
}

// --- Component ---
export default function AgentMaze3D() {
  const { templates } = useTemplates()
  const { user } = useAuth()
  const { theme } = useTheme()
  const { addLog } = useRawLogs()
  const { runTutorial } = useTutorial()

  const themeColors = useMemo(() => {
    const map: any = {
      slate: { primary: 0x6366f1, secondary: 0x818cf8, emissive: 0x4f46e5, light: 0x818cf8 },
      emerald: { primary: 0x10b981, secondary: 0x34d399, emissive: 0x059669, light: 0x34d399 },
      rose: { primary: 0xf43f5e, secondary: 0xfb7185, emissive: 0xe11d48, light: 0xfb7185 },
      amber: { primary: 0xf59e0b, secondary: 0xfbbf24, emissive: 0xd97706, light: 0xfbbf24 },
      violet: { primary: 0x8b5cf6, secondary: 0xa78bfa, emissive: 0x7c3aed, light: 0xa78bfa },
      cyan: { primary: 0x06b6d4, secondary: 0x22d3ee, emissive: 0x0891b2, light: 0x22d3ee },
      orange: { primary: 0xf97316, secondary: 0xfb923c, emissive: 0xea580c, light: 0xfb923c },
      fuchsia: { primary: 0xd946ef, secondary: 0xe879f9, emissive: 0xc026d3, light: 0xe879f9 },
      lime: { primary: 0x84cc16, secondary: 0xa3e635, emissive: 0x65a30d, light: 0xa3e635 },
      sky: { primary: 0x0ea5e9, secondary: 0x38bdf8, emissive: 0x0284c7, light: 0x38bdf8 }
    }
    return map[theme] || map.slate
  }, [theme])

  // Game State
  const [grid, setGrid] = useState<MazeCell[][]>([])
  const [agentPos, setAgentPos] = useState<Vec2>({ x: 1, y: 1 })
  const [exitPos, setExitPos] = useState<Vec2>({ x: MAZE_SIZE - 2, y: MAZE_SIZE - 2 })
  const [oxyPos, setOxyPos] = useState<Vec2[]>([])
  const [gameState, setGameState] = useState<AgentState>('idle')
  const [steps, setSteps] = useState(0)
  const [score, setScore] = useState(0)
  const [oxygen, setOxygen] = useState(0)
  const [time, setTime] = useState(0)
  const [startTime, setStartTime] = useState<number>(0)
  const [energy, setEnergy] = useState(150)
  const [agentSkills, setAgentSkills] = useState<AgentSkill[]>([])
  const [selectedAgentSkillId, setSelectedAgentSkillId] = useState<string | null>(null)
  const [useSkills, setUseSkills] = useState(true)
  const [toolUsage, setToolUsage] = useState<Record<string, number>>({})

  useEffect(() => {
    const loaded = getSkills(user?.id)
    setAgentSkills(loaded)
    if (loaded.length > 0 && !selectedAgentSkillId && useSkills) {
      setSelectedAgentSkillId(loaded[0].id)
    }
  }, [user])

  const activeSkill = useMemo(() => {
    if (!useSkills) return null
    return agentSkills.find(s => s.id === selectedAgentSkillId)
  }, [agentSkills, selectedAgentSkillId, useSkills])

  const activeTools = useMemo(() => {
    if (!activeSkill) return []
    return activeSkill.tools.map(tid => {
      const def = getAtomicSkill(tid)
      if (!def) return null
      return { ...def, lastUsed: toolUsage[tid] || 0 }
    }).filter(Boolean) as (AtomicSkill & { lastUsed: number })[]
  }, [activeSkill, toolUsage])
  const [revealed, setRevealed] = useState<Map<string, number>>(new Map())
  const [history, setHistory] = useState<string[]>([])
  const [positionHistory, setPositionHistory] = useState<Vec2[]>([]) // Strict position tracking for loop detection
  const [sessionId, setSessionId] = useState<string>(`maze_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
  const [isFirstMessage, setIsFirstMessage] = useState(true) // Track if first message in session
  const [lastPrompt, setLastPrompt] = useState('')
  const [lastAction, setLastAction] = useState<any>(null)
  const [lastThinking, setLastThinking] = useState<string | null>(null)
  const [lastExecutionResult, setLastExecutionResult] = useState<{ success: boolean; message: string } | null>(null)

  // UI State
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
  const [customPrompt, setCustomPrompt] = useState('')
  const [isMobile, setIsMobile] = useState(false)
  const [showExample, setShowExample] = useState(false)
  const [spectateMode, setSpectateMode] = useState(false)
  const [activeModel, setActiveModel] = useState<{ name: string, is_active: boolean } | null>(null)
  const [availableModels, setAvailableModels] = useState<any[]>([])
  const [checkingModel, setCheckingModel] = useState(false)
  const [isAutopilot, setIsAutopilot] = useState(false)
  const isAutopilotRef = useRef(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    isAutopilotRef.current = isAutopilot
    if (!isAutopilot && abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }, [isAutopilot])
  const [stepsThisTurn, setStepsThisTurn] = useState(0)
  const [sidebarWidth, setSidebarWidth] = useState(440)
  const [isResizing, setIsResizing] = useState(false)

  // Resizing Effect
  useEffect(() => {
    if (!isResizing) return
    const handleMouseMove = (e: MouseEvent) => {
      const newWidth = window.innerWidth - e.clientX
      if (newWidth > 320 && newWidth < 850) {
        setSidebarWidth(newWidth)
      }
    }
    const handleMouseUp = () => setIsResizing(false)
    window.addEventListener('mousemove', handleMouseMove)
    window.addEventListener('mouseup', handleMouseUp)
    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

  const activeTemplate = useMemo(() => {
    if (selectedTemplateId) return templates.find(t => t.id === selectedTemplateId)
    return null
  }, [selectedTemplateId, templates])

  const basePrompt = useMemo(() => activeTemplate?.content || customPrompt || "", [activeTemplate, customPrompt])
  const promptQuality = useMemo(() => basePrompt ? analyzePromptQuality(basePrompt) : null, [basePrompt])

  // Autopilot Loop Effect
  useEffect(() => {
    if (isAutopilot && gameState === 'idle') {
      const timer = setTimeout(() => {
        runAgentStep()
      }, 500)
      return () => clearTimeout(timer)
    }
  }, [isAutopilot, gameState])

  // Three.js Refs
  const mountRef = useRef<HTMLDivElement>(null)
  const agentPosRef = useRef<Vec2>(agentPos)
  const sceneRef = useRef<{
    scene: THREE.Scene,
    camera: THREE.PerspectiveCamera,
    renderer: THREE.WebGLRenderer,
    agent: THREE.Group,
    walls: THREE.Group,
    oxygen: THREE.Group,
    overlays: THREE.Group,
    pointLights: THREE.PointLight[],
    controls: OrbitControls,
    particles: THREE.Points,
    particlePositions: Float32Array,
    raycaster: THREE.Raycaster,
    mouse: THREE.Vector2,
    materials: Record<string, any>
  } | null>(null)

  useEffect(() => {
    checkLLMStatus()
    fetchAvailableModels()
    const timer = setInterval(checkLLMStatus, 30000)
    return () => clearInterval(timer)
  }, [])

  // Keep ref in sync with state for animation loop
  useEffect(() => {
    agentPosRef.current = agentPos
  }, [agentPos])

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

  // Initialize
  useEffect(() => {
    const newGrid = generateMaze(MAZE_SIZE)
    setGrid(newGrid)
    const floors: Vec2[] = []
    for (let y = 0; y < MAZE_SIZE; y++) for (let x = 0; x < MAZE_SIZE; x++) if (newGrid[y][x] === 0 && !(x === 1 && y === 1) && !(x === MAZE_SIZE - 2 && y === MAZE_SIZE - 2)) floors.push({ x, y })
    const oxy: Vec2[] = []
    for (let i = 0; i < 8; i++) if (floors.length) { const idx = Math.floor(Math.random() * floors.length); oxy.push(floors[idx]); floors.splice(idx, 1) }
    setOxyPos(oxy)
    setOxyPos(oxy)
    setAgentPos({ x: 1, y: 1 })
    setPositionHistory([{ x: 1, y: 1 }])
    setHistory(["1,1"])
    setSessionId(`session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`)
    setOxygen(0)
    setTime(0)
    setSteps(0)
    setScore(0)
    setStartTime(Date.now())
    setGameState('idle')
    // Initialize revealed cells around starting position
    const initialRevealed = new Map<string, number>()
    const now = Date.now()
    for (let dy = -2; dy <= 2; dy++) {
      for (let dx = -2; dx <= 2; dx++) {
        const nx = 1 + dx, ny = 1 + dy
        if (nx >= 0 && ny >= 0 && nx < MAZE_SIZE && ny < MAZE_SIZE) {
          initialRevealed.set(`${nx},${ny}`, now)
        }
      }
    }
    setRevealed(initialRevealed)

    // Trigger tutorial for Agent Maze 3D
    const hasSeenMazeTutorial = localStorage.getItem('tutorial_seen_maze')
    if (!hasSeenMazeTutorial) {
      setTimeout(() => {
        runTutorial([
          { target: '#maze-3d-mount', title: 'Neural Arena 3D', content: 'This is the 3D execution environment where your LAM agents navigate and act.', position: 'right' },
          { target: '#maze-hud-energy', title: 'Neural Energy', content: 'Energy is consumed by movement and skills. It regenerates slowly over time.', position: 'bottom' },
          { target: '#maze-hud-oxygen', title: 'Resource Monitoring', content: 'Track collected O2 canisters here. Resources boost your final mission score.', position: 'bottom' },
          { target: '#maze-hud-score', title: 'Performance Score', content: 'Calculated based on efficiency, speed, and resources collected.', position: 'bottom' },
          { target: '#maze-spectate-btn', title: 'View Mode', content: 'Switch between "Following" (locks to agent) and "Spectating" (free orbit camera).', position: 'bottom' },
          { target: '#maze-model-selector', title: 'LLM Engine', content: 'Select the model provider that powers the agent\'s reasoning process.', position: 'left' },
          { target: '#maze-skill-selector', title: 'Active Loadout', content: 'Choose which set of custom skills the agent has access to during this session.', position: 'left' },
          { target: '#maze-template-selector', title: 'Persona & Logic', content: 'Apply a prompt template to define high-level strategies and constraints.', position: 'left' },
          { target: '#maze-initiate-btn', title: 'Manual Step', content: 'Trigger a single reasoning cycle. Useful for debugging specific behaviors.', position: 'left' },
          { target: '#maze-autopilot-btn', title: 'Autopilot Mode', content: 'Let the agent run autonomously until it reaches the exit or exhausts energy.', position: 'left' },
          { target: '#maze-telemetry-data', title: 'Raw Telemetry', content: 'See exactly what data is being sent to the LLM in each cycle.', position: 'top' },
          { target: '#maze-thinking-panel', title: 'Cognitive Chain', content: 'Watch the agent\'s internal reasoning process (thinking blocks) in real-time.', position: 'top' },
          { target: '#maze-action-output', title: 'Command Result', content: 'The finalized JSON action output and the result of its execution in the environment.', position: 'top' },
        ]);
        localStorage.setItem('tutorial_seen_maze', 'true');
      }, 1500);
    }
  }, [])

  // Timer - cumulative session duration
  useEffect(() => {
    const itv = setInterval(() => {
      setGameState(current => {
        if (current !== 'success' && current !== 'failed') {
          setTime(t => t + 1)
        }
        return current
      })
    }, 1000)
    return () => clearInterval(itv)
  }, [])


  useEffect(() => {
    if (!mountRef.current) return
    const resizeObserver = new ResizeObserver(() => {
      if (!mountRef.current || !sceneRef.current) return
      const { camera, renderer } = sceneRef.current
      const width = mountRef.current.clientWidth
      const height = mountRef.current.clientHeight
      camera.aspect = width / height
      camera.updateProjectionMatrix()
      renderer.setSize(width, height)
    })
    resizeObserver.observe(mountRef.current)
    setIsMobile(window.innerWidth < 1000)

    const handleWinResize = () => setIsMobile(window.innerWidth < 1000)
    window.addEventListener('resize', handleWinResize)

    return () => {
      resizeObserver.disconnect()
      window.removeEventListener('resize', handleWinResize)
    }
  }, [])

  useEffect(() => {
    if (sceneRef.current?.controls) {
      sceneRef.current.controls.enabled = spectateMode
      if (spectateMode && sceneRef.current.agent) {
        // Snap target to agent when starting to spectate
        const { agent, controls } = sceneRef.current
        controls.target.set(agent.position.x, 0, agent.position.z)
        controls.update()
      }
    }
  }, [spectateMode])

  // --- Procedural Texture Generation ---
  const createOrganicTexture = useCallback((type: 'wall' | 'floor') => {
    const canvas = document.createElement('canvas')
    canvas.width = 512
    canvas.height = 512
    const ctx = canvas.getContext('2d')
    if (!ctx) return null

    // Base colors for "inside body"
    const colors = type === 'wall'
      ? { base: '#3b0b12', vein: '#6b111b', highlights: '#4a080f' }
      : { base: '#2b060a', vein: '#4a080f', highlights: '#1a0406' }

    ctx.fillStyle = colors.base
    ctx.fillRect(0, 0, 512, 512)

    // Add organic noise/blobs
    for (let i = 0; i < 40; i++) {
      ctx.fillStyle = i % 2 === 0 ? colors.vein : colors.highlights
      ctx.globalAlpha = 0.3
      const x = Math.random() * 512
      const y = Math.random() * 512
      const radius = 20 + Math.random() * 100
      ctx.beginPath()
      ctx.arc(x, y, radius, 0, Math.PI * 2)
      ctx.fill()
    }

    // Add "veins"
    ctx.strokeStyle = '#ff3344'
    ctx.lineWidth = 1
    ctx.globalAlpha = 0.2
    for (let i = 0; i < 15; i++) {
      ctx.beginPath()
      let x = Math.random() * 512
      let y = Math.random() * 512
      ctx.moveTo(x, y)
      for (let j = 0; j < 10; j++) {
        x += (Math.random() - 0.5) * 100
        y += (Math.random() - 0.5) * 100
        ctx.lineTo(x, y)
      }
      ctx.stroke()
    }

    const texture = new THREE.CanvasTexture(canvas)
    texture.wrapS = THREE.RepeatWrapping
    texture.wrapT = THREE.RepeatWrapping
    return texture
  }, [])

  // --- Three.js Scene Setup ---
  useEffect(() => {
    if (!mountRef.current) return

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x020617)
    scene.fog = new THREE.FogExp2(0x020617, 0.04)

    const camera = new THREE.PerspectiveCamera(70, mountRef.current.clientWidth / mountRef.current.clientHeight, 0.1, 1000)
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setSize(mountRef.current.clientWidth, mountRef.current.clientHeight)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.shadowMap.enabled = true
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    mountRef.current.appendChild(renderer.domElement)

    // Texture generation
    const wallTexture = createOrganicTexture('wall')
    const floorTexture = createOrganicTexture('floor')

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xff6666, 2) // Reddish ambient
    scene.add(ambientLight)

    const mainLight = new THREE.PointLight(themeColors.primary, 200, 80)
    mainLight.position.set(10, 30, 10)
    mainLight.castShadow = true
    scene.add(mainLight)

    // Floor
    const floorGeo = new THREE.PlaneGeometry(MAZE_SIZE * TILE_SIZE * 6, MAZE_SIZE * TILE_SIZE * 6)
    const floorMat = new THREE.MeshStandardMaterial({
      map: floorTexture,
      bumpMap: floorTexture,
      bumpScale: 0.2,
      color: 0xffaaaa, // Tint the floor
      roughness: 0.3,
      metalness: 0.1
    })
    const floor = new THREE.Mesh(floorGeo, floorMat)
    floor.rotation.x = -Math.PI / 2
    floor.receiveShadow = true
    scene.add(floor)

    const gridHelper = new THREE.GridHelper(MAZE_SIZE * TILE_SIZE * 6, 60, 0xff0000, 0x330000)
    gridHelper.position.y = -0.05
    gridHelper.material.transparent = true
    gridHelper.material.opacity = 0.3
    scene.add(gridHelper)

    // Wall Material
    const wallMat = new THREE.MeshStandardMaterial({
      map: wallTexture,
      bumpMap: wallTexture,
      bumpScale: 0.1,
      color: 0xffffff,
      roughness: 0.4,
      metalness: 0.1,
      emissive: 0x3b0b12,
      emissiveIntensity: 0.2
    })
    const wallGeo = new THREE.BoxGeometry(TILE_SIZE * 0.9, 3.5, TILE_SIZE * 0.9)

    // Oxygen Material & Geometry
    const textureLoader = new THREE.TextureLoader()
    const oxygenTexture = textureLoader.load('/oxygen_texture.png')
    oxygenTexture.wrapS = THREE.RepeatWrapping
    oxygenTexture.wrapT = THREE.RepeatWrapping

    const oxyMat = new THREE.MeshBasicMaterial({
      map: oxygenTexture,
      color: 0x00f2fe,
      transparent: true,
      opacity: 0.75,
      blending: THREE.AdditiveBlending,
      side: THREE.DoubleSide
    })
    const oxyGeo = new THREE.SphereGeometry(0.45, 32, 32)

    // Groups
    const walls = new THREE.Group(); scene.add(walls)
    const oxygen = new THREE.Group(); scene.add(oxygen)
    const overlays = new THREE.Group(); scene.add(overlays)
    const agent = new THREE.Group(); scene.add(agent)

    // Agent Model
    const core = new THREE.Mesh(new THREE.SphereGeometry(0.6, 32, 32), new THREE.MeshStandardMaterial({ color: 0xffffff, emissive: themeColors.primary, emissiveIntensity: 5 }))
    core.castShadow = true
    agent.add(core)
    const ring = new THREE.Mesh(new THREE.TorusGeometry(0.8, 0.05, 16, 100), new THREE.MeshBasicMaterial({ color: themeColors.primary }))
    ring.rotation.x = Math.PI / 2
    agent.add(ring)
    const agentLight = new THREE.PointLight(themeColors.primary, 50, 15)
    agentLight.position.y = 1
    agent.add(agentLight)

    // Particles
    const particleCount = 1500
    const particleGeo = new THREE.BufferGeometry()
    const particlePos = new Float32Array(particleCount * 3)
    for (let i = 0; i < particleCount * 3; i++) particlePos[i] = (Math.random() - 0.5) * 100
    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePos, 3))
    const particles = new THREE.Points(particleGeo, new THREE.PointsMaterial({ color: themeColors.primary, size: 0.1, transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending }))
    scene.add(particles)

    // Interaction
    const raycaster = new THREE.Raycaster()
    const mouse = new THREE.Vector2()
    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.rotateSpeed = 1.2
    controls.zoomSpeed = 1.5
    controls.screenSpacePanning = true
    controls.minDistance = 5
    controls.maxDistance = 60
    controls.maxPolarAngle = Math.PI / 2.1 // Prevent going under floor
    controls.enabled = false

    const handleMouseClick = (e: MouseEvent) => {
      if (!mountRef.current || !sceneRef.current) return
      const rect = mountRef.current.getBoundingClientRect()
      mouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1
      mouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1
      const { raycaster, scene, camera } = sceneRef.current
      raycaster.setFromCamera(mouse, camera)
      const intersects = raycaster.intersectObjects(scene.children, true)
      if (intersects.length) {
        const p = intersects[0].point
        const l = new THREE.PointLight(themeColors.secondary, 30, 8)
        l.position.copy(p); scene.add(l)
        setTimeout(() => scene.remove(l), 250)
      }
    }
    renderer.domElement.addEventListener('click', handleMouseClick)

    sceneRef.current = {
      scene, camera, renderer, agent, walls, oxygen, overlays,
      pointLights: [mainLight, agentLight], controls, particles,
      particlePositions: particlePos, raycaster, mouse,
      materials: { wall: wallMat, wallGeo: wallGeo as any, oxyMat, oxyGeo }
    }

    const animate = () => {
      requestAnimationFrame(animate)
      if (sceneRef.current) {
        const { renderer, scene, camera, agent, controls, particlePositions, particles } = sceneRef.current
        const currentPos = agentPosRef.current
        const tx = (currentPos.x - MAZE_SIZE / 2) * TILE_SIZE, tz = (currentPos.y - MAZE_SIZE / 2) * TILE_SIZE
        agent.position.x = THREE.MathUtils.lerp(agent.position.x, tx, 0.1)
        agent.position.z = THREE.MathUtils.lerp(agent.position.z, tz, 0.1)
        agent.position.y = 1.2 + Math.sin(Date.now() * 0.003) * 0.2
        ring.rotation.z += 0.05; ring.rotation.x += 0.02

        // Rotate oxygen balls
        oxygen.children.forEach(c => {
          if (c instanceof THREE.Mesh && c.geometry.type === 'SphereGeometry') {
            c.rotation.y += 0.01
            c.rotation.z += 0.005
            // Subtle scaling pulse
            const pulse = 1 + Math.sin(Date.now() * 0.002) * 0.05
            c.scale.set(pulse, pulse, pulse)
          }
        })

        // Particles follow agent
        for (let i = 0; i < particleCount; i++) {
          const idx = i * 3; particlePositions[idx + 1] -= 0.01
          if (particlePositions[idx + 1] < -5) {
            particlePositions[idx] = agent.position.x + (Math.random() - 0.5) * 4
            particlePositions[idx + 1] = agent.position.y + (Math.random() - 0.5) * 4
            particlePositions[idx + 2] = agent.position.z + (Math.random() - 0.5) * 4
          }
        }
        particles.geometry.attributes.position.needsUpdate = true

        controls.update()

        if (!spectateMode) {
          camera.position.x = THREE.MathUtils.lerp(camera.position.x, agent.position.x, 0.05)
          camera.position.z = THREE.MathUtils.lerp(camera.position.z, agent.position.z + 8, 0.05)
          camera.position.y = THREE.MathUtils.lerp(camera.position.y, 12, 0.05)
          camera.lookAt(agent.position.x, 0, agent.position.z)
        }
        renderer.render(scene, camera)
      }
    }
    animate()

    return () => {
      renderer.dispose()
      if (mountRef.current) mountRef.current.removeChild(renderer.domElement)
    }
  }, [themeColors]) // Reload scene when theme changes for lighting

  // Render Maze & Oxygen with Revealed State
  useEffect(() => {
    if (!sceneRef.current || grid.length === 0) return
    const { walls, oxygen, overlays, materials } = sceneRef.current
    walls.clear(); oxygen.clear(); overlays.clear()

    // Base materials
    const wallGeo = (materials.wallGeo as unknown as THREE.BoxGeometry) || new THREE.BoxGeometry(TILE_SIZE * 0.9, 3.5, TILE_SIZE * 0.9)
    const baseWallMat = materials.wall as THREE.MeshStandardMaterial

    // Revealed Wall Material (Brighter, styled)
    const revealedWallMat = new THREE.MeshStandardMaterial({
      color: themeColors.primary,
      roughness: 0.2,
      metalness: 0.5,
      emissive: themeColors.primary,
      emissiveIntensity: 0.3
    })

    // Revealed Floor Tiles (Holographic Overlay)
    const tileGeo = new THREE.PlaneGeometry(TILE_SIZE * 0.9, TILE_SIZE * 0.9)
    const tileMat = new THREE.MeshBasicMaterial({
      color: themeColors.primary,
      transparent: true,
      opacity: 0.15,
      side: THREE.DoubleSide
    })

    const now = Date.now()
    const FADE_DURATION = 30000 // 30 seconds fade

    for (let y = 0; y < MAZE_SIZE; y++) {
      for (let x = 0; x < MAZE_SIZE; x++) {
        const key = `${x},${y}`
        const revealTime = revealed.get(key)
        const isRevealed = revealTime !== undefined && (now - revealTime) < FADE_DURATION

        if (grid[y][x] === 1) {
          // Wall
          const w = new THREE.Mesh(wallGeo, isRevealed ? revealedWallMat : baseWallMat)
          w.position.set((x - MAZE_SIZE / 2) * TILE_SIZE, 1.75, (y - MAZE_SIZE / 2) * TILE_SIZE)
          w.castShadow = true;
          w.receiveShadow = true;
          walls.add(w)
        } else {
          // Path - if revealed, add highlight with fade
          if (isRevealed && revealTime) {
            const age = now - revealTime
            const opacity = Math.max(0.05, 0.25 * (1 - age / FADE_DURATION))
            const fadeTileMat = new THREE.MeshBasicMaterial({
              color: themeColors.primary,
              transparent: true,
              opacity,
              side: THREE.DoubleSide
            })
            const t = new THREE.Mesh(tileGeo, fadeTileMat)
            t.rotation.x = -Math.PI / 2
            t.position.set((x - MAZE_SIZE / 2) * TILE_SIZE, 0.05, (y - MAZE_SIZE / 2) * TILE_SIZE)
            overlays.add(t)
          }
        }
      }
    }

    const baseOxyMat = materials.oxyMat as THREE.MeshStandardMaterial
    const baseOxyGeo = materials.oxyGeo as THREE.SphereGeometry

    oxyPos.forEach(p => {
      const o = new THREE.Mesh(baseOxyGeo, baseOxyMat)
      o.position.set((p.x - MAZE_SIZE / 2) * TILE_SIZE, 1.2, (p.y - MAZE_SIZE / 2) * TILE_SIZE)
      o.userData = { id: `${p.x},${p.y}` };
      oxygen.add(o)

      // If revealed, add a beacon
      if (revealed.has(`${p.x},${p.y}`)) {
        const beacon = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.2, 12, 16, 1, true), new THREE.MeshBasicMaterial({
          color: 0x4ef0ff,
          transparent: true,
          opacity: 0.2,
          blending: THREE.AdditiveBlending
        }))
        beacon.position.set((p.x - MAZE_SIZE / 2) * TILE_SIZE, 6, (p.y - MAZE_SIZE / 2) * TILE_SIZE)
        oxygen.add(beacon)
      }
    })

    const exit = new THREE.Mesh(new THREE.TorusGeometry(0.8, 0.1, 16, 64), new THREE.MeshBasicMaterial({ color: 0x10b981 }))
    exit.rotation.x = Math.PI / 2; exit.position.set((exitPos.x - MAZE_SIZE / 2) * TILE_SIZE, 0.1, (exitPos.y - MAZE_SIZE / 2) * TILE_SIZE)
    walls.add(exit)
    const el = new THREE.PointLight(0x10b981, 100, 10); el.position.copy(exit.position); el.position.y = 2; walls.add(el)

  }, [grid, oxyPos, themeColors, exitPos, revealed])

  const checkLoop = (nextPos: Vec2) => {
    // Check if we have been at this position recently (last 4 steps)
    const len = positionHistory.length
    if (len < 2) return false
    // oscillating pattern: A -> B -> A
    if (positionHistory[len - 2].x === nextPos.x && positionHistory[len - 2].y === nextPos.y) return true
    return false
  }

  const runAgentStep = async () => {
    if (gameState !== 'idle') return
    setGameState('thinking')
    setLastAction(null)
    setLastExecutionResult(null)
    const surroundings = (pos: Vec2) => {
      const s: any = {}
      const c = (dx: number, dy: number, n: string) => {
        const nx = pos.x + dx, ny = pos.y + dy
        if (nx < 0 || ny < 0 || nx >= MAZE_SIZE || ny >= MAZE_SIZE) s[n] = 'boundary'
        else if (grid[ny][nx] === 1) s[n] = 'wall'
        else {
          const hasOxy = oxyPos.some(o => o.x === nx && o.y === ny)
          s[n] = hasOxy ? 'oxygen' : 'path'
        }
      }
      c(0, -1, 'north'); c(0, 1, 'south'); c(1, 0, 'east'); c(-1, 0, 'west')
      return s
    }
    const getMappedSurroundings = (pos: Vec2, radius: number) => {
      let mapStr = "Legend: A=Agent, E=Exit, O=Oxygen, #=Wall, .=Path, ?=Unknown\n      "
      // Add X-axis headers
      for (let x = 0; x < MAZE_SIZE; x++) mapStr += x % 10
      mapStr += "\n"

      for (let y = 0; y < MAZE_SIZE; y++) {
        mapStr += `${y % 10} ` // Y-axis label
        for (let x = 0; x < MAZE_SIZE; x++) {
          const key = `${x},${y}`
          if (x === pos.x && y === pos.y) mapStr += "A"
          else if (x === exitPos.x && y === exitPos.y && revealed.has(key)) mapStr += "E"
          else if (revealed.has(key)) {
            const hasOxy = oxyPos.some(o => o.x === x && o.y === y)
            if (hasOxy) mapStr += "O"
            else mapStr += grid[y][x] === 1 ? "#" : "."
          }
          else mapStr += "?"
        }
        mapStr += "\n"
      }
      return mapStr
    }

    // Build user message
    const availableSkillsText = activeTools.map(s => {
      const isAvailable = Date.now() - s.lastUsed > s.cooldown && energy >= s.energyCost
      return `- ${s.name} (${s.id}): ${s.description}. Cost: ${s.energyCost}. ${isAvailable ? '[READY]' : '[COOLDOWN/LOW ENERGY]'}`
    }).join('\n')

    let skillLogicAppend = ""
    if (activeSkill?.instructions) {
      skillLogicAppend = `\n\n[SKILL PROTOCOLS: ${activeSkill.name}]\n${activeSkill.instructions}`
    }

    // Get minimap for logging (the backend now handles optimization)
    const minimapStr = getMappedSurroundings(agentPos, 0)

    // Build surroundings object (renamed to avoid conflict with function)
    const nearbyData: { north: string; south: string; east: string; west: string } = {
      north: grid[agentPos.y - 1]?.[agentPos.x] === 1 ? 'wall' : (agentPos.y - 1 < 0 ? 'boundary' : 'path'),
      south: grid[agentPos.y + 1]?.[agentPos.x] === 1 ? 'wall' : (agentPos.y + 1 >= MAZE_SIZE ? 'boundary' : 'path'),
      east: grid[agentPos.y]?.[agentPos.x + 1] === 1 ? 'wall' : (agentPos.x + 1 >= MAZE_SIZE ? 'boundary' : 'path'),
      west: grid[agentPos.y]?.[agentPos.x - 1] === 1 ? 'wall' : (agentPos.x - 1 < 0 ? 'boundary' : 'path')
    }

    // Check for oxygen in surroundings
    for (const dir of ['north', 'south', 'east', 'west'] as const) {
      const dx = dir === 'east' ? 1 : dir === 'west' ? -1 : 0
      const dy = dir === 'north' ? -1 : dir === 'south' ? 1 : 0
      if (oxyPos.some(o => o.x === agentPos.x + dx && o.y === agentPos.y + dy)) {
        nearbyData[dir] = 'oxygen'
      }
    }

    // Build available skills array for the API
    const skillsForApi = useSkills ? activeTools.map(s => ({
      id: s.id,
      name: s.name,
      description: s.description,
      energyCost: s.energyCost,
      ready: Date.now() - s.lastUsed > s.cooldown && energy >= s.energyCost
    })) : []

    if (basePrompt) {
      // Build the full prompt with skill instructions for display
      const fullSystemPrompt = basePrompt + skillLogicAppend

      const qualityLine = promptQuality ? `[PROMPT QUALITY] ${promptQuality.level.toUpperCase()} | SCORE ${promptQuality.score}` : ''
      const skillsLine = `[SKILLS] ${useSkills ? 'ENABLED' : 'DISABLED'}`
      const headerLines = [qualityLine, skillsLine].filter(Boolean).join('\n')
      setLastPrompt(isFirstMessage ? `[SYSTEM PROMPT]\n${fullSystemPrompt}\n\n${headerLines}\n\n[MINIMAP]\n${minimapStr}` : `${headerLines}\n\n[MINIMAP]\n${minimapStr}`)
      addLog({
        type: 'request', content: JSON.stringify({
          session_id: sessionId,
          system_prompt: isFirstMessage ? fullSystemPrompt : undefined,
          position: [agentPos.x, agentPos.y],
          exit_position: [exitPos.x, exitPos.y],
          energy,
          oxygen,
          score,
          model: activeModel?.name || "default",
          is_first: isFirstMessage,
          skills_enabled: useSkills,
          prompt_quality: promptQuality ? { level: promptQuality.level, score: promptQuality.score } : null,
          memory_optimized: true // Flag indicating we're using the new system
        }, null, 2)
      })

      try {
        // Create new abort controller for this request
        if (abortControllerRef.current) abortControllerRef.current.abort()
        abortControllerRef.current = new AbortController()

        // Use the NEW optimized Maze Agent API with hierarchical memory management
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
          last_action: lastAction ? {
            action: lastAction.action,
            direction: lastAction.direction,
            skill: lastAction.skill
          } : undefined,
          last_result: lastExecutionResult?.message,
          temperature: 0.1,
          max_tokens: 400, // Reduced from 450 since prompts are now more efficient
          model: activeModel?.name || "default"
        }, abortControllerRef.current.signal)

        abortControllerRef.current = null

        // Mark that first message has been sent
        if (isFirstMessage) {
          setIsFirstMessage(false)
        }

        // Log response including memory stats if available
        const responseData = res.data
        addLog({
          type: 'full',
          content: JSON.stringify({
            response: responseData.response,
            memory_stats: responseData.memory_stats,
            tokens_saved: responseData.tokens_saved
          }, null, 2)
        })

        const responseText = responseData.response || ""
        const penalty = promptQuality ? applyPromptPenalty(responseText, promptQuality, steps) : { text: responseText, note: null, injected: false, penaltyEnergy: 0 }
        if (penalty.note) {
          addLog({ type: 'metadata', content: `PROMPT PENALTY: ${penalty.note}` })
        }
        addLog({ type: 'chunk', content: penalty.text })

        // Log token savings if available
        if (responseData.tokens_saved && responseData.tokens_saved > 0) {
          addLog({ type: 'metadata', content: `💾 Tokens saved: ~${responseData.tokens_saved} (Memory optimized)` })
        }

        const thinkTagRegex = /<think>([\s\S]*?)<\/think>/i
        const thinkingMatch = penalty.text.match(thinkTagRegex)
        const cleanText = thinkingMatch ? penalty.text.replace(thinkTagRegex, '').trim() : penalty.text.trim()

        if (thinkingMatch) setLastThinking(thinkingMatch[1].trim())
        else setLastThinking(null)

        const act = parseAgentAction(cleanText)
        if (act) {
          setLastAction(act)
          const result = await executeAction(act, isAutopilotRef.current)

          // Only stop autopilot if we reached the exit
          if (result.reachedExit) {
            setIsAutopilot(false)
          }
        } else {
          if (penalty.injected && penalty.penaltyEnergy > 0) {
            setEnergy(e => {
              const next = Math.max(0, e - penalty.penaltyEnergy)
              if (next <= 0) {
                setGameState('failed')
                setLastExecutionResult({ success: false, message: "CRITICAL: ENERGY EXHAUSTED. MISSION ABORTED." })
              }
              return next
            })
          }
          setLastExecutionResult({
            success: false,
            message: penalty.note ? `${penalty.note}. Energy -${penalty.penaltyEnergy}.` : "Parsed action was null/invalid. Retrying..."
          })
          setGameState('idle')
        }
      } catch (e: any) {
        if (axios.isCancel(e)) {
          addLog({ type: 'metadata', content: 'Agent step aborted by user.' })
          setLastExecutionResult({ success: false, message: "Cycle Aborted." })
        } else {
          addLog({ type: 'error', content: e.message })
          setLastExecutionResult({ success: false, message: `System Error: ${e.message}` })
        }
        setGameState('idle')
      }
    } else {
      setGameState('idle')
    }
  }


  const executeAction = async (action: any, wasAutopilot: boolean = false): Promise<{ success: boolean; reachedExit: boolean }> => {
    setGameState('moving')
    const count = Math.min(10, action.count || 1)
    let success = true
    let reachedExitFinal = false

    if (action.action === 'use_skill' && !useSkills) {
      setLastExecutionResult({ success: false, message: "Skill usage disabled for this run." })
      setGameState('idle')
      return { success: false, reachedExit: false }
    }

    // Maintain local history during multi-step execution for accurate checks
    let localHistory = [...positionHistory]

    for (let step = 0; step < count; step++) {
      // If it was started in autopilot but autopilot is now disabled, stop
      if (wasAutopilot && isAutopilotRef.current === false) {
        break
      }
      let stepReachedExit = false
      let stepSuccess = true

      await new Promise<void>(resolve => {
        setTimeout(() => {
          setAgentPos(currentPos => {
            let np = { ...currentPos }, eu = 0, d = action.direction?.toLowerCase()
            if (action.action === 'move') {
              if (d === 'north') np.y -= 1; if (d === 'south') np.y += 1; if (d === 'east') np.x += 1; if (d === 'west') np.x -= 1; eu = 5
            } else if (action.action === 'use_skill') {
              const toolId = action.skill
              const toolDef = activeTools.find(t => t.id === toolId)

              if (toolDef && energy >= toolDef.energyCost && Date.now() - toolDef.lastUsed > toolDef.cooldown) {
                eu = toolDef.energyCost
                setToolUsage(p => ({ ...p, [toolId]: Date.now() }))
                const logic = toolId
                // --- Skill Effect Dispatch ---
                const skillPos = { ...currentPos }

                if (logic === 'echo_pulse') {
                  // Reveal Radius 3
                  const nr = new Map(revealed)
                  const now = Date.now()
                  for (let dy = -3; dy <= 3; dy++) for (let dx = -3; dx <= 3; dx++) {
                    if (Math.abs(dx) + Math.abs(dy) <= 4) { // Diamond shape
                      nr.set(`${currentPos.x + dx},${currentPos.y + dy}`, now)
                    }
                  }
                  setRevealed(nr)

                  // FX: Expanding Sonic Wave
                  if (sceneRef.current) {
                    const { scene } = sceneRef.current
                    const geometry = new THREE.RingGeometry(0.5, 0.8, 32)
                    const material = new THREE.MeshBasicMaterial({ color: 0x38bdf8, side: THREE.DoubleSide, transparent: true, opacity: 0.8 })
                    const ring = new THREE.Mesh(geometry, material)
                    ring.rotation.x = -Math.PI / 2
                    ring.position.set((currentPos.x - MAZE_SIZE / 2) * TILE_SIZE, 0.5, (currentPos.y - MAZE_SIZE / 2) * TILE_SIZE)
                    scene.add(ring)

                    let scale = 1
                    const anim = setInterval(() => {
                      scale += 0.8
                      ring.scale.set(scale, scale, scale)
                      material.opacity -= 0.04
                    }, 16)
                    setTimeout(() => { clearInterval(anim); scene.remove(ring); geometry.dispose(); material.dispose() }, 600)
                  }
                }
                else if (logic === 'phase_dash') {
                  // Move 3 tiles, stop at wall
                  let steps = 0
                  for (let i = 1; i <= 3; i++) {
                    let nextX = np.x, nextY = np.y
                    if (d === 'north') nextY -= 1; if (d === 'south') nextY += 1; if (d === 'east') nextX += 1; if (d === 'west') nextX -= 1
                    if (nextX >= 0 && nextY >= 0 && nextX < MAZE_SIZE && nextY < MAZE_SIZE && grid[nextY][nextX] === 0) {
                      np.x = nextX; np.y = nextY
                      steps++
                    } else {
                      break // Hit wall
                    }
                  }

                  // FX: Afterimage Trail
                  if (sceneRef.current) {
                    const { scene, agent } = sceneRef.current
                    const startVec = agent.position.clone()
                    const endVec = new THREE.Vector3((np.x - MAZE_SIZE / 2) * TILE_SIZE, startVec.y, (np.y - MAZE_SIZE / 2) * TILE_SIZE)

                    const geometry = new THREE.BufferGeometry().setFromPoints([startVec, endVec])
                    const material = new THREE.LineBasicMaterial({ color: 0xf472b6, linewidth: 3 })
                    const line = new THREE.Line(geometry, material)
                    scene.add(line)
                    setTimeout(() => { scene.remove(line); geometry.dispose(); material.dispose() }, 300)
                  }
                }
                else if (logic === 'bio_scan') {
                  // Highlight Oxygen
                  if (sceneRef.current) {
                    const { oxygen } = sceneRef.current
                    oxygen.children.forEach(c => {
                      if (c instanceof THREE.Mesh) {
                        // Pulse effect
                        const originalScale = c.scale.clone()
                        const originalColor = c.material.color.getHex()
                        c.material.color.setHex(0xfacc15)

                        let pulse = 0
                        const anim = setInterval(() => {
                          pulse += 0.2
                          const s = 1 + Math.sin(pulse) * 0.5
                          c.scale.set(s, s, s)
                        }, 30)

                        setTimeout(() => {
                          clearInterval(anim)
                          c.scale.copy(originalScale)
                          c.material.color.setHex(originalColor)
                        }, 2000)
                      }
                    })
                    setLastExecutionResult({ success: true, message: `Bio-Scan Complete. Found ${oxyPos.length} signatures.` })
                  }
                }
                else if (logic === 'sys_override') {
                  // Reveal Map for 30s? Or permanent? Permanent is standard.
                  const nr = new Map(revealed)
                  const now = Date.now()
                  // Reveal all
                  for (let y = 0; y < MAZE_SIZE; y++) for (let x = 0; x < MAZE_SIZE; x++) {
                    nr.set(`${x},${y}`, now)
                  }
                  setRevealed(nr)

                  // FX: Orbital Beam
                  if (sceneRef.current) {
                    const { scene } = sceneRef.current
                    const geo = new THREE.CylinderGeometry(0.1, 20, 100, 32, 1, true)
                    const mat = new THREE.MeshBasicMaterial({ color: 0xef4444, transparent: true, opacity: 0.5, side: THREE.DoubleSide, blending: THREE.AdditiveBlending })
                    const beam = new THREE.Mesh(geo, mat)
                    beam.position.set(0, 50, 0)
                    scene.add(beam)

                    let t = 0
                    const anim = setInterval(() => {
                      t += 0.05
                      beam.scale.set(1 + t * 5, 1, 1 + t * 5)
                      mat.opacity -= 0.01
                    }, 20)
                    setTimeout(() => { clearInterval(anim); scene.remove(beam); geo.dispose(); mat.dispose() }, 1000)
                  }
                }
              }
            }



            const isValid = np.x >= 0 && np.y >= 0 && np.x < MAZE_SIZE && np.y < MAZE_SIZE && grid[np.y][np.x] === 0
            if (isValid) {
              setSteps(s => s + 1);
              // Energy logic: Consume eu, regenerate +2 per step
              setEnergy(e => {
                const next = Math.max(0, e - eu + 2)
                if (next <= 0) {
                  setGameState('failed')
                  setLastExecutionResult({ success: false, message: "CRITICAL: ENERGY EXHAUSTED. MISSION ABORTED." })
                }
                return next
              })

              // Only update position history if it's a move
              if (action.action === 'move') {
                setPositionHistory(prev => [...prev.slice(-10), np])
                localHistory.push(np) // Update local history too

                // Auto-reveal cells around new position
                setRevealed(prevRevealed => {
                  const newRevealed = new Map(prevRevealed)
                  const now = Date.now()
                  for (let dy = -1; dy <= 1; dy++) {
                    for (let dx = -1; dx <= 1; dx++) {
                      const rx = np.x + dx, ry = np.y + dy
                      if (rx >= 0 && ry >= 0 && rx < MAZE_SIZE && ry < MAZE_SIZE) {
                        newRevealed.set(`${rx},${ry}`, now)
                      }
                    }
                  }
                  return newRevealed
                })
              }

              const oIdx = oxyPos.findIndex(o => o.x === np.x && o.y === np.y)
              if (oIdx !== -1) {
                setOxygen(ox => ox + 1); setOxyPos(p => { const n = [...p]; n.splice(oIdx, 1); return n })
                setScore(sc => sc + 500)
                setLastExecutionResult({ success: true, message: `Collected Oxygen at (${np.x}, ${np.y})! (+500)` })
              } else {
                setLastExecutionResult({ success: true, message: action.action === 'move' ? `Moved ${d} to (${np.x}, ${np.y}) [Step ${step + 1}/${count}]` : `Used skill ${action.skill}` })
              }
              setHistory(prev => [...prev.slice(-30), `${np.x},${np.y}`])
              if (np.x === exitPos.x && np.y === exitPos.y) {
                const timeBonus = Math.max(0, 5000 - time * 50)
                const finalScore = score + 2000 + timeBonus
                setScore(sc => sc + 2000 + timeBonus);
                setGameState('success')
                setLastExecutionResult({ success: true, message: "REACHED EXIT! EXFILTRATION SUCCESSFUL." })
                stepReachedExit = true

                // Update leaderboard
                try {
                  const payload = {
                    template_id: selectedTemplateId || 0,
                    session_id: sessionId,
                    score: finalScore, // Legacy score
                    new_score: finalScore, // Primary score in backend
                    total_steps: steps + step + 1,
                    oxygen_collected: oxygen + (oIdx !== -1 ? 1 : 0),
                    mode: selectedTemplateId ? 'lam' : 'manual'
                  }
                  console.log('[LEADERBOARD] Submitting results:', payload)
                  leaderboardAPI.submitScore(payload)
                } catch (err) {
                  console.error('Failed to submit score:', err)
                }
              }
              resolve()
              return np
            } else {
              setEnergy(e => {
                const next = Math.max(0, e - 10) // Penalty for hitting a wall
                if (next <= 0) {
                  setGameState('failed')
                  setLastExecutionResult({ success: false, message: "CRITICAL: ENERGY EXHAUSTED. MISSION ABORTED." })
                }
                return next
              })
              setLastExecutionResult({ success: false, message: `COLLISION DETECTED at ${d}. Energy Penalty.` })
              stepSuccess = false
              stepReachedExit = false
              resolve()
              return currentPos
            }
          })
        }, 400)
      })
      if (stepReachedExit) { reachedExitFinal = true; break }
      if (!stepSuccess) { success = false; break }
    }
    setGameState(prev => (prev === 'moving' || prev === 'thinking') ? 'idle' : prev)
    return { success, reachedExit: reachedExitFinal }
  }

  // Dynamic Styles based on theme
  const dynamicSidebarStyle: CSSProperties = {
    background: `linear-gradient(180deg, rgba(15, 23, 42, 0.98) 0%, rgba(${(themeColors.primary >> 16) & 255}, ${(themeColors.primary >> 8) & 255}, ${themeColors.primary & 255}, 0.05) 100%)`,
    display: 'flex',
    flexDirection: 'column',
    borderLeft: '1px solid rgba(255,255,255,0.08)',
    boxShadow: '-10px 0 30px rgba(0,0,0,0.5)',
    backdropFilter: 'blur(20px)'
  }

  const dynamicPromptCardStyle: CSSProperties = {
    background: `rgba(2, 6, 23, 0.5)`,
    padding: 16,
    borderRadius: 12,
    border: '1px solid rgba(255,255,255,0.05)',
    borderTop: `1px solid rgba(${(themeColors.primary >> 16) & 255}, ${(themeColors.primary >> 8) & 255}, ${themeColors.primary & 255}, 0.2)`,
    overflowY: 'auto',
    maxHeight: '350px',
    fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
    fontSize: '0.75rem',
    lineHeight: 1.6,
    backdropFilter: 'blur(10px)'
  }

  const dynamicHelpStyle: CSSProperties = {
    ...dynamicPromptCardStyle,
    background: `rgba(${(themeColors.primary >> 16) & 255}, ${(themeColors.primary >> 8) & 255}, ${themeColors.primary & 255}, 0.05)`,
    fontSize: '0.7rem',
    color: '#94a3b8',
    whiteSpace: 'pre-wrap',
    borderColor: `rgba(${(themeColors.primary >> 16) & 255}, ${(themeColors.primary >> 8) & 255}, ${themeColors.primary & 255}, 0.1)`,
  }

  return (
    <div style={{
      ...containerStyle,
      flexDirection: isMobile ? 'column' : 'row',
      height: isMobile ? 'auto' : 'calc(100vh - 80px)', // Adjust for navbar
      minHeight: isMobile ? '100vh' : '0',
      userSelect: isResizing ? 'none' : 'auto'
    }}>
      <div style={{ flex: 1, position: 'relative', minHeight: isMobile ? '60vh' : '0' }}>
        <div id="maze-3d-mount" ref={mountRef} style={{ width: '100%', height: '100%', display: 'block' }} />
        <div style={{ position: 'absolute', top: 24, left: 24, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <div id="maze-hud-energy" style={hudBadgeStyle}><Zap size={14} className="text-yellow-400" /> <span>ENERGY: {energy}/150</span></div>
          <div id="maze-hud-oxygen" style={hudBadgeStyle}><Cylinder size={14} className="text-cyan-400" /> <span>OXYGEN: {oxygen}</span></div>
          <div id="maze-hud-score" style={hudBadgeStyle}><Coins size={14} className="text-amber-400" /> <span>SCORE: {score}</span></div>
          <div id="maze-hud-timer" style={hudBadgeStyle}><Clock size={14} className="text-indigo-400" /> <span>TIME: {time}s</span></div>
          <button id="maze-spectate-btn" onClick={() => setSpectateMode(!spectateMode)} style={{ ...hudBadgeStyle, background: spectateMode ? `${themeColors.primary}44` : 'rgba(15,23,42,0.7)', cursor: 'pointer' }}>
            {spectateMode ? <MousePointer2 size={14} /> : <Video size={14} />} <span>{spectateMode ? 'SPECTATING' : 'FOLLOWING'}</span>
          </button>
        </div>
        <div style={{ position: 'absolute', bottom: 32, left: '50%', transform: 'translateX(-50%)', width: '300px' }}>
          <div style={{ height: 8, background: 'rgba(0,0,0,0.6)', borderRadius: 4, overflow: 'hidden', border: '1px solid rgba(255,255,255,0.1)' }}>
            <motion.div animate={{ width: `${(energy / 150) * 100}%` }} style={{ height: '100%', background: `linear-gradient(90deg, ${themeColors.primary}, ${themeColors.secondary})` }} />
          </div>
        </div>
        <AnimatePresence>
          {gameState === 'success' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={winOverlayStyle}>
              <Trophy size={80} color="#fbbf24" className="mb-6" />
              <h2 style={{ fontSize: '3.5rem', fontWeight: 900 }}>EXTRACTED</h2>
              <div style={{ display: 'flex', gap: 24, margin: '20px 0' }}>
                <div style={statBoxStyle}><h3>SCORE</h3><p>{score}</p></div>
                <div style={statBoxStyle}><h3>OXYGEN</h3><p>{oxygen}</p></div>
                <div style={statBoxStyle}><h3>TIME</h3><p>{time}s</p></div>
              </div>
              <button onClick={() => window.location.reload()} style={primaryButtonStyle(themeColors.primary)}>New Session</button>
            </motion.div>
          )}
          {gameState === 'failed' && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} style={{ ...winOverlayStyle, background: 'rgba(127, 29, 29, 0.9)' }}>
              <AlertCircle size={80} color="#ef4444" className="mb-6" />
              <h2 style={{ fontSize: '3.5rem', fontWeight: 900 }}>MISSION FAILED</h2>
              <p style={{ fontSize: '1.2rem', opacity: 0.8, marginBottom: 20 }}>Neural integrity compromised. Energy depleted.</p>
              <div style={{ display: 'flex', gap: 24, margin: '20px 0' }}>
                <div style={statBoxStyle}><h3>SCORE</h3><p>{score}</p></div>
                <div style={statBoxStyle}><h3>OXYGEN</h3><p>{oxygen}</p></div>
              </div>
              <button onClick={() => window.location.reload()} style={primaryButtonStyle('#ef4444')}>Retry Mission</button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      {!isMobile && (
        <div
          onMouseDown={() => setIsResizing(true)}
          style={{
            width: '2px',
            cursor: 'col-resize',
            background: isResizing ? themeColors.primary : 'rgba(255,255,255,0.05)',
            transition: 'background 0.2s',
            zIndex: 50,
            position: 'relative'
          }}
        >
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '-4px',
            width: '10px',
            height: '40px',
            background: 'rgba(255,255,255,0.1)',
            borderRadius: '4px',
            transform: 'translateY(-50%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1px'
          }}>
            <div style={{ width: '1px', height: '12px', background: 'rgba(255,255,255,0.3)' }} />
            <div style={{ width: '1px', height: '12px', background: 'rgba(255,255,255,0.3)' }} />
          </div>
        </div>
      )}
      <aside style={{
        ...dynamicSidebarStyle,
        flexShrink: 0,
        width: isMobile ? '100%' : `${sidebarWidth}px`,
        maxHeight: isMobile ? 'none' : '100%'
      }}>
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid rgba(255,255,255,0.05)',
          background: `rgba(${(themeColors.primary >> 16) & 255}, ${(themeColors.primary >> 8) & 255}, ${themeColors.primary & 255}, 0.08)`
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 38, height: 38, background: 'transparent', borderRadius: 8, overflow: 'hidden', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <img src="/logo_new.png" style={{ width: '100%', height: '100%', objectFit: 'contain' }} alt="PiNG" />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <h3 style={{ margin: 0, fontFamily: "'Plus Jakarta Sans', sans-serif", fontSize: '0.95rem', letterSpacing: '-0.02em', fontWeight: 800, color: '#fff' }}>PiNG Terminal</h3>
                <span style={{
                  fontSize: '0.6rem',
                  color: `#${themeColors.secondary.toString(16).padStart(6, '0')}`,
                  fontWeight: 800,
                  fontFamily: "'Plus Jakarta Sans', sans-serif",
                  background: `rgba(${(themeColors.primary >> 16) & 255}, ${(themeColors.primary >> 8) & 255}, ${themeColors.primary & 255}, 0.1)`,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  marginTop: 2,
                  width: 'fit-content',
                  textShadow: `0 0 10px rgba(${(themeColors.primary >> 16) & 255}, ${(themeColors.primary >> 8) & 255}, ${themeColors.primary & 255}, 0.3)`
                }}>
                  {theme.toUpperCase()} CORE v2.0
                </span>
              </div>
            </div>
            <button
              onClick={() => setShowExample(!showExample)}
              style={{
                background: 'rgba(255,255,255,0.06)',
                border: '1px solid rgba(255,255,255,0.1)',
                color: '#fff',
                cursor: 'pointer',
                fontWeight: 800,
                padding: '6px 14px',
                borderRadius: '8px',
                fontSize: '0.65rem',
                letterSpacing: '0.05em',
                textTransform: 'uppercase',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              {showExample ? <X size={12} /> : <FileText size={12} />}
              {showExample ? 'Close' : 'Protocol'}
            </button>
          </div>
          <AnimatePresence>{showExample && <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} style={{ overflow: 'hidden', marginBottom: 16 }}><pre style={dynamicHelpStyle}>{AGENT_EXAMPLE_TEMPLATE}</pre></motion.div>}</AnimatePresence>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label style={labelStyle}>Neural Logic Engine</label>
              <select
                id="maze-model-selector"
                value={activeModel?.name ?? ''}
                onChange={async (e) => {
                  const name = e.target.value;
                  // Optimistically update
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
                {availableModels.map(m => <option key={m.name} value={m.name}>{m.name}</option>)}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Tactical Skill Loadout</label>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: '0.7rem', fontWeight: 700, color: useSkills ? '#10b981' : '#f97316' }}>
                  {useSkills ? 'Skills Enabled' : 'Skills Disabled'}
                </span>
                <button
                  onClick={() => {
                    setUseSkills(prev => {
                      const next = !prev
                      if (next && !selectedAgentSkillId && agentSkills.length > 0) {
                        setSelectedAgentSkillId(agentSkills[0].id)
                      }
                      return next
                    })
                  }}
                  style={{
                    background: 'rgba(255,255,255,0.06)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    color: '#fff',
                    cursor: 'pointer',
                    fontWeight: 800,
                    padding: '6px 12px',
                    borderRadius: '8px',
                    fontSize: '0.6rem',
                    letterSpacing: '0.05em',
                    textTransform: 'uppercase',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6
                  }}
                >
                  {useSkills ? <ToggleRight size={12} /> : <ToggleLeft size={12} />}
                  {useSkills ? 'On' : 'Off'}
                </button>
              </div>
              <select
                id="maze-skill-selector"
                value={useSkills ? (selectedAgentSkillId ?? '') : ''}
                onChange={e => {
                  const value = e.target.value
                  if (!value) {
                    setUseSkills(false)
                    setSelectedAgentSkillId(null)
                    return
                  }
                  setUseSkills(true)
                  setSelectedAgentSkillId(value)
                }}
                style={{ ...selectStyle, opacity: useSkills ? 1 : 0.6 }}
                disabled={!useSkills}
              >
                {agentSkills.length > 0 ? (
                  <>
                    <option value="">No Skills (Manual)</option>
                    {agentSkills.map(s => <option key={s.id} value={s.id}>{s.name} ({s.tools.length} Tools)</option>)}
                  </>
                ) : (
                  <option value="" disabled>No Skills Configured</option>
                )}
              </select>
            </div>
            <div>
              <label style={labelStyle}>Mission Protocol</label>
              <select
                id="maze-template-selector"
                value={selectedTemplateId ?? ''}
                onChange={e => setSelectedTemplateId(e.target.value ? Number(e.target.value) : null)}
                style={selectStyle}
              >
                {templates.length > 0 ? (
                  <>
                    <option value="" disabled>Select a strategy...</option>
                    {templates.map(t => <option key={t.id} value={t.id}>{t.title}</option>)}
                  </>
                ) : (
                  <option value="" disabled>Empty (Create a template first)</option>
                )}
              </select>
            </div>
            <div id="maze-controls" style={{ display: 'flex', gap: 10 }}>
              <motion.button
                id="maze-initiate-btn"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  setStepsThisTurn(0)
                  runAgentStep()
                }}
                disabled={gameState !== 'idle' || !basePrompt}
                style={{
                  background: gameState !== 'idle' || !basePrompt ? 'rgba(255,255,255,0.05)' : `linear-gradient(135deg, #${themeColors.primary.toString(16).padStart(6, '0')}, #${themeColors.secondary.toString(16).padStart(6, '0')})`,
                  color: '#fff',
                  border: 'none',
                  borderRadius: '12px',
                  padding: '12px',
                  fontWeight: 800,
                  cursor: gameState !== 'idle' || !basePrompt ? 'default' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  fontSize: '0.8rem',
                  flex: 1,
                  boxShadow: gameState !== 'idle' || !basePrompt ? 'none' : `0 4px 15px rgba(${(themeColors.primary >> 16) & 255}, ${(themeColors.primary >> 8) & 255}, ${themeColors.primary & 255}, 0.3)`
                }}
              >
                {gameState === 'thinking' && !isAutopilot ? <RefreshCw className="animate-spin" size={16} /> : <Zap size={16} />}
                Initiate Cycle
              </motion.button>
              <motion.button
                id="maze-autopilot-btn"
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  if (isAutopilot) {
                    setIsAutopilot(false)
                    if (abortControllerRef.current) {
                      abortControllerRef.current.abort()
                      abortControllerRef.current = null
                    }
                    setGameState('idle')
                  } else {
                    setIsAutopilot(true)
                    runAgentStep()
                  }
                }}
                disabled={!basePrompt}
                style={{
                  background: isAutopilot ? 'linear-gradient(135deg, #f43f5e, #fb7185)' : 'rgba(255,255,255,0.05)',
                  border: isAutopilot ? 'none' : '1px solid rgba(255,255,255,0.1)',
                  color: '#fff',
                  borderRadius: '12px',
                  padding: '12px',
                  fontWeight: 800,
                  cursor: !basePrompt ? 'default' : 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  fontSize: '0.8rem',
                  flex: 1,
                  boxShadow: isAutopilot ? '0 4px 15px rgba(244, 63, 94, 0.4)' : 'none'
                }}
              >
                {isAutopilot ? <Square size={16} /> : <Play size={16} />}
                {isAutopilot ? 'Abort' : 'Auto'}
              </motion.button>
            </div>
          </div>
        </div>
        <div style={{
          margin: '0 20px 20px',
          padding: 16,
          borderRadius: 12,
          border: '1px solid rgba(255,255,255,0.08)',
          background: 'rgba(15, 23, 42, 0.5)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
            <span style={labelStyle}>Prompt Quality</span>
            {promptQuality ? (
              <span style={{
                fontSize: '0.7rem',
                fontWeight: 800,
                color: promptQuality.level === 'good' ? '#10b981' : promptQuality.level === 'bad' ? '#f43f5e' : '#f59e0b'
              }}>
                {promptQuality.level.toUpperCase()}
              </span>
            ) : (
              <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#64748b' }}>NO PROMPT</span>
            )}
          </div>
          {promptQuality ? (
            <>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                {promptQuality.level === 'good' ? <Sparkles size={14} color="#10b981" /> : promptQuality.level === 'bad' ? <AlertTriangle size={14} color="#f43f5e" /> : <AlertCircle size={14} color="#f59e0b" />}
                <span style={{ fontSize: '0.75rem', color: '#cbd5e1' }}>
                  Score {promptQuality.score} | {promptQuality.level === 'good' ? 'Stable JSON output expected.' : promptQuality.level === 'bad' ? 'High syntax-error risk.' : 'Occasional format drift.'}
                </span>
              </div>
              {promptQuality.issues.length > 0 && (
                <div style={{ fontSize: '0.7rem', color: '#fda4af' }}>
                  Issues: {promptQuality.issues.join(', ')}
                </div>
              )}
              {promptQuality.strengths.length > 0 && (
                <div style={{ fontSize: '0.7rem', color: '#86efac', marginTop: 4 }}>
                  Strengths: {promptQuality.strengths.join(', ')}
                </div>
              )}
            </>
          ) : (
            <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Select a template or enter a custom prompt.</span>
          )}
        </div>
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: 20,
          backgroundColor: `rgba(${(themeColors.primary >> 16) & 255}, ${(themeColors.primary >> 8) & 255}, ${themeColors.primary & 255}, 0.03)`
        }}>
          <div id="maze-telemetry" style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <Terminal size={14} color={themeColors.primary} />
            <span style={labelStyle}>SYSTEM TELEMETRY</span>
          </div>
          <div id="maze-telemetry-data" style={{ ...dynamicPromptCardStyle, borderLeft: `3px solid #${themeColors.primary.toString(16).padStart(6, '0')}` }}>
            {lastPrompt.split('\n').map((l, i) => (
              <div key={i} style={{ fontSize: '0.75rem', color: l.startsWith('[') ? themeColors.secondary : '#cbd5e1', marginBottom: 2 }}>{l}</div>
            ))}
          </div>

          {lastThinking && (
            <div id="maze-thinking-panel" style={{ marginTop: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
                <Brain size={14} color="#a78bfa" />
                <span style={{ ...labelStyle, color: '#a78bfa' }}>COG REASONING CHAIN</span>
              </div>
              <div style={{ ...dynamicPromptCardStyle, color: '#a78bfa', background: 'rgba(139, 92, 246, 0.04)', borderColor: 'rgba(139, 92, 246, 0.2)', fontSize: '0.8rem', borderLeft: '3px solid #a78bfa' }} className="markdown-content">
                <Markdown remarkPlugins={[remarkGfm]}>{lastThinking}</Markdown>
              </div>
            </div>
          )}

          <div id="maze-action-output" style={{ ...dynamicPromptCardStyle, marginTop: 20, borderLeft: `3px solid #10b981`, background: 'rgba(16, 185, 129, 0.02)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}><Cpu size={14} color="#10b981" /><span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#10b981' }}>ACTION OUTPUT</span></div>
            <code style={{ fontSize: '0.8rem', color: '#34d399' }}>{lastAction ? JSON.stringify(lastAction) : "No Valid Action"}</code>
            {lastExecutionResult && (
              <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid rgba(16, 185, 129, 0.2)', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                {lastExecutionResult.success ? <Check size={14} className="text-emerald-400 mt-1" /> : <AlertCircle size={14} className="text-rose-400 mt-1" />}
                <span style={{ fontSize: '0.75rem', color: lastExecutionResult.success ? '#10b981' : '#f43f5e', fontWeight: 600 }}>
                  {lastExecutionResult.message}
                </span>
              </div>
            )}
          </div>
        </div>
      </aside >
    </div >
  )
}

const containerStyle: CSSProperties = { display: 'flex', width: '100%', background: '#020617', overflow: 'hidden', fontFamily: 'Urbanist, sans-serif' }
const hudBadgeStyle: CSSProperties = { background: 'rgba(15, 23, 42, 0.7)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.08)', padding: '10px 18px', borderRadius: '14px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', fontWeight: 800, color: '#fff', boxShadow: '0 4px 12px rgba(0,0,0,0.2)' }
const winOverlayStyle: CSSProperties = { position: 'absolute', inset: 0, background: 'rgba(2, 6, 23, 0.92)', backdropFilter: 'blur(24px)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', zIndex: 200, color: '#fff' }
const statBoxStyle: CSSProperties = { textAlign: 'center', background: 'rgba(255,255,255,0.03)', padding: '24px', borderRadius: '20px', border: '1px solid rgba(255,255,255,0.08)', minWidth: '140px' }
const labelStyle: CSSProperties = { fontSize: '0.65rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase', marginBottom: 6, fontFamily: 'Plus Jakarta Sans, sans-serif', letterSpacing: '0.1em' }
const selectStyle: CSSProperties = { background: 'rgba(15, 23, 42, 0.6)', border: '1px solid rgba(255,255,255,0.08)', borderRadius: '10px', padding: '12px', color: '#fff', outline: 'none', width: '100%', fontSize: '0.85rem', fontWeight: 600, fontFamily: 'Plus Jakarta Sans, sans-serif' }
const primaryButtonStyle = (c: any, d = false): CSSProperties => ({ background: d ? 'rgba(255,255,255,0.05)' : `#${c.toString(16).padStart(6, '0')}`, color: '#fff', border: 'none', borderRadius: '14px', padding: '16px', fontWeight: 800, cursor: d ? 'default' : 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, fontSize: '0.95rem', transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)', boxShadow: d ? 'none' : `0 4px 14px 0 rgba(${(c >> 16) & 255}, ${(c >> 8) & 255}, ${c & 255}, 0.39)` })

export type Vec2 = { x: number; y: number }
export type Cell = 0 | 1 // 0: path, 1: wall
export type Grid = Cell[][]
export type Template = { id: number; title: string }
export type HintMsg = {
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

export type GameState = {
  grid: Grid,
  player: Vec2,
  exit: Vec2,
  oxy: Vec2[],
  germs: { pos: Vec2; dir: Vec2; speed: number }[],
  oxygenCollected: number,
  startTime: number,
  started: boolean,
  gameOver: boolean,
  win: boolean,
  endTime: number | undefined,
  finalScore: number | undefined,
  lam: { hint: string; path: Vec2[]; breaks: number; error: string; showPath: boolean },
  // Effects & visuals
  effects: { speedBoostUntil: number, slowGermsUntil: number, freezeGermsUntil: number },
  highlight: Map<string, number>, // key(x,y) -> until timestamp
  revealMap: boolean,
  fxPopups: Array<{x:number;y:number;text:string;t0:number;ttl:number}>,
  hitFlash: number,
  particles: Array<{x:number;y:number;r:number;spd:number;alpha:number}>,
  germStepFlip: boolean,
  emotion: 'neutral'|'happy'|'scared'|'tired'|'excited',
  // New wall break FX
  wallBreakParts: Array<{x:number;y:number;vx:number;vy:number;life:number;ttl:number}>,
  cameraShake: number,
  fallTexts?: Array<{x:number;y:number;vx:number;vy:number;t0:number;ttl:number;text:string}>
}

export type LamFlowEvent = { 
  id:number; 
  publishAt:number; 
  receivedAt?:number; 
  latencyMs?:number; 
  actionsDeclared:string[]; 
  actionsApplied:Array<{action:string; at:number; detail?:any}>; 
  hintExcerpt?:string; 
  error?:string 
}

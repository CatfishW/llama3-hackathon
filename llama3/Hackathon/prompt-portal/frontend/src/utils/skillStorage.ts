import { Radar, Wind, Scan, Zap, Activity, Radio, Cpu, Eye } from 'lucide-react'

// The fundamental executable functions available to the system
export interface AtomicSkill {
    id: string
    name: string
    description: string
    energyCost: number
    cooldown: number // in ms
    icon: any
    color: string
}

export const ATOMIC_SKILLS: AtomicSkill[] = [
    {
        id: 'echo_pulse',
        name: 'Echo Pulse',
        description: 'Emits a sonic wave revealing immediate surroundings (Radius 3).',
        energyCost: 15,
        cooldown: 2000,
        icon: Radio,
        color: '#38bdf8'
    },
    {
        id: 'phase_dash',
        name: 'Phase Dash',
        description: 'A quantum leap forward by 3 units. Stops at walls.',
        energyCost: 35,
        cooldown: 5000,
        icon: Wind,
        color: '#f472b6'
    },
    {
        id: 'bio_scan',
        name: 'Bio-Scan',
        description: 'Detects and highlights all Oxygen/Resource signatures on the map.',
        energyCost: 20,
        cooldown: 3000,
        icon: Activity,
        color: '#facc15'
    },
    {
        id: 'sys_override',
        name: 'System Override',
        description: 'Brute-force hack to reveal the complete facility layout.',
        energyCost: 90,
        cooldown: 30000,
        icon: Cpu,
        color: '#ef4444'
    }
]

// User-defined skills that compose atomic skills with custom logic/instructions
export interface AgentSkill {
    id: string
    name: string
    description: string
    instructions: string // The logic/workflow (markdown)
    tools: string[] // IDs of AtomicSkills enabled for this skill
    created_at: number
}

// Default "Starter" skills provided to the user
export const DEFAULT_AGENT_SKILLS: AgentSkill[] = [
    {
        id: 'scout_v2',
        name: 'Scout Vanguard',
        description: 'Balanced feedback loop for exploration and retrieval.',
        instructions: `
# MISSION PROFILE: SCOUT
1. INIT: Use "System Override" (sys_override) if Energy > 100 to map the sector.
2. SEEK: Use "Bio-Scan" (bio_scan) to locate Oxygen targets.
3. MOVE: Proceed to nearest Oxygen. Use "Echo Pulse" (echo_pulse) if path is unclear.
        `.trim(),
        tools: ['echo_pulse', 'bio_scan', 'sys_override'],
        created_at: Date.now()
    },
    {
        id: 'speedster',
        name: 'Void Runner',
        description: 'High-velocity traversal logic using Phase Dash.',
        instructions: `
# MISSION PROFILE: RUNNER
1. MOVEMENT: Prioritize "Phase Dash" (phase_dash) for long corridors.
2. CAUTION: Do not dash into unknown sectors.
        `.trim(),
        tools: ['phase_dash', 'echo_pulse'],
        created_at: Date.now()
    }
]

export const getSkills = (userId?: number | string): AgentSkill[] => {
    try {
        const key = userId ? `agent_skills_v2_${userId}` : 'agent_skills_v2'
        const stored = localStorage.getItem(key)
        if (stored) {
            return JSON.parse(stored)
        }
    } catch (e) {
        console.error("Failed to load skills", e)
    }
    return DEFAULT_AGENT_SKILLS
}

export const saveSkills = (skills: AgentSkill[], userId?: number | string) => {
    const key = userId ? `agent_skills_v2_${userId}` : 'agent_skills_v2'
    localStorage.setItem(key, JSON.stringify(skills))
}

export const getAtomicSkill = (id: string): AtomicSkill | undefined => {
    return ATOMIC_SKILLS.find(s => s.id === id)
}

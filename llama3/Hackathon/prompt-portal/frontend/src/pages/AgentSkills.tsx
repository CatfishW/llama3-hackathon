import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
    Plus, Trash2, Save, RotateCcw, Zap, Book, Box, Layers, Code,
    CheckCircle, Circle, Brain, Terminal, Activity, FileText,
    Cpu, Scan, Wind, Radar
} from 'lucide-react'
import { useTheme } from '../contexts/ThemeContext'
import { getSkills, saveSkills, AgentSkill, DEFAULT_AGENT_SKILLS, ATOMIC_SKILLS, AtomicSkill } from '../utils/skillStorage'
import { useAuth } from '../auth/AuthContext'
import { useIsMobile } from '../hooks/useIsMobile'
import { useTutorial } from '../contexts/TutorialContext'

export default function AgentSkills() {
    const { user } = useAuth()
    const { theme } = useTheme()
    const isMobile = useIsMobile()
    const [skills, setSkills] = useState<AgentSkill[]>([])
    const [isEditing, setIsEditing] = useState(false)
    const [showGuide, setShowGuide] = useState(() => !window.matchMedia || window.innerWidth > 900)

    // Form State
    const [editingId, setEditingId] = useState<string | null>(null)
    const [formData, setFormData] = useState<Partial<AgentSkill>>({
        id: '',
        name: '',
        description: '',
        instructions: '',
        tools: []
    })
    const { runTutorial } = useTutorial()

    useEffect(() => {
        const hasSeenSkillsTutorial = localStorage.getItem('tutorial_seen_skills')
        if (!hasSeenSkillsTutorial) {
            runTutorial([
                { target: '#new-skill-btn', title: 'Expand Capabilities', content: 'Create custom skill sets for your agents. A skill is a combination of tools and specific instructions.', position: 'left' },
                { target: '#skill-architecture-guide', title: 'Modular Design', content: 'Learn the three pillars of skill architecture: Composition, Instructions, and Execution.', position: 'bottom' },
                { target: '#guide-toggle-btn', title: 'Knowledge Access', content: 'Toggle the architecture guide to refresh your memory on skill design principles.', position: 'bottom' },
                { target: '#skills-grid', title: 'Your Arsenal', content: 'View and manage the modular capabilities you\'ve designed for your autonomous agents.', position: 'top' },
                { target: '#skill-card-tools', title: 'Toolsets', content: 'Each skill lists its required atomic tools. Ensure your instructions reference these tools correctly.', position: 'top', allowMultiple: true },
            ]);
            localStorage.setItem('tutorial_seen_skills', 'true');
        }
    }, [runTutorial]);

    useEffect(() => {
        setSkills(getSkills(user?.id))
    }, [user])

    const handleSave = () => {
        // Validation
        if (!formData.name || !formData.id) return

        const newSkill: AgentSkill = {
            id: formData.id,
            name: formData.name,
            description: formData.description || '',
            instructions: formData.instructions || '',
            tools: formData.tools || [],
            created_at: editingId ? (skills.find(s => s.id === editingId)?.created_at || Date.now()) : Date.now()
        }

        let updatedSkills
        if (editingId) {
            updatedSkills = skills.map(s => s.id === editingId ? newSkill : s)
        } else {
            if (skills.find(s => s.id === newSkill.id)) {
                alert('Skill ID must be unique')
                return
            }
            updatedSkills = [...skills, newSkill]
        }

        setSkills(updatedSkills)
        saveSkills(updatedSkills, user?.id)
        setIsEditing(false)
        setEditingId(null)
    }

    const handleDelete = (id: string) => {
        if (window.confirm('Delete this skill? This cannot be undone.')) {
            const newSkills = skills.filter(s => s.id !== id)
            setSkills(newSkills)
            saveSkills(newSkills, user?.id)
        }
    }

    const startEdit = (skill?: AgentSkill) => {
        if (skill) {
            setEditingId(skill.id)
            setFormData({ ...skill })
        } else {
            setEditingId(null)
            setFormData({
                id: '',
                name: '',
                description: '',
                instructions: '# SKILL LOGIC\n\n1. Check surroundings...\n2. If [condition], use [tool]...',
                tools: []
            })
        }
        setIsEditing(true)
    }

    const toggleTool = (toolId: string) => {
        const current = formData.tools || []
        if (current.includes(toolId)) {
            setFormData({ ...formData, tools: current.filter(t => t !== toolId) })
        } else {
            setFormData({ ...formData, tools: [...current, toolId] })
        }
    }

    // Theme Colors
    const themeColors: any = {
        slate: { primary: '#6366f1', secondary: '#818cf8', bg: '#0f172a' },
        emerald: { primary: '#10b981', secondary: '#34d399', bg: '#064e3b' },
        rose: { primary: '#f43f5e', secondary: '#fb7185', bg: '#4c0519' },
        amber: { primary: '#f59e0b', secondary: '#fbbf24', bg: '#451a03' },
        violet: { primary: '#8b5cf6', secondary: '#a78bfa', bg: '#2e1065' },
        cyan: { primary: '#06b6d4', secondary: '#22d3ee', bg: '#164e63' },
        sky: { primary: '#0ea5e9', secondary: '#38bdf8', bg: '#082f49' }
    }
    const currentTheme = themeColors[theme] || themeColors.slate

    // Styles
    const containerStyle = {
        maxWidth: '1200px',
        margin: '0 auto',
        padding: isMobile ? '24px 12px 56px' : '40px 20px',
        color: '#fff'
    }

    const cardStyle = {
        background: 'rgba(30, 41, 59, 0.4)',
        backdropFilter: 'blur(10px)',
        borderRadius: '16px',
        padding: '24px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        marginBottom: '20px',
        transition: 'all 0.3s ease'
    }

    if (isEditing) {
        return (
            <div style={containerStyle}>
                <div style={{ marginBottom: '24px', display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', opacity: 0.7 }} onClick={() => setIsEditing(false)}>
                    <RotateCcw size={16} /> Back to Skills
                </div>

                <h1 style={{ fontSize: '2rem', fontWeight: 800, marginBottom: '8px' }}>
                    {editingId ? 'Edit Skill Configuration' : 'Design New Skill'}
                </h1>
                <p style={{ opacity: 0.7, marginBottom: '32px' }}>
                    Compose atomic functions into a higher-level agent behavior.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '2fr 1fr', gap: '32px' }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                        {/* Main Editor */}
                        <div style={cardStyle}>
                            <h3 style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '20px', fontSize: '1.2rem' }}>
                                <Brain size={20} color={currentTheme.primary} />
                                Core Identity
                            </h3>

                            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
                                <div>
                                    <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.85rem', marginBottom: '6px', fontWeight: 600 }}>SKILL ID (JSON Key)</label>
                                    <input
                                        type="text"
                                        value={formData.id}
                                        disabled={!!editingId}
                                        onChange={e => setFormData({ ...formData, id: e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, '') })}
                                        style={{
                                            width: '100%', padding: '12px', borderRadius: '10px',
                                            background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)',
                                            color: '#fff', fontFamily: 'monospace'
                                        }}
                                        placeholder="e.g. evasive_maneuvers"
                                    />
                                </div>
                                <div>
                                    <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.85rem', marginBottom: '6px', fontWeight: 600 }}>DISPLAY NAME</label>
                                    <input
                                        type="text"
                                        value={formData.name}
                                        onChange={e => setFormData({ ...formData, name: e.target.value })}
                                        style={{
                                            width: '100%', padding: '12px', borderRadius: '10px',
                                            background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)',
                                            color: '#fff'
                                        }}
                                        placeholder="e.g. Evasive Maneuvers"
                                    />
                                </div>
                            </div>

                            <div style={{ marginBottom: '20px' }}>
                                <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.85rem', marginBottom: '6px', fontWeight: 600 }}>DESCRIPTION</label>
                                <input
                                    type="text"
                                    value={formData.description}
                                    onChange={e => setFormData({ ...formData, description: e.target.value })}
                                    style={{
                                        width: '100%', padding: '12px', borderRadius: '10px',
                                        background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)',
                                        color: '#fff'
                                    }}
                                    placeholder="Brief summary of what this skill achieves..."
                                />
                            </div>

                            <div>
                                <label style={{ display: 'block', color: '#94a3b8', fontSize: '0.85rem', marginBottom: '6px', fontWeight: 600 }}>LOGIC & INSTRUCTIONS (MARKDOWN)</label>
                                <textarea
                                    value={formData.instructions}
                                    onChange={e => setFormData({ ...formData, instructions: e.target.value })}
                                    rows={10}
                                    style={{
                                        width: '100%', padding: '16px', borderRadius: '10px',
                                        background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)',
                                        color: '#cbd5e1', fontFamily: 'monospace', lineHeight: 1.5, resize: 'vertical'
                                    }}
                                    placeholder="# INSTRUCTIONS&#10;1. Analyze surroundings using scan...&#10;2. Calculate optimal path..."
                                />
                                <p style={{ marginTop: '8px', fontSize: '0.8rem', color: '#64748b' }}>
                                    These instructions will be injected into the agent's system prompt when this skill is equipped.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                        {/* Tools Selection */}
                        <div style={cardStyle}>
                            <h3 style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '20px', fontSize: '1.2rem' }}>
                                <Zap size={20} color={currentTheme.primary} />
                                Included Tools
                            </h3>
                            <p style={{ fontSize: '0.9rem', color: '#94a3b8', marginBottom: '16px' }}>
                                Select the atomic functions available to the agent when executing this skill.
                            </p>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                {ATOMIC_SKILLS.map(tool => {
                                    const isSelected = formData.tools?.includes(tool.id)
                                    const ToolIcon = tool.icon
                                    return (
                                        <div
                                            key={tool.id}
                                            onClick={() => toggleTool(tool.id)}
                                            style={{
                                                padding: '12px',
                                                borderRadius: '12px',
                                                background: isSelected ? `${tool.color}15` : 'rgba(255,255,255,0.03)',
                                                border: isSelected ? `1px solid ${tool.color}` : '1px solid rgba(255,255,255,0.05)',
                                                cursor: 'pointer',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '12px',
                                                transition: 'all 0.2s'
                                            }}
                                        >
                                            <div style={{
                                                width: '24px', height: '24px', borderRadius: '50%', border: '1px solid rgba(255,255,255,0.2)',
                                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                background: isSelected ? tool.color : 'transparent'
                                            }}>
                                                {isSelected && <CheckCircle size={16} color="#000" />}
                                            </div>
                                            <div style={{
                                                width: '32px', height: '32px', borderRadius: '8px', background: `${tool.color}20`, color: tool.color,
                                                display: 'flex', alignItems: 'center', justifyContent: 'center'
                                            }}>
                                                <ToolIcon size={18} />
                                            </div>
                                            <div>
                                                <div style={{ fontWeight: 600, fontSize: '0.9rem' }}>{tool.name}</div>
                                                <div style={{ fontSize: '0.75rem', opacity: 0.6 }}>{tool.energyCost} Energy • {tool.cooldown}ms</div>
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        </div>

                        {/* Actions */}
                        <div style={{ display: 'flex', gap: '12px' }}>
                            <button
                                onClick={handleSave}
                                style={{
                                    flex: 1, padding: '16px', borderRadius: '12px',
                                    background: currentTheme.primary, border: 'none',
                                    color: '#0f172a', fontWeight: 700,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                                    cursor: 'pointer', fontSize: '1rem',
                                    boxShadow: `0 10px 20px -5px ${currentTheme.primary}40`
                                }}
                            >
                                <Save size={20} /> Save Skill
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    // View Mode
    return (
        <div style={containerStyle}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: isMobile ? '28px' : '40px', flexWrap: 'wrap', gap: '20px' }}>
                <div>
                    <h1 style={{ fontSize: isMobile ? '2rem' : '2.5rem', fontWeight: '700', marginBottom: '10px', lineHeight: 1.2, display: 'flex', alignItems: 'center', gap: '16px' }}>
                        <Brain color={currentTheme.primary} size={40} />
                        Agent Skills
                    </h1>
                    <p style={{ opacity: '0.8', fontSize: isMobile ? '1rem' : '1.1rem', maxWidth: '600px' }}>
                        Define modular capabilities and strategies for your autonomous agents.
                    </p>
                </div>
                <button
                    id="new-skill-btn"
                    onClick={() => startEdit()}
                    style={{
                        background: `linear-gradient(45deg, ${currentTheme.primary}, ${currentTheme.secondary})`,
                        color: '#0f172a',
                        padding: '12px 24px',
                        borderRadius: '25px',
                        fontSize: '1rem',
                        fontWeight: '600',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: '8px',
                        border: 'none',
                        cursor: 'pointer',
                        boxShadow: `0 4px 15px ${currentTheme.primary}40`
                    }}
                >
                    <Plus size={20} /> New Skill
                </button>
            </div>

            {/* Guide Panel */}
            <div
                id="skill-architecture-guide"
                style={{
                    ...cardStyle,
                    background: 'rgba(15, 23, 42, 0.6)',
                }}
            >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ padding: '6px 12px', borderRadius: '100px', border: '1px solid rgba(255,255,255,0.2)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <Book size={14} /> KNOWLEDGE BASE
                        </div>
                        <h2 style={{ fontSize: '1.2rem', fontWeight: 700, margin: 0 }}>Skill Architecture</h2>
                    </div>
                    <button
                        id="guide-toggle-btn"
                        onClick={() => setShowGuide(!showGuide)}
                        style={{ background: 'transparent', border: 'none', color: '#94a3b8', cursor: 'pointer', fontWeight: 600, fontSize: '0.9rem' }}
                    >
                        {showGuide ? 'Hide' : 'Show'}
                    </button>
                </div>

                <AnimatePresence>
                    {showGuide && (
                        <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            style={{ overflow: 'hidden' }}
                        >
                            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(3, 1fr)', gap: '20px', paddingTop: '10px' }}>
                                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '12px' }}>
                                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#f472b6' }}>
                                        <Layers size={18} /> 1. Composition
                                    </h4>
                                    <p style={{ fontSize: '0.9rem', color: '#94a3b8', lineHeight: 1.5 }}>
                                        Skills are built by selecting specific <strong>Tools</strong> (executable functions) that the agent is allowed to use.
                                    </p>
                                </div>
                                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '12px' }}>
                                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#38bdf8' }}>
                                        <FileText size={18} /> 2. Instructions
                                    </h4>
                                    <p style={{ fontSize: '0.9rem', color: '#94a3b8', lineHeight: 1.5 }}>
                                        You write the logic in natural language. This becomes the "System Prompt" for that specific skill mode.
                                    </p>
                                </div>
                                <div style={{ background: 'rgba(255,255,255,0.03)', padding: '16px', borderRadius: '12px' }}>
                                    <h4 style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px', color: '#4ade80' }}>
                                        <Cpu size={18} /> 3. Execution
                                    </h4>
                                    <p style={{ fontSize: '0.9rem', color: '#94a3b8', lineHeight: 1.5 }}>
                                        The agent executes your instructions using the tools. It manages energy and cooldowns automatically.
                                    </p>
                                </div>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>

            {/* Skills Grid */}
            <div id="skills-grid" style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fill, minmax(340px, 1fr))', gap: '24px' }}>
                {skills.map(skill => (
                    <motion.div
                        key={skill.id}
                        layout
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        style={{
                            ...cardStyle,
                            marginBottom: 0,
                            display: 'flex',
                            flexDirection: 'column',
                            justifyContent: 'space-between',
                            height: '100%',
                            border: '1px solid rgba(255,255,255,0.08)',
                            background: 'rgba(30, 41, 59, 0.4)'
                        }}
                        whileHover={{ y: -5, boxShadow: '0 10px 30px -10px rgba(0,0,0,0.5)' }}
                    >
                        <div>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                                <div style={{
                                    width: '48px', height: '48px', borderRadius: '12px',
                                    background: `linear-gradient(135deg, ${currentTheme.primary}20, ${currentTheme.primary}05)`,
                                    border: `1px solid ${currentTheme.primary}30`,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    color: currentTheme.primary
                                }}>
                                    <Terminal size={24} />
                                </div>
                                <div style={{
                                    padding: '4px 8px', borderRadius: '4px', background: 'rgba(255,255,255,0.05)',
                                    fontSize: '0.75rem', fontFamily: 'monospace', color: '#64748b'
                                }}>
                                    {skill.id}
                                </div>
                            </div>

                            <h3 style={{ fontSize: '1.4rem', fontWeight: 700, marginBottom: '8px' }}>{skill.name}</h3>
                            <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: 1.5, marginBottom: '20px', minHeight: '40px' }}>
                                {skill.description}
                            </p>

                            <div style={{ marginBottom: '24px' }}>
                                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#64748b', marginBottom: '8px', textTransform: 'uppercase' }}>
                                    Included Tools
                                </div>
                                <div id="skill-card-tools" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                                    {skill.tools.map(tid => {
                                        const tool = ATOMIC_SKILLS.find(t => t.id === tid)
                                        if (!tool) return null
                                        const ToolIcon = tool.icon
                                        return (
                                            <div key={tid} style={{
                                                display: 'flex', alignItems: 'center', gap: '6px',
                                                background: 'rgba(0,0,0,0.3)', padding: '6px 10px', borderRadius: '6px',
                                                border: '1px solid rgba(255,255,255,0.05)', fontSize: '0.8rem',
                                                color: '#cbd5e1'
                                            }}>
                                                <ToolIcon size={14} color={tool.color} />
                                                {tool.name}
                                            </div>
                                        )
                                    })}
                                    {skill.tools.length === 0 && <span style={{ color: '#64748b', fontSize: '0.9rem' }}>None</span>}
                                </div>
                            </div>
                        </div>

                        <div style={{ display: 'flex', gap: '12px', paddingTop: '20px', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                            <button
                                onClick={() => startEdit(skill)}
                                style={{
                                    flex: 1, padding: '10px', borderRadius: '8px',
                                    background: 'rgba(255,255,255,0.05)', border: 'none',
                                    color: '#fff', cursor: 'pointer', fontWeight: 600,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px',
                                    transition: 'all 0.2s'
                                }}
                            >
                                <Code size={16} /> Edit
                            </button>
                            <button
                                onClick={() => handleDelete(skill.id)}
                                style={{
                                    padding: '10px', borderRadius: '8px',
                                    background: 'rgba(255, 107, 107, 0.1)', border: 'none',
                                    color: '#ff6b6b', cursor: 'pointer',
                                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                                }}
                            >
                                <Trash2 size={16} />
                            </button>
                        </div>
                    </motion.div>
                ))}

                {skills.length === 0 && (
                    <div style={{
                        gridColumn: '1 / -1',
                        padding: '60px', textAlign: 'center', color: '#64748b',
                        background: 'rgba(30, 41, 59, 0.2)', borderRadius: '24px',
                        border: '2px dashed rgba(255,255,255,0.05)'
                    }}>
                        <Brain size={48} style={{ marginBottom: '16px', opacity: 0.5 }} />
                        <h3 style={{ fontSize: '1.5rem', marginBottom: '8px', color: '#94a3b8' }}>No Skills Found</h3>
                        <p>Create your first agent skill to get started.</p>
                    </div>
                )}
            </div>
        </div>
    )
}

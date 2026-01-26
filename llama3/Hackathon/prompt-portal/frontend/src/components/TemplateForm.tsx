import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Tag,
  AlignLeft,
  Code,
  Check,
  Save,
  AlertTriangle,
  Info,
  GitBranch,
  ToggleRight,
  ToggleLeft,
  Loader2,
  Sparkles
} from 'lucide-react'

type Props = {
  initial?: { title: string; description?: string; content: string; is_active: boolean; version: number }
  onSubmit: (data: { title: string; description?: string; content: string; is_active: boolean; version: number }) => Promise<void>
}

export default function TemplateForm({ initial, onSubmit }: Props) {
  const [title, setTitle] = useState(initial?.title || '')
  const [description, setDescription] = useState(initial?.description || '')
  const [content, setContent] = useState(initial?.content || '')
  const [isActive, setIsActive] = useState(initial?.is_active ?? true)
  const [version, setVersion] = useState(initial?.version || 1)
  const [err, setErr] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await onSubmit({ title, description, content, is_active: isActive, version })
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to save template')
    } finally {
      setIsSubmitting(false)
    }
  }

  const containerVariants: any = {
    hidden: { opacity: 0, y: 20 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } }
  }

  const fieldStyle = {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '10px',
    marginBottom: '24px'
  }

  const labelStyle = {
    fontSize: '0.85rem',
    fontWeight: 700,
    color: 'rgba(255, 255, 255, 0.7)',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em'
  }

  const inputStyle = {
    width: '100%',
    padding: '14px 18px',
    borderRadius: '12px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    background: 'rgba(15, 23, 42, 0.4)',
    color: '#f1f5f9',
    fontSize: '1rem',
    outline: 'none',
    transition: 'all 0.2s ease'
  }

  const textareaStyle = {
    ...inputStyle,
    minHeight: '100px',
    lineHeight: '1.6',
    resize: 'vertical' as const
  }

  const codeAreaStyle = {
    ...textareaStyle,
    minHeight: '300px',
    fontFamily: '"Fira Code", "JetBrains Mono", monospace',
    fontSize: '0.9rem',
    background: 'rgba(15, 23, 42, 0.6)'
  }

  const goodPlaceholderText = `# ROLE: MAZE NAVIGATOR
You are an autonomous drone inside a hazardous environment.
Objective: Reach the Exit (usually 13, 13) and collect Oxygen canisters.

# RULES:
1. ALWAYS respond with valid JSON only.
2. Movement: Move toward path (0), avoid walls (1).
3. Efficiency: Prioritize moves that reduce distance to Exit (X, Y).
4. Oxygen: If a path to oxygen is visible, prioritize it to maximize score.

# RESPONSE FORMAT:
{"action": "move", "direction": "north" | "south" | "east" | "west"}
OR
{"action": "use_skill", "skill": "ping" | "sprint" | "scan"}

# INPUT:
You will receive JSON telemetry containing:
- status (x, y, energy, oxygen, exit)
- surroundings (north, south, east, west)
- available_skills`

  const badPlaceholderText = `# ROLE: IMPROVISER
Write a vivid narrative of your journey through the maze.

# IMPORTANT:
- Explain every thought step-by-step in Markdown.
- Respond in YAML with multiple actions per turn.
- Add commentary and a concluding paragraph.

# OUTPUT:
Give a long, descriptive answer. Do NOT use JSON.
`

  return (
    <motion.form
      variants={containerVariants}
      initial="hidden"
      animate="visible"
      onSubmit={submit}
      style={{
        background: 'rgba(30, 41, 59, 0.4)',
        backdropFilter: 'blur(16px)',
        borderRadius: '24px',
        padding: '32px',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
        width: '100%'
      }}
    >
      {err && (
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          style={{
            background: 'rgba(239, 68, 68, 0.1)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: '12px',
            padding: '14px 18px',
            color: '#fca5a5',
            marginBottom: '24px',
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            fontSize: '0.9rem'
          }}
        >
          <AlertTriangle size={20} />
          {err}
        </motion.div>
      )}

      <div style={fieldStyle}>
        <label style={labelStyle}>
          <Tag size={16} className="text-indigo-400" />
          Template Title
        </label>
        <input
          value={title}
          onChange={e => setTitle(e.target.value)}
          required
          style={inputStyle}
          placeholder="e.g., Maze Navigator Pro"
          className="focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        />
      </div>

      <div style={fieldStyle}>
        <label style={labelStyle}>
          <AlignLeft size={16} className="text-indigo-400" />
          Description
        </label>
        <textarea
          value={description}
          onChange={e => setDescription(e.target.value)}
          style={textareaStyle}
          placeholder="What does this template achieve?"
        />
      </div>

      <div style={fieldStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
          <label style={labelStyle}>
            <Code size={16} className="text-indigo-400" />
            Prompt Content
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              type="button"
              onClick={() => setContent(goodPlaceholderText)}
              style={{
                padding: '6px 12px',
                borderRadius: '8px',
                background: 'rgba(16, 185, 129, 0.15)',
                border: '1px solid rgba(16, 185, 129, 0.2)',
                color: '#34d399',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <Sparkles size={14} />
              Use Good
            </motion.button>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              type="button"
              onClick={() => setContent(badPlaceholderText)}
              style={{
                padding: '6px 12px',
                borderRadius: '8px',
                background: 'rgba(244, 63, 94, 0.15)',
                border: '1px solid rgba(244, 63, 94, 0.2)',
                color: '#fda4af',
                fontSize: '0.75rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              <AlertTriangle size={14} />
              Use Bad
            </motion.button>
          </div>
        </div>
        <textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          style={codeAreaStyle}
          placeholder="System instructions and game logic..."
          required
        />
        <div style={{
          marginTop: '10px',
          fontSize: '0.8rem',
          color: 'rgba(148, 163, 184, 0.7)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          background: 'rgba(255,255,255,0.03)',
          padding: '10px 14px',
          borderRadius: '10px'
        }}>
          <Info size={16} className="text-blue-400" />
          Use {'{variable_name}'} syntax for dynamic injection.
        </div>
      </div>

      <div style={{
        display: 'flex',
        gap: '32px',
        marginBottom: '32px',
        background: 'rgba(15, 23, 42, 0.2)',
        padding: '20px',
        borderRadius: '16px',
        border: '1px solid rgba(255, 255, 255, 0.05)'
      }}>
        <div
          onClick={() => setIsActive(!isActive)}
          style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer' }}
        >
          {isActive ? <ToggleRight size={32} className="text-indigo-400" /> : <ToggleLeft size={32} className="text-gray-500" />}
          <span style={{ fontSize: '0.9rem', fontWeight: 600, color: isActive ? '#f1f5f9' : '#94a3b8' }}>
            Active Status
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <GitBranch size={20} className="text-indigo-400" />
          <label style={{ fontSize: '0.9rem', fontWeight: 600 }}>Version</label>
          <input
            type="number"
            value={version}
            onChange={e => setVersion(parseInt(e.target.value || '1'))}
            min={1}
            style={{
              width: '60px',
              padding: '6px 10px',
              borderRadius: '8px',
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(15, 23, 42, 0.3)',
              color: '#fff',
              textAlign: 'center'
            }}
          />
        </div>
      </div>

      <motion.button
        whileHover={{ scale: 1.01, boxShadow: '0 10px 25px -5px rgba(99, 102, 241, 0.4)' }}
        whileTap={{ scale: 0.99 }}
        type="submit"
        disabled={isSubmitting}
        style={{
          width: '100%',
          padding: '16px',
          borderRadius: '14px',
          border: 'none',
          background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
          color: 'white',
          fontSize: '1rem',
          fontWeight: 700,
          cursor: isSubmitting ? 'not-allowed' : 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '10px',
          opacity: isSubmitting ? 0.7 : 1
        }}
      >
        {isSubmitting ? <Loader2 size={20} className="animate-spin" /> : <Save size={20} />}
        {isSubmitting ? 'Saving Template...' : 'Save Template'}
      </motion.button>
    </motion.form>
  )
}

import { useState } from 'react'

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

  const formStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '20px',
    padding: '40px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    boxShadow: '0 20px 40px rgba(0, 0, 0, 0.1)',
    maxWidth: '100%'
  }

  const fieldGroupStyle = {
    marginBottom: '30px'
  }

  const labelStyle = {
    fontSize: '1rem',
    fontWeight: '600',
    color: 'white',
    marginBottom: '8px',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  }

  const inputStyle = {
    width: '100%',
    padding: '15px 20px',
    borderRadius: '12px',
    border: '2px solid rgba(255, 255, 255, 0.2)',
    background: 'rgba(255, 255, 255, 0.1)',
    color: 'white',
    fontSize: '1rem',
    fontFamily: 'Inter, system-ui, sans-serif',
    transition: 'all 0.3s ease',
    outline: 'none'
  }

  const textareaStyle = {
    ...inputStyle,
    resize: 'vertical' as const,
    minHeight: '60px',
    fontFamily: 'Monaco, Consolas, "Lucida Console", monospace',
    lineHeight: '1.5'
  }

  const promptTextareaStyle = {
    ...textareaStyle,
    minHeight: '200px',
    fontSize: '0.95rem'
  }

  const errorStyle = {
    background: 'rgba(255, 107, 107, 0.2)',
    border: '1px solid rgba(255, 107, 107, 0.4)',
    borderRadius: '12px',
    padding: '15px 20px',
    color: '#ff6b6b',
    marginBottom: '25px',
    display: 'flex',
    alignItems: 'center',
    gap: '10px'
  }

  const controlsRowStyle = {
    display: 'flex',
    gap: '30px',
    alignItems: 'center',
    marginBottom: '30px',
    flexWrap: 'wrap' as const
  }

  const checkboxContainerStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    cursor: 'pointer'
  }

  const checkboxStyle = {
    width: '20px',
    height: '20px',
    cursor: 'pointer',
    accentColor: '#4ecdc4'
  }

  const versionContainerStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '10px'
  }

  const versionInputStyle = {
    width: '80px',
    padding: '10px 15px',
    borderRadius: '8px',
    border: '2px solid rgba(255, 255, 255, 0.2)',
    background: 'rgba(255, 255, 255, 0.1)',
    color: 'white',
    fontSize: '1rem',
    outline: 'none',
    textAlign: 'center' as const
  }

  const buttonStyle = {
    background: isSubmitting 
      ? 'rgba(78, 205, 196, 0.6)' 
      : 'linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)',
    color: 'white',
    border: 'none',
    padding: '18px 40px',
    borderRadius: '12px',
    fontSize: '1.1rem',
    fontWeight: '600',
    cursor: isSubmitting ? 'not-allowed' : 'pointer',
    transition: 'all 0.3s ease',
    boxShadow: '0 10px 20px rgba(78, 205, 196, 0.3)',
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    width: '100%',
    justifyContent: 'center'
  }

  const placeholderText = `Example template for LAM maze navigation:

You are a Large Action Model (LAM) navigating a maze environment. Your goal is to help an agent reach the target while avoiding obstacles.

Context: {maze_state}
Current Position: {current_position}
Target Position: {target_position}

Instructions:
1. Analyze the maze layout and current position
2. Identify the optimal path to the target
3. Provide specific movement actions
4. Suggest hints if the agent is stuck
5. Recommend wall-breaking if necessary

Return your response as JSON:
{
  "actions": ["move_up", "move_right"],
  "hints": ["Check the path to the right", "Look for alternative routes"],
  "wall_breaks": [{"x": 5, "y": 3, "reason": "Creates shortest path"}],
  "reasoning": "Explanation of your strategy"
}`

  return (
    <form onSubmit={submit} style={formStyle}>
      {err && (
        <div style={errorStyle}>
          <i className="fas fa-exclamation-triangle"></i>
          {err}
        </div>
      )}

      <div style={fieldGroupStyle}>
        <label style={labelStyle}>
          <i className="fas fa-tag"></i>
          Template Title
        </label>
        <input 
          value={title} 
          onChange={e => setTitle(e.target.value)} 
          required 
          style={inputStyle}
          placeholder="Enter a descriptive title for your template"
          onFocus={(e) => {
            e.target.style.borderColor = 'rgba(78, 205, 196, 0.6)'
            e.target.style.boxShadow = '0 0 0 3px rgba(78, 205, 196, 0.2)'
          }}
          onBlur={(e) => {
            e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)'
            e.target.style.boxShadow = 'none'
          }}
        />
      </div>

      <div style={fieldGroupStyle}>
        <label style={labelStyle}>
          <i className="fas fa-align-left"></i>
          Description
        </label>
        <textarea 
          value={description} 
          onChange={e => setDescription(e.target.value)} 
          rows={3} 
          style={textareaStyle}
          placeholder="Briefly describe what this template does and when to use it"
          onFocus={(e) => {
            e.target.style.borderColor = 'rgba(78, 205, 196, 0.6)'
            e.target.style.boxShadow = '0 0 0 3px rgba(78, 205, 196, 0.2)'
          }}
          onBlur={(e) => {
            e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)'
            e.target.style.boxShadow = 'none'
          }}
        />
      </div>

      <div style={fieldGroupStyle}>
        <label style={labelStyle}>
          <i className="fas fa-code"></i>
          Prompt Template
        </label>
        <textarea 
          value={content} 
          onChange={e => setContent(e.target.value)} 
          rows={12} 
          style={promptTextareaStyle}
          placeholder={placeholderText}
          required
          onFocus={(e) => {
            e.target.style.borderColor = 'rgba(78, 205, 196, 0.6)'
            e.target.style.boxShadow = '0 0 0 3px rgba(78, 205, 196, 0.2)'
          }}
          onBlur={(e) => {
            e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)'
            e.target.style.boxShadow = 'none'
          }}
        />
        <div style={{ 
          marginTop: '8px', 
          fontSize: '0.9rem', 
          color: 'rgba(255, 255, 255, 0.6)',
          display: 'flex',
          alignItems: 'center',
          gap: '6px'
        }}>
          <i className="fas fa-info-circle"></i>
          Use {'{variable_name}'} for dynamic content placeholders
        </div>
      </div>

      <div style={controlsRowStyle}>
        <label style={checkboxContainerStyle}>
          <input 
            type="checkbox" 
            checked={isActive} 
            onChange={e => setIsActive(e.target.checked)}
            style={checkboxStyle}
          />
          <span style={{ fontSize: '1rem', fontWeight: '500', color: 'white' }}>
            <i className="fas fa-toggle-on" style={{ marginRight: '8px', color: isActive ? '#4ecdc4' : 'rgba(255, 255, 255, 0.5)' }}></i>
            Active Template
          </span>
        </label>

        <div style={versionContainerStyle}>
          <label style={{ fontSize: '1rem', fontWeight: '500', color: 'white' }}>
            <i className="fas fa-code-branch" style={{ marginRight: '8px' }}></i>
            Version
          </label>
          <input 
            type="number" 
            value={version} 
            onChange={e => setVersion(parseInt(e.target.value || '1'))} 
            min={1}
            style={versionInputStyle}
            onFocus={(e) => {
              e.target.style.borderColor = 'rgba(78, 205, 196, 0.6)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)'
            }}
          />
        </div>
      </div>

      <button 
        type="submit" 
        style={buttonStyle}
        disabled={isSubmitting}
        onMouseOver={(e) => {
          if (!isSubmitting) {
            e.currentTarget.style.transform = 'translateY(-2px)'
            e.currentTarget.style.boxShadow = '0 15px 30px rgba(78, 205, 196, 0.4)'
          }
        }}
        onMouseOut={(e) => {
          if (!isSubmitting) {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = '0 10px 20px rgba(78, 205, 196, 0.3)'
          }
        }}
      >
        {isSubmitting ? (
          <>
            <i className="fas fa-spinner fa-spin"></i>
            Saving Template...
          </>
        ) : (
          <>
            <i className="fas fa-save"></i>
            Save Template
          </>
        )}
      </button>
    </form>
  )
}

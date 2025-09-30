import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { templatesAPI } from '../api'
import { useIsMobile } from '../hooks/useIsMobile'

type Template = {
  id: number
  title: string
  description?: string
  content: string
  is_active: boolean
  version: number
  created_at: string
  updated_at: string
  user_id: number
}

export default function TemplateView() {
  const { id } = useParams()
  const isMobile = useIsMobile()
  const [tpl, setTpl] = useState<Template | null>(null)
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    (async () => {
      try {
        setLoading(true)
        const res = await templatesAPI.getTemplatePublic(parseInt(id!))
        setTpl(res.data)
      } catch (e: any) {
        setErr(e?.response?.data?.detail || 'Failed to load template')
      } finally {
        setLoading(false)
      }
    })()
  }, [id])

  const containerStyle = {
    maxWidth: '900px',
    margin: '0 auto',
    padding: isMobile ? '24px 12px 56px' : '40px 20px'
  }

  const cardStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '15px',
    padding: '25px',
    border: '1px solid rgba(255, 255, 255, 0.2)'
  }

  if (loading) return (
    <div style={containerStyle}>
      <div style={{ textAlign: 'center', padding: 40 }}>
        <i className="fas fa-spinner fa-spin" style={{ fontSize: '1.8rem' }} /> Loading template...
      </div>
    </div>
  )

  if (err) return (
    <div style={containerStyle}>
      <div style={{ textAlign: 'center', color: '#ff6b6b' }}>{err}</div>
    </div>
  )

  if (!tpl) return null

  return (
    <div style={containerStyle}>
      <div style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0, fontSize: isMobile ? '1.8rem' : '2.2rem' }}>
          <i className="fas fa-file-code" style={{ marginRight: 10 }} />
          {tpl.title}
        </h1>
        <div style={{ opacity: 0.75, marginTop: 6 }}>Version {tpl.version} • Updated {new Date(tpl.updated_at).toLocaleString()}</div>
      </div>
      <div style={cardStyle as any}>
        {tpl.description && (
          <p style={{ opacity: 0.9, marginTop: 0 }}>{tpl.description}</p>
        )}
        <div style={{
          background: 'rgba(0, 0, 0, 0.35)',
          borderRadius: 10,
          padding: 16,
          fontFamily: 'Monaco, Consolas, monospace',
          fontSize: '0.95rem',
          lineHeight: 1.5,
          border: '1px solid rgba(255,255,255,0.15)'
        }}>
          <pre style={{ margin: 0, whiteSpace: 'pre-wrap', color: 'rgba(255,255,255,0.95)' }}>{tpl.content}</pre>
        </div>
      </div>
    </div>
  )
}

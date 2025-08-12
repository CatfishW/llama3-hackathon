import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import TemplateForm from '../components/TemplateForm'
import { api } from '../api'

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

export default function TemplateEdit() {
  const { id } = useParams()
  const nav = useNavigate()
  const [item, setItem] = useState<Template | null>(null)

  useEffect(() => {
    (async () => {
      const res = await api.get('/api/templates/' + id)
      setItem(res.data)
    })()
  }, [id])

  async function onSubmit(data: any) {
    await api.patch('/api/templates/' + id, data)
    nav('/templates')
  }

  const containerStyle = {
    maxWidth: '900px',
    margin: '0 auto',
    padding: '40px 20px',
    minHeight: 'calc(100vh - 200px)'
  }

  const headerStyle = {
    textAlign: 'center' as const,
    marginBottom: '40px'
  }

  const titleStyle = {
    fontSize: '2.5rem',
    fontWeight: '700',
    color: 'white',
    marginBottom: '10px',
    background: 'linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text'
  }

  const subtitleStyle = {
    fontSize: '1.1rem',
    color: 'rgba(255, 255, 255, 0.8)',
    fontWeight: '400'
  }

  const loadingStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '50vh',
    fontSize: '1.2rem',
    color: 'rgba(255, 255, 255, 0.8)',
    gap: '15px'
  }

  if (!item) return (
    <div style={containerStyle}>
      <div style={loadingStyle}>
        <i className="fas fa-spinner fa-spin" style={{ fontSize: '1.5rem', color: '#4ecdc4' }}></i>
        Loading template...
      </div>
    </div>
  )

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={titleStyle}>
          <i className="fas fa-edit" style={{ marginRight: '15px', color: '#4ecdc4' }}></i>
          Edit Template
        </h1>
        <p style={subtitleStyle}>
          Refine and improve your prompt template for better LAM performance
        </p>
      </div>
      <TemplateForm
        initial={{
          title: item.title, description: item.description, content: item.content,
          is_active: item.is_active, version: item.version
        }}
        onSubmit={onSubmit}
      />
    </div>
  )
}

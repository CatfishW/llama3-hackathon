import TemplateForm from '../components/TemplateForm'
import { api } from '../api'
import { useNavigate } from 'react-router-dom'
import { useIsMobile } from '../hooks/useIsMobile'

export default function NewTemplate() {
  const nav = useNavigate()
  const isMobile = useIsMobile()
  async function onSubmit(data: any) {
    await api.post('/api/templates', data)
    nav('/templates')
  }

  const containerStyle = {
    maxWidth: '900px',
    margin: '0 auto',
    padding: isMobile ? '28px 14px 60px' : '40px 20px',
    minHeight: 'calc(100vh - 200px)'
  }

  const headerStyle = {
    textAlign: 'center' as const,
    marginBottom: '40px'
  }

  const titleStyle = {
    fontSize: isMobile ? '2rem':'2.5rem',
    fontWeight: '700',
    color: 'white',
    marginBottom: '10px',
    background: 'linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text'
  }

  const subtitleStyle = {
    fontSize: isMobile ? '1rem':'1.1rem',
    color: 'rgba(255, 255, 255, 0.8)',
    fontWeight: '400'
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={titleStyle}>
          <i className="fas fa-magic" style={{ marginRight: '15px', color: '#4ecdc4' }}></i>
          Create New Template
        </h1>
        <p style={subtitleStyle}>
          Design powerful prompt templates for Large Action Models in maze environments
        </p>
      </div>
      <TemplateForm onSubmit={onSubmit} />
    </div>
  )
}

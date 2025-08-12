import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Navbar() {
  const { user, logout } = useAuth()
  const location = useLocation()
  const [templates, setTemplates] = useState<Array<{id:number; title:string}>>([])
  const [selectedId, setSelectedId] = useState<number | ''>('')
  const [sessionId, setSessionId] = useState<string>('')
  const [publishing, setPublishing] = useState(false)
  const [status, setStatus] = useState<string>('')

  useEffect(() => {
    if (!user) return
    ;(async () => {
      try {
        const res = await api.get('/api/templates')
        setTemplates(res.data.map((t: any) => ({ id: t.id, title: t.title })))
      } catch {}
    })()
  }, [user])

  const publishTemplate = async () => {
    if (!selectedId) return
    setPublishing(true); setStatus('')
    try {
      const params = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : ''
      await api.post(`/api/mqtt/publish_template${params}`, { template_id: selectedId, reset: true })
      setStatus('Published!')
    } catch (e: any) {
      setStatus('Failed')
    } finally {
      setPublishing(false)
      setTimeout(()=>setStatus(''), 2000)
    }
  }

  const isActive = (path: string) => location.pathname === path

  const navStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
    padding: '15px 0',
    position: 'sticky' as const,
    top: 0,
    zIndex: 1000
  }

  const containerStyle = {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '0 20px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  }

  const logoStyle = {
    fontSize: '1.5rem',
    fontWeight: '700',
    color: 'white',
    textDecoration: 'none',
    display: 'flex',
    alignItems: 'center',
    gap: '10px'
  }

  const navLinksStyle = {
    display: 'flex',
    gap: '30px',
    alignItems: 'center'
  }

  const linkStyle = (active: boolean) => ({
    color: 'white',
    textDecoration: 'none',
    fontSize: '1rem',
    fontWeight: '500',
    padding: '8px 16px',
    borderRadius: '20px',
    transition: 'all 0.3s ease',
    background: active ? 'rgba(255, 255, 255, 0.2)' : 'transparent',
    border: active ? '1px solid rgba(255, 255, 255, 0.3)' : '1px solid transparent'
  })

  const buttonStyle = {
    background: 'rgba(255, 107, 107, 0.8)',
    color: 'white',
    border: 'none',
    padding: '10px 20px',
    borderRadius: '20px',
    fontSize: '0.9rem',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.3s ease'
  }

  const authLinksStyle = {
    display: 'flex',
    gap: '15px',
    alignItems: 'center'
  }

  return (
    <nav style={navStyle}>
      <div style={containerStyle}>
        <Link to="/" style={logoStyle}>
          <i className="fas fa-puzzle-piece"></i>
          LAM Maze Platform
        </Link>

        <div style={navLinksStyle}>
          {user ? (
            <>
              <Link
                to="/dashboard"
                style={linkStyle(isActive('/dashboard'))}
                onMouseOver={(e) => {
                  if (!isActive('/dashboard')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseOut={(e) => {
                  if (!isActive('/dashboard')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <i className="fas fa-tachometer-alt" style={{ marginRight: '8px' }}></i>
                Dashboard
              </Link>
              <Link
                to="/play"
                style={linkStyle(isActive('/play'))}
                onMouseOver={(e) => {
                  if (!isActive('/play')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseOut={(e) => {
                  if (!isActive('/play')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <i className="fas fa-gamepad" style={{ marginRight: '8px' }}></i>
                Play
              </Link>

              {/* Quick template publish controls */}
              <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                <select
                  value={selectedId}
                  onChange={(e)=> setSelectedId(e.target.value ? parseInt(e.target.value) : '')}
                  style={{ background:'rgba(255,255,255,0.1)', color:'#fff', border:'1px solid rgba(255,255,255,0.3)', borderRadius: 12, padding: '6px 10px' }}
                  title="Select template"
                >
                  <option value="">Select template…</option>
                  {templates.map(t => (
                    <option key={t.id} value={t.id} style={{ background:'#333' }}>{t.title}</option>
                  ))}
                </select>
                <input
                  value={sessionId}
                  onChange={(e)=>setSessionId(e.target.value)}
                  placeholder="session-id (optional)"
                  style={{ background:'rgba(255,255,255,0.1)', color:'#fff', border:'1px solid rgba(255,255,255,0.3)', borderRadius: 12, padding: '6px 10px' }}
                  title="Target a running Play session"
                />
                <button onClick={publishTemplate} disabled={!selectedId || publishing} style={{ ...buttonStyle, opacity: (!selectedId || publishing) ? 0.6 : 1 }} title="Publish template to LAM">
                  <i className="fas fa-upload" style={{ marginRight: 6 }} /> {publishing ? 'Publishing…' : 'Publish'}
                </button>
                {status && <span style={{ color:'#fff', opacity:.8 }}>{status}</span>}
              </div>

              <Link
                to="/templates"
                style={linkStyle(isActive('/templates'))}
                onMouseOver={(e) => {
                  if (!isActive('/templates')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseOut={(e) => {
                  if (!isActive('/templates')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <i className="fas fa-file-code" style={{ marginRight: '8px' }}></i>
                Templates
              </Link>
              <Link
                to="/leaderboard"
                style={linkStyle(isActive('/leaderboard'))}
                onMouseOver={(e) => {
                  if (!isActive('/leaderboard')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseOut={(e) => {
                  if (!isActive('/leaderboard')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <i className="fas fa-trophy" style={{ marginRight: '8px' }}></i>
                Leaderboard
              </Link>
              <Link
                to="/friends"
                style={linkStyle(isActive('/friends'))}
                onMouseOver={(e) => {
                  if (!isActive('/friends')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseOut={(e) => {
                  if (!isActive('/friends')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <i className="fas fa-users" style={{ marginRight: '8px' }}></i>
                Friends
              </Link>
              <Link
                to="/messages"
                style={linkStyle(isActive('/messages'))}
                onMouseOver={(e) => {
                  if (!isActive('/messages')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseOut={(e) => {
                  if (!isActive('/messages')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <i className="fas fa-comments" style={{ marginRight: '8px' }}></i>
                Messages
              </Link>
              <Link
                to="/test"
                style={linkStyle(isActive('/test'))}
                onMouseOver={(e) => {
                  if (!isActive('/test')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseOut={(e) => {
                  if (!isActive('/test')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <i className="fas fa-vial" style={{ marginRight: '8px' }}></i>
                Test
              </Link>
              
              {/* User Menu Dropdown */}
              <div style={{ position: 'relative', marginLeft: '10px' }}>
                <div style={authLinksStyle}>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '10px',
                    padding: '8px 12px',
                    borderRadius: '20px',
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.2)'
                  }}>
                    <div style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '50%',
                      background: 'linear-gradient(45deg, #4ecdc4, #44a08d)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: '0.9rem',
                      fontWeight: '600'
                    }}>
                      {user.email.charAt(0).toUpperCase()}
                    </div>
                    <span style={{ color: 'rgba(255, 255, 255, 0.9)', fontSize: '0.9rem', fontWeight: '500' }}>
                      {user.email.split('@')[0]}
                    </span>
                    <div style={{ display: 'flex', gap: '5px' }}>
                      <Link
                        to="/profile"
                        style={{
                          color: 'rgba(255, 255, 255, 0.8)',
                          fontSize: '0.9rem',
                          textDecoration: 'none',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.background = 'transparent'
                        }}
                        title="Profile"
                      >
                        <i className="fas fa-user"></i>
                      </Link>
                      <Link
                        to="/settings"
                        style={{
                          color: 'rgba(255, 255, 255, 0.8)',
                          fontSize: '0.9rem',
                          textDecoration: 'none',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.background = 'transparent'
                        }}
                        title="Settings"
                      >
                        <i className="fas fa-cog"></i>
                      </Link>
                      <button
                        onClick={logout}
                        style={{
                          background: 'transparent',
                          border: 'none',
                          color: 'rgba(255, 255, 255, 0.8)',
                          fontSize: '0.9rem',
                          cursor: 'pointer',
                          padding: '4px 8px',
                          borderRadius: '4px',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseOver={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 107, 107, 0.3)'
                          e.currentTarget.style.color = '#ff6b6b'
                        }}
                        onMouseOut={(e) => {
                          e.currentTarget.style.background = 'transparent'
                          e.currentTarget.style.color = 'rgba(255, 255, 255, 0.8)'
                        }}
                        title="Logout"
                      >
                        <i className="fas fa-sign-out-alt"></i>
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div style={authLinksStyle}>
              <Link
                to="/register"
                style={{
                  ...linkStyle(isActive('/register')),
                  background: 'rgba(78, 205, 196, 0.8)',
                  border: '1px solid rgba(78, 205, 196, 0.8)'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.background = 'rgba(78, 205, 196, 1)'
                  e.currentTarget.style.transform = 'translateY(-1px)'
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.background = 'rgba(78, 205, 196, 0.8)'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                <i className="fas fa-user-plus" style={{ marginRight: '8px' }}></i>
                Register
              </Link>
              <Link
                to="/login"
                style={linkStyle(isActive('/login'))}
                onMouseOver={(e) => {
                  if (!isActive('/login')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseOut={(e) => {
                  if (!isActive('/login')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <i className="fas fa-sign-in-alt" style={{ marginRight: '8px' }}></i>
                Login
              </Link>
            </div>
          )}
        </div>
      </div>
    </nav>
  )
}

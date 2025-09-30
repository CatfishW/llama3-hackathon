import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { leaderboardAPI } from '../api'
import { useIsMobile } from '../hooks/useIsMobile'

type Entry = {
  rank: number
  user_email: string
  template_title: string
  score: number
  session_id: string
  created_at: string
}

export default function Leaderboard() {
  const [items, setItems] = useState<Entry[]>([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [mode, setMode] = useState<'lam'|'manual'>('lam')
  const [participants, setParticipants] = useState<number | null>(null)
  const [registeredUsers, setRegisteredUsers] = useState<number | null>(null)
  const PAGE_SIZE = 50
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const isMobile = useIsMobile()
  
  // Theme state
  const [theme, setTheme] = useState<'default' | 'orange'>(() => {
    const saved = localStorage.getItem('webgame-theme')
    return (saved === 'orange' || saved === 'default') ? saved : 'default'
  })

  // Persist theme changes
  useEffect(() => {
    localStorage.setItem('webgame-theme', theme)
  }, [theme])

  // Theme configuration
  const themeConfig = {
    default: {
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      buttonPrimary: 'linear-gradient(45deg,#4ecdc4,#44a08d)',
      avatarGradient: 'linear-gradient(45deg, #4ecdc4, #44a08d)'
    },
    orange: {
      background: 'linear-gradient(135deg, #ff9a56 0%, #ff6b35 50%, #f7931e 100%)',
      buttonPrimary: 'linear-gradient(45deg,#ff8c42,#ff6b35)',
      avatarGradient: 'linear-gradient(45deg, #ff8c42, #ff6b35)'
    }
  }

  const currentTheme = themeConfig[theme]

  async function load(initial = false) {
    try {
      setLoading(true)
      const { data, total } = await leaderboardAPI.getLeaderboard(PAGE_SIZE, initial ? 0 : skip, mode)
      setTotal(total)
      if (initial) {
        setItems(data)
        setSkip(data.length)
      } else {
        setItems(prev => [...prev, ...data])
        setSkip(prev => prev + data.length)
      }
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to load leaderboard')
    } finally {
      setLoading(false)
    }
  }
  
  useEffect(() => { load(true) }, [mode])

  useEffect(() => {
    ;(async ()=>{
      try {
        const s = await leaderboardAPI.getStats()
        setParticipants(s.participants)
        setRegisteredUsers(s.registered_users)
      } catch {}
    })()
  }, [])

  const containerStyle = {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: isMobile ? '24px 12px 56px' : '40px 20px'
  }

  const headerStyle = {
    textAlign: 'center' as const,
    marginBottom: isMobile ? '28px' : '40px'
  }

  const tableContainerStyle: any = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '15px',
    padding: isMobile ? '18px 14px' : '30px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    overflowX: 'auto' as const,
    WebkitOverflowScrolling: 'touch'
  }

  const tableStyle = {
    width: '100%',
    borderCollapse: 'collapse' as const,
    color: 'white'
  }

  const thStyle = {
    padding: isMobile ? '10px 12px' : '15px 20px',
    textAlign: 'left' as const,
    borderBottom: '2px solid rgba(255, 255, 255, 0.2)',
    fontSize: isMobile ? '.85rem' : '1.1rem',
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.9)',
    whiteSpace: isMobile ? 'nowrap' : 'normal'
  }

  const tdStyle = {
    padding: isMobile ? '10px 12px' : '15px 20px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
    fontSize: isMobile ? '.85rem' : '1rem',
    whiteSpace: isMobile ? 'nowrap' : 'normal'
  }

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1: return '🥇'
      case 2: return '🥈'
      case 3: return '🥉'
      default: return `#${rank}`
    }
  }

  const getRankStyle = (rank: number) => {
    const baseStyle = {
      fontWeight: '700',
      fontSize: '1.1rem',
      padding: '8px 12px',
      borderRadius: '20px',
      display: 'inline-block',
      minWidth: '50px',
      textAlign: 'center' as const
    }

    switch (rank) {
      case 1:
        return { ...baseStyle, background: 'linear-gradient(45deg, #ffd700, #ffed4e)', color: '#333' }
      case 2:
        return { ...baseStyle, background: 'linear-gradient(45deg, #c0c0c0, #e8e8e8)', color: '#333' }
      case 3:
        return { ...baseStyle, background: 'linear-gradient(45deg, #cd7f32, #daa520)', color: 'white' }
      default:
        return { ...baseStyle, background: 'rgba(255, 255, 255, 0.1)', color: 'white' }
    }
  }

  return (
  <div style={{ minHeight: '100vh', background: currentTheme.background, color: 'white' }}>
      <div style={containerStyle}>
        <div style={headerStyle}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
      <h1 style={{ fontSize: isMobile ? '2.2rem':'3rem', fontWeight: '700', margin: 0, lineHeight:1.15 }}>
              🏆 Leaderboard
            </h1>
            {/* Theme Switcher */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '14px', opacity: 0.9 }}>Theme:</span>
              <select 
                value={theme} 
                onChange={(e) => setTheme(e.target.value as 'default' | 'orange')}
                style={{ 
                  padding: '4px 8px', 
                  borderRadius: '6px', 
                  background: 'rgba(255,255,255,0.1)', 
                  color: '#fff', 
                  border: '1px solid rgba(255,255,255,0.3)',
                  fontSize: '14px'
                }}
              >
                <option value="default" style={{ background: '#333' }}>Default Blue</option>
                <option value="orange" style={{ background: '#333' }}>Orange Sunset</option>
              </select>
            </div>
          </div>
          <div style={{ fontSize: isMobile ? '1rem':'1.1rem', opacity: 0.9, maxWidth: '820px', margin: '10px auto 0', lineHeight:1.45 }}>
            <div style={{ display:'flex', gap:16, justifyContent:'center', flexWrap:'wrap' }}>
              <div style={{ background:'rgba(0,0,0,0.25)', border:'1px solid rgba(255,255,255,0.25)', borderRadius:12, padding:'8px 12px' }}>
                Participants: <b>{participants!=null? participants : '—'}</b>
              </div>
              <div style={{ background:'rgba(0,0,0,0.25)', border:'1px solid rgba(255,255,255,0.25)', borderRadius:12, padding:'8px 12px' }}>
                Registered Users: <b>{registeredUsers!=null? registeredUsers : '—'}</b>
              </div>
            </div>
            {/* Mode toggle */}
            <div style={{ marginTop: 16, display:'flex', justifyContent:'center' }}>
              <div style={{ display:'inline-flex', background:'rgba(255,255,255,0.12)', border:'1px solid rgba(255,255,255,0.25)', borderRadius: 999, padding:4 }}>
                {(['lam','manual'] as const).map(m => (
                  <button key={m}
                    onClick={()=>setMode(m)}
                    style={{
                      padding: isMobile ? '6px 12px':'8px 16px',
                      borderRadius: 999,
                      border: 'none',
                      cursor: 'pointer',
                      color: '#fff',
                      background: mode===m ? (theme==='orange' ? 'linear-gradient(45deg,#ff8c42,#ff6b35)' : 'linear-gradient(45deg,#4ecdc4,#44a08d)') : 'transparent',
                      boxShadow: mode===m ? '0 2px 8px rgba(0,0,0,0.25)' : 'none',
                      transition: 'all .2s',
                      fontWeight: 700,
                      fontSize: isMobile ? '.9rem':'1rem',
                      minWidth: 120
                    }}>
                    {m==='lam' ? 'LAM Mode' : 'Manual Mode'}
                  </button>
                ))}
              </div>
            </div>
            <div style={{ marginTop:8, textAlign:'center', opacity:.85 }}>
              Viewing: <b>{mode==='lam' ? 'LAM Mode (LLM controls)' : 'Manual Mode (You control)'}</b>
            </div>
          </div>
        </div>

      {err && (
        <div style={{
          background: 'rgba(255, 107, 107, 0.2)',
          border: '1px solid rgba(255, 107, 107, 0.4)',
          borderRadius: '10px',
          padding: '15px',
          marginBottom: '20px',
          color: '#ff6b6b',
          textAlign: 'center'
        }}>
          <i className="fas fa-exclamation-triangle" style={{ marginRight: '8px' }}></i>
          {err}
        </div>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '60px' }}>
          <i className="fas fa-spinner fa-spin" style={{ fontSize: '2rem', marginBottom: '20px' }}></i>
          <p style={{ fontSize: '1.1rem', opacity: '0.8' }}>Loading leaderboard...</p>
        </div>
      ) : (
        <div style={tableContainerStyle}>
          {isMobile && items.length>0 && (
            <div style={{ fontSize: '.7rem', opacity:.65, marginBottom:8, textAlign:'right' }}>Swipe horizontally ↔ to see all columns</div>
          )}
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12, color:'rgba(255,255,255,0.85)'}}>
            <div>Total entries: <b>{total}</b></div>
            <div>Showing: <b>{items.length}</b></div>
          </div>
          {items.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '40px' }}>
              <i className="fas fa-trophy" style={{ fontSize: '3rem', marginBottom: '20px', opacity: '0.5' }}></i>
              <h3 style={{ marginBottom: '10px', fontSize: '1.5rem' }}>No entries yet</h3>
              <p style={{ opacity: '0.7' }}>Be the first to submit a template and score!</p>
            </div>
          ) : (
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>
                    <i className="fas fa-medal" style={{ marginRight: '8px' }}></i>
                    Rank
                  </th>
                  <th style={thStyle}>
                    <i className="fas fa-user" style={{ marginRight: '8px' }}></i>
                    User
                  </th>
                  <th style={thStyle}>
                    <i className="fas fa-file-code" style={{ marginRight: '8px' }}></i>
                    Template
                  </th>
                  <th style={thStyle}>
                    <i className="fas fa-star" style={{ marginRight: '8px' }}></i>
                    Score
                  </th>
                  <th style={thStyle}>
                    <i className="fas fa-gamepad" style={{ marginRight: '8px' }}></i>
                    Session
                  </th>
                  <th style={thStyle}>
                    <i className="fas fa-clock" style={{ marginRight: '8px' }}></i>
                    Date
                  </th>
                </tr>
              </thead>
              <tbody>
        {items.map((entry, index) => (
                  <tr 
          key={entry.session_id + '-' + index}
                    style={{
                      background: index % 2 === 0 ? 'rgba(255, 255, 255, 0.05)' : 'transparent',
                      transition: 'background-color 0.3s ease'
                    }}
                    onMouseOver={(e) => {
                      e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                    }}
                    onMouseOut={(e) => {
                      e.currentTarget.style.background = index % 2 === 0 ? 'rgba(255, 255, 255, 0.05)' : 'transparent'
                    }}
                  >
                    <td style={tdStyle}>
                      <span style={getRankStyle(entry.rank)}>
                        {getRankIcon(entry.rank)}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <div style={{ display: 'flex', alignItems: 'center' }}>
                        <div style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '50%',
                          background: currentTheme.avatarGradient,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          marginRight: '12px',
                          fontSize: '0.9rem',
                          fontWeight: '600'
                        }}>
                          {entry.user_email.charAt(0).toUpperCase()}
                        </div>
                        {entry.user_email}
                      </div>
                    </td>
                    <td style={tdStyle}>
                      <Link to={`/templates/view/${(entry as any).template_id}`} style={{
                        background: 'rgba(78, 205, 196, 0.2)',
                        border: '1px solid rgba(78, 205, 196, 0.4)',
                        borderRadius: '15px',
                        padding: '4px 12px',
                        fontSize: '0.9rem',
                        fontWeight: '500',
                        color: 'white',
                        textDecoration: 'none'
                      }}>
                        {entry.template_title}
                      </Link>
                    </td>
                    <td style={tdStyle}>
                      <span style={{
                        fontSize: '1.2rem',
                        fontWeight: '700',
                        color: '#ffd93d'
                      }}>
                        {entry.score}
                      </span>
                    </td>
                    <td style={tdStyle}>
                      <code style={{
                        background: 'rgba(255, 255, 255, 0.1)',
                        padding: '4px 8px',
                        borderRadius: '6px',
                        fontSize: '0.85rem',
                        fontFamily: 'monospace'
                      }}>
                        {entry.session_id.slice(0, 8)}...
                      </code>
                    </td>
                    <td style={tdStyle}>
                      <span style={{ opacity: '0.8' }}>
                        {new Date(entry.created_at).toLocaleDateString()} {' '}
                        <span style={{ fontSize: '0.9rem', opacity: '0.6' }}>
                          {new Date(entry.created_at).toLocaleTimeString()}
                        </span>
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Controls */}
      <div style={{ textAlign: 'center', marginTop: '30px', display:'flex', gap:12, justifyContent:'center', flexWrap:'wrap' }}>
        <button
          onClick={() => load(true)}
          disabled={loading}
          style={{
            background: currentTheme.buttonPrimary,
            color: 'white',
            border: 'none',
            padding: '12px 24px',
            borderRadius: '25px',
            fontSize: '1rem',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer',
            transition: 'all 0.3s ease',
            opacity: loading ? 0.6 : 1
          }}
          onMouseOver={(e) => {
            if (!loading) {
              e.currentTarget.style.background = theme === 'orange' ? '#ff8c42' : 'rgba(78, 205, 196, 1)'
              e.currentTarget.style.transform = 'translateY(-2px)'
            }
          }}
          onMouseOut={(e) => {
            if (!loading) {
              e.currentTarget.style.background = currentTheme.buttonPrimary
              e.currentTarget.style.transform = 'translateY(0)'
            }
          }}
        >
          <i className={`fas ${loading ? 'fa-spinner fa-spin' : 'fa-sync-alt'}`} style={{ marginRight: '8px' }}></i>
          {loading ? 'Refreshing...' : 'Refresh'}
        </button>

        {skip < total && (
          <button
            onClick={() => load(false)}
            disabled={loading}
            style={{
              background: 'linear-gradient(45deg,#36c,#59f)',
              color: 'white',
              border: 'none',
              padding: '12px 24px',
              borderRadius: '25px',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: loading ? 'not-allowed' : 'pointer',
              transition: 'all 0.3s ease',
              opacity: loading ? 0.6 : 1
            }}
          >
            <i className={`fas ${loading ? 'fa-spinner fa-spin' : 'fa-arrow-down'}`} style={{ marginRight: '8px' }}></i>
            {loading ? 'Loading...' : 'Load more'} ({skip}/{total})
          </button>
        )}
      </div>
    </div>
    </div>
  )
}

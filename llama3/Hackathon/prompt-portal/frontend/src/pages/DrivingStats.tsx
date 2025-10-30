// Driving Stats - Completely separate from maze leaderboard
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { drivingStatsAPI } from '../api'
import { useIsMobile } from '../hooks/useIsMobile'

type Entry = {
  rank: number
  user_email: string
  template_title: string
  score: number
  message_count: number
  duration_seconds: number
  session_id: string
  created_at: string
}

export default function DrivingStats() {
  const [items, setItems] = useState<Entry[]>([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [forceRefresh, setForceRefresh] = useState(0)
  const [participants, setParticipants] = useState<number | null>(null)
  const [registeredUsers, setRegisteredUsers] = useState<number | null>(null)
  const PAGE_SIZE = 50
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const isMobile = useIsMobile()
  
  // Theme state
  const [theme, setTheme] = useState<'default' | 'orange'>(() => {
    const saved = localStorage.getItem('driving-game-theme')
    return (saved === 'orange' || saved === 'default') ? saved : 'default'
  })

  // Persist theme changes
  useEffect(() => {
    localStorage.setItem('driving-game-theme', theme)
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
      setErr(null)
      
      console.log(`[DRIVING STATS PAGE] Loading data... initial=${initial}, skip=${initial ? 0 : skip}`)
      
      // Use dedicated drivingStatsAPI
      const { data, total } = await drivingStatsAPI.getLeaderboard(PAGE_SIZE, initial ? 0 : skip)
      
      console.log(`[DRIVING STATS PAGE] Received: total=${total}, entries=${data.length}`)
      if (data.length > 0) {
        console.log(`[DRIVING STATS PAGE] First entry:`, data[0])
      }
      
      setTotal(total)
      if (initial) {
        setItems(data)
        setSkip(data.length)
      } else {
        setItems(prev => [...prev, ...data])
        setSkip(prev => prev + data.length)
      }
    } catch (e: any) {
      console.error('[DRIVING STATS PAGE] Error loading data:', e)
      setErr(e?.response?.data?.detail || e?.message || 'Failed to load driving stats')
    } finally {
      setLoading(false)
    }
  }
  
  useEffect(() => { 
    load(true) 
  }, [forceRefresh])

  useEffect(() => {
    ;(async ()=>{
      try {
        const s = await drivingStatsAPI.getStats()
        setParticipants(s.participants)
        setRegisteredUsers(s.registered_users)
      } catch (err) {
        console.error('[DRIVING STATS PAGE] Error loading stats:', err)
      }
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
    minWidth: isMobile ? '800px' : '100%',
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
    whiteSpace: 'nowrap' as const
  }

  const tdStyle = {
    padding: isMobile ? '10px 12px' : '15px 20px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
    fontSize: isMobile ? '.85rem' : '1rem',
    whiteSpace: 'nowrap' as const
  }

  const buttonStyle = {
    background: currentTheme.buttonPrimary,
    color: 'white',
    border: 'none',
    padding: isMobile ? '10px 18px' : '12px 24px',
    borderRadius: '25px',
    fontSize: isMobile ? '.9rem' : '1rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'transform 0.2s ease, box-shadow 0.2s ease',
    boxShadow: '0 4px 15px rgba(0, 0, 0, 0.2)',
    marginTop: '20px'
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(1)}s`
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}m ${secs}s`
  }

  return (
    <div style={{ minHeight: '100vh', background: currentTheme.background, paddingBottom: isMobile ? '40px' : '60px' }}>
      <div style={containerStyle}>
        <div style={headerStyle}>
          <h1 style={{
            fontSize: isMobile ? '2rem' : '3rem',
            fontWeight: '700',
            marginBottom: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: isMobile ? '12px' : '15px'
          }}>
            <i className="fas fa-flag-checkered"></i>
            Driving Stats
          </h1>
          <p style={{
            fontSize: isMobile ? '.95rem' : '1.15rem',
            opacity: 0.9,
            maxWidth: '600px',
            margin: '0 auto'
          }}>
            Prompt Testing Game - Reach consensus with the AI!
          </p>
        </div>

        {/* Theme Selector */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'center', 
          gap: '10px',
          marginBottom: '20px',
          alignItems: 'center'
        }}>
          <label style={{ fontSize: '.95rem', fontWeight: '500' }}>Theme:</label>
          <select 
            value={theme}
            onChange={(e) => setTheme(e.target.value as 'default' | 'orange')}
            style={{
              padding: '8px 15px',
              borderRadius: '20px',
              border: '1px solid rgba(255, 255, 255, 0.3)',
              background: 'rgba(255, 255, 255, 0.1)',
              color: 'white',
              fontSize: '.9rem',
              cursor: 'pointer',
              backdropFilter: 'blur(10px)'
            }}
          >
            <option value="default" style={{ background: '#1a1a2e', color: 'white' }}>Default Blue</option>
            <option value="orange" style={{ background: '#1a1a2e', color: 'white' }}>Racing Orange</option>
          </select>
        </div>

        {/* Stats */}
        {(participants !== null || registeredUsers !== null) && (
          <div style={{
            display: 'flex',
            gap: isMobile ? '10px' : '15px',
            justifyContent: 'center',
            marginBottom: '25px',
            flexWrap: 'wrap'
          }}>
            {participants !== null && (
              <div style={{
                background: 'rgba(255, 255, 255, 0.15)',
                padding: isMobile ? '10px 20px' : '12px 24px',
                borderRadius: '25px',
                border: '1px solid rgba(255, 255, 255, 0.25)',
                fontSize: isMobile ? '.9rem' : '1rem',
                fontWeight: '600',
                backdropFilter: 'blur(8px)'
              }}>
                Participants: {participants}
              </div>
            )}
            {registeredUsers !== null && (
              <div style={{
                background: 'rgba(255, 255, 255, 0.15)',
                padding: isMobile ? '10px 20px' : '12px 24px',
                borderRadius: '25px',
                border: '1px solid rgba(255, 255, 255, 0.25)',
                fontSize: isMobile ? '.9rem' : '1rem',
                fontWeight: '600',
                backdropFilter: 'blur(8px)'
              }}>
                Registered Users: {registeredUsers}
              </div>
            )}
          </div>
        )}

        {/* Summary */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.12)',
          padding: isMobile ? '14px 18px' : '18px 24px',
          borderRadius: '15px',
          marginBottom: '25px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          backdropFilter: 'blur(10px)',
          flexWrap: 'wrap',
          gap: '10px'
        }}>
          <span style={{ fontSize: isMobile ? '.9rem' : '1.05rem', fontWeight: '600' }}>
            Total entries: <strong style={{ color: '#4ecdc4' }}>{total}</strong>
          </span>
          <span style={{ fontSize: isMobile ? '.85rem' : '1rem', opacity: 0.85 }}>
            Showing: <strong>{Math.min(skip, total)}</strong>
          </span>
        </div>

        {err && (
          <div style={{
            background: 'rgba(255, 107, 107, 0.2)',
            padding: '15px',
            borderRadius: '10px',
            marginBottom: '20px',
            border: '1px solid rgba(255, 107, 107, 0.5)'
          }}>
            {err}
          </div>
        )}

        {/* Table */}
        <div style={tableContainerStyle}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}><i className="fas fa-trophy" style={{ marginRight: '8px' }}></i>Rank</th>
                <th style={thStyle}><i className="fas fa-user" style={{ marginRight: '8px' }}></i>User</th>
                <th style={thStyle}><i className="fas fa-file-alt" style={{ marginRight: '8px' }}></i>Template</th>
                <th style={thStyle}><i className="fas fa-star" style={{ marginRight: '8px' }}></i>Score</th>
                <th style={thStyle}><i className="fas fa-comment" style={{ marginRight: '8px' }}></i>Messages</th>
                <th style={thStyle}><i className="fas fa-clock" style={{ marginRight: '8px' }}></i>Duration</th>
                <th style={thStyle}><i className="fas fa-calendar" style={{ marginRight: '8px' }}></i>Date</th>
              </tr>
            </thead>
            <tbody>
              {loading && items.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ ...tdStyle, textAlign: 'center', padding: '40px' }}>
                    <i className="fas fa-spinner fa-spin" style={{ marginRight: '10px' }}></i>
                    Loading...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ ...tdStyle, textAlign: 'center', padding: '40px' }}>
                    No driving game scores yet. Be the first to play!
                  </td>
                </tr>
              ) : (
                items.map((item) => {
                  const getRankStyle = () => {
                    if (item.rank === 1) return { fontSize: '1.5rem', color: '#FFD700' }
                    if (item.rank === 2) return { fontSize: '1.3rem', color: '#C0C0C0' }
                    if (item.rank === 3) return { fontSize: '1.2rem', color: '#CD7F32' }
                    return {}
                  }

                  const getInitial = (email: string) => email.charAt(0).toUpperCase()

                  return (
                    <tr key={`${item.session_id}-${item.created_at}`} style={{
                      transition: 'background 0.2s ease'
                    }}>
                      <td style={{ ...tdStyle, fontWeight: '700', ...getRankStyle() }}>
                        {item.rank <= 3 ? (
                          <span>
                            {item.rank === 1 && '🥇'}
                            {item.rank === 2 && '🥈'}
                            {item.rank === 3 && '🥉'}
                            {' '}#{item.rank}
                          </span>
                        ) : (
                          `#${item.rank}`
                        )}
                      </td>
                      <td style={tdStyle}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <div style={{
                            width: '32px',
                            height: '32px',
                            borderRadius: '50%',
                            background: currentTheme.avatarGradient,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            fontSize: '.9rem',
                            fontWeight: '600',
                            flexShrink: 0
                          }}>
                            {getInitial(item.user_email)}
                          </div>
                          <span style={{ fontSize: isMobile ? '.8rem' : '.9rem' }}>
                            {item.user_email}
                          </span>
                        </div>
                      </td>
                      <td style={tdStyle}>
                        <span style={{
                          background: 'rgba(78, 205, 196, 0.2)',
                          padding: '4px 12px',
                          borderRadius: '15px',
                          fontSize: isMobile ? '.75rem' : '.85rem',
                          border: '1px solid rgba(78, 205, 196, 0.4)'
                        }}>
                          {item.template_title}
                        </span>
                      </td>
                      <td style={{ ...tdStyle, fontWeight: '700', color: '#4ecdc4', fontSize: isMobile ? '1rem' : '1.1rem' }}>
                        {Math.round(item.score)}
                      </td>
                      <td style={tdStyle}>
                        <span style={{
                          background: 'rgba(255, 206, 84, 0.2)',
                          padding: '4px 10px',
                          borderRadius: '12px',
                          fontSize: isMobile ? '.75rem' : '.85rem',
                          border: '1px solid rgba(255, 206, 84, 0.4)'
                        }}>
                          {item.message_count}
                        </span>
                      </td>
                      <td style={tdStyle}>
                        <span style={{
                          background: 'rgba(155, 89, 182, 0.2)',
                          padding: '4px 10px',
                          borderRadius: '12px',
                          fontSize: isMobile ? '.75rem' : '.85rem',
                          border: '1px solid rgba(155, 89, 182, 0.4)'
                        }}>
                          {formatDuration(item.duration_seconds)}
                        </span>
                      </td>
                      <td style={{ ...tdStyle, fontSize: isMobile ? '.75rem' : '.85rem', opacity: 0.8 }}>
                        {new Date(item.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Load More */}
        {skip < total && (
          <div style={{ textAlign: 'center' }}>
            <button
              onClick={() => load(false)}
              disabled={loading}
              style={buttonStyle}
              onMouseOver={(e) => {
                if (!loading) {
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.3)'
                }
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = '0 4px 15px rgba(0, 0, 0, 0.2)'
              }}
            >
              {loading ? (
                <>
                  <i className="fas fa-spinner fa-spin" style={{ marginRight: '10px' }}></i>
                  Loading...
                </>
              ) : (
                <>Load More</>
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}


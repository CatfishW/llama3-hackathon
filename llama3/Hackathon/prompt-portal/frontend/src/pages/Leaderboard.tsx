import { useEffect, useState } from 'react'
import { api } from '../api'

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
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      setLoading(true)
      const res = await api.get('/api/leaderboard?limit=50')
      setItems(res.data)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to load leaderboard')
    } finally {
      setLoading(false)
    }
  }
  
  useEffect(() => { load() }, [])

  const containerStyle = {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '40px 20px'
  }

  const headerStyle = {
    textAlign: 'center' as const,
    marginBottom: '40px'
  }

  const tableContainerStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '15px',
    padding: '30px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    overflowX: 'auto' as const
  }

  const tableStyle = {
    width: '100%',
    borderCollapse: 'collapse' as const,
    color: 'white'
  }

  const thStyle = {
    padding: '15px 20px',
    textAlign: 'left' as const,
    borderBottom: '2px solid rgba(255, 255, 255, 0.2)',
    fontSize: '1.1rem',
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.9)'
  }

  const tdStyle = {
    padding: '15px 20px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
    fontSize: '1rem'
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
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={{ fontSize: '3rem', fontWeight: '700', marginBottom: '20px' }}>
          🏆 Leaderboard
        </h1>
        <p style={{ fontSize: '1.2rem', opacity: '0.8', maxWidth: '600px', margin: '0 auto' }}>
          Top performing prompt templates ranked by player scores and performance metrics
        </p>
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
                    key={entry.rank + entry.session_id}
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
                          background: 'linear-gradient(45deg, #4ecdc4, #44a08d)',
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
                      <span style={{
                        background: 'rgba(78, 205, 196, 0.2)',
                        border: '1px solid rgba(78, 205, 196, 0.4)',
                        borderRadius: '15px',
                        padding: '4px 12px',
                        fontSize: '0.9rem',
                        fontWeight: '500'
                      }}>
                        {entry.template_title}
                      </span>
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

      {/* Refresh Button */}
      <div style={{ textAlign: 'center', marginTop: '30px' }}>
        <button
          onClick={load}
          disabled={loading}
          style={{
            background: 'rgba(78, 205, 196, 0.8)',
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
              e.currentTarget.style.background = 'rgba(78, 205, 196, 1)'
              e.currentTarget.style.transform = 'translateY(-2px)'
            }
          }}
          onMouseOut={(e) => {
            if (!loading) {
              e.currentTarget.style.background = 'rgba(78, 205, 196, 0.8)'
              e.currentTarget.style.transform = 'translateY(0)'
            }
          }}
        >
          <i className={`fas ${loading ? 'fa-spinner fa-spin' : 'fa-sync-alt'}`} style={{ marginRight: '8px' }}></i>
          {loading ? 'Refreshing...' : 'Refresh Leaderboard'}
        </button>
      </div>
    </div>
  )
}

import { useEffect, useState, CSSProperties } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Trophy,
  Users,
  User as UserIcon,
  FileCode,
  Star,
  Archive,
  Activity,
  Gamepad,
  Clock,
  RotateCcw,
  ChevronDown,
  Medal,
  Zap,
  Info,
  AlertTriangle,
  Loader2,
  ArrowRight
} from 'lucide-react'
import { leaderboardAPI } from '../api'
import { useIsMobile } from '../hooks/useIsMobile'
import { useTutorial } from '../contexts/TutorialContext'

type Entry = {
  rank: number
  user_email: string
  template_id: number
  template_title: string
  score: number  // Deprecated score (old system)
  new_score?: number | null  // New comprehensive scoring system
  session_id: string
  created_at: string
  total_steps?: number | null
  collision_count?: number | null
}

export default function Leaderboard() {
  const [items, setItems] = useState<Entry[]>([])
  const [total, setTotal] = useState(0)
  const [skip, setSkip] = useState(0)
  const [mode, setMode] = useState<'lam' | 'manual'>('lam')
  const [forceRefresh, setForceRefresh] = useState(0)
  const [participants, setParticipants] = useState<number | null>(null)
  const [registeredUsers, setRegisteredUsers] = useState<number | null>(null)
  const PAGE_SIZE = 50
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const isMobile = useIsMobile()
  const { runTutorial } = useTutorial()

  useEffect(() => {
    const hasSeenLeaderboardTutorial = localStorage.getItem('tutorial_seen_leaderboard')
    if (!hasSeenLeaderboardTutorial && !loading) {
      runTutorial([
        { target: '#leaderboard-stats', title: 'Global Statistics', content: 'See the total number of participants and registered engineers in the LAM ecosystem.', position: 'bottom' },
        { target: '#leaderboard-table', title: 'The Hall of Fame', content: 'Analyze the top-performing sessions. You can see the rank, score, and the specific template used.', position: 'top' },
        { target: '#load-more-btn', title: 'Deeper Insights', content: 'Click here to load more rankings and see how other engineers are performing.', position: 'top' },
      ]);
      localStorage.setItem('tutorial_seen_leaderboard', 'true');
    }
  }, [loading, runTutorial]);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.05 } }
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0 }
  }

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

  useEffect(() => { load(true) }, [mode, forceRefresh])

  useEffect(() => {
    ; (async () => {
      try {
        const s = await leaderboardAPI.getStats()
        setParticipants(s.participants)
        setRegisteredUsers(s.registered_users)
      } catch { }
    })()
  }, [])

  const getRankIcon = (rank: number) => {
    switch (rank) {
      case 1: return <Medal size={20} color="#fbbf24" />
      case 2: return <Medal size={20} color="#cbd5e1" />
      case 3: return <Medal size={20} color="#d97706" />
      default: return <span style={{ fontSize: '0.85rem', fontWeight: 700, opacity: 0.5 }}>#{rank}</span>
    }
  }

  const getRankStyle = (rank: number): any => {
    const baseStyle = {
      width: '36px',
      height: '36px',
      borderRadius: '10px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'rgba(255,255,255,0.03)',
      border: '1px solid rgba(255,255,255,0.05)'
    }

    if (rank === 1) return { ...baseStyle, background: 'rgba(251, 191, 36, 0.1)', borderColor: 'rgba(251, 191, 36, 0.2)' }
    if (rank === 2) return { ...baseStyle, background: 'rgba(203, 213, 225, 0.1)', borderColor: 'rgba(203, 213, 225, 0.2)' }
    if (rank === 3) return { ...baseStyle, background: 'rgba(217, 119, 6, 0.1)', borderColor: 'rgba(217, 119, 6, 0.2)' }
    return baseStyle
  }

  return (
    <div style={{ minHeight: '100vh', background: 'transparent', color: '#f8fafc', fontFamily: 'Urbanist, sans-serif' }}>
      <motion.div
        style={{ maxWidth: '1200px', margin: '0 auto', padding: isMobile ? '24px 16px 80px' : '60px 24px' }}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        <motion.div variants={itemVariants} style={{ textAlign: 'center', marginBottom: '48px' }}>
          <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '24px' }}>
            <div style={{ padding: '16px', borderRadius: '24px', background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.2)', boxShadow: '0 0 40px rgba(99,102,241,0.1)' }}>
              <Trophy size={48} className="text-indigo-400" />
            </div>
          </div>
          <h1 style={{ fontSize: isMobile ? '2.5rem' : '4rem', fontWeight: 900, margin: 0, letterSpacing: '-0.04em', fontFamily: 'Plus Jakarta Sans, sans-serif' }}>
            Global Leaderboard
          </h1>
          <p style={{ color: '#94a3b8', marginTop: '16px', fontSize: '1.2rem', fontWeight: 500 }}>
            Top performing prompt engineering strategies in the arena.
          </p>
        </motion.div>

        <motion.div variants={itemVariants} style={{ display: 'flex', flexDirection: 'column', gap: '24px', marginBottom: '40px' }}>
          <div id="leaderboard-stats" style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap' }}>
            <div style={statCardStyle}>
              <Users size={18} className="text-indigo-400" />
              <span>Participants: <b>{participants ?? '—'}</b></span>
            </div>
            <div style={statCardStyle}>
              <Users size={18} className="text-blue-400" />
              <span>Registered: <b>{registeredUsers ?? '—'}</b></span>
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'center' }}>
            <div style={{ display: 'inline-flex', background: 'rgba(30, 41, 59, 0.4)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: 16, padding: '10px 24px', backdropFilter: 'blur(8px)', color: '#fff', fontWeight: 700, fontSize: '0.95rem' }}>
              LAM Arena Rankings
            </div>
          </div>
        </motion.div>

        {err && (
          <motion.div variants={itemVariants} style={errorStyle}>
            <AlertTriangle size={20} />
            {err}
          </motion.div>
        )}

        <motion.div id="leaderboard-table" variants={itemVariants} style={tableWrapperStyle}>
          {loading && items.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '100px 0' }}>
              <Loader2 size={40} className="animate-spin text-indigo-500" style={{ margin: '0 auto' }} />
            </div>
          ) : items.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '80px 0', color: '#64748b' }}>
              <Trophy size={48} style={{ margin: '0 auto 16px', opacity: 0.2 }} />
              <h3 style={{ fontSize: '1.25rem', color: '#cbd5e1' }}>No rankings available</h3>
              <p>Be the first to compete in this mode!</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={thStyle}>Rank</th>
                    <th style={thStyle}>Engineer</th>
                    <th style={thStyle}>Template</th>
                    <th style={thStyle}>Arena Score</th>
                    <th style={thStyle}>Legacy</th>
                    <th style={thStyle}>Performance</th>
                    <th style={thStyle}>Session</th>
                    <th style={thStyle}>Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  <AnimatePresence>
                    {items.map((entry, idx) => (
                      <motion.tr
                        key={entry.session_id + idx}
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        style={trStyle}
                      >
                        <td style={tdStyle}>
                          <div style={getRankStyle(entry.rank)}>
                            {getRankIcon(entry.rank)}
                          </div>
                        </td>
                        <td style={tdStyle}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <div style={avatarStyle}>
                              {entry.user_email.charAt(0).toUpperCase()}
                            </div>
                            <span style={{ fontWeight: 600, color: '#f1f5f9' }}>{entry.user_email.split('@')[0]}</span>
                          </div>
                        </td>
                        <td style={tdStyle}>
                          <Link to={`/templates/view/${entry.template_id}`} style={templateLinkStyle}>
                            <FileCode size={14} />
                            {entry.template_title}
                          </Link>
                        </td>
                        <td style={tdStyle}>
                          {entry.new_score != null ? (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span style={{ fontSize: '1.25rem', fontWeight: 800, color: '#4ade80' }}>{entry.new_score}</span>
                              <Zap size={12} className="text-yellow-400" />
                            </div>
                          ) : <span style={{ opacity: 0.3 }}>—</span>}
                        </td>
                        <td style={tdStyle}>
                          <span style={{ color: '#94a3b8', fontSize: '0.9rem' }}>{entry.score}</span>
                        </td>
                        <td style={tdStyle}>
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '0.8rem' }}>
                            {entry.total_steps != null && <span style={{ color: '#cbd5e1' }}>Steps: <b>{entry.total_steps}</b></span>}
                            {entry.collision_count != null && (
                              <span style={{ color: entry.collision_count > 0 ? '#f87171' : '#4ade80' }}>
                                Collisions: <b>{entry.collision_count}</b>
                              </span>
                            )}
                          </div>
                        </td>
                        <td style={tdStyle}>
                          <code style={codeStyle}>{entry.session_id.slice(0, 8)}</code>
                        </td>
                        <td style={tdStyle}>
                          <div style={{ display: 'flex', flexDirection: 'column', fontSize: '0.8rem' }}>
                            <span style={{ color: '#cbd5e1' }}>{new Date(entry.created_at).toLocaleDateString()}</span>
                            <span style={{ color: '#64748b' }}>{new Date(entry.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                          </div>
                        </td>
                      </motion.tr>
                    ))}
                  </AnimatePresence>
                </tbody>
              </table>
            </div>
          )}
        </motion.div>

        {(skip < total) && (
          <motion.div variants={itemVariants} style={{ textAlign: 'center' }}>
            <motion.button
              id="load-more-btn"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => load(false)}
              disabled={loading}
              style={loadMoreButtonStyle}
            >
              {loading ? <Loader2 size={18} className="animate-spin" /> : <ChevronDown size={18} />}
              Load More Rankings ({items.length} / {total})
            </motion.button>
          </motion.div>
        )}
      </motion.div>
    </div>
  )
}

const statCardStyle: CSSProperties = {
  background: 'rgba(30, 41, 59, 0.4)',
  border: '1px solid rgba(255, 255, 255, 0.05)',
  borderRadius: '12px',
  padding: '10px 16px',
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  fontSize: '0.9rem',
  color: '#cbd5e1'
}

const tableWrapperStyle: CSSProperties = {
  background: 'rgba(30, 41, 59, 0.4)',
  backdropFilter: 'blur(16px)',
  borderRadius: '24px',
  border: '1px solid rgba(255, 255, 255, 0.08)',
  padding: '8px',
  boxShadow: '0 20px 50px -12px rgba(0, 0, 0, 0.5)'
}

const tableStyle: CSSProperties = {
  width: '100%',
  borderCollapse: 'separate',
  borderSpacing: '0 4px',
}

const thStyle: CSSProperties = {
  padding: '16px 20px',
  textAlign: 'left',
  fontSize: '0.75rem',
  fontWeight: 700,
  color: '#64748b',
  textTransform: 'uppercase',
  letterSpacing: '0.05em'
}

const trStyle: CSSProperties = {
  background: 'transparent',
}

const tdStyle: CSSProperties = {
  padding: '16px 20px',
  borderBottom: '1px solid rgba(255, 255, 255, 0.03)',
  whiteSpace: 'nowrap'
}

const avatarStyle: CSSProperties = {
  width: '32px',
  height: '32px',
  borderRadius: '50%',
  background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontSize: '0.85rem',
  fontWeight: 700,
  color: '#fff'
}

const templateLinkStyle: CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '8px',
  padding: '6px 12px',
  background: 'rgba(99, 102, 241, 0.1)',
  border: '1px solid rgba(99, 102, 241, 0.2)',
  borderRadius: '10px',
  color: '#818cf8',
  fontSize: '0.85rem',
  fontWeight: 600,
  textDecoration: 'none',
  transition: 'all 0.2s'
}

const codeStyle: CSSProperties = {
  fontFamily: 'monospace',
  background: 'rgba(15, 23, 42, 0.4)',
  padding: '4px 8px',
  borderRadius: '6px',
  color: '#94a3b8',
  fontSize: '0.8rem'
}

const errorStyle: CSSProperties = {
  background: 'rgba(239, 68, 68, 0.1)',
  border: '1px solid rgba(239, 68, 68, 0.2)',
  borderRadius: '16px',
  padding: '16px 24px',
  color: '#fca5a5',
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  marginBottom: '32px'
}

const loadMoreButtonStyle: CSSProperties = {
  marginTop: '32px',
  padding: '12px 32px',
  borderRadius: '14px',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  background: 'rgba(255, 255, 255, 0.03)',
  color: '#f1f5f9',
  fontSize: '0.95rem',
  fontWeight: 600,
  cursor: 'pointer',
  display: 'inline-flex',
  alignItems: 'center',
  gap: '10px',
  transition: 'all 0.2s'
}

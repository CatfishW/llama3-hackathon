import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useEffect, useState } from 'react'

export default function Navbar() {
  const { user, logout } = useAuth()
  const location = useLocation()
  
  const [mobile, setMobile] = useState<boolean>(() => typeof window !== 'undefined' ? window.innerWidth < 880 : false)
  const [menuOpen, setMenuOpen] = useState(false)

  useEffect(()=>{
    function onResize(){ setMobile(window.innerWidth < 880) }
    window.addEventListener('resize', onResize)
    return ()=> window.removeEventListener('resize', onResize)
  }, [])

  const isActive = (path: string) => location.pathname === path

  const navStyle = {
    background: menuOpen ? 'rgba(15,15,28,0.85)' : 'rgba(20, 20, 35, 0.65)',
    backdropFilter: 'blur(14px)',
    WebkitBackdropFilter: 'blur(14px)',
    borderBottom: '1px solid rgba(255,255,255,0.12)',
    padding: '14px 0',
    position: 'sticky' as const,
    top: 0,
    zIndex: menuOpen ? 1500 : 1100,
    transition: 'background .3s ease'
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

  const navLinksStyle: any = mobile ? {
    display: menuOpen ? 'flex':'none',
    flexDirection: 'column',
    alignItems: 'stretch',
    gap: 14,
    position: 'absolute',
    left: 0,
    right: 0,
    top: '100%',
    background: 'rgba(18,18,34,0.94)',
    backdropFilter: 'blur(22px)',
    padding: '18px 18px 28px',
    borderBottom: '1px solid rgba(255,255,255,0.15)',
    boxShadow: '0 18px 40px -10px rgba(0,0,0,0.45)',
    maxHeight: '78vh',
    overflowY: 'auto'
  } : {
    display: 'flex',
    gap: '20px',
    alignItems: 'center',
    background: 'transparent',
    flexWrap: 'wrap'
  }

  const linkStyle = (active: boolean) => ({
    color: 'white',
    textDecoration: 'none',
    fontSize: mobile ? '0.95rem':'0.95rem',
    fontWeight: 500,
    padding: mobile ? '10px 16px':'8px 14px',
    borderRadius: 16,
    transition: 'background 0.25s ease, color 0.25s ease',
    background: active ? 'rgba(255,255,255,0.22)' : 'rgba(255,255,255,0.07)',
    border: active ? '1px solid rgba(255,255,255,0.35)' : '1px solid rgba(255,255,255,0.08)',
    display: 'flex',
    alignItems: 'center',
    gap: 8
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
      <div style={{ ...containerStyle, position:'relative' }}>
        <Link to="/" style={logoStyle}>
          <i className="fas fa-puzzle-piece"></i>
          LAM Maze Platform
        </Link>
        {mobile && (
          <button
            aria-label={menuOpen? 'Close menu':'Open menu'}
            aria-expanded={menuOpen}
            onClick={()=>setMenuOpen(o=>!o)}
            style={{ background:'rgba(0,0,0,0.35)', color:'#fff', border:'1px solid rgba(255,255,255,0.25)', padding:'10px 14px', borderRadius:12, cursor:'pointer', display:'flex', alignItems:'center', gap:8 }}
          >
            <i className={`fas ${menuOpen? 'fa-times':'fa-bars'}`}></i>
            <span style={{ fontSize:'.85rem', letterSpacing:'.5px' }}>{menuOpen? 'Close':'Menu'}</span>
          </button>
        )}
        {menuOpen && mobile && (
          <div onClick={()=>setMenuOpen(false)} style={{position:'fixed', inset:0, background:'rgba(0,0,0,0.35)', backdropFilter:'blur(2px)', zIndex:1490}} />
        )}

        <div style={navLinksStyle}>
          {user ? (
            <>
              {mobile && (
                <div style={{ display:'flex', flexDirection:'column', gap:8, marginBottom:4 }}>
                  <div style={{ fontSize:'.75rem', textTransform:'uppercase', opacity:.6, letterSpacing:'.8px', fontWeight:600 }}>Navigation</div>
                </div>
              )}
              <Link
                to="/dashboard"
                style={linkStyle(isActive('/dashboard'))}
                onMouseOver={(e) => {
                  if (!isActive('/dashboard')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.12)'
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
                to="/chat"
                style={linkStyle(isActive('/chat'))}
                onMouseOver={(e) => {
                  if (!isActive('/chat')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseOut={(e) => {
                  if (!isActive('/chat')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <i className="fas fa-robot" style={{ marginRight: '8px' }}></i>
                Chat
              </Link>
              <Link
                to="/voice-chat"
                style={linkStyle(isActive('/voice-chat'))}
                onMouseOver={(e) => {
                  if (!isActive('/voice-chat')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseOut={(e) => {
                  if (!isActive('/voice-chat')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <i className="fas fa-microphone" style={{ marginRight: '8px' }}></i>
                Voice
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
                to="/driving-stats"
                style={linkStyle(isActive('/driving-stats'))}
                onMouseOver={(e) => {
                  if (!isActive('/driving-stats')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                  }
                }}
                onMouseOut={(e) => {
                  if (!isActive('/driving-stats')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <i className="fas fa-flag-checkered" style={{ marginRight: '8px' }}></i>
                Driving
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

              {/* Admin Link - Only show for admin user */}
              {user?.email === '1819409756@qq.com' && (
                <>
                  {mobile && (
                    <div style={{ fontSize:'.75rem', textTransform:'uppercase', opacity:.6, letterSpacing:'.8px', fontWeight:600, marginTop: 12, marginBottom: 4 }}>Admin</div>
                  )}
                  <Link
                    to="/admin/announcements"
                    style={{
                      ...linkStyle(isActive('/admin/announcements')),
                      background: isActive('/admin/announcements') 
                        ? 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)'
                        : 'linear-gradient(135deg, rgba(240, 147, 251, 0.3) 0%, rgba(245, 87, 108, 0.3) 100%)',
                      border: '1px solid rgba(245, 87, 108, 0.5)',
                      fontWeight: 600,
                      boxShadow: '0 2px 8px rgba(245, 87, 108, 0.3)'
                    }}
                    onMouseOver={(e) => {
                      if (!isActive('/admin/announcements')) {
                        e.currentTarget.style.background = 'linear-gradient(135deg, rgba(240, 147, 251, 0.5) 0%, rgba(245, 87, 108, 0.5) 100%)'
                        e.currentTarget.style.transform = 'translateY(-2px)'
                      }
                    }}
                    onMouseOut={(e) => {
                      if (!isActive('/admin/announcements')) {
                        e.currentTarget.style.background = 'linear-gradient(135deg, rgba(240, 147, 251, 0.3) 0%, rgba(245, 87, 108, 0.3) 100%)'
                        e.currentTarget.style.transform = 'translateY(0)'
                      }
                    }}
                  >
                    <i className="fas fa-bullhorn" style={{ marginRight: '8px' }}></i>
                    📢 Announcements
                  </Link>
                </>
              )}
              
              {/* User Menu */}
              <div style={{ position: 'relative', marginLeft: mobile? 0 : '10px', width: mobile? '100%':'auto' }}>
                <div style={{ ...authLinksStyle, width: mobile? '100%':'auto', justifyContent: mobile? 'space-between':'flex-start' }}>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '10px',
                    padding: mobile? '10px 14px':'8px 12px',
                    borderRadius: mobile? 16 : '20px',
                    background: 'rgba(255, 255, 255, 0.1)',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    flex: mobile? 1 : 'unset'
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

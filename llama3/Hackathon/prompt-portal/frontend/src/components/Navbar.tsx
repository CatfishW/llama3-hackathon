import { Link, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Puzzle,
  Menu,
  X,
  LayoutDashboard,
  Gamepad2,
  FileCode,
  MessageSquare,
  Trophy,
  Flag,
  Users,
  Mail,
  Megaphone,
  User,
  Settings,
  LogOut,
  Palette,
  Check,
  Bot,
  Zap,
  HelpCircle
} from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useTutorial } from '../contexts/TutorialContext'
import { useEffect, useState } from 'react'

export default function Navbar() {
  const { user, logout } = useAuth()
  const { theme, setTheme } = useTheme()
  const { runTutorial } = useTutorial()
  const location = useLocation()

  const [mobile, setMobile] = useState<boolean>(() => typeof window !== 'undefined' ? window.innerWidth < 880 : false)
  const [menuOpen, setMenuOpen] = useState(false)
  const [themeMenuOpen, setThemeMenuOpen] = useState(false)

  useEffect(() => {
    function onResize() { setMobile(window.innerWidth < 880) }
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])

  const isActive = (path: string) => location.pathname === path

  const themeOptions = [
    { id: 'slate', name: 'Slate', color: '#6366f1' },
    { id: 'emerald', name: 'Emerald', color: '#10b981' },
    { id: 'rose', name: 'Rose', color: '#f43f5e' },
    { id: 'amber', name: 'Amber', color: '#f59e0b' },
    { id: 'violet', name: 'Violet', color: '#8b5cf6' },
    { id: 'cyan', name: 'Cyan', color: '#06b6d4' },
    { id: 'orange', name: 'Orange', color: '#f97316' },
    { id: 'fuchsia', name: 'Fuchsia', color: '#d946ef' },
    { id: 'lime', name: 'Lime', color: '#84cc16' },
    { id: 'sky', name: 'Sky', color: '#0ea5e9' }
  ] as const

  const navStyle = {
    background: 'rgba(15, 23, 42, 0.4)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    borderBottom: '1px solid rgba(255,255,255,0.08)',
    padding: '12px 0',
    position: 'sticky' as const,
    top: 0,
    zIndex: 1100,
    transition: 'all 0.3s ease'
  }

  const linkStyle = (active: boolean) => ({
    color: active ? '#fff' : '#94a3b8',
    textDecoration: 'none',
    fontSize: '0.9rem',
    fontWeight: 600,
    padding: '8px 12px',
    borderRadius: '10px',
    transition: 'all 0.2s ease',
    background: active ? 'rgba(255,255,255,0.05)' : 'transparent',
    display: 'flex',
    alignItems: 'center',
    gap: '8px'
  })

  return (
    <nav style={navStyle}>
      <div style={{ maxWidth: '1400px', margin: '0 auto', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Link to="/" style={{ fontSize: '1.25rem', fontWeight: 800, color: '#fff', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '12px',
            overflow: 'hidden',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <img src="/logo_new.png" style={{ width: '100%', height: '100%', objectFit: 'contain' }} alt="PiNG Logo" />
          </div>
          <span>PiNG LAM</span>
        </Link>

        {!mobile && (
          <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
            <Link id="nav-dashboard" to="/dashboard" style={linkStyle(isActive('/dashboard'))}><LayoutDashboard size={16} />Dashboard</Link>
            <Link id="nav-templates" to="/templates" style={linkStyle(isActive('/templates'))}><FileCode size={16} />Templates</Link>
            <Link id="nav-chat" to="/chat" style={linkStyle(isActive('/chat'))}><MessageSquare size={16} />Chat</Link>
            <Link id="nav-agent-3d" to="/agent-3d" style={linkStyle(isActive('/agent-3d'))}><Bot size={16} />Agent 3D</Link>
            <Link id="nav-skills" to="/agent-skills" style={linkStyle(isActive('/agent-skills'))}><Zap size={16} />Skills</Link>
            <Link id="nav-leaderboard" to="/leaderboard" style={linkStyle(isActive('/leaderboard'))}><Trophy size={16} />Arena</Link>
            <Link id="nav-friends" to="/friends" style={linkStyle(isActive('/friends'))}><Users size={16} />Social</Link>
            <Link id="nav-messages" to="/messages" style={linkStyle(isActive('/messages'))}><Mail size={16} />Inbox</Link>
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {/* Theme Switcher */}
          <div style={{ position: 'relative' }}>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => setThemeMenuOpen(!themeMenuOpen)}
              style={{
                background: 'rgba(255,255,255,0.05)',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '10px',
                padding: '8px',
                color: '#fff',
                cursor: 'pointer',
                display: 'flex'
              }}
            >
              <Palette size={18} />
            </motion.button>

            <AnimatePresence>
              {themeMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  style={{
                    position: 'absolute',
                    top: '100%',
                    right: 0,
                    marginTop: '12px',
                    background: '#1e293b',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: '16px',
                    padding: '8px',
                    minWidth: '160px',
                    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
                    zIndex: 1200
                  }}
                >
                  {themeOptions.map((opt) => (
                    <button
                      key={opt.id}
                      onClick={() => { setTheme(opt.id as any); setThemeMenuOpen(false); }}
                      style={{
                        width: '100%',
                        padding: '10px 12px',
                        borderRadius: '10px',
                        border: 'none',
                        background: theme === opt.id ? 'rgba(255,255,255,0.05)' : 'transparent',
                        color: theme === opt.id ? '#fff' : '#94a3b8',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        fontSize: '0.85rem',
                        fontWeight: 600
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: opt.color }} />
                        {opt.name}
                      </div>
                      {theme === opt.id && <Check size={14} />}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* Help Button */}
          {user && (
            <motion.button
              id="help-button"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => {
                runTutorial([
                  { target: '#nav-dashboard', title: 'Dashboard', content: 'Your central hub for monitoring AI activities and quick access to all tools.', position: 'bottom' },
                  { target: '#nav-templates', title: 'Prompt Templates', content: 'Create, edit, and manage your prompt templates for different AI models.', position: 'bottom' },
                  { target: '#nav-chat', title: 'Chat Studio', content: 'Test your prompts in real-time with our advanced Chat Studio.', position: 'bottom' },
                  { target: '#nav-agent-3d', title: 'Agent Maze 3D', content: 'Watch your AI agents navigate through complex 3D environments.', position: 'bottom' },
                  { target: '#nav-skills', title: 'Agent Skills', content: 'Manage and visualize the skills your agents have acquired.', position: 'bottom' },
                  { target: '#nav-leaderboard', title: 'Global Arena', content: 'See how your prompts and agents perform against others in the community.', position: 'bottom' },
                  { target: '#help-button', title: 'Need Help?', content: 'You can always click this button to restart the tutorial if you get lost!', position: 'bottom' },
                ]);
              }}
              style={{
                ...iconButtonStyle,
                background: 'rgba(99, 102, 241, 0.1)',
                border: '1px solid rgba(99, 102, 241, 0.2)',
                color: '#818cf8',
              }}
              title="Start Tutorial"
            >
              <HelpCircle size={18} />
            </motion.button>
          )}

          {user && !mobile && (
            <div style={{ display: 'flex', gap: '8px', marginLeft: '12px', paddingLeft: '12px', borderLeft: '1px solid rgba(255,255,255,0.1)' }}>
              <Link to="/profile" style={iconButtonStyle} title="Profile"><User size={18} /></Link>
              <Link to="/settings" style={iconButtonStyle} title="Settings"><Settings size={18} /></Link>
              <button onClick={logout} style={{ ...iconButtonStyle, color: '#fca5a5' }} title="Logout"><LogOut size={18} /></button>
            </div>
          )}

          {mobile && (
            <button
              onClick={() => setMenuOpen(!menuOpen)}
              style={{ background: 'transparent', border: 'none', color: '#fff', cursor: 'pointer' }}
            >
              {menuOpen ? <X size={24} /> : <Menu size={24} />}
            </button>
          )}
        </div>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobile && menuOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            style={{ overflow: 'hidden', background: '#0f172a', borderBottom: '1px solid rgba(255,255,255,0.1)' }}
          >
            <div style={{ padding: '16px 24px 32px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <Link onClick={() => setMenuOpen(false)} to="/dashboard" style={mobileLinkStyle(isActive('/dashboard'))}><LayoutDashboard size={18} />Dashboard</Link>
              <Link onClick={() => setMenuOpen(false)} to="/templates" style={mobileLinkStyle(isActive('/templates'))}><FileCode size={18} />Templates</Link>
              <Link onClick={() => setMenuOpen(false)} to="/chat" style={mobileLinkStyle(isActive('/chat'))}><MessageSquare size={18} />Chat Studio</Link>
              <Link onClick={() => setMenuOpen(false)} to="/agent-3d" style={mobileLinkStyle(isActive('/agent-3d'))}><Bot size={18} />Agent 3D</Link>
              <Link onClick={() => setMenuOpen(false)} to="/agent-skills" style={mobileLinkStyle(isActive('/agent-skills'))}><Zap size={18} />Skills</Link>
              <Link onClick={() => setMenuOpen(false)} to="/leaderboard" style={mobileLinkStyle(isActive('/leaderboard'))}><Trophy size={18} />Global Arena</Link>
              <Link onClick={() => setMenuOpen(false)} to="/friends" style={mobileLinkStyle(isActive('/friends'))}><Users size={18} />Friends</Link>
              <Link onClick={() => setMenuOpen(false)} to="/messages" style={mobileLinkStyle(isActive('/messages'))}><Mail size={18} />Messages</Link>
              <div style={{ height: '1px', background: 'rgba(255,255,255,0.05)', margin: '8px 0' }} />
              <Link onClick={() => setMenuOpen(false)} to="/profile" style={mobileLinkStyle(isActive('/profile'))}><User size={18} />My Profile</Link>
              <Link onClick={() => setMenuOpen(false)} to="/settings" style={mobileLinkStyle(isActive('/settings'))}><Settings size={18} />Settings</Link>
              <button onClick={() => { setMenuOpen(false); logout(); }} style={{ ...mobileLinkStyle(false), color: '#fca5a5' }}><LogOut size={18} />Sign Out</button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </nav>
  )
}

const iconButtonStyle = {
  background: 'transparent',
  border: 'none',
  color: '#94a3b8',
  cursor: 'pointer',
  padding: '8px',
  borderRadius: '10px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  transition: 'all 0.2s ease',
  textDecoration: 'none'
}

const mobileLinkStyle = (active: boolean) => ({
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  padding: '12px 16px',
  borderRadius: '12px',
  color: active ? '#fff' : '#94a3b8',
  textDecoration: 'none',
  fontSize: '1rem',
  fontWeight: 600,
  background: active ? 'rgba(99, 102, 241, 0.1)' : 'transparent'
})

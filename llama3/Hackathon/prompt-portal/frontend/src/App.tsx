import React, { useEffect, useState } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import Homepage from './pages/Homepage'
import Register from './pages/Register'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Templates from './pages/Templates'
import NewTemplate from './pages/NewTemplate'
import TemplateEdit from './pages/TemplateEdit'
import Leaderboard from './pages/Leaderboard'
import TemplateView from './pages/TemplateView'
import Friends from './pages/Friends'
import Messages from './pages/Messages'
import Profile from './pages/Profile'
import Settings from './pages/Settings'
import AdminAnnouncements from './pages/AdminAnnouncements'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import PrivateRoute from './components/PrivateRoute'
import AnnouncementPopup from './components/AnnouncementPopup'
import { useAuth } from './auth/AuthContext'
import { TemplateProvider } from './contexts/TemplateContext'
import { ThemeProvider, useTheme } from './contexts/ThemeContext'
import ChatStudio from './pages/ChatStudio'
import AgentMaze3D from './pages/AgentMaze3D'
import AgentSkills from './pages/AgentSkills'
import { announcementsAPI } from './api'
import { RawLogProvider } from './contexts/RawLogContext'
import { RawLogPanel } from './components/RawLogPanel'
import { TutorialProvider } from './contexts/TutorialContext'
import { AlertCircle, RefreshCcw, Home } from 'lucide-react'

// Professional Error Boundary component
class ErrorBoundary extends React.Component<{ children: React.ReactNode }, { hasError: boolean, error: Error | null }> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    console.error("Critical Application Error:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          height: '100vh',
          width: '100vw',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'radial-gradient(circle at center, #2e1065 0%, #020617 100%)',
          color: 'white',
          fontFamily: 'Urbanist, sans-serif',
          padding: '20px',
          textAlign: 'center'
        }}>
          <div style={{
            background: 'rgba(255, 255, 255, 0.05)',
            backdropFilter: 'blur(20px)',
            borderRadius: '24px',
            padding: '48px',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            maxWidth: '500px',
            boxShadow: '0 20px 50px rgba(0,0,0,0.5)'
          }}>
            <div style={{
              width: '80px', height: '80px', borderRadius: '50%', background: 'rgba(239, 68, 68, 0.1)',
              display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 24px'
            }}>
              <AlertCircle size={40} color="#ef4444" />
            </div>
            <h1 style={{ fontSize: '2rem', marginBottom: '16px', fontWeight: 800 }}>System Anomaly Detected</h1>
            <p style={{ color: '#94a3b8', marginBottom: '32px', lineHeight: 1.6 }}>
              A critical reasoning error occurred in the front-end processor. The cognitive engine needs a manually triggered synchronization.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
              <button
                onClick={() => window.location.reload()}
                style={{
                  background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                  color: 'white', border: 'none', padding: '12px 24px', borderRadius: '12px',
                  fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px'
                }}
              >
                <RefreshCcw size={18} /> Resync Terminal
              </button>
              <a
                href="/"
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  color: 'white', border: '1px solid rgba(255, 255, 255, 0.1)', textDecoration: 'none',
                  padding: '12px 24px', borderRadius: '12px',
                  fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '8px'
                }}
              >
                <Home size={18} /> Return Home
              </a>
            </div>
            <pre style={{ marginTop: '24px', textAlign: 'left', fontSize: '10px', opacity: 0.5, overflow: 'auto', maxHeight: '100px' }}>
              {this.state.error?.message}
            </pre>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function AppContent() {
  const { user } = useAuth()
  const { theme } = useTheme()
  const location = useLocation()
  const [announcements, setAnnouncements] = useState<any[]>([])
  const [dismissedAnnouncements, setDismissedAnnouncements] = useState<number[]>([])

  const isMobile = typeof window !== 'undefined' ? window.innerWidth < 768 : false

  const fetchAnnouncements = React.useCallback(async () => {
    if (!user) return;
    try {
      const response = await announcementsAPI.getActive()
      const currentDismissed = JSON.parse(localStorage.getItem('dismissedAnnouncements') || '[]')
      const newAnnouncements = response.data.filter((a: any) =>
        !currentDismissed.includes(a.id)
      )
      setAnnouncements(newAnnouncements)
    } catch (error) {
      console.error('Failed to fetch announcements:', error)
    }
  }, [user])

  // Fetch announcements when user is logged in
  useEffect(() => {
    fetchAnnouncements()
    const interval = setInterval(fetchAnnouncements, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchAnnouncements])

  const handleDismissAnnouncement = (id: number) => {
    setDismissedAnnouncements(prev => [...prev, id])
    setAnnouncements(prev => prev.filter(a => a.id !== id))
    const dismissed = JSON.parse(localStorage.getItem('dismissedAnnouncements') || '[]')
    localStorage.setItem('dismissedAnnouncements', JSON.stringify([...dismissed, id]))
  }

  useEffect(() => {
    const dismissed = JSON.parse(localStorage.getItem('dismissedAnnouncements') || '[]')
    setDismissedAnnouncements(dismissed)
  }, [])

  const themeColors: any = {
    slate: { primary: '#6366f1', secondary: '#818cf8', bg: '#0f172a', accent: 'rgba(99, 102, 241, 0.15)' },
    emerald: { primary: '#10b981', secondary: '#34d399', bg: '#064e3b', accent: 'rgba(16, 185, 129, 0.15)' },
    rose: { primary: '#f43f5e', secondary: '#fb7185', bg: '#4c0519', accent: 'rgba(244, 63, 94, 0.15)' },
    amber: { primary: '#f59e0b', secondary: '#fbbf24', bg: '#451a03', accent: 'rgba(245, 158, 11, 0.15)' },
    violet: { primary: '#8b5cf6', secondary: '#a78bfa', bg: '#2e1065', accent: 'rgba(139, 92, 246, 0.15)' },
    cyan: { primary: '#06b6d4', secondary: '#22d3ee', bg: '#164e63', accent: 'rgba(6, 182, 212, 0.15)' },
    orange: { primary: '#f97316', secondary: '#fb923c', bg: '#431407', accent: 'rgba(249, 115, 22, 0.15)' },
    fuchsia: { primary: '#d946ef', secondary: '#e879f9', bg: '#4a044e', accent: 'rgba(217, 70, 239, 0.15)' },
    lime: { primary: '#84cc16', secondary: '#a3e635', bg: '#1a2e05', accent: 'rgba(132, 204, 22, 0.15)' },
    sky: { primary: '#0ea5e9', secondary: '#38bdf8', bg: '#082f49', accent: 'rgba(14, 165, 233, 0.15)' }
  }

  const currentTheme = themeColors[theme] || themeColors.slate

  const appStyle = {
    minHeight: '100vh',
    background: currentTheme.bg,
    color: '#f8fafc',
    fontFamily: '"Urbanist", system-ui, -apple-system, sans-serif',
    display: 'flex',
    flexDirection: 'column' as const,
    position: 'relative' as const,
    overflow: 'hidden',
    transition: 'background 0.5s ease-in-out'
  }

  const blobStyle: any = {
    position: 'absolute',
    width: '600px',
    height: '600px',
    background: `radial-gradient(circle, ${currentTheme.accent} 0%, rgba(0,0,0,0) 70%)`,
    borderRadius: '50%',
    zIndex: 0,
    pointerEvents: 'none',
    transition: 'background 0.5s ease-in-out'
  }

  const contentStyle = {
    flex: 1,
    position: 'relative' as const,
    zIndex: 1
  }

  const pageVariants: any = {
    initial: { opacity: 0, scale: 0.99 },
    animate: { opacity: 1, scale: 1, transition: { duration: 0.4, ease: [0.4, 0, 0.2, 1] } },
    exit: { opacity: 0, scale: 1.01, transition: { duration: 0.3 } }
  }

  return (
    <div style={appStyle}>
      <div style={{ ...blobStyle, top: '-10%', right: '-5%' }} />
      <div style={{ ...blobStyle, bottom: '10%', left: '-10%', opacity: 0.8 }} />

      <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <TemplateProvider>
          {user && announcements.length > 0 && (
            <AnnouncementPopup
              announcements={announcements}
              onDismiss={handleDismissAnnouncement}
            />
          )}

          <Navbar />

          <AnimatePresence mode="wait" initial={false}>
            <motion.main
              key={location.pathname}
              variants={pageVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
            >
              <Routes location={location}>
                <Route path="/" element={<Homepage />} />
                <Route path="/register" element={<div style={{ ...contentStyle, flex: 1, padding: isMobile ? '20px' : '40px' }}><Register /></div>} />
                <Route path="/login" element={<div style={{ ...contentStyle, flex: 1, padding: isMobile ? '20px' : '40px' }}><Login /></div>} />
                <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
                <Route path="/templates" element={<PrivateRoute><Templates /></PrivateRoute>} />
                <Route path="/templates/new" element={<PrivateRoute><NewTemplate /></PrivateRoute>} />
                <Route path="/templates/:id" element={<PrivateRoute><TemplateEdit /></PrivateRoute>} />
                <Route path="/leaderboard" element={<PrivateRoute><Leaderboard /></PrivateRoute>} />
                <Route path="/agent-3d" element={<PrivateRoute><AgentMaze3D /></PrivateRoute>} />
                <Route path="/agent-skills" element={<PrivateRoute><AgentSkills /></PrivateRoute>} />
                <Route path="/chat" element={<PrivateRoute><ChatStudio /></PrivateRoute>} />
                <Route path="/templates/view/:id" element={<PrivateRoute><TemplateView /></PrivateRoute>} />
                <Route path="/friends" element={<PrivateRoute><Friends /></PrivateRoute>} />
                <Route path="/messages" element={<PrivateRoute><Messages /></PrivateRoute>} />
                <Route path="/messages/:userId" element={<PrivateRoute><Messages /></PrivateRoute>} />
                <Route path="/profile" element={<PrivateRoute><Profile /></PrivateRoute>} />
                <Route path="/settings" element={<PrivateRoute><Settings /></PrivateRoute>} />
                <Route path="/admin/announcements" element={<PrivateRoute><AdminAnnouncements /></PrivateRoute>} />
                <Route path="*" element={<Navigate to="/" />} />
              </Routes>
            </motion.main>
          </AnimatePresence>
          <Footer />
          <RawLogPanel />
        </TemplateProvider>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <RawLogProvider>
        <TutorialProvider>
          <ErrorBoundary>
            <AppContent />
          </ErrorBoundary>
        </TutorialProvider>
      </RawLogProvider>
    </ThemeProvider>
  )
}

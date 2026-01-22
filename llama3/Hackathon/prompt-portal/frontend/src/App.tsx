import { Routes, Route, Navigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import Homepage from './pages/Homepage'
import Register from './pages/Register'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Templates from './pages/Templates'
import NewTemplate from './pages/NewTemplate'
import TemplateEdit from './pages/TemplateEdit'
import Leaderboard from './pages/Leaderboard'
import DrivingStats from './pages/DrivingStats'
import TemplateView from './pages/TemplateView'
import TestMQTT from './pages/TestMQTT'
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
import WebGame from './pages/WebGame'
import ChatStudio from './pages/ChatStudio'
import { announcementsAPI } from './api'

export default function App() {
  const { user } = useAuth()
  const [announcements, setAnnouncements] = useState<any[]>([])
  const [dismissedAnnouncements, setDismissedAnnouncements] = useState<number[]>([])

  // Fetch announcements when user is logged in
  useEffect(() => {
    if (user) {
      fetchAnnouncements()
      // Poll for new announcements every 5 minutes
      const interval = setInterval(fetchAnnouncements, 5 * 60 * 1000)
      return () => clearInterval(interval)
    }
  }, [user])

  const fetchAnnouncements = async () => {
    try {
      const response = await announcementsAPI.getActive()
      const newAnnouncements = response.data.filter((a: any) => 
        !dismissedAnnouncements.includes(a.id)
      )
      setAnnouncements(newAnnouncements)
    } catch (error) {
      console.error('Failed to fetch announcements:', error)
    }
  }

  const handleDismissAnnouncement = (id: number) => {
    setDismissedAnnouncements(prev => [...prev, id])
    setAnnouncements(prev => prev.filter(a => a.id !== id))
    // Store dismissed announcements in localStorage to persist across sessions
    const dismissed = JSON.parse(localStorage.getItem('dismissedAnnouncements') || '[]')
    localStorage.setItem('dismissedAnnouncements', JSON.stringify([...dismissed, id]))
  }

  // Load dismissed announcements from localStorage on mount
  useEffect(() => {
    const dismissed = JSON.parse(localStorage.getItem('dismissedAnnouncements') || '[]')
    setDismissedAnnouncements(dismissed)
  }, [])
  
  const appStyle = {
    minHeight: '100vh',
    background: '#0f172a', // Slate 950
    color: '#f8fafc',
    fontFamily: '"Inter", system-ui, -apple-system, sans-serif',
    display: 'flex',
    flexDirection: 'column' as const,
    position: 'relative' as const,
    overflow: 'hidden'
  }

  const blobStyle: any = {
    position: 'absolute',
    width: '500px',
    height: '500px',
    background: 'radial-gradient(circle, rgba(99, 102, 241, 0.15) 0%, rgba(99, 102, 241, 0) 70%)',
    borderRadius: '50%',
    zIndex: 0,
    pointerEvents: 'none'
  }

  return (
    <div style={appStyle}>
      <div style={{ ...blobStyle, top: '-10%', right: '-5%' }} />
      <div style={{ ...blobStyle, bottom: '10%', left: '-10%', background: 'radial-gradient(circle, rgba(168, 85, 247, 0.1) 0%, rgba(168, 85, 247, 0) 70%)' }} />
      
      <div style={{ position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
        <TemplateProvider>
          {/* Show announcements for logged-in users */}
          {user && announcements.length > 0 && (
            <AnnouncementPopup 
              announcements={announcements}
              onDismiss={handleDismissAnnouncement}
            />
          )}
          
          <Routes>
          <Route path="/" element={
            <div style={{ flex: 1 }}>
              <Homepage />
              <Footer />
            </div>
          } />
          <Route path="/register" element={
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <Navbar />
              <div style={{ ...contentStyle, flex: 1 }}><Register /></div>
              <Footer />
            </div>
          } />
          <Route path="/login" element={
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <Navbar />
              <div style={{ ...contentStyle, flex: 1 }}><Login /></div>
              <Footer />
            </div>
          } />
          <Route path="/dashboard" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><Dashboard /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/templates" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><Templates /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/templates/new" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><NewTemplate /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/templates/:id" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><TemplateEdit /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/leaderboard" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><Leaderboard /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/driving-stats" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><DrivingStats /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/chat" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><ChatStudio /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/templates/view/:id" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><TemplateView /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/friends" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><Friends /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/messages" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><Messages /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/messages/:userId" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><Messages /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/profile" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><Profile /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/settings" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><Settings /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/play" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><WebGame /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="/admin/announcements" element={
            <PrivateRoute>
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                <Navbar />
                <div style={{ ...contentStyle, flex: 1 }}><AdminAnnouncements /></div>
                <Footer />
              </div>
            </PrivateRoute>
          } />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </TemplateProvider>
      </div>
    </div>
  )
}

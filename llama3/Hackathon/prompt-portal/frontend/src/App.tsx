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
import { CompletionProvider } from './completion/CompletionProvider'
import WebGame from './pages/WebGame'
import ChatStudio from './pages/ChatStudio'
import VoiceChat from './pages/VoiceChat'
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
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
    color: 'white',
    fontFamily: 'Inter, system-ui, sans-serif',
    display: 'flex',
    flexDirection: 'column' as const
  }

  const contentStyle = {
    flex: 1,
    padding: user ? '0' : '0' // No padding for homepage, some for other pages
  }

  return (
    <div style={appStyle}>
      <TemplateProvider>
        <CompletionProvider>
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
          <Route path="/voice-chat" element={
            <PrivateRoute>
              <VoiceChat />
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
        </CompletionProvider>
      </TemplateProvider>
    </div>
  )
}

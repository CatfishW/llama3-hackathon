import { Routes, Route, Navigate } from 'react-router-dom'
import Homepage from './pages/Homepage'
import Register from './pages/Register'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Templates from './pages/Templates'
import NewTemplate from './pages/NewTemplate'
import TemplateEdit from './pages/TemplateEdit'
import Leaderboard from './pages/Leaderboard'
import TestMQTT from './pages/TestMQTT'
import Friends from './pages/Friends'
import Messages from './pages/Messages'
import Profile from './pages/Profile'
import Settings from './pages/Settings'
import Navbar from './components/Navbar'
import Footer from './components/Footer'
import PrivateRoute from './components/PrivateRoute'
import { useAuth } from './auth/AuthContext'
import { TemplateProvider } from './contexts/TemplateContext'
import WebGame from './pages/WebGame'

export default function App() {
  const { user } = useAuth()
  
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
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </TemplateProvider>
    </div>
  )
}

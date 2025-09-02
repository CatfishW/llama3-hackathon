import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useIsMobile } from '../hooks/useIsMobile'

export default function Dashboard() {
  const { user } = useAuth()
  const isMobile = useIsMobile()

  const containerStyle = {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: isMobile ? '24px 14px 64px' : '40px 20px'
  }

  const headerStyle = {
    textAlign: 'center' as const,
    marginBottom: isMobile ? '32px' : '50px'
  }

  const cardStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '15px',
    padding: '30px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    transition: 'all 0.3s ease',
    cursor: 'pointer'
  }

  const gridStyle = {
    display: 'grid',
    gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: isMobile ? '20px' : '30px',
    marginBottom: isMobile ? '36px' : '50px'
  }

  const iconStyle = {
    fontSize: '3rem',
    marginBottom: '20px',
    display: 'block'
  }

  const buttonStyle = {
    background: 'rgba(78, 205, 196, 0.8)',
    color: 'white',
    padding: '12px 24px',
    borderRadius: '25px',
    textDecoration: 'none',
    fontSize: '1rem',
    fontWeight: '600',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    transition: 'all 0.3s ease',
    border: 'none',
    cursor: 'pointer'
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
  <h1 style={{ fontSize: isMobile ? '2.2rem' : '3rem', fontWeight: '700', marginBottom: '20px', lineHeight: 1.15 }}>
          Welcome back, {user?.email}! 👋
        </h1>
  <p style={{ fontSize: isMobile ? '1rem' : '1.2rem', opacity: '0.8', maxWidth: '680px', margin: '0 auto', lineHeight: 1.45 }}>
          Ready to create amazing prompt templates for the LAM Maze Game? 
          Manage your templates, monitor performance, and climb the leaderboard!
        </p>
      </div>

      <div style={gridStyle}>
        <Link to="/templates" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div 
            style={cardStyle}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-5px)'
              e.currentTarget.style.boxShadow = '0 10px 30px rgba(0,0,0,0.2)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            <i className="fas fa-file-code" style={{ ...iconStyle, fontSize: isMobile ? '2.4rem' : '3rem' }}></i>
            <h3 style={{ fontSize: isMobile ? '1.3rem':'1.5rem', marginBottom: '15px', fontWeight: '600' }}>
              Manage Templates
            </h3>
            <p style={{ opacity: '0.8', lineHeight: 1.5, marginBottom: '20px', fontSize: isMobile ? '.95rem':'1rem' }}>
              Create, edit, and organize your prompt templates. Design intelligent prompts 
              that guide AI agents through complex maze challenges.
            </p>
            <span style={buttonStyle}>
              <i className="fas fa-plus"></i>
              Create New Template
            </span>
          </div>
        </Link>

        <Link to="/play" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div 
            style={cardStyle}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-5px)'
              e.currentTarget.style.boxShadow = '0 10px 30px rgba(0,0,0,0.2)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            <i className="fas fa-vial" style={{ ...iconStyle, fontSize: isMobile ? '2.4rem' : '3rem' }}></i>
            <h3 style={{ fontSize: isMobile ? '1.3rem':'1.5rem', marginBottom: '15px', fontWeight: '600' }}>
              Test & Monitor
            </h3>
            <p style={{ opacity: '0.8', lineHeight: 1.5, marginBottom: '20px', fontSize: isMobile ? '.95rem':'1rem' }}>
              Test your templates in real-time and monitor MQTT communication. 
              Watch your AI agents navigate mazes using your prompts.
            </p>
            <span style={buttonStyle}>
              <i className="fas fa-play"></i>
              Start Testing
            </span>
          </div>
        </Link>

        <Link to="/leaderboard" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div 
            style={cardStyle}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-5px)'
              e.currentTarget.style.boxShadow = '0 10px 30px rgba(0,0,0,0.2)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            <i className="fas fa-trophy" style={{ ...iconStyle, fontSize: isMobile ? '2.4rem' : '3rem' }}></i>
            <h3 style={{ fontSize: isMobile ? '1.3rem':'1.5rem', marginBottom: '15px', fontWeight: '600' }}>
              Leaderboard
            </h3>
            <p style={{ opacity: '0.8', lineHeight: 1.5, marginBottom: '20px', fontSize: isMobile ? '.95rem':'1rem' }}>
              See how your templates perform against others. Track scores, rankings, 
              and discover the most effective prompt strategies.
            </p>
            <span style={buttonStyle}>
              <i className="fas fa-chart-line"></i>
              View Rankings
            </span>
          </div>
        </Link>
      </div>

      {/* Quick Stats Section */}
      <div style={{
        background: 'rgba(255, 255, 255, 0.1)',
        backdropFilter: 'blur(10px)',
        borderRadius: '15px',
        padding: isMobile ? '28px 20px' : '40px',
        border: '1px solid rgba(255, 255, 255, 0.2)',
        textAlign: 'center' as const
      }}>
        <h2 style={{ fontSize: isMobile ? '1.6rem':'2rem', marginBottom: isMobile ? '20px':'30px', fontWeight: '600' }}>
          Platform Overview
        </h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? 'repeat(2, minmax(0,1fr))':'repeat(auto-fit, minmax(200px, 1fr))',
          gap: isMobile ? '18px':'30px'
        }}>
          <div>
            <div style={{ fontSize: isMobile ? '2rem':'2.5rem', fontWeight: '700', color: '#4ecdc4' }}>🎮</div>
            <h4 style={{ fontSize: '1.2rem', margin: '10px 0', fontWeight: '600' }}>Interactive Gameplay</h4>
            <p style={{ opacity: '0.8', fontSize: '0.9rem' }}>Real-time maze navigation with AI assistance</p>
          </div>
          <div>
            <div style={{ fontSize: isMobile ? '2rem':'2.5rem', fontWeight: '700', color: '#ff6b6b' }}>🤖</div>
            <h4 style={{ fontSize: '1.2rem', margin: '10px 0', fontWeight: '600' }}>AI Agents</h4>
            <p style={{ opacity: '0.8', fontSize: '0.9rem' }}>DQN reinforcement learning integration</p>
          </div>
          <div>
            <div style={{ fontSize: isMobile ? '2rem':'2.5rem', fontWeight: '700', color: '#ffd93d' }}>📡</div>
            <h4 style={{ fontSize: '1.2rem', margin: '10px 0', fontWeight: '600' }}>MQTT Communication</h4>
            <p style={{ opacity: '0.8', fontSize: '0.9rem' }}>Real-time state and hint exchange</p>
          </div>
          <div>
            <div style={{ fontSize: isMobile ? '2rem':'2.5rem', fontWeight: '700', color: '#a8e6cf' }}>🏆</div>
            <h4 style={{ fontSize: '1.2rem', margin: '10px 0', fontWeight: '600' }}>Competitive Scoring</h4>
            <p style={{ opacity: '0.8', fontSize: '0.9rem' }}>Performance-based leaderboard system</p>
          </div>
        </div>
      </div>
    </div>
  )
}

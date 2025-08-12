import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export default function Homepage() {
  const { user } = useAuth()

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      color: 'white',
      fontFamily: 'Inter, system-ui, sans-serif'
    }}>
      {/* Hero Section */}
      <div style={{
        padding: '80px 20px',
        textAlign: 'center',
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
        <div style={{
          background: 'rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(10px)',
          borderRadius: '20px',
          padding: '60px 40px',
          marginBottom: '60px',
          border: '1px solid rgba(255, 255, 255, 0.2)'
        }}>
          <h1 style={{
            fontSize: '3.5rem',
            fontWeight: '700',
            marginBottom: '20px',
            textShadow: '2px 2px 4px rgba(0,0,0,0.3)'
          }}>
            🧩 LAM Maze Game Platform
          </h1>
          <h2 style={{
            fontSize: '1.8rem',
            fontWeight: '400',
            marginBottom: '30px',
            opacity: '0.9'
          }}>
            Prompt-Driven Large Action Model Interactive Experience
          </h2>
          <p style={{
            fontSize: '1.2rem',
            lineHeight: '1.6',
            maxWidth: '800px',
            margin: '0 auto 40px',
            opacity: '0.8'
          }}>
            Create intelligent prompt templates that guide AI agents through complex maze environments. 
            Compete with other developers to build the most effective Large Action Model prompts!
          </p>
          
          {!user ? (
            <div style={{ display: 'flex', gap: '20px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <Link
                to="/register"
                style={{
                  backgroundColor: '#ff6b6b',
                  color: 'white',
                  padding: '15px 30px',
                  borderRadius: '50px',
                  textDecoration: 'none',
                  fontSize: '1.1rem',
                  fontWeight: '600',
                  boxShadow: '0 4px 15px rgba(255, 107, 107, 0.4)',
                  transition: 'transform 0.3s ease'
                }}
                onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
                onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
              >
                <i className="fas fa-user-plus" style={{ marginRight: '8px' }}></i>
                Get Started
              </Link>
              <Link
                to="/login"
                style={{
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                  color: 'white',
                  padding: '15px 30px',
                  borderRadius: '50px',
                  textDecoration: 'none',
                  fontSize: '1.1rem',
                  fontWeight: '600',
                  border: '2px solid rgba(255, 255, 255, 0.3)',
                  transition: 'all 0.3s ease'
                }}
                onMouseOver={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.3)'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseOut={(e) => {
                  e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.2)'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                <i className="fas fa-sign-in-alt" style={{ marginRight: '8px' }}></i>
                Sign In
              </Link>
            </div>
          ) : (
            <Link
              to="/dashboard"
              style={{
                backgroundColor: '#4ecdc4',
                color: 'white',
                padding: '15px 30px',
                borderRadius: '50px',
                textDecoration: 'none',
                fontSize: '1.1rem',
                fontWeight: '600',
                boxShadow: '0 4px 15px rgba(78, 205, 196, 0.4)',
                transition: 'transform 0.3s ease'
              }}
              onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-2px)'}
              onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
            >
              <i className="fas fa-tachometer-alt" style={{ marginRight: '8px' }}></i>
              Go to Dashboard
            </Link>
          )}
        </div>

        {/* Features Section */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '30px',
          marginBottom: '60px'
        }}>
          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: '15px',
            padding: '40px 30px',
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            transition: 'transform 0.3s ease'
          }}
          onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
          onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <div style={{ fontSize: '3rem', marginBottom: '20px' }}>🎮</div>
            <h3 style={{ fontSize: '1.5rem', marginBottom: '15px', fontWeight: '600' }}>Interactive Maze Game</h3>
            <p style={{ opacity: '0.8', lineHeight: '1.6' }}>
              Navigate through dynamically generated mazes with your AI agent. Collect oxygen pellets, 
              avoid germs, and reach the exit with the help of your custom LAM prompts.
            </p>
          </div>

          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: '15px',
            padding: '40px 30px',
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            transition: 'transform 0.3s ease'
          }}
          onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
          onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <div style={{ fontSize: '3rem', marginBottom: '20px' }}>🤖</div>
            <h3 style={{ fontSize: '1.5rem', marginBottom: '15px', fontWeight: '600' }}>AI Agent Integration</h3>
            <p style={{ opacity: '0.8', lineHeight: '1.6' }}>
              Choose between human players or sophisticated RL agents (DQN) to test your prompts. 
              Watch as your AI makes strategic decisions based on your guidance.
            </p>
          </div>

          <div style={{
            background: 'rgba(255, 255, 255, 0.1)',
            backdropFilter: 'blur(10px)',
            borderRadius: '15px',
            padding: '40px 30px',
            textAlign: 'center',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            transition: 'transform 0.3s ease'
          }}
          onMouseOver={(e) => e.currentTarget.style.transform = 'translateY(-5px)'}
          onMouseOut={(e) => e.currentTarget.style.transform = 'translateY(0)'}
          >
            <div style={{ fontSize: '3rem', marginBottom: '20px' }}>🏆</div>
            <h3 style={{ fontSize: '1.5rem', marginBottom: '15px', fontWeight: '600' }}>Competitive Leaderboard</h3>
            <p style={{ opacity: '0.8', lineHeight: '1.6' }}>
              Compete with other prompt engineers! Your templates are ranked based on player performance, 
              survival time, and objectives completed.
            </p>
          </div>
        </div>

        {/* How it Works Section */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(10px)',
          borderRadius: '20px',
          padding: '50px 40px',
          border: '1px solid rgba(255, 255, 255, 0.2)'
        }}>
          <h2 style={{
            fontSize: '2.5rem',
            fontWeight: '600',
            marginBottom: '40px',
            textAlign: 'center'
          }}>
            How It Works
          </h2>
          
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '30px',
            textAlign: 'center'
          }}>
            <div>
              <div style={{
                background: 'rgba(255, 107, 107, 0.3)',
                borderRadius: '50%',
                width: '80px',
                height: '80px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px',
                fontSize: '2rem'
              }}>
                1️⃣
              </div>
              <h4 style={{ fontSize: '1.3rem', marginBottom: '15px', fontWeight: '600' }}>Create Prompts</h4>
              <p style={{ opacity: '0.8', lineHeight: '1.6' }}>
                Design intelligent prompt templates that guide the Large Action Model in making strategic decisions.
              </p>
            </div>

            <div>
              <div style={{
                background: 'rgba(78, 205, 196, 0.3)',
                borderRadius: '50%',
                width: '80px',
                height: '80px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px',
                fontSize: '2rem'
              }}>
                2️⃣
              </div>
              <h4 style={{ fontSize: '1.3rem', marginBottom: '15px', fontWeight: '600' }}>Test & Monitor</h4>
              <p style={{ opacity: '0.8', lineHeight: '1.6' }}>
                Watch your prompts in action through real-time MQTT communication and live game monitoring.
              </p>
            </div>

            <div>
              <div style={{
                background: 'rgba(255, 193, 7, 0.3)',
                borderRadius: '50%',
                width: '80px',
                height: '80px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 20px',
                fontSize: '2rem'
              }}>
                3️⃣
              </div>
              <h4 style={{ fontSize: '1.3rem', marginBottom: '15px', fontWeight: '600' }}>Compete & Win</h4>
              <p style={{ opacity: '0.8', lineHeight: '1.6' }}>
                Climb the leaderboard as players achieve higher scores using your optimized prompt templates.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

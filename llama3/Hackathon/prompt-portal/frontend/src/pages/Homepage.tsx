import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useEffect, useState } from 'react'

export default function Homepage() {
  const { user } = useAuth()
  const [isMobile, setIsMobile] = useState(false)
  useEffect(()=>{
    const update=()=> setIsMobile(window.innerWidth < 680)
    update(); window.addEventListener('resize', update); window.addEventListener('orientationchange', update)
    return ()=> { window.removeEventListener('resize', update); window.removeEventListener('orientationchange', update) }
  }, [])

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      color: 'white',
      fontFamily: 'Inter, system-ui, sans-serif',
      paddingBottom: 40
    }}>
      {/* Hero Section */}
      <div style={{
        padding: isMobile? '48px 16px 32px':'80px 20px',
        textAlign: 'center',
        maxWidth: '1200px',
        margin: '0 auto'
      }}>
        <div style={{
          background: 'rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(10px)',
          borderRadius: isMobile? '16px':'20px',
          padding: isMobile? '36px 22px':'60px 40px',
          marginBottom: isMobile? '40px':'60px',
          border: '1px solid rgba(255, 255, 255, 0.2)'
        }}>
          <h1 style={{
            fontSize: isMobile? '2.3rem':'3.5rem',
            fontWeight: '700',
            marginBottom: isMobile? '16px':'20px',
            textShadow: '2px 2px 4px rgba(0,0,0,0.3)',
            lineHeight: 1.1
          }}>
            🧩 LAM Maze Game Platform
          </h1>
          <h2 style={{
            fontSize: isMobile? '1.25rem':'1.8rem',
            fontWeight: '400',
            marginBottom: isMobile? '22px':'30px',
            opacity: '0.9',
            lineHeight: 1.3
          }}>
            Prompt-Driven Large Action Model Interactive Experience
          </h2>
          <p style={{
            fontSize: isMobile? '1rem':'1.2rem',
            lineHeight: '1.55',
            maxWidth: '800px',
            margin: '0 auto 32px',
            opacity: '0.85',
            padding: isMobile? '0 4px': undefined
          }}>
            Create intelligent prompt templates that guide AI agents through complex maze environments. 
            Compete with other developers to build the most effective Large Action Model prompts!
          </p>
          {!user ? (
            <div style={{ display: 'flex', gap: isMobile? '14px':'20px', justifyContent: 'center', flexWrap: 'wrap' }}>
              <Link
                to="/register"
                style={{
                  backgroundColor: '#ff6b6b',
                  color: 'white',
                  padding: isMobile? '14px 24px':'15px 30px',
                  borderRadius: '50px',
                  textDecoration: 'none',
                  fontSize: isMobile? '1rem':'1.1rem',
                  fontWeight: '600',
                  boxShadow: '0 4px 15px rgba(255, 107, 107, 0.4)',
                  transition: 'transform 0.3s ease'
                }}
              >
                <i className="fas fa-user-plus" style={{ marginRight: '8px' }}></i>
                Get Started
              </Link>
              <Link
                to="/login"
                style={{
                  backgroundColor: 'rgba(255, 255, 255, 0.2)',
                  color: 'white',
                  padding: isMobile? '14px 24px':'15px 30px',
                  borderRadius: '50px',
                  textDecoration: 'none',
                  fontSize: isMobile? '1rem':'1.1rem',
                  fontWeight: '600',
                  border: '2px solid rgba(255, 255, 255, 0.3)',
                  transition: 'all 0.3s ease'
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
                padding: isMobile? '14px 24px':'15px 30px',
                borderRadius: '50px',
                textDecoration: 'none',
                fontSize: isMobile? '1rem':'1.1rem',
                fontWeight: '600',
                boxShadow: '0 4px 15px rgba(78, 205, 196, 0.4)',
                transition: 'transform 0.3s ease'
              }}
            >
              <i className="fas fa-tachometer-alt" style={{ marginRight: '8px' }}></i>
              Go to Dashboard
            </Link>
          )}
        </div>

        {/* Features Section */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
          gap: isMobile? '20px':'30px',
          marginBottom: isMobile? '40px':'60px'
        }}>
          {[{
            icon:'🎮', title:'Interactive Maze Game', text:'Navigate through dynamically generated mazes with your AI agent. Collect oxygen pellets, avoid germs, and reach the exit with the help of your custom LAM prompts.'
          },{
            icon:'🤖', title:'AI Agent Integration', text:'Choose between human players or sophisticated RL agents (DQN) to test your prompts. Watch as your AI makes strategic decisions based on your guidance.'
          },{
            icon:'🏆', title:'Competitive Leaderboard', text:'Compete with other prompt engineers! Your templates are ranked based on player performance, survival time, and objectives completed.'
          }].map(card => (
            <div key={card.title} style={{
              background: 'rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(10px)',
              borderRadius: '15px',
              padding: isMobile? '28px 20px':'40px 30px',
              textAlign: 'center',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              transition: 'transform 0.3s ease'
            }}>
              <div style={{ fontSize: isMobile? '2.4rem':'3rem', marginBottom: '18px' }}>{card.icon}</div>
              <h3 style={{ fontSize: isMobile? '1.25rem':'1.5rem', marginBottom: '12px', fontWeight: '600' }}>{card.title}</h3>
              <p style={{ opacity: '0.8', lineHeight: '1.55', fontSize: isMobile? '.95rem':'1rem' }}>
                {card.text}
              </p>
            </div>
          ))}
        </div>

        {/* How it Works Section */}
        <div style={{
          background: 'rgba(255, 255, 255, 0.1)',
          backdropFilter: 'blur(10px)',
          borderRadius: '20px',
          padding: isMobile? '36px 24px':'50px 40px',
          border: '1px solid rgba(255, 255, 255, 0.2)'
        }}>
          <h2 style={{
            fontSize: isMobile? '1.9rem':'2.5rem',
            fontWeight: '600',
            marginBottom: isMobile? '28px':'40px',
            textAlign: 'center',
            lineHeight:1.2
          }}>
            How It Works
          </h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: isMobile? '22px':'30px',
            textAlign: 'center'
          }}>
            {[{
              num:'1️⃣', title:'Create Prompts', text:'Design intelligent prompt templates that guide the Large Action Model in making strategic decisions.'
            },{
              num:'2️⃣', title:'Test & Monitor', text:'Watch your prompts in action through real-time MQTT communication and live game monitoring.'
            },{
              num:'3️⃣', title:'Compete & Win', text:'Climb the leaderboard as players achieve higher scores using your optimized prompt templates.'
            }].map(step => (
              <div key={step.num}>
                <div style={{
                  background: step.num==='1️⃣'? 'rgba(255, 107, 107, 0.3)': step.num==='2️⃣'? 'rgba(78, 205, 196, 0.3)':'rgba(255, 193, 7, 0.3)',
                  borderRadius: '50%',
                  width: isMobile? '70px':'80px',
                  height: isMobile? '70px':'80px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 16px',
                  fontSize: isMobile? '1.6rem':'2rem'
                }}>
                  {step.num}
                </div>
                <h4 style={{ fontSize: isMobile? '1.05rem':'1.3rem', marginBottom: '12px', fontWeight: '600' }}>{step.title}</h4>
                <p style={{ opacity: '0.8', lineHeight: '1.55', fontSize: isMobile? '.92rem':'1rem', padding:'0 4px' }}>
                  {step.text}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

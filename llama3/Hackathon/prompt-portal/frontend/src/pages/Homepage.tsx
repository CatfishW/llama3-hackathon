import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Puzzle,
  ArrowRight,
  Gamepad2,
  Bot,
  Trophy,
  Zap,
  Target,
  Code2,
  LayoutDashboard,
  LogIn,
  UserPlus
} from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { useEffect, useState } from 'react'

export default function Homepage() {
  const { user } = useAuth()
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const update = () => setIsMobile(window.innerWidth < 680)
    update(); window.addEventListener('resize', update);
    return () => window.removeEventListener('resize', update)
  }, [])

  const containerVariants: any = {
    hidden: { opacity: 0 },
    visible: { opacity: 1, transition: { staggerChildren: 0.15 } }
  }

  const itemVariants: any = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1, transition: { duration: 0.6, ease: 'easeOut' } }
  }

  return (
    <div style={{ minHeight: '100vh', background: 'transparent', color: '#f8fafc', paddingBottom: 80 }}>
      <motion.div
        style={{ maxWidth: '1200px', margin: '0 auto', padding: isMobile ? '40px 20px' : '80px 24px' }}
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {/* Hero Section */}
        <motion.div
          variants={itemVariants}
          style={{
            background: 'rgba(30, 41, 59, 0.4)',
            backdropFilter: 'blur(16px)',
            borderRadius: '32px',
            padding: isMobile ? '48px 24px' : '80px 48px',
            marginBottom: '60px',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            textAlign: 'center',
            boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)'
          }}
        >
          <div style={{ display: 'inline-flex', padding: '12px', borderRadius: '20px', background: 'rgba(99, 102, 241, 0.1)', border: '1px solid rgba(99, 102, 241, 0.2)', marginBottom: '24px' }}>
            <Puzzle size={40} className="text-indigo-400" />
          </div>

          <h1 style={{
            fontSize: isMobile ? '2rem' : '3.5rem',
            fontWeight: 900,
            marginBottom: '24px',
            letterSpacing: '-0.025em',
            lineHeight: 1.1,
            color: '#fff'
          }}>
            Personalized Instruction and <span style={{ background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>Need-aware Gamification</span>
          </h1>

          <h2 style={{
            fontSize: isMobile ? '1.1rem' : '1.5rem',
            fontWeight: 500,
            marginBottom: '32px',
            color: '#94a3b8',
            maxWidth: '900px',
            margin: '0 auto 32px'
          }}>
            Large Action Model Platform for Orchestration and Reasoning.
          </h2>

          <p style={{
            fontSize: isMobile ? '1rem' : '1.15rem',
            lineHeight: 1.7,
            maxWidth: '700px',
            margin: '0 auto 48px',
            color: '#64748b'
          }}>
            Architect complex system instructions that empower AI agents to navigate dynamic environments.
            Real-time validation, competitive arena, and direct LLM interaction.
          </p>

          <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', flexWrap: 'wrap' }}>
            {!user ? (
              <>
                <Link to="/register" style={primaryButtonStyle}>
                  <UserPlus size={20} />
                  Engineer Account
                </Link>
                <Link to="/login" style={secondaryButtonStyle}>
                  <LogIn size={20} />
                  Access Portal
                </Link>
              </>
            ) : (
              <Link to="/dashboard" style={primaryButtonStyle}>
                <LayoutDashboard size={20} />
                Return to Dashboard
                <ArrowRight size={20} />
              </Link>
            )}
          </div>
        </motion.div>

        {/* Features Grid */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
          gap: '24px',
          marginBottom: '60px'
        }}>
          {[
            { icon: <Gamepad2 size={32} />, title: 'Spatial Simulation', text: 'Navigate high-fidelity maze environments with adaptive state management and real-time objectives.' },
            { icon: <Bot size={32} />, title: 'Agent Integration', text: 'Connect state-of-the-art LLMs and RL agents. Observe complex decision making driven by your prompts.' },
            { icon: <Trophy size={32} />, title: 'The Arena', text: 'Compete in global rankings. Optimized templates are benchmarked on performance, efficiency, and logic.' }
          ].map((card, i) => (
            <motion.div
              key={i}
              variants={itemVariants}
              whileHover={{ y: -8, borderColor: 'rgba(99, 102, 241, 0.3)', background: 'rgba(30, 41, 59, 0.6)' }}
              style={featureCardStyle}
            >
              <div style={{ color: '#818cf8', marginBottom: '20px' }}>{card.icon}</div>
              <h3 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '16px', color: '#f1f5f9' }}>{card.title}</h3>
              <p style={{ color: '#94a3b8', lineHeight: 1.6 }}>{card.text}</p>
            </motion.div>
          ))}
        </div>

        {/* Workflow Section */}
        <motion.div
          variants={itemVariants}
          style={{
            background: 'rgba(15, 23, 42, 0.3)',
            borderRadius: '32px',
            padding: isMobile ? '48px 24px' : '64px 48px',
            border: '1px solid rgba(255, 255, 255, 0.05)'
          }}
        >
          <h2 style={{ fontSize: '2.5rem', fontWeight: 800, marginBottom: '48px', textAlign: 'center', letterSpacing: '-0.025em' }}>
            The Engineering Workflow
          </h2>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
            gap: '40px'
          }}>
            {[
              { icon: <Code2 />, color: '#6366f1', title: 'Architect', text: 'Design complex prompt templates with dynamic variables and system constraints.' },
              { icon: <Zap />, color: '#10b981', title: 'Execute', text: 'Watch your instructions manifest into actions through real-time state synchronization.' },
              { icon: <Target />, color: '#f59e0b', title: 'Optimize', text: 'Refine reasoning chains based on performance metrics and competitive benchmarks.' }
            ].map((step, i) => (
              <div key={i} style={{ textAlign: 'center' }}>
                <div style={{
                  background: `${step.color}15`,
                  color: step.color,
                  width: '64px',
                  height: '64px',
                  borderRadius: '16px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  margin: '0 auto 24px',
                  border: `1px solid ${step.color}30`
                }}>
                  {step.icon}
                </div>
                <h4 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '12px', color: '#f1f5f9' }}>{step.title}</h4>
                <p style={{ color: '#94a3b8', lineHeight: 1.6 }}>{step.text}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </motion.div>
    </div>
  )
}

const primaryButtonStyle: any = {
  backgroundColor: '#6366f1',
  color: 'white',
  padding: '16px 32px',
  borderRadius: '16px',
  textDecoration: 'none',
  fontSize: '1.1rem',
  fontWeight: 700,
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  boxShadow: '0 10px 25px -5px rgba(99, 102, 241, 0.4)',
  transition: 'all 0.2s ease'
}

const secondaryButtonStyle: any = {
  backgroundColor: 'rgba(255, 255, 255, 0.05)',
  color: 'white',
  padding: '16px 32px',
  borderRadius: '16px',
  textDecoration: 'none',
  fontSize: '1.1rem',
  fontWeight: 700,
  display: 'flex',
  alignItems: 'center',
  gap: '12px',
  border: '1px solid rgba(255, 255, 255, 0.1)',
  transition: 'all 0.2s ease'
}

const featureCardStyle: any = {
  background: 'rgba(30, 41, 59, 0.4)',
  backdropFilter: 'blur(16px)',
  borderRadius: '24px',
  padding: '40px 32px',
  border: '1px solid rgba(255, 255, 255, 0.08)',
  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
}


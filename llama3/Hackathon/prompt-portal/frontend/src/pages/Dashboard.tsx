import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  FileCode,
  Play,
  Trophy,
  Plus,
  TrendingUp,
  Megaphone,
  Crown,
  Cpu,
  Activity,
  Layers,
  ArrowRight,
  MessageSquare
} from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { useIsMobile } from '../hooks/useIsMobile'
import { useTutorial } from '../contexts/TutorialContext'
import { useEffect } from 'react'

export default function Dashboard() {
  const { user } = useAuth()
  const isMobile = useIsMobile()
  const { runTutorial } = useTutorial()

  useEffect(() => {
    const hasSeenWelcome = localStorage.getItem('tutorial_seen_welcome')
    if (!hasSeenWelcome && user) {
      runTutorial([
        { target: '#welcome-header', title: 'Mission Briefing', content: 'Welcome, Engineer. This is your command center for directing and refining Large Action Models.', position: 'bottom' },
        { target: '#card-templates', title: 'Cognitive Templates', content: 'Design the underlying reasoning structures for your agents before deployment.', position: 'bottom' },
        { target: '#card-chat', title: 'Live Prototyping', content: 'Use the Chat Studio to stress-test your prompts and observe raw LLM responses.', position: 'bottom' },
        { target: '#card-rankings', title: 'Performance Analytics', content: 'Monitor the global leaderboard to compare your LLM efficiency and agent success rates.', position: 'bottom' },
        { target: '#platform-infrastructure', title: 'System Health', content: 'Overview of the low-latency infrastructure powering your agents and real-time syncing.', position: 'top' },
        { target: '#help-button', title: 'On-Demand Support', content: 'Need a tutorial reset or technical help? The help center is always available in the navbar.', position: 'bottom' },
      ]);
      localStorage.setItem('tutorial_seen_welcome', 'true');
    }
  }, [user, runTutorial]);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: { staggerChildren: 0.1 }
    }
  }

  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: { y: 0, opacity: 1 }
  }

  const containerStyle = {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: isMobile ? '24px 16px 80px' : '60px 24px'
  }

  const cardStyle = {
    background: 'rgba(30, 41, 59, 0.4)',
    backdropFilter: 'blur(12px)',
    borderRadius: '24px',
    padding: '32px',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    height: '100%',
    display: 'flex',
    flexDirection: 'column' as const,
    boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)'
  }

  const buttonStyle = {
    background: 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
    color: 'white',
    padding: '12px 24px',
    borderRadius: '14px',
    textDecoration: 'none',
    fontSize: '0.95rem',
    fontWeight: 600,
    display: 'inline-flex',
    alignItems: 'center',
    gap: '10px',
    border: 'none',
    cursor: 'pointer',
    marginTop: 'auto',
    width: 'fit-content',
    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.2)'
  }

  return (
    <motion.div
      style={containerStyle}
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    >
      <motion.div id="welcome-header" variants={itemVariants} style={{ textAlign: 'center', marginBottom: '60px' }}>
        <h1 style={{ fontSize: isMobile ? '2.2rem' : '3.5rem', fontWeight: 800, marginBottom: '24px', letterSpacing: '-0.025em', color: '#f8fafc' }}>
          Welcome, <span className="text-indigo-400">{user?.email?.split('@')[0]}</span>! <motion.span animate={{ rotate: [0, 20, 0] }} transition={{ repeat: Infinity, duration: 2 }}>👋</motion.span>
        </h1>
        <p style={{ fontSize: isMobile ? '1.1rem' : '1.25rem', color: '#94a3b8', maxWidth: '750px', margin: '0 auto', lineHeight: 1.6 }}>
          Engineer the perfect prompt, orchestrate AI agents, and dominate the maze.
          Your central hub for prompt engineering and LAM orchestration.
        </p>
      </motion.div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(340px, 1fr))',
        gap: '24px',
        marginBottom: '60px'
      }}>
        <motion.div variants={itemVariants}>
          <Link to="/templates" style={{ textDecoration: 'none', color: 'inherit' }}>
            <motion.div
              id="card-templates"
              style={cardStyle}
              whileHover={{ y: -8, borderColor: 'rgba(99, 102, 241, 0.4)', background: 'rgba(30, 41, 59, 0.6)' }}
            >
              <div style={{ width: '56px', height: '56px', borderRadius: '16px', background: 'rgba(99, 102, 241, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '24px' }}>
                <FileCode size={28} className="text-indigo-400" />
              </div>
              <h3 style={{ fontSize: '1.5rem', marginBottom: '16px', fontWeight: 700, color: '#f1f5f9' }}>
                Manage Templates
              </h3>
              <p style={{ color: '#94a3b8', lineHeight: 1.6, marginBottom: '32px', fontSize: '1rem' }}>
                Architect complex system instructions. Design prompt chains that empower
                agents to solve intricate spatial puzzles.
              </p>
              <div style={buttonStyle}>
                <Plus size={18} />
                Create New
              </div>
            </motion.div>
          </Link>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Link to="/chat" style={{ textDecoration: 'none', color: 'inherit' }}>
            <motion.div
              id="card-chat"
              style={cardStyle}
              whileHover={{ y: -8, borderColor: 'rgba(34, 197, 94, 0.4)', background: 'rgba(30, 41, 59, 0.6)' }}
            >
              <div style={{ width: '56px', height: '56px', borderRadius: '16px', background: 'rgba(34, 197, 94, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '24px' }}>
                <MessageSquare size={28} className="text-green-400" />
              </div>
              <h3 style={{ fontSize: '1.5rem', marginBottom: '16px', fontWeight: 700, color: '#f1f5f9' }}>
                Chat Studio
              </h3>
              <p style={{ color: '#94a3b8', lineHeight: 1.6, marginBottom: '32px', fontSize: '1rem' }}>
                Interact directly with Large Action Models. Test your personas,
                debug reasoning, and refine conversational flow in real-time.
              </p>
              <div style={{ ...buttonStyle, background: 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)', boxShadow: '0 4px 12px rgba(34, 197, 94, 0.2)' }}>
                <Play size={18} />
                Open Studio
              </div>
            </motion.div>
          </Link>
        </motion.div>

        <motion.div variants={itemVariants}>
          <Link to="/leaderboard" style={{ textDecoration: 'none', color: 'inherit' }}>
            <motion.div
              id="card-rankings"
              style={cardStyle}
              whileHover={{ y: -8, borderColor: 'rgba(245, 158, 11, 0.4)', background: 'rgba(30, 41, 59, 0.6)' }}
            >
              <div style={{ width: '56px', height: '56px', borderRadius: '16px', background: 'rgba(245, 158, 11, 0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: '24px' }}>
                <Trophy size={28} className="text-amber-400" />
              </div>
              <h3 style={{ fontSize: '1.5rem', marginBottom: '16px', fontWeight: 700, color: '#f1f5f9' }}>
                Global Rankings
              </h3>
              <p style={{ color: '#94a3b8', lineHeight: 1.6, marginBottom: '32px', fontSize: '1rem' }}>
                Analyze cross-platform performance metrics. Track how your
                engineering strategies stack up against the best in the arena.
              </p>
              <div style={{ ...buttonStyle, background: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)', boxShadow: '0 4px 12px rgba(245, 158, 11, 0.2)' }}>
                <TrendingUp size={18} />
                View Rankings
              </div>
            </motion.div>
          </Link>
        </motion.div>
      </div>

      {user?.email === '1819409756@qq.com' && (
        <motion.div
          variants={itemVariants}
          whileHover={{ scale: 1.01 }}
          style={{
            background: 'linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(168, 85, 247, 0.15) 100%)',
            backdropFilter: 'blur(16px)',
            borderRadius: '28px',
            padding: isMobile ? '32px 24px' : '48px',
            border: '1px solid rgba(168, 85, 247, 0.3)',
            marginBottom: '60px',
            display: 'flex',
            flexDirection: isMobile ? 'column' : 'row',
            alignItems: isMobile ? 'flex-start' : 'center',
            justifyContent: 'space-between',
            gap: '32px'
          }}
        >
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
              <Crown size={32} className="text-amber-400" />
              <h2 style={{ fontSize: '2rem', margin: 0, fontWeight: 800, color: '#f8fafc' }}>
                Administrator
              </h2>
            </div>
            <p style={{ color: '#cbd5e1', fontSize: '1.1rem', lineHeight: 1.6, margin: 0 }}>
              Broadcast mission critical updates and manage the LAM Maze ecosystem announcements.
            </p>
          </div>
          <Link
            to="/admin/announcements"
            style={{
              ...buttonStyle,
              background: 'linear-gradient(135deg, #f472b6 0%, #dc2626 100%)',
              padding: '16px 32px',
              fontSize: '1.1rem',
              boxShadow: '0 8px 24px rgba(220, 38, 38, 0.3)'
            }}
          >
            <Megaphone size={20} />
            Manage Broadcasts
            <ArrowRight size={20} />
          </Link>
        </motion.div>
      )}

      <motion.div id="platform-infrastructure" variants={itemVariants} style={{
        background: 'rgba(15, 23, 42, 0.3)',
        borderRadius: '28px',
        padding: isMobile ? '40px 24px' : '60px',
        border: '1px solid rgba(255, 255, 255, 0.05)',
        textAlign: 'center'
      }}>
        <h2 style={{ fontSize: '2.2rem', marginBottom: '48px', fontWeight: 800, color: '#f8fafc' }}>
          Platform Infrastructure
        </h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'repeat(4, 1fr)',
          gap: '40px'
        }}>
          <div>
            <Cpu size={40} className="text-indigo-400" style={{ margin: '0 auto 20px' }} />
            <h4 style={{ fontSize: '1.2rem', color: '#f1f5f9', fontWeight: 700, marginBottom: '12px' }}>LAM Core</h4>
            <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: 1.5 }}>High-fidelity action modeling engine</p>
          </div>
          <div>
            <Activity size={40} className="text-green-400" style={{ margin: '0 auto 20px' }} />
            <h4 style={{ fontSize: '1.2rem', color: '#f1f5f9', fontWeight: 700, marginBottom: '12px' }}>Real-time</h4>
            <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: 1.5 }}>SSE powered sub-50ms state sync</p>
          </div>
          <div>
            <Layers size={40} className="text-blue-400" style={{ margin: '0 auto 20px' }} />
            <h4 style={{ fontSize: '1.2rem', color: '#f1f5f9', fontWeight: 700, marginBottom: '12px' }}>Multi-modal</h4>
            <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: 1.5 }}>Vision and text reasoning integration</p>
          </div>
          <div>
            <Crown size={40} className="text-amber-400" style={{ margin: '0 auto 20px' }} />
            <h4 style={{ fontSize: '1.2rem', color: '#f1f5f9', fontWeight: 700, marginBottom: '12px' }}>Arena</h4>
            <p style={{ color: '#94a3b8', fontSize: '0.95rem', lineHeight: 1.5 }}>Competitive validation framework</p>
          </div>
        </div>
      </motion.div>
    </motion.div>
  )
}

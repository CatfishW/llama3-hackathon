export default function Footer() {
  const footerStyle = {
    background: 'rgba(0, 0, 0, 0.3)',
    borderTop: '1px solid rgba(255, 255, 255, 0.1)',
    padding: '40px 20px 20px',
    marginTop: '60px',
    color: 'rgba(255, 255, 255, 0.8)'
  }

  const containerStyle = {
    maxWidth: '1200px',
    margin: '0 auto',
    textAlign: 'center' as const
  }

  const linkStyle = {
    color: '#4ecdc4',
    textDecoration: 'none',
    fontWeight: '500'
  }

  return (
    <footer style={footerStyle}>
      <div style={containerStyle}>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '30px',
          marginBottom: '30px',
          textAlign: 'left'
        }}>
          <div>
            <h4 style={{ fontSize: '1.2rem', marginBottom: '15px', color: 'white' }}>
              <i className="fas fa-puzzle-piece" style={{ marginRight: '8px' }}></i>
              Personalized Instruction and Gamification
            </h4>
            <p style={{ lineHeight: '1.6', fontSize: '0.95rem' }}>
              An interactive platform for developing and testing prompt templates
              for Large Action Models in maze environments.
            </p>
          </div>

          <div>
            <h4 style={{ fontSize: '1.2rem', marginBottom: '15px', color: 'white' }}>
              Features
            </h4>
            <ul style={{ listStyle: 'none', padding: 0, lineHeight: '1.8' }}>
              <li><i className="fas fa-check" style={{ marginRight: '8px', color: '#4ecdc4' }}></i>AI Agent Integration</li>
              <li><i className="fas fa-check" style={{ marginRight: '8px', color: '#4ecdc4' }}></i>Real-time Server-Sent Events</li>
              <li><i className="fas fa-check" style={{ marginRight: '8px', color: '#4ecdc4' }}></i>Competitive Leaderboard</li>
              <li><i className="fas fa-check" style={{ marginRight: '8px', color: '#4ecdc4' }}></i>Template Management</li>
            </ul>
          </div>

          <div>
            <h4 style={{ fontSize: '1.2rem', marginBottom: '15px', color: 'white' }}>
              Technology Stack
            </h4>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
              {['Python', 'PyGame', 'PyTorch', 'React', 'TypeScript', 'SSE'].map(tech => (
                <span key={tech} style={{
                  background: 'rgba(78, 205, 196, 0.2)',
                  padding: '4px 12px',
                  borderRadius: '12px',
                  fontSize: '0.85rem',
                  border: '1px solid rgba(78, 205, 196, 0.4)'
                }}>
                  {tech}
                </span>
              ))}
            </div>
          </div>
        </div>

        <div style={{
          borderTop: '1px solid rgba(255, 255, 255, 0.1)',
          paddingTop: '20px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '15px'
        }}>
          <div>
            <p style={{ margin: 0, fontSize: '0.95rem', fontWeight: 600, color: '#f1f5f9' }}>
              Developer: Yanlai Wu | Advisor: Ying Tang
            </p>
            <p style={{ margin: 0, fontSize: '0.85rem', color: '#94a3b8' }}>
              © 2026 LAM Maze Platform. Built for prompt engineering research.
            </p>
          </div>
          <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
            <a href="#" style={linkStyle}>
              <i className="fab fa-github" style={{ marginRight: '5px' }}></i>
              GitHub
            </a>
            <a href="#" style={linkStyle}>
              <i className="fas fa-book" style={{ marginRight: '5px' }}></i>
              Documentation
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}

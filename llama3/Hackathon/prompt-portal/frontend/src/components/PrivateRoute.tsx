import { useAuth } from '../auth/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { Navigate } from 'react-router-dom'

type PrivateRouteProps = {
  children: React.ReactNode
}

export default function PrivateRoute({ children }: PrivateRouteProps) {
  const { user, isLoading } = useAuth()
  const { theme } = useTheme()

  const themeColors: any = {
    slate: { primary: '#6366f1', bg: '#0f172a' },
    emerald: { primary: '#10b981', bg: '#064e3b' },
    rose: { primary: '#f43f5e', bg: '#4c0519' },
    amber: { primary: '#f59e0b', bg: '#451a03' },
    violet: { primary: '#8b5cf6', bg: '#2e1065' },
    cyan: { primary: '#06b6d4', bg: '#164e63' },
    orange: { primary: '#f97316', bg: '#431407' },
    fuchsia: { primary: '#d946ef', bg: '#4a044e' },
    lime: { primary: '#84cc16', bg: '#1a2e05' },
    sky: { primary: '#0ea5e9', bg: '#082f49' }
  }

  const currentTheme = themeColors[theme] || themeColors.slate

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: `radial-gradient(circle at center, ${currentTheme.bg} 0%, #020617 100%)`,
        color: 'white',
        fontFamily: '"Urbanist", sans-serif'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '24px', letterSpacing: '0.05em', opacity: 0.8 }}>SYNERGIZING NEURAL CORE...</div>
          <div style={{
            width: '48px',
            height: '48px',
            border: '3px solid rgba(255,255,255,0.05)',
            borderTop: `3px solid ${currentTheme.primary}`,
            borderRadius: '50%',
            animation: 'spin 1s cubic-bezier(0.4, 0, 0.2, 1) infinite',
            margin: '0 auto',
            boxShadow: `0 0 20px ${currentTheme.primary}44`
          }}></div>
          <style>{`
            @keyframes spin {
              from { transform: rotate(0deg); }
              to { transform: rotate(360deg); }
            }
          `}</style>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  return <>{children}</>
}

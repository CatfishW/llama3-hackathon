import { FormEvent, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useNavigate, Link } from 'react-router-dom'
import { useIsMobile } from '../hooks/useIsMobile'

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const isMobile = useIsMobile()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      await login(email, password)
      nav('/dashboard')
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const containerStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 'calc(100vh - 80px)',
    padding: isMobile ? '24px 16px 56px' : '40px 20px'
  }

  const formStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '20px',
    padding: isMobile ? '28px 22px' : '40px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    width: '100%',
    maxWidth: '450px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
  }

  const inputStyle = {
    width: '100%',
    padding: isMobile ? '13px 16px':'15px 20px',
    borderRadius: '10px',
    border: '1px solid rgba(255, 255, 255, 0.3)',
    background: 'rgba(255, 255, 255, 0.1)',
    color: 'white',
    fontSize: isMobile ? '.95rem':'1rem',
    marginTop: '8px',
    transition: 'all 0.3s ease'
  }

  const labelStyle = {
    color: 'rgba(255, 255, 255, 0.9)',
    fontSize: '1rem',
    fontWeight: '500',
    marginBottom: '8px',
    display: 'block'
  }

  const buttonStyle = {
    width: '100%',
    background: 'linear-gradient(45deg, #4ecdc4, #44a08d)',
    color: 'white',
    border: 'none',
    padding: isMobile ? '13px 18px':'15px 20px',
    borderRadius: '10px',
    fontSize: isMobile ? '1rem':'1.1rem',
    fontWeight: '600',
    cursor: loading ? 'not-allowed' : 'pointer',
    transition: 'all 0.3s ease',
    marginTop: '25px',
    opacity: loading ? 0.7 : 1
  }

  const errorStyle = {
    background: 'rgba(255, 107, 107, 0.2)',
    border: '1px solid rgba(255, 107, 107, 0.4)',
    borderRadius: '8px',
    padding: '12px 16px',
    color: '#ff6b6b',
    marginBottom: '20px',
    fontSize: '0.9rem'
  }

  return (
    <div style={containerStyle}>
      <form onSubmit={onSubmit} style={formStyle}>
        <div style={{ textAlign: 'center', marginBottom: isMobile ? '22px':'30px' }}>
          <div style={{ fontSize: isMobile ? '2.4rem':'3rem', marginBottom: '15px' }}>🔐</div>
          <h2 style={{ fontSize: isMobile ? '1.7rem':'2rem', fontWeight: '700', marginBottom: '10px' }}>
            Welcome Back
          </h2>
          <p style={{ opacity: '0.8', fontSize: isMobile ? '.95rem':'1rem' }}>
            Sign in to continue to your dashboard
          </p>
        </div>

        {err && (
          <div style={errorStyle}>
            <i className="fas fa-exclamation-triangle" style={{ marginRight: '8px' }}></i>
            {err}
          </div>
        )}

        <div style={{ marginBottom: '20px' }}>
          <label style={labelStyle}>
            <i className="fas fa-envelope" style={{ marginRight: '8px' }}></i>
            Email Address
          </label>
          <input
            type="email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            style={inputStyle}
            placeholder="Enter your email"
            onFocus={(e) => {
              e.target.style.borderColor = 'rgba(78, 205, 196, 0.6)'
              e.target.style.boxShadow = '0 0 0 3px rgba(78, 205, 196, 0.1)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = 'rgba(255, 255, 255, 0.3)'
              e.target.style.boxShadow = 'none'
            }}
          />
        </div>

        <div style={{ marginBottom: '30px' }}>
          <label style={labelStyle}>
            <i className="fas fa-lock" style={{ marginRight: '8px' }}></i>
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            style={inputStyle}
            placeholder="Enter your password"
            onFocus={(e) => {
              e.target.style.borderColor = 'rgba(78, 205, 196, 0.6)'
              e.target.style.boxShadow = '0 0 0 3px rgba(78, 205, 196, 0.1)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = 'rgba(255, 255, 255, 0.3)'
              e.target.style.boxShadow = 'none'
            }}
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          style={buttonStyle}
          onMouseOver={(e) => {
            if (!loading) {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 4px 15px rgba(78, 205, 196, 0.4)'
            }
          }}
          onMouseOut={(e) => {
            if (!loading) {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'none'
            }
          }}
        >
          {loading ? (
            <>
              <i className="fas fa-spinner fa-spin" style={{ marginRight: '8px' }}></i>
              Signing in...
            </>
          ) : (
            <>
              <i className="fas fa-sign-in-alt" style={{ marginRight: '8px' }}></i>
              Sign In
            </>
          )}
        </button>

        <div style={{ textAlign: 'center', marginTop: '25px' }}>
          <p style={{ opacity: '0.8', fontSize: isMobile ? '.85rem': '0.95rem' }}>
            Don't have an account?{' '}
            <Link
              to="/register"
              style={{
                color: '#4ecdc4',
                textDecoration: 'none',
                fontWeight: '600'
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.textDecoration = 'underline'
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.textDecoration = 'none'
              }}
            >
              Create one here
            </Link>
          </p>
        </div>
      </form>
    </div>
  )
}

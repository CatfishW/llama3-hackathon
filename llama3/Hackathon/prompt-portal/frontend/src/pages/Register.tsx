import { FormEvent, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useNavigate, Link } from 'react-router-dom'

export default function Register() {
  const { register } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    
    if (password !== confirmPassword) {
      setErr('Passwords do not match')
      return
    }

    if (password.length < 6) {
      setErr('Password must be at least 6 characters long')
      return
    }

    setLoading(true)
    try {
      await register(email, password)
      nav('/dashboard')
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const containerStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 'calc(100vh - 80px)',
    padding: '40px 20px'
  }

  const formStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '20px',
    padding: '40px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    width: '100%',
    maxWidth: '450px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)'
  }

  const inputStyle = {
    width: '100%',
    padding: '15px 20px',
    borderRadius: '10px',
    border: '1px solid rgba(255, 255, 255, 0.3)',
    background: 'rgba(255, 255, 255, 0.1)',
    color: 'white',
    fontSize: '1rem',
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
    background: 'linear-gradient(45deg, #ff6b6b, #ee5a52)',
    color: 'white',
    border: 'none',
    padding: '15px 20px',
    borderRadius: '10px',
    fontSize: '1.1rem',
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
        <div style={{ textAlign: 'center', marginBottom: '30px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '15px' }}>🚀</div>
          <h2 style={{ fontSize: '2rem', fontWeight: '700', marginBottom: '10px' }}>
            Join the Platform
          </h2>
          <p style={{ opacity: '0.8', fontSize: '1rem' }}>
            Create your account to start building amazing prompts
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
              e.target.style.borderColor = 'rgba(255, 107, 107, 0.6)'
              e.target.style.boxShadow = '0 0 0 3px rgba(255, 107, 107, 0.1)'
            }}
            onBlur={(e) => {
              e.target.style.borderColor = 'rgba(255, 255, 255, 0.3)'
              e.target.style.boxShadow = 'none'
            }}
          />
        </div>

        <div style={{ marginBottom: '20px' }}>
          <label style={labelStyle}>
            <i className="fas fa-lock" style={{ marginRight: '8px' }}></i>
            Password
          </label>
          <input
            type="password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            minLength={6}
            style={inputStyle}
            placeholder="Create a password (min. 6 characters)"
            onFocus={(e) => {
              e.target.style.borderColor = 'rgba(255, 107, 107, 0.6)'
              e.target.style.boxShadow = '0 0 0 3px rgba(255, 107, 107, 0.1)'
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
            Confirm Password
          </label>
          <input
            type="password"
            value={confirmPassword}
            onChange={e => setConfirmPassword(e.target.value)}
            required
            style={inputStyle}
            placeholder="Confirm your password"
            onFocus={(e) => {
              e.target.style.borderColor = 'rgba(255, 107, 107, 0.6)'
              e.target.style.boxShadow = '0 0 0 3px rgba(255, 107, 107, 0.1)'
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
              e.currentTarget.style.boxShadow = '0 4px 15px rgba(255, 107, 107, 0.4)'
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
              Creating account...
            </>
          ) : (
            <>
              <i className="fas fa-user-plus" style={{ marginRight: '8px' }}></i>
              Create Account
            </>
          )}
        </button>

        <div style={{ textAlign: 'center', marginTop: '25px' }}>
          <p style={{ opacity: '0.8', fontSize: '0.95rem' }}>
            Already have an account?{' '}
            <Link
              to="/login"
              style={{
                color: '#ff6b6b',
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
              Sign in instead
            </Link>
          </p>
        </div>
      </form>
    </div>
  )
}

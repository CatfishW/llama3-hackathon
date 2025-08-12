import { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../api'

type User = { id: number; email: string }
type AuthContextT = {
  user: User | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

const AuthContext = createContext<AuthContextT>({
  user: null,
  login: async () => {},
  register: async () => {},
  logout: () => {},
  isLoading: true
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (token) {
      // Validate token by making a request to a protected endpoint
      validateToken()
    } else {
      setIsLoading(false)
    }
  }, [])

  async function validateToken() {
    try {
      // Try to get profile to validate token
      const res = await api.get('/api/profile/me')
      setUser(res.data)
    } catch (error) {
      // Token is invalid, clear it
      logout()
    } finally {
      setIsLoading(false)
    }
  }

  async function register(email: string, password: string) {
    const res = await api.post('/api/auth/register', { email, password })
    // After register, directly login
    await login(email, password)
    return res.data
  }

  async function login(email: string, password: string) {
    const res = await api.post('/api/auth/login', { email, password })
    localStorage.setItem('token', res.data.access_token)
    
    // Get user profile after successful login
    try {
      const profileRes = await api.get('/api/profile/me')
      setUser(profileRes.data)
      localStorage.setItem('user', JSON.stringify(profileRes.data))
    } catch (error) {
      // Fallback to minimal user data
      const me = { id: 0, email }
      localStorage.setItem('user', JSON.stringify(me))
      setUser(me)
    }
  }

  function logout() {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, login, register, logout, isLoading }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)

import { useEffect, useState, useMemo } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { profileAPI } from '../api'
import { useNavigate } from 'react-router-dom'
import { User as UserIcon, Camera, Save, X, Edit, Mail, MapPin, GraduationCap, ExternalLink, Loader2, UserCircle } from 'lucide-react'

type UserProfile = {
  id: number
  email: string
  display_name?: string
  school?: string
  birthday?: string
  bio?: string
  profile_picture?: string
  location?: string
  website?: string
  created_at: string
  updated_at: string
}

export default function Profile() {
  const { user } = useAuth()
  const { theme } = useTheme()
  const navigate = useNavigate()
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const themeColors = useMemo(() => {
    const map: any = {
      slate: { primary: '#6366f1', secondary: '#818cf8', bg: '#0f172a' },
      emerald: { primary: '#10b981', secondary: '#34d399', bg: '#064e3b' },
      rose: { primary: '#f43f5e', secondary: '#fb7185', bg: '#4c0519' },
      amber: { primary: '#f59e0b', secondary: '#fbbf24', bg: '#451a03' },
      violet: { primary: '#8b5cf6', secondary: '#a78bfa', bg: '#2e1065' },
      cyan: { primary: '#06b6d4', secondary: '#22d3ee', bg: '#164e63' },
      orange: { primary: '#f97316', secondary: '#fb923c', bg: '#431407' },
      fuchsia: { primary: '#d946ef', secondary: '#e879f9', bg: '#4a044e' },
      lime: { primary: '#84cc16', secondary: '#a3e635', bg: '#1a2e05' },
      sky: { primary: '#0ea5e9', secondary: '#38bdf8', bg: '#082f49' }
    }
    return map[theme] || map.slate
  }, [theme])
  const [formData, setFormData] = useState({
    display_name: '',
    school: '',
    birthday: '',
    bio: '',
    location: '',
    website: ''
  })

  useEffect(() => {
    loadProfile()
  }, [])

  async function loadProfile() {
    try {
      setLoading(true)
      const res = await profileAPI.getProfile()
      setProfile(res.data)
      setFormData({
        display_name: res.data.display_name || '',
        school: res.data.school || '',
        birthday: res.data.birthday || '',
        bio: res.data.bio || '',
        location: res.data.location || '',
        website: res.data.website || ''
      })
    } catch (e: any) {
      console.error('Failed to load profile:', e)
      setErr('Failed to load profile. Please make sure you are logged in.')
    } finally {
      setLoading(false)
    }
  }

  async function saveProfile() {
    try {
      setSaving(true)
      setErr(null)
      const res = await profileAPI.updateProfile(formData)
      setProfile(res.data)
      setEditing(false)
      // Auto refresh the page after successful save to update all UI components
      setTimeout(() => window.location.reload(), 600)
    } catch (e: any) {
      console.error('Failed to save profile:', e)
      setErr(e?.response?.data?.detail || 'Failed to save profile. Check your connection.')
    } finally {
      setSaving(false)
    }
  }

  async function uploadProfilePicture(file: File) {
    try {
      const res = await profileAPI.uploadPhoto(file)
      setProfile(prev => prev ? { ...prev, profile_picture: res.data.profile_picture } : null)
      // Auto refresh the page after photo update
      setTimeout(() => window.location.reload(), 600)
    } catch (e: any) {
      setErr('Failed to upload profile picture')
    }
  }

  const containerStyle = {
    maxWidth: '800px',
    margin: '0 auto',
    padding: '40px 20px'
  }

  const cardStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '15px',
    padding: '30px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    marginBottom: '20px'
  }

  const inputStyle = {
    width: '100%',
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.3)',
    background: 'rgba(255, 255, 255, 0.1)',
    color: 'white',
    fontSize: '1rem',
    marginTop: '8px'
  }

  const buttonStyle = (variant: 'primary' | 'secondary') => ({
    padding: '12px 24px',
    borderRadius: '8px',
    fontSize: '1rem',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.3s ease',
    border: 'none',
    background: variant === 'primary'
      ? 'linear-gradient(45deg, #4ecdc4, #44a08d)'
      : 'rgba(255, 255, 255, 0.2)',
    color: 'white'
  })

  if (loading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '80vh',
        fontFamily: '"Urbanist", sans-serif'
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontSize: '1.2rem', fontWeight: 800, marginBottom: '24px', letterSpacing: '0.05em', opacity: 0.8, color: '#fff' }}>CALIBRATING NEURAL PROFILE...</div>
          <Loader2 className="animate-spin" size={48} color={themeColors.primary} style={{ margin: '0 auto', filter: `drop-shadow(0 0 10px ${themeColors.primary}66)` }} />
        </div>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: 800, marginBottom: '10px', color: '#fff' }}>
          <UserCircle size={40} style={{ verticalAlign: 'middle', marginRight: '15px', color: themeColors.primary }} />
          My Profile
        </h1>
        <p style={{ opacity: '0.6', fontSize: '1.1rem', fontWeight: 500, color: '#fff' }}>
          Neural Core Identity Configuration
        </p>
      </div>

      {err && (
        <div style={{
          background: 'rgba(255, 107, 107, 0.2)',
          border: '1px solid rgba(255, 107, 107, 0.4)',
          borderRadius: '10px',
          padding: '15px',
          marginBottom: '20px',
          color: '#ff6b6b',
          textAlign: 'center'
        }}>
          <i className="fas fa-exclamation-triangle" style={{ marginRight: '8px' }}></i>
          {err}
        </div>
      )}

      <div style={cardStyle}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: '30px', marginBottom: '30px' }}>
          {/* Profile Picture */}
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: '120px',
              height: '120px',
              borderRadius: '50%',
              background: profile?.profile_picture
                ? `url(${profile.profile_picture})`
                : 'linear-gradient(45deg, #4ecdc4, #44a08d)',
              backgroundSize: 'cover',
              backgroundPosition: 'center',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '3rem',
              color: 'white',
              marginBottom: '15px',
              border: '3px solid rgba(255, 255, 255, 0.3)'
            }}>
              {!profile?.profile_picture && (
                <i className="fas fa-user"></i>
              )}
            </div>

            <input
              type="file"
              accept="image/*"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) uploadProfilePicture(file)
              }}
              style={{ display: 'none' }}
              id="profile-picture-upload"
            />
            <label
              htmlFor="profile-picture-upload"
              style={{
                ...buttonStyle('secondary'),
                fontSize: '0.8rem',
                padding: '10px 16px',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                justifyContent: 'center',
                borderRadius: '12px'
              }}
            >
              <Camera size={14} />
              Change Pulse
            </label>
          </div>

          {/* Basic Info */}
          <div style={{ flex: 1, color: '#fff' }}>
            <h3 style={{ fontSize: '1.8rem', marginBottom: '8px', fontWeight: 800 }}>
              {profile?.display_name || user?.email?.split('@')[0] || 'Unknown Entity'}
            </h3>
            <p style={{ opacity: '0.6', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.95rem' }}>
              <Mail size={16} color={themeColors.primary} />
              {profile?.email}
            </p>
            {profile?.location && (
              <p style={{ opacity: '0.6', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.95rem' }}>
                <MapPin size={16} color={themeColors.primary} />
                {profile.location}
              </p>
            )}
            {profile?.school && (
              <p style={{ opacity: '0.6', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.95rem' }}>
                <GraduationCap size={16} color={themeColors.primary} />
                {profile.school}
              </p>
            )}
            <p style={{ opacity: '0.4', fontSize: '0.8rem', marginTop: '16px', fontWeight: 600, letterSpacing: '0.05em' }}>
              PROVISIONED: {new Date(profile?.created_at || '').toLocaleDateString()}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '15px', marginBottom: '30px' }}>
          <button
            onClick={() => setEditing(!editing)}
            style={{
              ...buttonStyle(editing ? 'secondary' : 'primary'),
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              borderRadius: '12px'
            }}
          >
            {editing ? <X size={18} /> : <Edit size={18} />}
            {editing ? 'Abort Changes' : 'Initialize Edit'}
          </button>

          {editing && (
            <button
              onClick={saveProfile}
              disabled={saving}
              style={{
                ...buttonStyle('primary'),
                opacity: saving ? 0.7 : 1,
                cursor: saving ? 'not-allowed' : 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                borderRadius: '12px',
                background: `linear-gradient(45deg, ${themeColors.primary}, ${themeColors.secondary})`,
                boxShadow: `0 4px 15px ${themeColors.primary}44`
              }}
            >
              {saving ? (
                <>
                  <Loader2 className="animate-spin" size={18} />
                  Synchronizing...
                </>
              ) : (
                <>
                  <Save size={18} />
                  Commit Changes
                </>
              )}
            </button>
          )}
        </div>

        {editing ? (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
            <div>
              <label style={{ color: 'rgba(255, 255, 255, 0.9)', display: 'block', marginBottom: '5px' }}>
                Display Name
              </label>
              <input
                type="text"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                style={inputStyle}
                placeholder="Your display name"
              />
            </div>

            <div>
              <label style={{ color: 'rgba(255, 255, 255, 0.9)', display: 'block', marginBottom: '5px' }}>
                School/University
              </label>
              <input
                type="text"
                value={formData.school}
                onChange={(e) => setFormData({ ...formData, school: e.target.value })}
                style={inputStyle}
                placeholder="Your school or university"
              />
            </div>

            <div>
              <label style={{ color: 'rgba(255, 255, 255, 0.9)', display: 'block', marginBottom: '5px' }}>
                Birthday
              </label>
              <input
                type="date"
                value={formData.birthday}
                onChange={(e) => setFormData({ ...formData, birthday: e.target.value })}
                style={inputStyle}
              />
            </div>

            <div>
              <label style={{ color: 'rgba(255, 255, 255, 0.9)', display: 'block', marginBottom: '5px' }}>
                Location
              </label>
              <input
                type="text"
                value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                style={inputStyle}
                placeholder="City, Country"
              />
            </div>

            <div>
              <label style={{ color: 'rgba(255, 255, 255, 0.9)', display: 'block', marginBottom: '5px' }}>
                Website
              </label>
              <input
                type="url"
                value={formData.website}
                onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                style={inputStyle}
                placeholder="https://your-website.com"
              />
            </div>

            <div style={{ gridColumn: '1 / -1' }}>
              <label style={{ color: 'rgba(255, 255, 255, 0.9)', display: 'block', marginBottom: '5px' }}>
                Bio
              </label>
              <textarea
                value={formData.bio}
                onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                style={{ ...inputStyle, minHeight: '100px', resize: 'vertical' }}
                placeholder="Tell us about yourself..."
                maxLength={500}
              />
              <div style={{ textAlign: 'right', fontSize: '0.8rem', opacity: '0.6', marginTop: '5px' }}>
                {formData.bio.length}/500 characters
              </div>
            </div>
          </div>
        ) : (
          <div>
            {profile?.bio && (
              <div style={{ marginBottom: '20px' }}>
                <h4 style={{ marginBottom: '10px', fontSize: '1.2rem' }}>About</h4>
                <p style={{ lineHeight: '1.6', opacity: '0.8' }}>{profile.bio}</p>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
              {profile?.birthday && (
                <div>
                  <h5 style={{ marginBottom: '5px', opacity: '0.8' }}>Birthday</h5>
                  <p>{new Date(profile.birthday).toLocaleDateString()}</p>
                </div>
              )}

              {profile?.website && (
                <div>
                  <h5 style={{ marginBottom: '5px', opacity: '0.8' }}>Website</h5>
                  <a
                    href={profile.website}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ color: '#4ecdc4', textDecoration: 'none' }}
                  >
                    <i className="fas fa-external-link-alt" style={{ marginRight: '5px' }}></i>
                    Visit Website
                  </a>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

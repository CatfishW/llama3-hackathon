import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { api } from '../api'

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
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
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
      const res = await api.get('/api/profile/me')
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
      setErr('Failed to load profile')
    } finally {
      setLoading(false)
    }
  }

  async function saveProfile() {
    try {
      setSaving(true)
      const res = await api.put('/api/profile/update', formData)
      setProfile(res.data)
      setEditing(false)
      setErr(null)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  async function uploadProfilePicture(file: File) {
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await api.post('/api/profile/upload-photo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
      setProfile(prev => prev ? { ...prev, profile_picture: res.data.profile_picture } : null)
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
      <div style={containerStyle}>
        <div style={{ textAlign: 'center', padding: '60px' }}>
          <i className="fas fa-spinner fa-spin" style={{ fontSize: '2rem', marginBottom: '20px' }}></i>
          <p>Loading profile...</p>
        </div>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: '700', marginBottom: '10px' }}>
          <i className="fas fa-user-circle" style={{ marginRight: '15px' }}></i>
          My Profile
        </h1>
        <p style={{ opacity: '0.8', fontSize: '1.1rem' }}>
          Manage your personal information and settings
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
                fontSize: '0.9rem',
                padding: '8px 16px',
                cursor: 'pointer',
                display: 'inline-block'
              }}
            >
              <i className="fas fa-camera" style={{ marginRight: '5px' }}></i>
              Change Photo
            </label>
          </div>

          {/* Basic Info */}
          <div style={{ flex: 1 }}>
            <h3 style={{ fontSize: '1.5rem', marginBottom: '10px' }}>
              {profile?.display_name || user?.email || 'User'}
            </h3>
            <p style={{ opacity: '0.8', marginBottom: '5px' }}>
              <i className="fas fa-envelope" style={{ marginRight: '8px' }}></i>
              {profile?.email}
            </p>
            {profile?.location && (
              <p style={{ opacity: '0.8', marginBottom: '5px' }}>
                <i className="fas fa-map-marker-alt" style={{ marginRight: '8px' }}></i>
                {profile.location}
              </p>
            )}
            {profile?.school && (
              <p style={{ opacity: '0.8', marginBottom: '5px' }}>
                <i className="fas fa-graduation-cap" style={{ marginRight: '8px' }}></i>
                {profile.school}
              </p>
            )}
            <p style={{ opacity: '0.6', fontSize: '0.9rem', marginTop: '10px' }}>
              Member since {new Date(profile?.created_at || '').toLocaleDateString()}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '15px', marginBottom: '30px' }}>
          <button
            onClick={() => setEditing(!editing)}
            style={buttonStyle(editing ? 'secondary' : 'primary')}
          >
            <i className={`fas ${editing ? 'fa-times' : 'fa-edit'}`} style={{ marginRight: '8px' }}></i>
            {editing ? 'Cancel' : 'Edit Profile'}
          </button>
          
          {editing && (
            <button
              onClick={saveProfile}
              disabled={saving}
              style={{
                ...buttonStyle('primary'),
                opacity: saving ? 0.7 : 1,
                cursor: saving ? 'not-allowed' : 'pointer'
              }}
            >
              {saving ? (
                <>
                  <i className="fas fa-spinner fa-spin" style={{ marginRight: '8px' }}></i>
                  Saving...
                </>
              ) : (
                <>
                  <i className="fas fa-save" style={{ marginRight: '8px' }}></i>
                  Save Changes
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

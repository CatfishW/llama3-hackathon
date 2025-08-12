import { useState, useEffect } from 'react'
import { useAuth } from '../auth/AuthContext'
import { api } from '../api'

type UserSettings = {
  email_notifications: boolean
  friend_requests: boolean
  message_notifications: boolean
  leaderboard_visibility: boolean
  profile_visibility: 'public' | 'friends' | 'private'
  theme: 'dark' | 'light' | 'auto'
  language: string
  timezone: string
}

export default function Settings() {
  const { user, logout } = useAuth()
  const [settings, setSettings] = useState<UserSettings>({
    email_notifications: true,
    friend_requests: true,
    message_notifications: true,
    leaderboard_visibility: true,
    profile_visibility: 'public',
    theme: 'dark',
    language: 'en',
    timezone: 'UTC'
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [changePasswordForm, setChangePasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  })
  const [passwordChanging, setPasswordChanging] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  useEffect(() => {
    loadSettings()
  }, [])

  async function loadSettings() {
    try {
      setLoading(true)
      const res = await api.get('/api/settings')
      setSettings(res.data)
    } catch (e) {
      setErr('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  async function saveSettings() {
    try {
      setSaving(true)
      await api.put('/api/settings', settings)
      setSuccess('Settings saved successfully!')
      setErr(null)
      setTimeout(() => setSuccess(null), 3000)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  async function changePassword() {
    if (changePasswordForm.new_password !== changePasswordForm.confirm_password) {
      setErr('New passwords do not match')
      return
    }

    if (changePasswordForm.new_password.length < 6) {
      setErr('New password must be at least 6 characters')
      return
    }

    try {
      setPasswordChanging(true)
      await api.post('/api/auth/change-password', {
        current_password: changePasswordForm.current_password,
        new_password: changePasswordForm.new_password
      })
      setChangePasswordForm({
        current_password: '',
        new_password: '',
        confirm_password: ''
      })
      setSuccess('Password changed successfully!')
      setErr(null)
      setTimeout(() => setSuccess(null), 3000)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to change password')
    } finally {
      setPasswordChanging(false)
    }
  }

  async function deleteAccount() {
    const confirmText = 'delete my account permanently'
    const userInput = prompt(
      `This action cannot be undone. All your data will be permanently deleted.\n\nType "${confirmText}" to confirm:`
    )
    
    if (userInput !== confirmText) {
      return
    }

    try {
      await api.delete('/api/auth/account')
      logout()
      alert('Your account has been deleted')
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to delete account')
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
    marginBottom: '25px'
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

  const selectStyle = {
    ...inputStyle,
    cursor: 'pointer'
  }

  const buttonStyle = (variant: 'primary' | 'secondary' | 'danger') => {
    const variants = {
      primary: 'linear-gradient(45deg, #4ecdc4, #44a08d)',
      secondary: 'rgba(255, 255, 255, 0.2)',
      danger: 'linear-gradient(45deg, #ff6b6b, #ee5a52)'
    }
    
    return {
      background: variants[variant],
      color: 'white',
      border: 'none',
      padding: '12px 24px',
      borderRadius: '8px',
      fontSize: '1rem',
      fontWeight: '600',
      cursor: 'pointer',
      transition: 'all 0.3s ease'
    }
  }

  const switchStyle = {
    position: 'relative' as const,
    display: 'inline-block',
    width: '50px',
    height: '24px'
  }

  const switchSliderStyle = (checked: boolean) => ({
    position: 'absolute' as const,
    cursor: 'pointer',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: checked ? '#4ecdc4' : 'rgba(255, 255, 255, 0.3)',
    borderRadius: '24px',
    transition: 'all 0.3s ease',
    '::before': {
      position: 'absolute' as const,
      content: '""',
      height: '18px',
      width: '18px',
      left: checked ? '29px' : '3px',
      bottom: '3px',
      background: 'white',
      borderRadius: '50%',
      transition: 'all 0.3s ease'
    }
  })

  if (loading) {
    return (
      <div style={containerStyle}>
        <div style={{ textAlign: 'center', padding: '60px' }}>
          <i className="fas fa-spinner fa-spin" style={{ fontSize: '2rem', marginBottom: '20px' }}></i>
          <p>Loading settings...</p>
        </div>
      </div>
    )
  }

  return (
    <div style={containerStyle}>
      <div style={{ textAlign: 'center', marginBottom: '40px' }}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: '700', marginBottom: '10px' }}>
          <i className="fas fa-cog" style={{ marginRight: '15px' }}></i>
          Settings
        </h1>
        <p style={{ opacity: '0.8', fontSize: '1.1rem' }}>
          Manage your account preferences and privacy settings
        </p>
      </div>

      {(err || success) && (
        <div style={{
          background: err ? 'rgba(255, 107, 107, 0.2)' : 'rgba(76, 175, 80, 0.2)',
          border: `1px solid ${err ? 'rgba(255, 107, 107, 0.4)' : 'rgba(76, 175, 80, 0.4)'}`,
          borderRadius: '10px',
          padding: '15px',
          marginBottom: '20px',
          color: err ? '#ff6b6b' : '#4caf50',
          textAlign: 'center'
        }}>
          <i className={`fas ${err ? 'fa-exclamation-triangle' : 'fa-check-circle'}`} style={{ marginRight: '8px' }}></i>
          {err || success}
        </div>
      )}

      {/* Privacy Settings */}
      <div style={cardStyle}>
        <h3 style={{ fontSize: '1.5rem', marginBottom: '25px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <i className="fas fa-shield-alt"></i>
          Privacy & Visibility
        </h3>

        <div style={{ display: 'grid', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              Profile Visibility
            </label>
            <select
              value={settings.profile_visibility}
              onChange={(e) => setSettings({ ...settings, profile_visibility: e.target.value as any })}
              style={selectStyle}
            >
              <option value="public" style={{ background: '#333', color: 'white' }}>Public - Everyone can see</option>
              <option value="friends" style={{ background: '#333', color: 'white' }}>Friends only</option>
              <option value="private" style={{ background: '#333', color: 'white' }}>Private - Hidden</option>
            </select>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h4 style={{ marginBottom: '5px' }}>Leaderboard Visibility</h4>
              <p style={{ fontSize: '0.9rem', opacity: '0.7' }}>Show your scores on public leaderboards</p>
            </div>
            <label style={switchStyle}>
              <input
                type="checkbox"
                checked={settings.leaderboard_visibility}
                onChange={(e) => setSettings({ ...settings, leaderboard_visibility: e.target.checked })}
                style={{ opacity: 0, width: 0, height: 0 }}
              />
              <span style={switchSliderStyle(settings.leaderboard_visibility)}></span>
            </label>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h4 style={{ marginBottom: '5px' }}>Allow Friend Requests</h4>
              <p style={{ fontSize: '0.9rem', opacity: '0.7' }}>Let other users send you friend requests</p>
            </div>
            <label style={switchStyle}>
              <input
                type="checkbox"
                checked={settings.friend_requests}
                onChange={(e) => setSettings({ ...settings, friend_requests: e.target.checked })}
                style={{ opacity: 0, width: 0, height: 0 }}
              />
              <span style={switchSliderStyle(settings.friend_requests)}></span>
            </label>
          </div>
        </div>
      </div>

      {/* Notification Settings */}
      <div style={cardStyle}>
        <h3 style={{ fontSize: '1.5rem', marginBottom: '25px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <i className="fas fa-bell"></i>
          Notifications
        </h3>

        <div style={{ display: 'grid', gap: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h4 style={{ marginBottom: '5px' }}>Email Notifications</h4>
              <p style={{ fontSize: '0.9rem', opacity: '0.7' }}>Receive important updates via email</p>
            </div>
            <label style={switchStyle}>
              <input
                type="checkbox"
                checked={settings.email_notifications}
                onChange={(e) => setSettings({ ...settings, email_notifications: e.target.checked })}
                style={{ opacity: 0, width: 0, height: 0 }}
              />
              <span style={switchSliderStyle(settings.email_notifications)}></span>
            </label>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <h4 style={{ marginBottom: '5px' }}>Message Notifications</h4>
              <p style={{ fontSize: '0.9rem', opacity: '0.7' }}>Get notified when you receive new messages</p>
            </div>
            <label style={switchStyle}>
              <input
                type="checkbox"
                checked={settings.message_notifications}
                onChange={(e) => setSettings({ ...settings, message_notifications: e.target.checked })}
                style={{ opacity: 0, width: 0, height: 0 }}
              />
              <span style={switchSliderStyle(settings.message_notifications)}></span>
            </label>
          </div>
        </div>
      </div>

      {/* Appearance Settings */}
      <div style={cardStyle}>
        <h3 style={{ fontSize: '1.5rem', marginBottom: '25px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <i className="fas fa-palette"></i>
          Appearance & Language
        </h3>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              Theme
            </label>
            <select
              value={settings.theme}
              onChange={(e) => setSettings({ ...settings, theme: e.target.value as any })}
              style={selectStyle}
            >
              <option value="dark" style={{ background: '#333', color: 'white' }}>Dark</option>
              <option value="light" style={{ background: '#333', color: 'white' }}>Light</option>
              <option value="auto" style={{ background: '#333', color: 'white' }}>Auto (System)</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              Language
            </label>
            <select
              value={settings.language}
              onChange={(e) => setSettings({ ...settings, language: e.target.value })}
              style={selectStyle}
            >
              <option value="en" style={{ background: '#333', color: 'white' }}>English</option>
              <option value="es" style={{ background: '#333', color: 'white' }}>Español</option>
              <option value="fr" style={{ background: '#333', color: 'white' }}>Français</option>
              <option value="de" style={{ background: '#333', color: 'white' }}>Deutsch</option>
              <option value="zh" style={{ background: '#333', color: 'white' }}>中文</option>
            </select>
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              Timezone
            </label>
            <select
              value={settings.timezone}
              onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
              style={selectStyle}
            >
              <option value="UTC" style={{ background: '#333', color: 'white' }}>UTC</option>
              <option value="America/New_York" style={{ background: '#333', color: 'white' }}>Eastern Time</option>
              <option value="America/Chicago" style={{ background: '#333', color: 'white' }}>Central Time</option>
              <option value="America/Denver" style={{ background: '#333', color: 'white' }}>Mountain Time</option>
              <option value="America/Los_Angeles" style={{ background: '#333', color: 'white' }}>Pacific Time</option>
              <option value="Europe/London" style={{ background: '#333', color: 'white' }}>GMT</option>
              <option value="Europe/Paris" style={{ background: '#333', color: 'white' }}>CET</option>
              <option value="Asia/Tokyo" style={{ background: '#333', color: 'white' }}>JST</option>
            </select>
          </div>
        </div>
      </div>

      {/* Change Password */}
      <div style={cardStyle}>
        <h3 style={{ fontSize: '1.5rem', marginBottom: '25px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <i className="fas fa-key"></i>
          Change Password
        </h3>

        <div style={{ display: 'grid', gap: '20px', maxWidth: '400px' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              Current Password
            </label>
            <input
              type="password"
              value={changePasswordForm.current_password}
              onChange={(e) => setChangePasswordForm({ ...changePasswordForm, current_password: e.target.value })}
              style={inputStyle}
              placeholder="Enter current password"
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              New Password
            </label>
            <input
              type="password"
              value={changePasswordForm.new_password}
              onChange={(e) => setChangePasswordForm({ ...changePasswordForm, new_password: e.target.value })}
              style={inputStyle}
              placeholder="Enter new password"
              minLength={6}
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              Confirm New Password
            </label>
            <input
              type="password"
              value={changePasswordForm.confirm_password}
              onChange={(e) => setChangePasswordForm({ ...changePasswordForm, confirm_password: e.target.value })}
              style={inputStyle}
              placeholder="Confirm new password"
            />
          </div>

          <button
            onClick={changePassword}
            disabled={passwordChanging || !changePasswordForm.current_password || !changePasswordForm.new_password}
            style={{
              ...buttonStyle('primary'),
              opacity: passwordChanging || !changePasswordForm.current_password || !changePasswordForm.new_password ? 0.6 : 1
            }}
          >
            {passwordChanging ? (
              <>
                <i className="fas fa-spinner fa-spin" style={{ marginRight: '8px' }}></i>
                Changing...
              </>
            ) : (
              <>
                <i className="fas fa-key" style={{ marginRight: '8px' }}></i>
                Change Password
              </>
            )}
          </button>
        </div>
      </div>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '15px', justifyContent: 'center', flexWrap: 'wrap' }}>
        <button
          onClick={saveSettings}
          disabled={saving}
          style={{
            ...buttonStyle('primary'),
            opacity: saving ? 0.6 : 1
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
              Save Settings
            </>
          )}
        </button>

        <button
          onClick={deleteAccount}
          style={buttonStyle('danger')}
        >
          <i className="fas fa-trash" style={{ marginRight: '8px' }}></i>
          Delete Account
        </button>
      </div>
    </div>
  )
}

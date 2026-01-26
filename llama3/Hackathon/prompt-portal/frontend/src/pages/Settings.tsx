import { useState, useEffect } from 'react'
import { useAuth } from '../auth/AuthContext'
import { api, modelsAPI } from '../api'
import { useTutorial } from '../contexts/TutorialContext'
import { motion, AnimatePresence } from 'framer-motion'

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

type ModelInfo = {
  name: string
  provider: string
  model: string
  description?: string
  features: string[]
  maxTokens?: number
  supportsFunctions: boolean
  supportsVision: boolean
}

type ModelStatus = {
  name: string
  provider: string
  model: string
  description?: string
  features: string[]
  maxTokens?: number
  supportsFunctions: boolean
  supportsVision: boolean
  is_active: boolean
  status_message: string
  response_time_ms?: number
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
  const [isMobile, setIsMobile] = useState(false)

  // Model selection state
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([])
  const [selectedModel, setSelectedModel] = useState<ModelInfo | null>(null)
  const [loadingModels, setLoadingModels] = useState(true)
  const [selectingModel, setSelectingModel] = useState(false)

  // Model management state
  const [showModelDialog, setShowModelDialog] = useState(false)
  const [editingModel, setEditingModel] = useState<ModelInfo | null>(null)
  const [modelForm, setModelForm] = useState({
    name: '',
    provider: 'openai',
    model: '',
    apiBase: '',
    apiKey: '',
    description: '',
    features: '',
    maxTokens: 4096,
    supportsFunctions: true,
    supportsVision: false
  })

  // Model status state
  const [modelsStatus, setModelsStatus] = useState<ModelStatus[]>([])
  const [loadingStatus, setLoadingStatus] = useState(false)
  const [testingConnection, setTestingConnection] = useState(false)
  const [testResult, setTestResult] = useState<{ success: boolean, message: string } | null>(null)
  const { runTutorial } = useTutorial()

  useEffect(() => {
    const hasSeenSettingsTutorial = localStorage.getItem('tutorial_seen_settings')
    if (!hasSeenSettingsTutorial && !loading) {
      runTutorial([
        { target: '#settings-check-status', title: 'LLM Diagnostics', content: 'Verify the health of all configured AI models and check latency in real-time.', position: 'bottom' },
        { target: '#settings-add-model', title: 'Bring Your Own Brain', content: 'Connect any OpenAI-compatible API to expand your agent capabilities.', position: 'bottom' },
        { target: '#settings-privacy-card', title: 'Data Sovereignty', content: 'Control who sees your profile and how your scores are displayed on leaderboards.', position: 'top' },
        { target: '#settings-notif-card', title: 'Alert Preferences', content: 'Manage which system events trigger email or in-app notifications.', position: 'top' },
        { target: '#settings-password-card', title: 'Security Perimeter', content: 'Regularly update your credentials to maintain mission security.', position: 'top' },
      ]);
      localStorage.setItem('tutorial_seen_settings', 'true');
    }
  }, [loading, runTutorial]);

  useEffect(() => {
    loadSettings()
    loadModels()
  }, [])

  useEffect(() => {
    const upd = () => setIsMobile(window.innerWidth < 720);
    upd();
    window.addEventListener('resize', upd);
    window.addEventListener('orientationchange', upd);
    return () => {
      window.removeEventListener('resize', upd);
      window.removeEventListener('orientationchange', upd)
    }
  }, [])

  async function loadSettings() {
    try {
      setLoading(true)
      const res = await api.get('/api/settings/')
      setSettings(res.data)
    } catch (e) {
      setErr('Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  async function loadModels() {
    try {
      setLoadingModels(true)
      const [availableRes, selectedRes] = await Promise.all([
        modelsAPI.getAvailable(),
        modelsAPI.getSelected()
      ])
      setAvailableModels(availableRes.data)
      setSelectedModel(selectedRes.data)
    } catch (e) {
      console.error('Failed to load models:', e)
    } finally {
      setLoadingModels(false)
    }
  }

  async function loadModelsStatus() {
    try {
      setLoadingStatus(true)
      const res = await modelsAPI.getStatus()
      setModelsStatus(res.data)
    } catch (e) {
      console.error('Failed to load models status:', e)
    } finally {
      setLoadingStatus(false)
    }
  }

  async function testModelConnection() {
    if (!modelForm.apiBase || !modelForm.apiKey) {
      setTestResult({ success: false, message: 'Please enter API Base URL and API Key' })
      return
    }

    try {
      setTestingConnection(true)
      setTestResult(null)
      const res = await modelsAPI.testConnectivity(modelForm.apiBase, modelForm.apiKey, modelForm.model)
      setTestResult({
        success: res.data.success,
        message: res.data.message + (res.data.model_name ? ` (Model: ${res.data.model_name})` : '')
      })
      // If successful and model was auto-detected, fill in the model field
      if (res.data.success && res.data.model_name && !modelForm.model) {
        setModelForm(prev => ({ ...prev, model: res.data.model_name }))
      }
    } catch (e: any) {
      setTestResult({
        success: false,
        message: e?.response?.data?.message || 'Connection test failed'
      })
    } finally {
      setTestingConnection(false)
    }
  }

  async function selectModelHandler(modelName: string) {
    try {
      setSelectingModel(true)
      await modelsAPI.selectModel(modelName)

      // Update selected model locally
      const model = availableModels.find(m => m.name === modelName)
      if (model) {
        setSelectedModel(model)
      }

      setSuccess(`Successfully switched to ${modelName}!`)
      setErr(null)
      setTimeout(() => {
        window.location.reload()
      }, 1000)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to select model')
    } finally {
      setSelectingModel(false)
    }
  }

  async function openAddModelDialog() {
    setEditingModel(null)
    setTestResult(null)
    setModelForm({
      name: '',
      provider: 'openai',
      model: '',
      apiBase: '',
      apiKey: '',
      description: '',
      features: '',
      maxTokens: 4096,
      supportsFunctions: true,
      supportsVision: false
    })
    setShowModelDialog(true)
  }

  async function openEditModelDialog(model: ModelInfo) {
    try {
      // Fetch full config including API key
      const res = await modelsAPI.getModelConfig(model.name)
      setEditingModel(model)
      setTestResult(null)
      setModelForm({
        name: model.name,
        provider: res.data.provider,
        model: res.data.model,
        apiBase: res.data.apiBase,
        apiKey: res.data.apiKey,
        description: res.data.description || '',
        features: (res.data.features || []).join(', '),
        maxTokens: res.data.maxTokens || 4096,
        supportsFunctions: res.data.supportsFunctions !== false,
        supportsVision: res.data.supportsVision === true
      })
      setShowModelDialog(true)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to load model config')
    }
  }

  async function saveModel() {
    try {
      const modelData = {
        ...modelForm,
        features: modelForm.features.split(',').map(f => f.trim()).filter(f => f)
      }

      if (editingModel) {
        // Update existing model
        await modelsAPI.updateModel(editingModel.name, modelData)
        setSuccess(`Successfully updated ${editingModel.name}!`)
      } else {
        // Add new model
        await modelsAPI.addModel(modelData)
        setSuccess(`Successfully added ${modelForm.name}!`)
      }

      setShowModelDialog(false)
      setErr(null)
      await loadModels()
      setTimeout(() => setSuccess(null), 3000)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to save model')
    }
  }

  async function deleteModelHandler(modelName: string) {
    if (!confirm(`Are you sure you want to delete "${modelName}"? This cannot be undone.`)) {
      return
    }

    try {
      await modelsAPI.deleteModel(modelName)
      setSuccess(`Successfully deleted ${modelName}!`)
      setErr(null)
      await loadModels()
      setTimeout(() => setSuccess(null), 3000)
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to delete model')
    }
  }

  async function saveSettings() {
    try {
      setSaving(true)
      await api.put('/api/settings/', settings)
      setSuccess('Settings saved successfully!')
      setErr(null)
      setTimeout(() => {
        window.location.reload()
      }, 1000)
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
    padding: isMobile ? '28px 14px' : '40px 20px'
  }

  const cardStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '15px',
    padding: isMobile ? '22px 18px' : '30px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    marginBottom: '25px'
  }

  const inputStyle = {
    width: '100%',
    padding: isMobile ? '10px 14px' : '12px 16px',
    borderRadius: '8px',
    border: '1px solid rgba(255, 255, 255, 0.3)',
    background: 'rgba(255, 255, 255, 0.1)',
    color: 'white',
    fontSize: isMobile ? '.95rem' : '1rem',
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

      {/* AI Model Selection */}
      <div style={cardStyle}>
        <h3 style={{ fontSize: '1.5rem', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <i className="fas fa-robot"></i>
          AI Model Selection
        </h3>
        <p style={{ fontSize: '0.95rem', opacity: '0.8', marginBottom: '25px' }}>
          Choose the AI model that powers your conversations and interactions
        </p>

        {loadingModels ? (
          <div style={{ textAlign: 'center', padding: '30px' }}>
            <i className="fas fa-spinner fa-spin" style={{ fontSize: '1.5rem', opacity: '0.6' }}></i>
            <p style={{ marginTop: '10px', opacity: '0.7' }}>Loading models...</p>
          </div>
        ) : (
          <>
            <div style={{ marginBottom: '20px', display: 'flex', gap: '10px', justifyContent: 'flex-end', flexWrap: 'wrap' }}>
              <button
                id="settings-check-status"
                onClick={loadModelsStatus}
                disabled={loadingStatus}
                style={{
                  background: 'rgba(255, 255, 255, 0.1)',
                  border: '1px solid rgba(255, 255, 255, 0.3)',
                  color: 'white',
                  padding: '10px 20px',
                  borderRadius: '8px',
                  fontSize: '0.9rem',
                  cursor: loadingStatus ? 'wait' : 'pointer',
                  fontWeight: '500',
                  transition: 'all 0.3s ease'
                }}
              >
                {loadingStatus ? (
                  <>
                    <i className="fas fa-spinner fa-spin" style={{ marginRight: '8px' }}></i>
                    Checking...
                  </>
                ) : (
                  <>
                    <i className="fas fa-plug" style={{ marginRight: '8px' }}></i>
                    Check LLM Status
                  </>
                )}
              </button>
              <button
                id="settings-add-model"
                onClick={openAddModelDialog}
                style={{
                  ...buttonStyle('primary'),
                  padding: '10px 20px',
                  fontSize: '0.9rem'
                }}
              >
                <i className="fas fa-plus" style={{ marginRight: '8px' }}></i>
                Add Custom Model
              </button>
            </div>

            {/* LLM Status Display */}
            {modelsStatus.length > 0 && (
              <div style={{
                background: 'rgba(0, 0, 0, 0.2)',
                borderRadius: '10px',
                padding: '15px',
                marginBottom: '20px'
              }}>
                <h4 style={{ fontSize: '1rem', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <i className="fas fa-signal"></i>
                  LLM Connectivity Status
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                  {modelsStatus.map(status => (
                    <div key={status.name} style={{
                      background: status.is_active ? 'rgba(76, 175, 80, 0.15)' : 'rgba(255, 107, 107, 0.15)',
                      border: `1px solid ${status.is_active ? 'rgba(76, 175, 80, 0.4)' : 'rgba(255, 107, 107, 0.4)'}`,
                      borderRadius: '8px',
                      padding: '10px 15px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '10px',
                      minWidth: '200px'
                    }}>
                      <div style={{
                        width: '10px',
                        height: '10px',
                        borderRadius: '50%',
                        background: status.is_active ? '#4caf50' : '#ff6b6b',
                        boxShadow: status.is_active ? '0 0 8px rgba(76, 175, 80, 0.6)' : '0 0 8px rgba(255, 107, 107, 0.6)'
                      }}></div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: '600', fontSize: '0.9rem' }}>{status.name}</div>
                        <div style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                          {status.status_message}
                          {status.response_time_ms && ` (${status.response_time_ms}ms)`}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(300px, 1fr))', gap: '15px' }}>
              {availableModels.map((model) => {
                const isSelected = selectedModel?.name === model.name

                return (
                  <div
                    key={model.name}
                    onClick={() => !selectingModel && selectModelHandler(model.name)}
                    style={{
                      background: isSelected ? 'linear-gradient(135deg, rgba(78, 205, 196, 0.2), rgba(68, 160, 141, 0.2))' : 'rgba(255, 255, 255, 0.05)',
                      border: isSelected ? '2px solid #4ecdc4' : '2px solid rgba(255, 255, 255, 0.1)',
                      borderRadius: '12px',
                      padding: '20px',
                      cursor: selectingModel ? 'wait' : 'pointer',
                      transition: 'all 0.3s ease',
                      position: 'relative' as const,
                      overflow: 'hidden'
                    }}
                    onMouseEnter={(e) => {
                      if (!selectingModel && !isSelected) {
                        e.currentTarget.style.transform = 'translateY(-2px)'
                        e.currentTarget.style.borderColor = 'rgba(78, 205, 196, 0.5)'
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.08)'
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!isSelected) {
                        e.currentTarget.style.transform = 'translateY(0)'
                        e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.1)'
                        e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                      }
                    }}
                  >
                    {isSelected && (
                      <div style={{
                        position: 'absolute' as const,
                        top: '10px',
                        right: '10px',
                        background: '#4ecdc4',
                        borderRadius: '50%',
                        width: '30px',
                        height: '30px',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        boxShadow: '0 2px 8px rgba(78, 205, 196, 0.4)'
                      }}>
                        <i className="fas fa-check" style={{ fontSize: '0.9rem', color: 'white' }}></i>
                      </div>
                    )}

                    <div style={{ marginBottom: '12px' }}>
                      <h4 style={{ fontSize: '1.2rem', fontWeight: '600', marginBottom: '5px' }}>
                        {model.name}
                      </h4>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', opacity: '0.7' }}>
                        <i className="fas fa-server" style={{ fontSize: '0.75rem' }}></i>
                        <span>{model.provider}</span>
                        {model.supportsVision && (
                          <>
                            <span>•</span>
                            <i className="fas fa-eye" title="Vision Support"></i>
                          </>
                        )}
                      </div>
                    </div>

                    {model.description && (
                      <p style={{ fontSize: '0.9rem', opacity: '0.8', marginBottom: '12px', lineHeight: '1.4' }}>
                        {model.description}
                      </p>
                    )}

                    {model.features && model.features.length > 0 && (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '12px', marginBottom: '12px' }}>
                        {model.features.slice(0, 4).map((feature, idx) => (
                          <span
                            key={idx}
                            style={{
                              background: 'rgba(78, 205, 196, 0.2)',
                              color: '#4ecdc4',
                              padding: '4px 10px',
                              borderRadius: '12px',
                              fontSize: '0.75rem',
                              fontWeight: '500'
                            }}
                          >
                            {feature}
                          </span>
                        ))}
                      </div>
                    )}

                    {/* Model management buttons */}
                    <div style={{ display: 'flex', gap: '8px', marginTop: '12px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '12px' }}
                      onClick={(e) => e.stopPropagation()}>
                      <button
                        onClick={() => openEditModelDialog(model)}
                        style={{
                          flex: 1,
                          background: 'rgba(255, 255, 255, 0.1)',
                          border: '1px solid rgba(255, 255, 255, 0.2)',
                          color: 'white',
                          padding: '8px 12px',
                          borderRadius: '6px',
                          fontSize: '0.85rem',
                          cursor: 'pointer',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'rgba(78, 205, 196, 0.2)'
                          e.currentTarget.style.borderColor = '#4ecdc4'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 255, 255, 0.1)'
                          e.currentTarget.style.borderColor = 'rgba(255, 255, 255, 0.2)'
                        }}
                      >
                        <i className="fas fa-edit" style={{ marginRight: '6px' }}></i>
                        Edit
                      </button>
                      <button
                        onClick={() => deleteModelHandler(model.name)}
                        style={{
                          flex: 1,
                          background: 'rgba(255, 107, 107, 0.1)',
                          border: '1px solid rgba(255, 107, 107, 0.3)',
                          color: '#ff6b6b',
                          padding: '8px 12px',
                          borderRadius: '6px',
                          fontSize: '0.85rem',
                          cursor: 'pointer',
                          transition: 'all 0.3s ease'
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 107, 107, 0.2)'
                          e.currentTarget.style.borderColor = '#ff6b6b'
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.background = 'rgba(255, 107, 107, 0.1)'
                          e.currentTarget.style.borderColor = 'rgba(255, 107, 107, 0.3)'
                        }}
                      >
                        <i className="fas fa-trash" style={{ marginRight: '6px' }}></i>
                        Delete
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          </>
        )}
      </div>

      {/* Privacy Settings */}
      <div id="settings-privacy-card" style={cardStyle}>
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
      <div id="settings-notif-card" style={cardStyle}>
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
      <div id="settings-password-card" style={cardStyle}>
        <h3 style={{ fontSize: '1.5rem', marginBottom: '25px', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <i className="fas fa-key"></i>
          Change Password
        </h3>

        <form onSubmit={(e) => { e.preventDefault(); changePassword(); }} style={{ display: 'grid', gap: '20px', maxWidth: '400px' }}>
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
              autoComplete="current-password"
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
              autoComplete="new-password"
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
              autoComplete="new-password"
            />
          </div>

          <button
            type="submit"
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
        </form>
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

      {/* Model Configuration Dialog */}
      {showModelDialog && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px',
        }}>
          <div style={{
            ...cardStyle,
            maxWidth: '600px',
            width: '100%',
            maxHeight: '90vh',
            overflowY: 'auto',
            position: 'relative',
          }}>
            <h3 style={{ fontSize: '1.5rem', marginBottom: '25px', display: 'flex', alignItems: 'center', gap: '10px' }}>
              <i className={editingModel ? "fas fa-edit" : "fas fa-plus-circle"}></i>
              {editingModel ? 'Edit Model' : 'Add Custom Model'}
            </h3>

            <form onSubmit={(e) => { e.preventDefault(); saveModel(); }} style={{ display: 'grid', gap: '20px' }}>
              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  Model Name *
                </label>
                <input
                  type="text"
                  value={modelForm.name}
                  onChange={(e) => setModelForm({ ...modelForm, name: e.target.value })}
                  placeholder="e.g., GPT-4 Turbo"
                  style={inputStyle}
                  disabled={editingModel !== null}
                />
                {editingModel && (
                  <small style={{ color: '#888', fontSize: '0.85rem' }}>Model name cannot be changed</small>
                )}
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  Provider *
                </label>
                <input
                  type="text"
                  value={modelForm.provider}
                  onChange={(e) => setModelForm({ ...modelForm, provider: e.target.value })}
                  placeholder="e.g., OpenAI, OpenRouter"
                  style={inputStyle}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  Model ID *
                </label>
                <input
                  type="text"
                  value={modelForm.model}
                  onChange={(e) => setModelForm({ ...modelForm, model: e.target.value })}
                  placeholder="e.g., gpt-4-turbo-preview"
                  style={inputStyle}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  API Base URL *
                </label>
                <input
                  type="url"
                  value={modelForm.apiBase}
                  onChange={(e) => setModelForm({ ...modelForm, apiBase: e.target.value })}
                  placeholder="e.g., https://api.openai.com/v1"
                  style={inputStyle}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  API Key *
                </label>
                <input
                  type="password"
                  value={modelForm.apiKey}
                  onChange={(e) => setModelForm({ ...modelForm, apiKey: e.target.value })}
                  placeholder="Enter API key (use 'not-needed' if not required)"
                  style={inputStyle}
                  autoComplete="off"
                />
                <small style={{ color: '#888', fontSize: '0.8rem' }}>
                  Tip: For AGAII Cloud models, use "not-needed" as the API key
                </small>
              </div>

              {/* Test Connection Button */}
              <div>
                <button
                  type="button"
                  onClick={testModelConnection}
                  disabled={testingConnection || !modelForm.apiBase}
                  style={{
                    background: 'rgba(78, 205, 196, 0.2)',
                    border: '1px solid #4ecdc4',
                    color: '#4ecdc4',
                    padding: '10px 20px',
                    borderRadius: '8px',
                    fontSize: '0.9rem',
                    cursor: testingConnection ? 'wait' : 'pointer',
                    fontWeight: '500',
                    transition: 'all 0.3s ease',
                    width: '100%'
                  }}
                >
                  {testingConnection ? (
                    <>
                      <i className="fas fa-spinner fa-spin" style={{ marginRight: '8px' }}></i>
                      Testing Connection...
                    </>
                  ) : (
                    <>
                      <i className="fas fa-plug" style={{ marginRight: '8px' }}></i>
                      Test Connection
                    </>
                  )}
                </button>
                {testResult && (
                  <div style={{
                    marginTop: '10px',
                    padding: '10px 15px',
                    borderRadius: '8px',
                    background: testResult.success ? 'rgba(76, 175, 80, 0.15)' : 'rgba(255, 107, 107, 0.15)',
                    border: `1px solid ${testResult.success ? 'rgba(76, 175, 80, 0.4)' : 'rgba(255, 107, 107, 0.4)'}`,
                    color: testResult.success ? '#4caf50' : '#ff6b6b',
                    fontSize: '0.9rem',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}>
                    <i className={`fas ${testResult.success ? 'fa-check-circle' : 'fa-exclamation-circle'}`}></i>
                    {testResult.message}
                  </div>
                )}
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  Description
                </label>
                <textarea
                  value={modelForm.description}
                  onChange={(e) => setModelForm({ ...modelForm, description: e.target.value })}
                  placeholder="Brief description of this model"
                  rows={3}
                  style={{
                    ...inputStyle,
                    resize: 'vertical',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <div>
                <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                  Features (comma-separated)
                </label>
                <input
                  type="text"
                  value={modelForm.features}
                  onChange={(e) => setModelForm({ ...modelForm, features: e.target.value })}
                  placeholder="e.g., Fast responses, Code generation"
                  style={inputStyle}
                />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '15px' }}>
                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                    Max Tokens
                  </label>
                  <input
                    type="number"
                    value={modelForm.maxTokens}
                    onChange={(e) => setModelForm({ ...modelForm, maxTokens: parseInt(e.target.value) || 0 })}
                    placeholder="e.g., 4096"
                    style={inputStyle}
                  />
                </div>

                <div>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                    Capabilities
                  </label>
                  <div style={{ display: 'flex', gap: '15px', marginTop: '8px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={modelForm.supportsFunctions}
                        onChange={(e) => setModelForm({ ...modelForm, supportsFunctions: e.target.checked })}
                        style={{ cursor: 'pointer' }}
                      />
                      Functions
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '5px', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={modelForm.supportsVision}
                        onChange={(e) => setModelForm({ ...modelForm, supportsVision: e.target.checked })}
                        style={{ cursor: 'pointer' }}
                      />
                      Vision
                    </label>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '15px', marginTop: '30px', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  onClick={() => {
                    setShowModelDialog(false);
                    setEditingModel(null);
                    setModelForm({
                      name: '',
                      provider: '',
                      model: '',
                      apiBase: '',
                      apiKey: '',
                      description: '',
                      features: '',
                      maxTokens: 4096,
                      supportsFunctions: false,
                      supportsVision: false,
                    });
                  }}
                  style={{
                    padding: '12px 24px',
                    borderRadius: '8px',
                    border: 'none',
                    background: 'rgba(255, 255, 255, 0.1)',
                    color: 'white',
                    cursor: 'pointer',
                    fontWeight: '500',
                    transition: 'all 0.3s ease',
                  }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={!modelForm.name || !modelForm.provider || !modelForm.model || !modelForm.apiBase || !modelForm.apiKey}
                  style={{
                    ...buttonStyle('primary'),
                    opacity: (!modelForm.name || !modelForm.provider || !modelForm.model || !modelForm.apiBase || !modelForm.apiKey) ? 0.5 : 1,
                  }}
                >
                  <i className="fas fa-save" style={{ marginRight: '8px' }}></i>
                  {editingModel ? 'Update Model' : 'Add Model'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

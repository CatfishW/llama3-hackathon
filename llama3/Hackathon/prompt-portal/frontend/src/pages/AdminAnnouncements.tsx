import { useState, useEffect } from 'react'
import { announcementsAPI } from '../api'
import { useAuth } from '../auth/AuthContext'

interface Announcement {
  id: number
  title: string
  content: string
  announcement_type: 'info' | 'warning' | 'success' | 'error'
  priority: number
  is_active: boolean
  created_by: string
  created_at: string
  expires_at: string | null
  updated_at: string
}

export default function AdminAnnouncements() {
  const { user } = useAuth()
  const [announcements, setAnnouncements] = useState<Announcement[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  
  const [formData, setFormData] = useState({
    title: '',
    content: '',
    announcement_type: 'info' as 'info' | 'warning' | 'success' | 'error',
    priority: 0,
    expires_at: ''
  })

  const isAdmin = user?.email === '1819409756@qq.com'

  useEffect(() => {
    if (isAdmin) {
      fetchAnnouncements()
    }
  }, [isAdmin])

  const fetchAnnouncements = async () => {
    try {
      setLoading(true)
      const response = await announcementsAPI.getAll()
      setAnnouncements(response.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to fetch announcements')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const data = {
        ...formData,
        expires_at: formData.expires_at ? new Date(formData.expires_at).toISOString() : null
      }

      if (editingId) {
        await announcementsAPI.update(editingId, data)
      } else {
        await announcementsAPI.create(data)
      }

      setShowForm(false)
      setEditingId(null)
      resetForm()
      fetchAnnouncements()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save announcement')
    }
  }

  const handleEdit = (announcement: Announcement) => {
    setFormData({
      title: announcement.title,
      content: announcement.content,
      announcement_type: announcement.announcement_type,
      priority: announcement.priority,
      expires_at: announcement.expires_at ? announcement.expires_at.split('T')[0] : ''
    })
    setEditingId(announcement.id)
    setShowForm(true)
  }

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this announcement?')) return
    
    try {
      await announcementsAPI.delete(id)
      fetchAnnouncements()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete announcement')
    }
  }

  const handleToggle = async (id: number) => {
    try {
      await announcementsAPI.toggle(id)
      fetchAnnouncements()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to toggle announcement')
    }
  }

  const resetForm = () => {
    setFormData({
      title: '',
      content: '',
      announcement_type: 'info',
      priority: 0,
      expires_at: ''
    })
  }

  if (!isAdmin) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <h2>Access Denied</h2>
        <p>You do not have permission to access this page.</p>
      </div>
    )
  }

  return (
    <div style={{ padding: '40px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        marginBottom: '30px'
      }}>
        <h1 style={{ margin: 0 }}>📢 Announcement Management</h1>
        <button
          onClick={() => {
            setShowForm(!showForm)
            setEditingId(null)
            resetForm()
          }}
          style={{
            padding: '12px 24px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            border: 'none',
            borderRadius: '10px',
            color: 'white',
            cursor: 'pointer',
            fontSize: '16px',
            fontWeight: '600',
            boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
            transition: 'transform 0.2s'
          }}
          onMouseEnter={e => e.currentTarget.style.transform = 'translateY(-2px)'}
          onMouseLeave={e => e.currentTarget.style.transform = 'translateY(0)'}
        >
          {showForm ? '✕ Cancel' : '+ New Announcement'}
        </button>
      </div>

      {error && (
        <div style={{
          padding: '15px',
          background: 'rgba(255, 100, 100, 0.2)',
          border: '1px solid rgba(255, 100, 100, 0.5)',
          borderRadius: '10px',
          marginBottom: '20px',
          color: '#ffcccc'
        }}>
          {error}
        </div>
      )}

      {showForm && (
        <form onSubmit={handleSubmit} style={{
          background: 'rgba(255, 255, 255, 0.1)',
          padding: '30px',
          borderRadius: '15px',
          marginBottom: '30px',
          backdropFilter: 'blur(10px)',
          boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)'
        }}>
          <h2 style={{ marginTop: 0 }}>
            {editingId ? 'Edit Announcement' : 'Create New Announcement'}
          </h2>
          
          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              Title *
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={e => setFormData({ ...formData, title: e.target.value })}
              required
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '2px solid rgba(255, 255, 255, 0.2)',
                background: 'rgba(255, 255, 255, 0.1)',
                color: 'white',
                fontSize: '16px'
              }}
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
              Content *
            </label>
            <textarea
              value={formData.content}
              onChange={e => setFormData({ ...formData, content: e.target.value })}
              required
              rows={4}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '2px solid rgba(255, 255, 255, 0.2)',
                background: 'rgba(255, 255, 255, 0.1)',
                color: 'white',
                fontSize: '16px',
                fontFamily: 'inherit',
                resize: 'vertical'
              }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '15px', marginBottom: '20px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                Type
              </label>
              <select
                value={formData.announcement_type}
                onChange={e => setFormData({ ...formData, announcement_type: e.target.value as any })}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '8px',
                  border: '2px solid rgba(255, 255, 255, 0.2)',
                  background: 'rgba(255, 255, 255, 0.1)',
                  color: 'white',
                  fontSize: '16px'
                }}
              >
                <option value="info">ℹ Info</option>
                <option value="success">✓ Success</option>
                <option value="warning">⚠ Warning</option>
                <option value="error">✕ Error</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                Priority (0-10)
              </label>
              <input
                type="number"
                min="0"
                max="10"
                value={formData.priority}
                onChange={e => setFormData({ ...formData, priority: parseInt(e.target.value) })}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '8px',
                  border: '2px solid rgba(255, 255, 255, 0.2)',
                  background: 'rgba(255, 255, 255, 0.1)',
                  color: 'white',
                  fontSize: '16px'
                }}
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                Expires At (Optional)
              </label>
              <input
                type="date"
                value={formData.expires_at}
                onChange={e => setFormData({ ...formData, expires_at: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '8px',
                  border: '2px solid rgba(255, 255, 255, 0.2)',
                  background: 'rgba(255, 255, 255, 0.1)',
                  color: 'white',
                  fontSize: '16px'
                }}
              />
            </div>
          </div>

          <button
            type="submit"
            style={{
              padding: '12px 32px',
              background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
              border: 'none',
              borderRadius: '10px',
              color: 'white',
              cursor: 'pointer',
              fontSize: '16px',
              fontWeight: '600',
              boxShadow: '0 4px 15px rgba(17, 153, 142, 0.4)'
            }}
          >
            {editingId ? 'Update Announcement' : 'Create Announcement'}
          </button>
        </form>
      )}

      {loading ? (
        <div style={{ textAlign: 'center', padding: '40px' }}>Loading...</div>
      ) : (
        <div style={{ display: 'grid', gap: '20px' }}>
          {announcements.map(announcement => (
            <div
              key={announcement.id}
              style={{
                background: 'rgba(255, 255, 255, 0.1)',
                padding: '25px',
                borderRadius: '15px',
                backdropFilter: 'blur(10px)',
                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
                border: `2px solid ${announcement.is_active ? 'rgba(56, 239, 125, 0.3)' : 'rgba(255, 255, 255, 0.1)'}`
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '15px' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                    <span style={{ 
                      fontSize: '12px',
                      padding: '4px 12px',
                      background: announcement.announcement_type === 'info' ? 'rgba(102, 126, 234, 0.3)' :
                                 announcement.announcement_type === 'success' ? 'rgba(56, 239, 125, 0.3)' :
                                 announcement.announcement_type === 'warning' ? 'rgba(245, 87, 108, 0.3)' :
                                 'rgba(250, 112, 154, 0.3)',
                      borderRadius: '6px',
                      fontWeight: '600'
                    }}>
                      {announcement.announcement_type.toUpperCase()}
                    </span>
                    <span style={{ fontSize: '12px', opacity: 0.7 }}>
                      Priority: {announcement.priority}
                    </span>
                    {!announcement.is_active && (
                      <span style={{ 
                        fontSize: '12px',
                        padding: '4px 12px',
                        background: 'rgba(255, 255, 255, 0.1)',
                        borderRadius: '6px'
                      }}>
                        INACTIVE
                      </span>
                    )}
                  </div>
                  <h3 style={{ margin: '0 0 10px 0', fontSize: '20px' }}>{announcement.title}</h3>
                  <p style={{ margin: '0 0 10px 0', opacity: 0.9, whiteSpace: 'pre-wrap' }}>
                    {announcement.content}
                  </p>
                  <div style={{ fontSize: '13px', opacity: 0.6 }}>
                    Created: {new Date(announcement.created_at).toLocaleString()} 
                    {announcement.expires_at && ` • Expires: ${new Date(announcement.expires_at).toLocaleDateString()}`}
                  </div>
                </div>
                
                <div style={{ display: 'flex', gap: '10px', marginLeft: '20px' }}>
                  <button
                    onClick={() => handleToggle(announcement.id)}
                    style={{
                      padding: '8px 16px',
                      background: announcement.is_active ? 'rgba(255, 200, 0, 0.2)' : 'rgba(56, 239, 125, 0.2)',
                      border: 'none',
                      borderRadius: '8px',
                      color: 'white',
                      cursor: 'pointer',
                      fontSize: '14px',
                      fontWeight: '500'
                    }}
                  >
                    {announcement.is_active ? 'Deactivate' : 'Activate'}
                  </button>
                  <button
                    onClick={() => handleEdit(announcement)}
                    style={{
                      padding: '8px 16px',
                      background: 'rgba(102, 126, 234, 0.2)',
                      border: 'none',
                      borderRadius: '8px',
                      color: 'white',
                      cursor: 'pointer',
                      fontSize: '14px',
                      fontWeight: '500'
                    }}
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => handleDelete(announcement.id)}
                    style={{
                      padding: '8px 16px',
                      background: 'rgba(250, 112, 154, 0.2)',
                      border: 'none',
                      borderRadius: '8px',
                      color: 'white',
                      cursor: 'pointer',
                      fontSize: '14px',
                      fontWeight: '500'
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && announcements.length === 0 && (
        <div style={{
          textAlign: 'center',
          padding: '60px',
          background: 'rgba(255, 255, 255, 0.1)',
          borderRadius: '15px',
          backdropFilter: 'blur(10px)'
        }}>
          <p style={{ fontSize: '18px', opacity: 0.7 }}>No announcements yet. Create your first one!</p>
        </div>
      )}
    </div>
  )
}

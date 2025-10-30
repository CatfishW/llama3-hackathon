import axios from 'axios'

// Use relative URLs - no absolute domain
const API_BASE = (import.meta as any).env.VITE_API_BASE || ''

export const api = axios.create({
  baseURL: API_BASE
})

// Attach token if exists
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// Response interceptor to handle authentication errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token is invalid or expired, clear it and redirect to login
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      // Only redirect if we're not already on login/register pages
      if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register') && window.location.pathname !== '/') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Profile API
export const profileAPI = {
  getProfile: () => api.get('/api/profile/me'),
  updateProfile: (data: any) => api.put('/api/profile/update', data),
  uploadPhoto: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/api/profile/upload-photo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  getPrivacySettings: () => api.get('/api/profile/privacy'),
  updatePrivacySettings: (data: any) => api.put('/api/profile/privacy', data),
  getNotificationSettings: () => api.get('/api/profile/notifications'),
  updateNotificationSettings: (data: any) => api.put('/api/profile/notifications', data),
  updateSecuritySettings: (data: any) => api.put('/api/profile/security', data),
  updateOnlineStatus: (isOnline: boolean) => api.put('/api/profile/online-status', { is_online: isOnline })
}

// Friends API
export const friendsAPI = {
  searchUsers: (query: string) => api.get(`/api/friends/search?q=${encodeURIComponent(query)}`),
  sendFriendRequest: (userId: number) => api.post('/api/friends/request', { requested_id: userId }),
  getFriendRequests: () => api.get('/api/friends/requests'),
  getSentRequests: () => api.get('/api/friends/sent-requests'),
  acceptFriendRequest: (friendshipId: number) => api.put(`/api/friends/accept/${friendshipId}`),
  rejectFriendRequest: (friendshipId: number) => api.put(`/api/friends/reject/${friendshipId}`),
  cancelFriendRequest: (friendshipId: number) => api.delete(`/api/friends/cancel/${friendshipId}`),
  getFriends: () => api.get('/api/friends/list'),
  removeFriend: (friendId: number) => api.delete(`/api/friends/remove/${friendId}`),
  blockUser: (userId: number) => api.put(`/api/friends/block/${userId}`),
  getFriendSuggestions: () => api.get('/api/friends/suggestions')
}

// Messages API
export const messagesAPI = {
  getConversations: () => api.get('/api/messages/conversations'),
  getConversationMessages: (userId: number, limit = 50, offset = 0) => 
    api.get(`/api/messages/conversation/${userId}?limit=${limit}&offset=${offset}`),
  sendMessage: (data: any) => api.post('/api/messages/send', data),
  markMessageRead: (messageId: number) => api.put(`/api/messages/mark-read/${messageId}`),
  markConversationRead: (userId: number) => api.put(`/api/messages/mark-conversation-read/${userId}`),
  deleteMessage: (messageId: number) => api.delete(`/api/messages/delete/${messageId}`),
  getUnreadCount: () => api.get('/api/messages/unread-count'),
  searchMessages: (query: string, userId?: number) => {
    const params = new URLSearchParams({ q: query })
    if (userId) params.append('user_id', userId.toString())
    return api.get(`/api/messages/search?${params}`)
  }
}

// Settings API
export const settingsAPI = {
  getSettings: () => api.get('/api/settings/'),
  updateGeneralSettings: (data: any) => api.put('/api/settings/general', data),
  updatePrivacySettings: (data: any) => api.put('/api/settings/privacy', data),
  updateNotificationSettings: (data: any) => api.put('/api/settings/notifications', data),
  deleteAccount: () => api.delete('/api/settings/account'),
  exportData: () => api.get('/api/settings/export')
}

// Leaderboard API (Maze Game only - LAM/Manual modes)
export const leaderboardAPI = {
  submitScore: (data: any) => api.post('/api/leaderboard/submit', data),
  getLeaderboard: async (limit: number = 20, skip: number = 0, mode?: 'lam'|'manual') => {
    const q = new URLSearchParams({ limit: String(limit), skip: String(skip) })
    if (mode) q.set('mode', mode)
    const url = `/api/leaderboard/?${q.toString()}`
    console.log('[MAZE LEADERBOARD API] Calling:', url)
    const res = await api.get(url)
    const total = Number(res.headers['x-total-count'] ?? '0')
    console.log('[MAZE LEADERBOARD API] Response total:', total, 'entries:', res.data.length)
    return { data: res.data, total }
  },
  getStats: async () => {
    const res = await api.get('/api/leaderboard/stats')
    return res.data as { participants: number; registered_users: number }
  }
}

// Driving Stats API (Completely separate system with own endpoints)
export const drivingStatsAPI = {
  submitScore: (data: {
    template_id: number
    session_id: string
    score: number
    message_count: number
    duration_seconds: number
    player_option: string
    agent_option: string
  }) => {
    console.log('[DRIVING API] Submitting score to /api/driving/submit:', data)
    return api.post('/api/driving/submit', data)
  },
  getLeaderboard: async (limit: number = 50, skip: number = 0) => {
    const q = new URLSearchParams({ 
      limit: String(limit), 
      skip: String(skip)
    })
    const url = `/api/driving/leaderboard?${q.toString()}`
    console.log('[DRIVING API] GET', url)
    const res = await api.get(url)
    const total = Number(res.headers['x-total-count'] ?? '0')
    console.log('[DRIVING API] Response: total=', total, 'entries=', res.data.length)
    if (res.data.length > 0) {
      console.log('[DRIVING API] First entry:', res.data[0])
    }
    return { data: res.data, total }
  },
  getStats: async () => {
    console.log('[DRIVING API] GET /api/driving/stats')
    const res = await api.get('/api/driving/stats')
    console.log('[DRIVING API] Stats:', res.data)
    return res.data as { participants: number; registered_users: number; total_scores: number }
  }
}

// Templates API
export const templatesAPI = {
  getTemplates: (skip: number = 0, limit: number = 50, mine: boolean = true) => 
    api.get(`/api/templates?skip=${skip}&limit=${limit}&mine=${mine}`),
  getTemplate: (id: number) => api.get(`/api/templates/${id}`),
  getTemplatePublic: (id: number) => api.get(`/api/templates/public/${id}`),
  createTemplate: (data: any) => api.post('/api/templates', data),
  updateTemplate: (id: number, data: any) => api.patch(`/api/templates/${id}`, data),
  deleteTemplate: (id: number) => api.delete(`/api/templates/${id}`)
}

export const chatbotAPI = {
  getPresets: () => api.get('/api/chatbot/presets'),
  listSessions: () => api.get('/api/chatbot/sessions'),
  createSession: (data: any) => api.post('/api/chatbot/sessions', data),
  updateSession: (id: number, data: any) => api.patch(`/api/chatbot/sessions/${id}`, data),
  resetSession: (id: number) => api.post(`/api/chatbot/sessions/${id}/reset`),
  deleteSession: (id: number) => api.delete(`/api/chatbot/sessions/${id}`),
  getMessages: (id: number, limit = 200) => api.get(`/api/chatbot/sessions/${id}/messages?limit=${limit}`),
  sendMessage: (data: any) => api.post('/api/chatbot/messages', data)
}

// LLM API (Direct inference endpoints)
export const llmAPI = {
  // Standard (non-streaming) chat
  chat: (data: any) => api.post('/api/llm/chat', data),
  chatSession: (data: any) => api.post('/api/llm/chat/session', data),
  
  // Streaming chat - returns EventSource for Server-Sent Events
  chatStream: async (
    data: any,
    onChunk: (chunk: string) => void,
    onComplete: () => void,
    onError: (error: any) => void
  ) => {
    const token = localStorage.getItem('token')
    const url = API_BASE ? `${API_BASE}/api/llm/chat/stream` : '/api/llm/chat/stream'
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('Response body is not readable')
    }

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))
            if (data.error) {
              onError(new Error(data.error))
            } else if (data.done) {
              onComplete()
            } else if (data.content) {
              onChunk(data.content)
            }
          }
        }
      }
    } catch (error) {
      onError(error)
    }
  },

  // Streaming session chat
  chatSessionStream: async (
    data: any,
    onChunk: (chunk: string) => void,
    onComplete: () => void,
    onError: (error: any) => void
  ) => {
    const token = localStorage.getItem('token')
    const url = API_BASE ? `${API_BASE}/api/llm/chat/session/stream` : '/api/llm/chat/session/stream'
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
      },
      body: JSON.stringify(data)
    })

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }

    const reader = response.body?.getReader()
    const decoder = new TextDecoder()

    if (!reader) {
      throw new Error('Response body is not readable')
    }

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = JSON.parse(line.slice(6))
            if (data.error) {
              onError(new Error(data.error))
            } else if (data.done) {
              onComplete()
            } else if (data.content) {
              onChunk(data.content)
            }
          }
        }
      }
    } catch (error) {
      onError(error)
    }
  },
  
  // Session management
  getSessionHistory: (sessionId: string) => api.get(`/api/llm/chat/session/${sessionId}/history`),
  clearSession: (sessionId: string) => api.delete(`/api/llm/chat/session/${sessionId}`),
  healthCheck: () => api.get('/api/llm/health')
}

// WebSocket connection helper
export const createWebSocketConnection = (token: string) => {
  // Use relative WebSocket URL if no API_BASE, otherwise convert http to ws
  const wsURL = API_BASE 
    ? API_BASE.replace('http', 'ws') + `/ws/${token}`
    : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/${token}`
  return new WebSocket(wsURL)
}

// Announcements API
export const announcementsAPI = {
  getActive: () => api.get('/api/announcements/'),
  getAll: () => api.get('/api/announcements/all'),
  getById: (id: number) => api.get(`/api/announcements/${id}`),
  create: (data: any) => api.post('/api/announcements/', data),
  update: (id: number, data: any) => api.put(`/api/announcements/${id}`, data),
  delete: (id: number) => api.delete(`/api/announcements/${id}`),
  toggle: (id: number) => api.put(`/api/announcements/${id}/toggle`)
}

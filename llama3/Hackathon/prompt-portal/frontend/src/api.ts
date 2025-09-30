import axios from 'axios'

const API_BASE = (import.meta as any).env.VITE_API_BASE || 'http://localhost:8000'

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

// Leaderboard API
export const leaderboardAPI = {
  submitScore: (data: any) => api.post('/api/leaderboard/submit', data),
  getLeaderboard: (limit: number = 20) => api.get(`/api/leaderboard/?limit=${limit}`)
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

// WebSocket connection helper
export const createWebSocketConnection = (token: string) => {
  const wsURL = API_BASE.replace('http', 'ws') + `/ws/${token}`
  return new WebSocket(wsURL)
}

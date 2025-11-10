import axios from 'axios'

export const api = axios.create({ baseURL: '/api' })

export type ChatSession = {
  id: number
  session_key: string
  title: string
  template_id?: number | null
  system_prompt?: string | null
  temperature?: number | null
  top_p?: number | null
  max_tokens?: number | null
  message_count: number
  created_at: string
  updated_at: string
  last_used_at: string
}

export type ChatMessage = {
  id: number
  session_id: number
  role: 'user' | 'assistant'
  content: string
  created_at: string
  request_id?: string | null
}

export type Template = {
  id: number
  title: string
  content: string
  description?: string
  is_active: boolean
  version: number
}

export async function createSession(title?: string) {
  const { data } = await api.post<ChatSession>('/chat/sessions', { title })
  return data
}

export async function listSessions() {
  const { data } = await api.get<ChatSession[]>('/chat/sessions')
  return data
}

export async function getMessages(sessionId: number) {
  const { data } = await api.get<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`)
  return data
}

export async function sendMessage(sessionId: number, content: string, images?: string[]) {
  const payload: any = { session_id: sessionId, content }
  if (images && images.length > 0) payload.images = images
  const { data } = await api.post('/chat/messages', payload)
  return data
}

export async function listTemplates() {
  const { data } = await api.get<Template[]>('/templates/')
  return data
}

export async function createTemplate(title: string, content: string, description?: string) {
  const { data } = await api.post<Template>('/templates/', { title, content, description })
  return data
}

export async function updateTemplate(id: number, updates: Partial<Template>) {
  const { data } = await api.patch<Template>(`/templates/${id}`, updates)
  return data
}

export async function deleteTemplate(id: number) {
  await api.delete(`/templates/${id}`)
}

export async function deleteSession(sessionId: number) {
  await api.delete(`/chat/sessions/${sessionId}`)
}

export async function updateSession(sessionId: number, updates: Partial<ChatSession>) {
  const { data } = await api.patch<ChatSession>(`/chat/sessions/${sessionId}`, updates)
  return data
}



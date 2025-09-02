import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { api } from '../api'

interface Template {
  id: number
  title: string
  description?: string
  content: string
  is_active: boolean
  version: number
  created_at: string
  updated_at: string
  user_id: number
}

interface TemplateContextType {
  templates: Template[]
  loading: boolean
  refreshTemplates: () => Promise<void>
  addTemplate: (template: Template) => void
  updateTemplate: (id: number, template: Partial<Template>) => void
  removeTemplate: (id: number) => void
}

const TemplateContext = createContext<TemplateContextType | undefined>(undefined)

export function TemplateProvider({ children }: { children: ReactNode }) {
  const [templates, setTemplates] = useState<Template[]>([])
  const [loading, setLoading] = useState(true)

  const refreshTemplates = async () => {
    try {
      setLoading(true)
      const res = await api.get('/api/templates')
      setTemplates(res.data)
    } catch (e) {
      console.error('Failed to load templates', e)
    } finally {
      setLoading(false)
    }
  }

  const addTemplate = (template: Template) => {
    setTemplates(prev => [template, ...prev])
  }

  const updateTemplate = (id: number, template: Partial<Template>) => {
    setTemplates(prev => prev.map(t => t.id === id ? { ...t, ...template } : t))
  }

  const removeTemplate = (id: number) => {
    setTemplates(prev => prev.filter(t => t.id !== id))
  }

  useEffect(() => {
    refreshTemplates()
  }, [])

  return (
    <TemplateContext.Provider value={{
      templates,
      loading,
      refreshTemplates,
      addTemplate,
      updateTemplate,
      removeTemplate
    }}>
      {children}
    </TemplateContext.Provider>
  )
}

export function useTemplates() {
  const context = useContext(TemplateContext)
  if (context === undefined) {
    throw new Error('useTemplates must be used within a TemplateProvider')
  }
  return context
}

import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { chatbotAPI } from '../api'
import { useTemplates } from '../contexts/TemplateContext'

type ChatPreset = {
  key: string
  title: string
  description?: string
  system_prompt: string
}

type ChatSession = {
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
  last_message_preview?: string | null
}

type ChatMessage = {
  id: number
  session_id: number
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  metadata?: Record<string, any> | null
  request_id?: string | null
  created_at: string
}

type DraftState = {
  title: string
  system_prompt: string
  temperature: number | null
  top_p: number | null
  max_tokens: number | null
  template_id: number | null
  preset_key: string | null
  prompt_source: 'preset' | 'template' | 'custom'
}

const bubbleStyles: Record<string, CSSProperties> = {
  user: {
    background: 'linear-gradient(135deg, rgba(99,102,241,0.25), rgba(129,140,248,0.25))',
    alignSelf: 'flex-end',
    border: '1px solid rgba(129,140,248,0.45)',
  },
  assistant: {
    background: 'rgba(15,23,42,0.45)',
    border: '1px solid rgba(148,163,184,0.25)',
    alignSelf: 'flex-start',
  },
  system: {
    background: 'rgba(94,234,212,0.18)',
    border: '1px solid rgba(94,234,212,0.4)',
    alignSelf: 'center',
    color: '#0f172a'
  }
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const style = bubbleStyles[message.role] || bubbleStyles.assistant
  const timestamp = new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  return (
    <div style={{ maxWidth: '70%', padding: '14px 18px', borderRadius: '18px', display: 'flex', flexDirection: 'column', gap: '10px', ...style }}>
      <div style={{ fontSize: message.role === 'system' ? '0.75rem' : '0.85rem', opacity: 0.85, whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
        {message.content}
      </div>
      <div style={{ fontSize: '0.7rem', alignSelf: 'flex-end', color: 'rgba(226,232,240,0.8)' }}>{timestamp}</div>
    </div>
  )
}

export default function ChatStudio() {
  const { templates } = useTemplates()

  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [presets, setPresets] = useState<ChatPreset[]>([])
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionDraft, setSessionDraft] = useState<DraftState | null>(null)
  const [draftDirty, setDraftDirtyFlag] = useState<boolean>(false)
  const [inputValue, setInputValue] = useState<string>('')
  const [loadingSessions, setLoadingSessions] = useState<boolean>(true)
  const [loadingMessages, setLoadingMessages] = useState<boolean>(false)
  const [sending, setSending] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [showPromptEditor, setShowPromptEditor] = useState<boolean>(false)
  const [savingPrompt, setSavingPrompt] = useState<boolean>(false)
  const [streamingMessageId, setStreamingMessageId] = useState<number | null>(null)
  const messageContainerRef = useRef<HTMLDivElement | null>(null)
  const streamingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const selectedSession = useMemo(
    () => sessions.find(s => s.id === selectedSessionId) || null,
    [sessions, selectedSessionId]
  )

  const hasAssistantMessage = useMemo(
    () => messages.some(msg => msg.role === 'assistant'),
    [messages]
  )

  const hasUserMessage = useMemo(
    () => messages.some(msg => msg.role === 'user'),
    [messages]
  )

  // Cleanup streaming timeout on unmount
  useEffect(() => {
    return () => {
      if (streamingTimeoutRef.current) {
        clearTimeout(streamingTimeoutRef.current)
      }
    }
  }, [])

  useEffect(() => {
    (async () => {
      try {
        const [presetRes, sessionRes] = await Promise.all([
          chatbotAPI.getPresets(),
          chatbotAPI.listSessions()
        ])
        setPresets(presetRes.data as ChatPreset[])
        setSessions(sessionRes.data as ChatSession[])
        if ((sessionRes.data as ChatSession[]).length) {
          setSelectedSessionId(sessionRes.data[0].id)
        }
      } catch (e) {
        setErrorMessage('Failed to load chat sessions.')
      }
      setLoadingSessions(false)
    })()
  }, [])

  // Rehydrate the local draft whenever the active session or its stored parameters change.
  useEffect(() => {
    if (!selectedSession) {
      setMessages([])
      setSessionDraft(null)
      setShowPromptEditor(false)
      return
    }

    const normalizedSystemPrompt = (selectedSession.system_prompt ?? '').trim()
    const matchedPreset = presets.find(p => p.system_prompt.trim() === normalizedSystemPrompt)
    const matchedTemplate = selectedSession.template_id 
      ? templates.find(t => t.id === selectedSession.template_id)
      : null

    let promptSource: 'preset' | 'template' | 'custom' = 'custom'
    if (matchedPreset) promptSource = 'preset'
    else if (matchedTemplate) promptSource = 'template'

    const draft: DraftState = {
      title: selectedSession.title,
      system_prompt: normalizedSystemPrompt || (presets[0]?.system_prompt || ''),
      temperature: selectedSession.temperature ?? 0.6,
      top_p: selectedSession.top_p ?? 0.9,
      max_tokens: selectedSession.max_tokens ?? 512,
      template_id: selectedSession.template_id ?? null,
      preset_key: matchedPreset?.key ?? null,
      prompt_source: promptSource,
    }

    setSessionDraft(draft)
    setDraftDirtyFlag(false)
    setShowPromptEditor(false)

    const currentSessionId = selectedSession.id
    let cancelled = false

    ;(async () => {
      try {
        setLoadingMessages(true)
        const res = await chatbotAPI.getMessages(currentSessionId)
        if (!cancelled) {
          setMessages(res.data as ChatMessage[])
        }
      } catch (e) {
        if (!cancelled) {
          setErrorMessage('Unable to load conversation messages.')
        }
      } finally {
        if (!cancelled) {
          setLoadingMessages(false)
        }
      }
    })()

    return () => {
      cancelled = true
    }
  }, [selectedSession?.id, selectedSession?.system_prompt, selectedSession?.temperature, selectedSession?.top_p, selectedSession?.max_tokens, selectedSession?.template_id, presets, templates])

  // Auto-detect preset matches once presets load so the dropdown reflects the current prompt.
  useEffect(() => {
    if (!sessionDraft || sessionDraft.preset_key) return
    const promptValue = (sessionDraft.system_prompt ?? '').trim()
    if (!promptValue) return
    const match = presets.find(p => p.system_prompt.trim() === promptValue)
    if (!match) return
    setSessionDraft(prev => (prev ? { ...prev, preset_key: match.key, prompt_source: 'preset' } : prev))
  }, [presets, sessionDraft?.system_prompt, sessionDraft?.preset_key])

  // Keep the latest messages in view as new responses stream in.
  useEffect(() => {
    const container = messageContainerRef.current
    if (!container) return
    container.scrollTop = container.scrollHeight
  }, [messages, loadingMessages, selectedSessionId, streamingMessageId])

  // Debounced hot update for template/preset changes - auto-saves prompt changes immediately
  const hotUpdateTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  
  const hotUpdatePrompt = async (
    templateId: number | null,
    systemPrompt: string,
    presetKey: string | null
  ) => {
    if (!selectedSession) return

    // Clear any pending timeout
    if (hotUpdateTimeoutRef.current) {
      clearTimeout(hotUpdateTimeoutRef.current)
    }

    setSavingPrompt(true)

    // Set a new timeout for debouncing - saves after 500ms of inactivity
    hotUpdateTimeoutRef.current = setTimeout(async () => {
      try {
        const payload = {
          template_id: templateId,
          system_prompt: systemPrompt,
        }
        const res = await chatbotAPI.updateSession(selectedSession.id, payload)
        const updated = res.data as ChatSession
        setSessions(prev => prev.map(s => (s.id === updated.id ? updated : s)))
      } catch (e) {
        console.error('Failed to hot update prompt:', e)
      } finally {
        setSavingPrompt(false)
      }
    }, 500)
  }

  const handleCreateSession = async () => {
    try {
      const res = await chatbotAPI.createSession({})
      const newSession = res.data as ChatSession
      setSessions(prev => [newSession, ...prev])
      setSelectedSessionId(newSession.id)
      setErrorMessage(null)
    } catch (e) {
      setErrorMessage('Failed to create a new chat session.')
    }
  }

  const handleSelectSession = (sessionId: number) => {
    if (sessionId === selectedSessionId) return
    
    // Clear any ongoing streaming
    if (streamingTimeoutRef.current) {
      clearTimeout(streamingTimeoutRef.current)
      streamingTimeoutRef.current = null
    }
    setStreamingMessageId(null)
    
    setInputValue('')
    setErrorMessage(null)
    setSelectedSessionId(sessionId)
  }

  const handleSaveDraft = async () => {
    if (!selectedSession || !sessionDraft) return
    try {
      const payload = {
        title: sessionDraft.title,
        system_prompt: sessionDraft.system_prompt,
        temperature: sessionDraft.temperature,
        top_p: sessionDraft.top_p,
        max_tokens: sessionDraft.max_tokens,
        template_id: sessionDraft.template_id,
      }
    const res = await chatbotAPI.updateSession(selectedSession.id, payload)
    const updated = res.data as ChatSession
    setSessions(prev => prev.map(s => (s.id === updated.id ? updated : s)))
    setDraftDirtyFlag(false)
      setErrorMessage(null)
    } catch (e) {
      setErrorMessage('Failed to save session settings.')
    }
  }

  const handleResetSession = async () => {
    if (!selectedSession) return
    try {
    const res = await chatbotAPI.resetSession(selectedSession.id)
    const updated = res.data as ChatSession
    setSessions(prev => prev.map(s => (s.id === updated.id ? updated : s)))
    setMessages([])
    setDraftDirtyFlag(false)
      setErrorMessage(null)
    } catch (e) {
      setErrorMessage('Unable to reset session.')
    }
  }

  const handleDeleteSession = async (sessionId: number) => {
    try {
      await chatbotAPI.deleteSession(sessionId)
      setSessions(prev => prev.filter(s => s.id !== sessionId))
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(null)
        setMessages([])
        setSessionDraft(null)
      }
    } catch (e) {
      setErrorMessage('Failed to delete session.')
    }
  }

  const handlePresetApply = (key: string) => {
    if (!key) {
      setSessionDraft(prev => (prev ? { ...prev, preset_key: null, prompt_source: 'custom' } : prev))
      // Hot update: immediately save the change
      hotUpdatePrompt(null, sessionDraft?.system_prompt || '', null)
      return
    }
    const preset = presets.find(p => p.key === key)
    if (!preset) return
    setSessionDraft(prev => {
      if (!prev) return prev
      const nextTitle = prev.title === 'New Chat' ? preset.title : prev.title
      return {
        ...prev,
        system_prompt: preset.system_prompt,
        title: nextTitle,
        preset_key: preset.key,
        template_id: null,
        prompt_source: 'preset',
      }
    })
    // Hot update: immediately save the preset change
    hotUpdatePrompt(null, preset.system_prompt, preset.key)
    setDraftDirtyFlag(true)
    setShowPromptEditor(true)
  }

  const handleTemplateChange = (templateId: number | null) => {
    setSessionDraft(prev => {
      if (!prev) return prev
      const template = templates.find(t => t.id === templateId)
      return {
        ...prev,
        template_id: templateId,
        system_prompt: template ? template.content : prev.system_prompt,
        preset_key: null,
        prompt_source: templateId ? 'template' : 'custom',
      }
    })
    // Hot update: immediately save the template change
    const template = templates.find(t => t.id === templateId)
    hotUpdatePrompt(templateId, template ? template.content : (sessionDraft?.system_prompt || ''), null)
    setDraftDirtyFlag(true)
  }

  const appendOptimisticMessage = (content: string): number => {
    const tempId = -Date.now()
    const now = new Date().toISOString()
    const optimistic: ChatMessage = {
      id: tempId,
      session_id: selectedSessionId ?? 0,
      role: 'user',
      content,
      created_at: now,
    }
    setMessages(prev => [...prev, optimistic])
    return tempId
  }

  const replaceOptimisticMessage = (tempId: number, real: ChatMessage) => {
    setMessages(prev => prev.map(msg => msg.id === tempId ? real : msg))
  }

  const simulateStreamingMessage = (messageId: number, fullContent: string) => {
    setStreamingMessageId(messageId)
    let currentIndex = 0
    const chunkSize = 3 // Characters per chunk
    const delayMs = 20 // Delay between chunks in milliseconds

    const streamNextChunk = () => {
      if (currentIndex < fullContent.length) {
        currentIndex += chunkSize
        const streamedContent = fullContent.slice(0, currentIndex)
        
        setMessages(prev => prev.map(msg => 
          msg.id === messageId 
            ? { ...msg, content: streamedContent }
            : msg
        ))

        streamingTimeoutRef.current = setTimeout(streamNextChunk, delayMs)
      } else {
        setStreamingMessageId(null)
        streamingTimeoutRef.current = null
      }
    }

    // Start with empty message and begin streaming
    setMessages(prev => prev.map(msg => 
      msg.id === messageId 
        ? { ...msg, content: '' }
        : msg
    ))
    
    streamingTimeoutRef.current = setTimeout(streamNextChunk, delayMs)
  }

  const handleSendMessage = async (text?: string) => {
    if (!selectedSession || !sessionDraft) return
    const content = (text ?? inputValue).trim()
    if (!content) return
    if (sending) return

    setSending(true)
    setErrorMessage(null)
    const optimisticId = appendOptimisticMessage(content)
    
    // Clear input immediately after sending
    setInputValue('')

    try {
      const res = await chatbotAPI.sendMessage({
        session_id: selectedSession.id,
        content,
        temperature: sessionDraft.temperature,
        top_p: sessionDraft.top_p,
        max_tokens: sessionDraft.max_tokens,
        system_prompt: sessionDraft.system_prompt,
        template_id: sessionDraft.template_id
      })
      const data = res.data
      replaceOptimisticMessage(optimisticId, data.user_message as ChatMessage)
      
      // Create placeholder for assistant message before streaming
      const assistantMsg = data.assistant_message as ChatMessage
      setMessages(prev => [...prev, assistantMsg])
      
      // Simulate streaming the response
      setTimeout(() => {
        simulateStreamingMessage(assistantMsg.id, assistantMsg.content)
      }, 100)
      
      setSessions(prev => prev.map(s => s.id === selectedSession.id ? data.session as ChatSession : s))
    } catch (e) {
      setMessages(prev => prev.filter(msg => msg.id !== optimisticId))
      setErrorMessage('Failed to send message.')
    } finally {
      setSending(false)
    }
  }

  const handleRegenerate = async () => {
    if (!messages.length) return
    const lastUser = [...messages].reverse().find(msg => msg.role === 'user')
    if (!lastUser) return
    setInputValue(lastUser.content)
    await handleSendMessage(lastUser.content)
  }

  const handleCopyLast = async () => {
    const lastAssistant = [...messages].reverse().find(msg => msg.role === 'assistant')
    if (lastAssistant) {
      try {
        await navigator.clipboard.writeText(lastAssistant.content)
      } catch {
        setErrorMessage('Copy failed – clipboard permissions denied.')
      }
    }
  }

  const handleExport = () => {
    if (!selectedSession) return
    const payload = {
      session: selectedSession,
      messages,
      exported_at: new Date().toISOString()
    }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${selectedSession.title.replace(/\s+/g, '_').toLowerCase()}_chat.json`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const sidebarStyle: CSSProperties = {
    width: '280px',
    background: 'rgba(15, 23, 42, 0.45)',
    borderRight: '1px solid rgba(148,163,184,0.25)',
    padding: '22px',
    display: 'flex',
    flexDirection: 'column',
    gap: '18px',
    overflow: 'hidden'
  }

  const mainStyle: CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: 'rgba(15, 23, 42, 0.25)',
    minHeight: 0
  }

  return (
    <div style={{ display: 'flex', flex: 1, minHeight: '100%', backdropFilter: 'blur(24px)' }}>
      <aside style={sidebarStyle}>
        <div style={{ flexShrink: 0 }}>
          <div style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '10px', color: '#e0e7ff' }}>Chats</div>
          <button
            onClick={handleCreateSession}
            style={{
              width: '100%',
              padding: '10px 12px',
              borderRadius: '12px',
              border: '1px solid rgba(94,234,212,0.55)',
              background: 'linear-gradient(135deg, rgba(94,234,212,0.2), rgba(20,184,166,0.15))',
              color: '#bef264',
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            + New Chat
          </button>
        </div>
  <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', overflowY: 'auto', paddingRight: '6px', flex: 1, minHeight: 0 }}>
          {loadingSessions && <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Loading sessions…</div>}
          {!loadingSessions && !sessions.length && (
            <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No chats yet. Create your first session to begin.</div>
          )}
          {sessions.map(session => (
            <div
              key={session.id}
              onClick={() => handleSelectSession(session.id)}
              style={{
                padding: '12px 14px',
                borderRadius: '12px',
                border: selectedSessionId === session.id ? '2px solid rgba(129,140,248,0.6)' : '1px solid rgba(148,163,184,0.2)',
                background: selectedSessionId === session.id ? 'rgba(79,70,229,0.15)' : 'rgba(15, 23, 42, 0.4)',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px'
              }}
            >
              <div style={{ fontWeight: 600, color: '#e2e8f0' }}>{session.title}</div>
              {session.last_message_preview && (
                <div style={{ fontSize: '0.75rem', color: 'rgba(148,163,184,0.85)' }}>
                  {session.last_message_preview}
                </div>
              )}
              <div style={{ fontSize: '0.7rem', color: 'rgba(148,163,184,0.75)' }}>
                {new Date(session.updated_at).toLocaleDateString()} · {session.message_count} messages
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  handleDeleteSession(session.id)
                }}
                style={{
                  alignSelf: 'flex-end',
                  padding: '4px 8px',
                  fontSize: '0.7rem',
                  background: 'transparent',
                  border: '1px solid rgba(248,113,113,0.45)',
                  color: 'rgba(248,113,113,0.9)',
                  borderRadius: '8px',
                  cursor: 'pointer'
                }}
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      </aside>

      <main style={mainStyle}>
        {errorMessage && (
          <div style={{ background: 'rgba(248, 113, 113, 0.15)', borderBottom: '1px solid rgba(248,113,113,0.3)', padding: '10px 16px', color: '#fecaca', fontSize: '0.85rem' }}>
            {errorMessage}
          </div>
        )}

        {selectedSession && sessionDraft ? (
          <>
            <div style={{ padding: '18px 24px', borderBottom: '1px solid rgba(148,163,184,0.15)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <input
                  value={sessionDraft.title}
                  onChange={(e) => {
                    setSessionDraft({ ...sessionDraft, title: e.target.value })
                    setDraftDirtyFlag(true);
                  }}
                  style={{
                    fontSize: '1.4rem',
                    fontWeight: 600,
                    background: 'transparent',
                    border: 'none',
                    color: '#e2e8f0'
                  }}
                />
                <div style={{ fontSize: '0.75rem', color: 'rgba(148,163,184,0.7)' }}>Session ID: {selectedSession.session_key}</div>
              </div>
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={handleCopyLast}
                  disabled={!hasAssistantMessage}
                  style={{
                    ...actionButtonStyle,
                    opacity: hasAssistantMessage ? 1 : 0.5,
                    cursor: hasAssistantMessage ? 'pointer' : 'default'
                  }}
                >
                  Copy Reply
                </button>
                <button onClick={handleExport} style={actionButtonStyle}>Export</button>
                <button onClick={handleResetSession} style={actionButtonStyle}>Reset</button>
                <button
                  onClick={handleRegenerate}
                  disabled={sending || !hasUserMessage}
                  style={{
                    ...actionButtonStyle,
                    opacity: sending || !hasUserMessage ? 0.5 : 1,
                    cursor: sending || !hasUserMessage ? 'default' : 'pointer'
                  }}
                >
                  Regenerate
                </button>
                <button onClick={handleSaveDraft} disabled={!draftDirty} style={{ ...actionButtonStyle, border: '1px solid rgba(94,234,212,0.55)', color: '#bbf7d0', opacity: draftDirty ? 1 : 0.5 }}>Save</button>
              </div>
            </div>

            <div
              ref={messageContainerRef}
              style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '12px', minHeight: 0 }}
            >
              {loadingMessages ? (
                <div style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Loading conversation…</div>
              ) : messages.length ? (
                messages.map(msg => <MessageBubble key={msg.id} message={msg} />)
              ) : (
                <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No messages yet. Start the conversation!</div>
              )}
            </div>

            <div style={{ borderTop: '1px solid rgba(148,163,184,0.15)', padding: '18px 24px', display: 'flex', gap: '18px' }}>
              <div style={{ flex: 1 }}>
                <textarea
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder={sending ? 'Waiting for model response…' : 'Type your message…'}
                  disabled={sending}
                  rows={3}
                  style={{
                    width: '100%',
                    resize: 'vertical',
                    background: 'rgba(15,23,42,0.55)',
                    border: '1px solid rgba(129,140,248,0.35)',
                    borderRadius: '12px',
                    padding: '14px',
                    color: '#e2e8f0'
                  }}
                />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <button
                  onClick={() => handleSendMessage()}
                  disabled={sending || !inputValue.trim()}
                  style={{
                    padding: '12px 18px',
                    borderRadius: '12px',
                    border: '1px solid rgba(129,140,248,0.65)',
                    background: 'linear-gradient(135deg, rgba(129,140,248,0.35), rgba(79,70,229,0.35))',
                    color: '#ede9fe',
                    fontWeight: 600,
                    cursor: sending || !inputValue.trim() ? 'default' : 'pointer',
                    opacity: sending || !inputValue.trim() ? 0.6 : 1
                  }}
                >
                  {sending ? 'Sending…' : 'Send'}
                </button>
                <button
                  onClick={() => setShowPromptEditor(prev => !prev)}
                  style={{ ...actionButtonStyle }}
                >
                  {showPromptEditor ? 'Hide Prompt' : 'Edit Prompt'}
                </button>
              </div>
            </div>

            <div style={{ borderTop: '1px solid rgba(148,163,184,0.15)', padding: '18px 24px', background: 'rgba(15,23,42,0.35)', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '200px' }}>
                  <label style={labelStyle}>Temperature ({sessionDraft.temperature ?? 'auto'})</label>
                  <input
                    type="range"
                    min="0"
                    max="2"
                    step="0.1"
                    value={sessionDraft.temperature ?? 0.6}
                    onChange={(e) => {
                      setSessionDraft({ ...sessionDraft, temperature: Number(e.target.value) })
                      setDraftDirtyFlag(true);
                    }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '200px' }}>
                  <label style={labelStyle}>Top-P ({sessionDraft.top_p ?? 'auto'})</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.05"
                    value={sessionDraft.top_p ?? 0.9}
                    onChange={(e) => {
                      setSessionDraft({ ...sessionDraft, top_p: Number(e.target.value) })
                      setDraftDirtyFlag(true);
                    }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '200px' }}>
                  <label style={labelStyle}>Max Tokens ({sessionDraft.max_tokens ?? 'auto'})</label>
                  <input
                    type="number"
                    min="64"
                    value={sessionDraft.max_tokens ?? ''}
                    onChange={(e) => {
                      const value = e.target.value ? Number(e.target.value) : null
                      setSessionDraft({ ...sessionDraft, max_tokens: value })
                      setDraftDirtyFlag(true);
                    }}
                    style={{
                      background: 'rgba(15,23,42,0.55)',
                      border: '1px solid rgba(148,163,184,0.25)',
                      borderRadius: '8px',
                      color: '#e2e8f0',
                      padding: '8px'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '220px' }}>
                  <label style={labelStyle}>Preset Persona</label>
                  <select
                    value={sessionDraft.preset_key ?? ''}
                    onChange={(e) => handlePresetApply(e.target.value)}
                    style={selectStyle}
                  >
                    <option value="">Choose preset…</option>
                    {presets.map(p => (
                      <option key={p.key} value={p.key}>{p.title}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: '220px' }}>
                  <label style={labelStyle}>My Prompt Template</label>
                  <select
                    value={sessionDraft.template_id ?? ''}
                    onChange={(e) => handleTemplateChange(e.target.value ? Number(e.target.value) : null)}
                    style={selectStyle}
                  >
                    <option value="">None</option>
                    {templates.map(t => (
                      <option key={t.id} value={t.id}>{t.title}</option>
                    ))}
                  </select>
                </div>
                {savingPrompt && (
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '0.75rem',
                    color: '#94a3b8',
                    padding: '0 8px',
                    height: '36px'
                  }}>
                    <span style={{ display: 'inline-block', width: '4px', height: '4px', borderRadius: '50%', background: '#60a5fa', animation: 'pulse 2s infinite' }} />
                    Saving…
                  </div>
                )}
              </div>

              {showPromptEditor && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <label style={labelStyle}>System Prompt</label>
                    <span style={{
                      fontSize: '0.75rem',
                      padding: '2px 8px',
                      borderRadius: '4px',
                      backgroundColor: sessionDraft?.prompt_source === 'preset' ? 'rgba(34,197,94,0.2)' : sessionDraft?.prompt_source === 'template' ? 'rgba(59,130,246,0.2)' : 'rgba(107,114,128,0.2)',
                      color: sessionDraft?.prompt_source === 'preset' ? '#86efac' : sessionDraft?.prompt_source === 'template' ? '#93c5fd' : '#d1d5db',
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px'
                    }}>
                      {sessionDraft?.prompt_source === 'preset' ? '📌 Preset' : sessionDraft?.prompt_source === 'template' ? '📄 Template' : '✏️ Custom'}
                    </span>
                  </div>
                  <textarea
                    value={sessionDraft.system_prompt}
                    onChange={(e) => {
                      setSessionDraft(prev => prev ? { ...prev, system_prompt: e.target.value, preset_key: null, prompt_source: 'custom' } : prev)
                      setDraftDirtyFlag(true);
                    }}
                    rows={6}
                    style={{
                      width: '100%',
                      background: 'rgba(15,23,42,0.55)',
                      border: '1px solid rgba(129,140,248,0.3)',
                      borderRadius: '10px',
                      color: '#e2e8f0',
                      padding: '12px',
                      fontSize: '0.85rem'
                    }}
                  />
                </div>
              )}
            </div>
          </>
        ) : (
          <div style={{ display: 'flex', flex: 1, alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
            {loadingSessions ? 'Loading…' : 'Select or create a chat session to begin.'}
          </div>
        )}
      </main>
    </div>
  )
}

const actionButtonStyle: CSSProperties = {
  padding: '8px 14px',
  borderRadius: '10px',
  border: '1px solid rgba(148,163,184,0.35)',
  background: 'rgba(30,41,59,0.55)',
  color: 'rgba(226,232,240,0.85)',
  fontSize: '0.75rem',
  cursor: 'pointer'
}

const labelStyle: CSSProperties = {
  fontSize: '0.75rem',
  color: 'rgba(148,163,184,0.85)',
  fontWeight: 600,
  letterSpacing: '0.4px'
}

const selectStyle: CSSProperties = {
  background: 'rgba(15,23,42,0.55)',
  border: '1px solid rgba(148,163,184,0.3)',
  borderRadius: '10px',
  padding: '10px',
  color: '#e2e8f0'
}

// Add pulse animation for saving indicator
if (typeof document !== 'undefined' && !document.querySelector('#pulse-animation')) {
  const style = document.createElement('style')
  style.id = 'pulse-animation'
  style.textContent = `
    @keyframes pulse {
      0%, 100% {
        opacity: 1;
      }
      50% {
        opacity: 0.4;
      }
    }
  `
  document.head.appendChild(style)
}

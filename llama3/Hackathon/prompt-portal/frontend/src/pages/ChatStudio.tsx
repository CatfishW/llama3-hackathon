import { useEffect, useMemo, useRef, useState, type CSSProperties } from 'react'
import { chatbotAPI, drivingStatsAPI } from '../api'
import { useTemplates } from '../contexts/TemplateContext'

// Hook to detect mobile and handle responsive behavior
const useIsMobile = () => {
  const [isMobile, setIsMobile] = useState<boolean>(() => 
    typeof window !== 'undefined' ? window.innerWidth < 768 : false
  )

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return isMobile
}

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
  const isMobile = useIsMobile()
  const style = bubbleStyles[message.role] || bubbleStyles.assistant
  const timestamp = new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null)

  const copyToClipboard = async (text: string, index: number) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedIndex(index)
      setTimeout(() => setCopiedIndex(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const renderContent = () => {
    const content = message.content
    
    // Detect and render code blocks with syntax highlighting
    const codeBlockRegex = /```(\w+)?\n([\s\S]*?)```/g
    const inlineCodeRegex = /`([^`]+)`/g
    
    const parts: JSX.Element[] = []
    let lastIndex = 0
    let match
    
    // Process code blocks first
    const matches: Array<{ type: 'code' | 'inline', start: number, end: number, language?: string, content: string }> = []
    
    while ((match = codeBlockRegex.exec(content)) !== null) {
      matches.push({
        type: 'code',
        start: match.index,
        end: match.index + match[0].length,
        language: match[1] || 'text',
        content: match[2]
      })
    }
    
    // Sort matches by start position
    matches.sort((a, b) => a.start - b.start)
    
    // Build the content with code blocks
    matches.forEach((match, idx) => {
      // Add text before code block
      if (match.start > lastIndex) {
        const textSegment = content.substring(lastIndex, match.start)
        parts.push(
          <span key={`text-${idx}`} style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
            {renderInlineFormatting(textSegment)}
          </span>
        )
      }
      
      // Add code block
      parts.push(
        <div
          key={`code-${idx}`}
          style={{
            background: 'rgba(0,0,0,0.4)',
            border: '1px solid rgba(148,163,184,0.2)',
            borderRadius: '8px',
            padding: '12px',
            margin: '8px 0',
            overflowX: 'auto',
            position: 'relative'
          }}
        >
          <div style={{ 
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '6px'
          }}>
            <div style={{ 
              fontSize: '0.7rem', 
              color: 'rgba(148,163,184,0.7)', 
              fontWeight: 600,
              textTransform: 'uppercase'
            }}>
              {match.language}
            </div>
            <button
              onClick={() => copyToClipboard(match.content, idx)}
              style={{
                background: copiedIndex === idx ? 'rgba(34,197,94,0.2)' : 'rgba(148,163,184,0.1)',
                border: `1px solid ${copiedIndex === idx ? 'rgba(34,197,94,0.4)' : 'rgba(148,163,184,0.3)'}`,
                borderRadius: '6px',
                padding: '4px 8px',
                fontSize: '0.65rem',
                color: copiedIndex === idx ? '#86efac' : 'rgba(226,232,240,0.8)',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              {copiedIndex === idx ? '✓ Copied' : 'Copy'}
            </button>
          </div>
          <pre style={{ 
            margin: 0, 
            fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            fontSize: '0.8rem',
            lineHeight: '1.5',
            color: '#e2e8f0',
            whiteSpace: 'pre-wrap',
            wordBreak: 'break-all'
          }}>
            {match.content}
          </pre>
        </div>
      )
      
      lastIndex = match.end
    })
    
    // Add remaining text
    if (lastIndex < content.length) {
      const textSegment = content.substring(lastIndex)
      parts.push(
        <span key="text-final" style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {renderInlineFormatting(textSegment)}
        </span>
      )
    }
    
    return parts.length > 0 ? parts : renderInlineFormatting(content)
  }
  
  const renderInlineFormatting = (text: string) => {
    // First, render markdown images and image URLs
    const elements: (string | JSX.Element)[] = []

    // Helper to push text with inline code formatting later
    const pushFormattedText = (segment: string) => {
      // Handle inline code
      const inlineCodeRegex = /`([^`]+)`/g
      const parts: (string | JSX.Element)[] = []
      let lastIndex = 0
      let match
      while ((match = inlineCodeRegex.exec(segment)) !== null) {
        if (match.index > lastIndex) {
          parts.push(segment.substring(lastIndex, match.index))
        }
        parts.push(
          <code
            key={`inline-${lastIndex}`}
            style={{
              background: 'rgba(0,0,0,0.3)',
              padding: '2px 6px',
              borderRadius: '4px',
              fontFamily: 'Consolas, Monaco, "Courier New", monospace',
              fontSize: '0.85em',
              border: '1px solid rgba(148,163,184,0.2)'
            }}
          >
            {match[1]}
          </code>
        )
        lastIndex = match.index + match[0].length
      }
      if (lastIndex < segment.length) parts.push(segment.substring(lastIndex))
      elements.push(...parts)
    }

    // Regex for markdown images: ![alt](url)
    const imgMd = /!\[([^\]]*)\]\(([^)]+)\)/g
    // Regex for bare image URLs (including local /uploads paths)
    const imgUrl = /(https?:\/\/[^\s)]+\.(?:png|jpe?g|gif|webp|svg)|\/uploads\/[^\s)]+\.(?:png|jpe?g|gif|webp|svg))/ig

    let last = 0
    let mdMatch
    // First split by markdown image tags
    while ((mdMatch = imgMd.exec(text)) !== null) {
      if (mdMatch.index > last) {
        const before = text.substring(last, mdMatch.index)
        // Within this segment, also render bare image URLs
        let urlLast = 0
        let urlMatch
        while ((urlMatch = imgUrl.exec(before)) !== null) {
          if (urlMatch.index > urlLast) pushFormattedText(before.substring(urlLast, urlMatch.index))
          const url = urlMatch[0]
          elements.push(
            <div key={`imgurl-${mdMatch.index}-${urlLast}`} style={{ margin: '6px 0' }}>
              <img src={url} alt="image" style={{ maxWidth: '100%', borderRadius: '8px', border: '1px solid rgba(148,163,184,0.25)' }} />
            </div>
          )
          urlLast = urlMatch.index + urlMatch[0].length
        }
        if (urlLast < before.length) pushFormattedText(before.substring(urlLast))
      }
      const alt = mdMatch[1] || 'image'
      const url = mdMatch[2]
      elements.push(
        <div key={`imgmd-${mdMatch.index}`} style={{ margin: '6px 0' }}>
          <img src={url} alt={alt} style={{ maxWidth: '100%', borderRadius: '8px', border: '1px solid rgba(148,163,184,0.25)' }} />
        </div>
      )
      last = mdMatch.index + mdMatch[0].length
    }
    if (last < text.length) {
      const tail = text.substring(last)
      // Handle bare image URLs in tail
      let urlLast = 0
      let urlMatch
      while ((urlMatch = imgUrl.exec(tail)) !== null) {
        if (urlMatch.index > urlLast) pushFormattedText(tail.substring(urlLast, urlMatch.index))
        const url = urlMatch[0]
        elements.push(
          <div key={`imgtail-${last}-${urlLast}`} style={{ margin: '6px 0' }}>
            <img src={url} alt="image" style={{ maxWidth: '100%', borderRadius: '8px', border: '1px solid rgba(148,163,184,0.25)' }} />
          </div>
        )
        urlLast = urlMatch.index + urlMatch[0].length
      }
      if (urlLast < tail.length) pushFormattedText(tail.substring(urlLast))
    }

    if (elements.length) return elements

    // Fallback to original simple inline code formatting
    const inlineCodeRegex = /`([^`]+)`/g
    const boldRegex = /\*\*(.+?)\*\*/g
    const italicRegex = /\*(.+?)\*/g
    const listItemRegex = /^[\s]*[-*]\s(.+)$/gm
    const numberedListRegex = /^[\s]*\d+\.\s(.+)$/gm
    
    const parts: (string | JSX.Element)[] = []
    let lastIndex = 0
    let match
    
    // Find all inline code matches
    const inlineMatches: Array<{ start: number, end: number, content: string }> = []
    while ((match = inlineCodeRegex.exec(text)) !== null) {
      inlineMatches.push({
        start: match.index,
        end: match.index + match[0].length,
        content: match[1]
      })
    }
    
    inlineMatches.forEach((m, idx) => {
      if (m.start > lastIndex) {
        parts.push(text.substring(lastIndex, m.start))
      }
      parts.push(
        <code
          key={`inline-${idx}`}
          style={{
            background: 'rgba(0,0,0,0.3)',
            padding: '2px 6px',
            borderRadius: '4px',
            fontFamily: 'Consolas, Monaco, "Courier New", monospace',
            fontSize: '0.85em',
            border: '1px solid rgba(148,163,184,0.2)'
          }}
        >
          {m.content}
        </code>
      )
      lastIndex = m.end
    })
    
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex))
    }
    
    return parts.length > 0 ? parts : text
  }

  const [showContextMenu, setShowContextMenu] = useState(false)
  const [contextMenuPos, setContextMenuPos] = useState({ x: 0, y: 0 })
  const [messageCopied, setMessageCopied] = useState(false)

  const handleContextMenu = (e: React.MouseEvent) => {
    e.preventDefault()
    setContextMenuPos({ x: e.clientX, y: e.clientY })
    setShowContextMenu(true)
  }

  const handleCopyMessage = async () => {
    try {
      await navigator.clipboard.writeText(message.content)
      setMessageCopied(true)
      setTimeout(() => setMessageCopied(false), 2000)
      setShowContextMenu(false)
    } catch (err) {
      console.error('Failed to copy message:', err)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'c') {
      handleCopyMessage()
    }
  }

  // Close context menu when clicking elsewhere
  useEffect(() => {
    const handleClickOutside = () => setShowContextMenu(false)
    if (showContextMenu) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [showContextMenu])

  return (
    <div style={{ position: 'relative', maxWidth: isMobile ? '90%' : '70%', ...style.alignSelf ? { alignSelf: style.alignSelf as any } : {} }}>
      <div 
        style={{ padding: '14px 18px', borderRadius: '18px', display: 'flex', flexDirection: 'column', gap: '10px', ...style, position: 'relative' }}
        onContextMenu={handleContextMenu}
        onKeyDown={handleKeyDown}
        tabIndex={0}
      >
        <div style={{ fontSize: message.role === 'system' ? '0.75rem' : '0.85rem', lineHeight: '1.6' }}>
          {renderContent()}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ fontSize: '0.7rem', color: 'rgba(226,232,240,0.8)' }}>{timestamp}</div>
          <button
            onClick={handleCopyMessage}
            style={{
              background: messageCopied ? 'rgba(34,197,94,0.2)' : 'rgba(148,163,184,0.1)',
              border: `1px solid ${messageCopied ? 'rgba(34,197,94,0.4)' : 'rgba(148,163,184,0.3)'}`,
              borderRadius: '6px',
              padding: '4px 8px',
              fontSize: '0.65rem',
              color: messageCopied ? '#86efac' : 'rgba(226,232,240,0.8)',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
          >
            {messageCopied ? '✓ Copied' : 'Copy'}
          </button>
        </div>
      </div>
      
      {/* Context Menu */}
      {showContextMenu && (
        <div
          style={{
            position: 'fixed',
            left: contextMenuPos.x,
            top: contextMenuPos.y,
            background: 'rgba(15,23,42,0.95)',
            border: '1px solid rgba(148,163,184,0.3)',
            borderRadius: '8px',
            padding: '4px',
            zIndex: 1000,
            boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
            minWidth: '120px'
          }}
        >
          <button
            onClick={handleCopyMessage}
            style={{
              width: '100%',
              padding: '8px 12px',
              background: 'transparent',
              border: 'none',
              color: '#e2e8f0',
              textAlign: 'left',
              cursor: 'pointer',
              borderRadius: '6px',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(129,140,248,0.2)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <i className="fas fa-copy"></i>
            Copy Message
          </button>
        </div>
      )}
    </div>
  )
}

export default function ChatStudio() {
  const { templates } = useTemplates()
  const isMobile = useIsMobile()

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
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(!isMobile)
  const [uploadedFiles, setUploadedFiles] = useState<Array<{ name: string; content?: string; imageUrl?: string }>>([])
  const [uploading, setUploading] = useState<boolean>(false)
  const messageContainerRef = useRef<HTMLDivElement | null>(null)
  const streamingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  
  // Driving Game Testing Mode
  const [drivingGameMode, setDrivingGameMode] = useState<boolean>(false)
  const [drivingGameStartTime, setDrivingGameStartTime] = useState<number | null>(null)
  const [drivingGameMessageCount, setDrivingGameMessageCount] = useState<number>(0)
  const [showConsensusModal, setShowConsensusModal] = useState<boolean>(false)
  const [consensusScore, setConsensusScore] = useState<number>(0)
  const [consensusMessageCount, setConsensusMessageCount] = useState<number>(0)
  const [lastPlayerOption, setLastPlayerOption] = useState<string>('')
  const [lastAgentOption, setLastAgentOption] = useState<string>('')

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

  // Reset Driving Game mode when session changes
  useEffect(() => {
    setDrivingGameMode(false)
    setDrivingGameStartTime(null)
    setDrivingGameMessageCount(0)
    setConsensusMessageCount(0)
    setShowConsensusModal(false)
  }, [selectedSessionId])

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
  max_tokens: selectedSession.max_tokens ?? 20000,
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
    const chunkSize = 5 // Characters per chunk
    const delayMs = 5 // Delay between chunks in milliseconds

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
    const base = (text ?? inputValue).trim()
    // Append attachments to the outgoing content (documents as text, images as markdown)
    const attachmentChunks: string[] = []
    for (const f of uploadedFiles) {
      if (f.imageUrl) {
        attachmentChunks.push(`![${f.name}](${f.imageUrl})`)
        if (f.content) {
          attachmentChunks.push(`(OCR)\n${f.content}`)
        }
      } else if (f.content) {
        attachmentChunks.push(`[File: ${f.name}]\n${f.content}`)
      }
    }
    const content = [base, ...attachmentChunks].filter(Boolean).join('\n\n')
    if (!content) return
    if (sending) return

    setSending(true)
    setErrorMessage(null)
    const optimisticId = appendOptimisticMessage(content)
    
  // Clear input and attachments immediately after sending
  setInputValue('')
  setUploadedFiles([])

    try {
      // Use streaming API
      let streamedContent = ''
      let assistantMessageId: number | null = null
      let tempAssistantId = -Date.now() // Temporary negative ID for streaming message
      
      await chatbotAPI.sendMessageStream(
        {
          session_id: selectedSession.id,
          content,
          // If backend supports vision, also send image URLs; backend will fall back to text if disabled
          image_urls: uploadedFiles.filter(f => !!f.imageUrl).map(f => f.imageUrl!) || undefined,
          temperature: sessionDraft.temperature,
          top_p: sessionDraft.top_p,
          max_tokens: sessionDraft.max_tokens,
          system_prompt: sessionDraft.system_prompt,
          template_id: sessionDraft.template_id
        },
        // onMetadata
        (metadata) => {
          // Replace optimistic user message with real one
          replaceOptimisticMessage(optimisticId, {
            id: -1, // Will be updated
            session_id: metadata.session_id,
            role: 'user',
            content,
            created_at: new Date().toISOString()
          } as ChatMessage)
          
          // Create placeholder for assistant message
          const placeholderAssistant: ChatMessage = {
            id: tempAssistantId,
            session_id: metadata.session_id,
            role: 'assistant',
            content: '',
            created_at: new Date().toISOString()
          }
          setMessages(prev => [...prev, placeholderAssistant])
          setStreamingMessageId(tempAssistantId)
        },
        // onChunk
        (chunk) => {
          streamedContent += chunk
          setMessages(prev => prev.map(msg => 
            msg.id === tempAssistantId 
              ? { ...msg, content: streamedContent }
              : msg
          ))
        },
        // onComplete
        async (fullContent, realAssistantId) => {
          assistantMessageId = realAssistantId
          // Update with final content and real ID
          setMessages(prev => prev.map(msg => 
            msg.id === tempAssistantId 
              ? { ...msg, id: realAssistantId, content: fullContent }
              : msg
          ))
          setStreamingMessageId(null)
          
          // Check for consensus if in Driving Game mode
          if (drivingGameMode && drivingGameStartTime && assistantMessageId) {
            // Increment message count for this exchange
            const newMessageCount = drivingGameMessageCount + 1
            setDrivingGameMessageCount(newMessageCount)
            
            const { hasConsensus, playerOp, agentOp } = detectConsensus(fullContent)
            
            if (hasConsensus) {
              // Calculate score using the updated count
              const durationSeconds = (Date.now() - drivingGameStartTime) / 1000
              const score = calculateDrivingGameScore(newMessageCount, durationSeconds)
              
              // Save options, score, and message count for modal display
              setLastPlayerOption(playerOp)
              setLastAgentOption(agentOp)
              setConsensusScore(score)
              setConsensusMessageCount(newMessageCount)
              
              // Submit score to leaderboard
              try {
                await submitDrivingGameScore(score, newMessageCount, durationSeconds, playerOp, agentOp)
                console.log('[DRIVING GAME] Score submitted successfully, showing modal')
              } catch (e) {
                console.error('[DRIVING GAME] Score submission failed, but still showing modal:', e)
              }
              
              // Show modal
              setShowConsensusModal(true)
              
              // Reset driving game mode
              setDrivingGameMode(false)
              setDrivingGameStartTime(null)
              setDrivingGameMessageCount(0)
            }
          }
        },
        // onError
        (error) => {
          console.error('Streaming error:', error)
          setErrorMessage(`Failed to send message: ${error.message}`)
          setMessages(prev => prev.filter(msg => msg.id !== optimisticId && msg.id !== tempAssistantId))
          setStreamingMessageId(null)
        }
      )
      
      // Fetch updated session info
      const sessionsRes = await chatbotAPI.listSessions()
      setSessions(sessionsRes.data)
      
    } catch (e) {
      console.error('Send message error:', e)
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

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    setUploading(true)
    setErrorMessage(null)

    try {
      for (const file of Array.from(files)) {
        const fileExtension = file.name.split('.').pop()?.toLowerCase() || ''
        const isDocument = ['pdf', 'doc', 'docx'].includes(fileExtension)
        const isImage = ['png', 'jpg', 'jpeg', 'gif', 'webp'].includes(fileExtension)

        if (!isDocument && !isImage) {
          setErrorMessage(`Unsupported file type: ${file.name}. Allowed: PDF, DOC, DOCX, PNG, JPG, JPEG, GIF, WEBP.`)
          continue
        }

        const formData = new FormData()
        formData.append('file', file)

        const endpoint = isDocument ? '/api/chatbot/upload-document' : '/api/chatbot/upload-image'
        const response = await fetch(endpoint, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: formData
        })

        if (!response.ok) {
          const errText = await response.text()
          throw new Error(`Failed to upload ${file.name}: ${errText}`)
        }

        const data = await response.json()

        if (isDocument) {
          setUploadedFiles(prev => [...prev, { name: file.name, content: data.text }])
          setInputValue(prev => prev + `\n\n[File: ${file.name}]\n${data.text}\n`)
        } else if (isImage) {
          setUploadedFiles(prev => [...prev, { name: file.name, content: data.ocr_text, imageUrl: data.url }])
          if (data.ocr_text) {
            setInputValue(prev => prev + `\n\n[Image: ${file.name}] (OCR Extracted)\n${data.ocr_text}\n`)
          } else {
            setInputValue(prev => prev + `\n\n[Image: ${file.name}] Uploaded. (No OCR text)\n`)
          }
        }
      }
    } catch (e: any) {
      setErrorMessage(`File upload failed: ${e.message}`)
    } finally {
      setUploading(false)
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  const handleRemoveUploadedFile = (index: number) => {
    setUploadedFiles(prev => prev.filter((_, i) => i !== index))
  }

  // Driving Game Mode functions
  const toggleDrivingGameMode = () => {
    const newMode = !drivingGameMode
    setDrivingGameMode(newMode)
    if (newMode) {
      // Starting driving game mode
      setDrivingGameStartTime(Date.now())
      setDrivingGameMessageCount(0)
      setShowConsensusModal(false)
      setLastPlayerOption('')
      setLastAgentOption('')
    } else {
      // Stopping driving game mode
      setDrivingGameStartTime(null)
      setDrivingGameMessageCount(0)
    }
  }

  const detectConsensus = (content: string): { hasConsensus: boolean, playerOp: string, agentOp: string } => {
    // Check for <EOS> tag
    const hasEOS = content.includes('<EOS>')
    
    // Extract PlayerOp and AgentOP
    const playerOpMatch = content.match(/<PlayerOp:([^>]+)>/)
    const agentOpMatch = content.match(/<AgentOP:([^>]+)>/)
    
    const playerOp = playerOpMatch ? playerOpMatch[1].trim() : ''
    const agentOp = agentOpMatch ? agentOpMatch[1].trim() : ''
    
    return {
      hasConsensus: hasEOS,
      playerOp,
      agentOp
    }
  }

  const calculateDrivingGameScore = (messageCount: number, durationSeconds: number): number => {
    // Scoring formula:
    // Base score: 1000 points
    // Penalty for messages: -50 points per message (fewer messages = better)
    // Penalty for time: -1 point per second (faster = better)
    // Minimum score: 100
    
    const baseScore = 1000
    const messagePenalty = messageCount * 50
    const timePenalty = Math.floor(durationSeconds)
    
    const finalScore = Math.max(100, baseScore - messagePenalty - timePenalty)
    return finalScore
  }

  const submitDrivingGameScore = async (score: number, messageCount: number, durationSeconds: number, playerOp: string, agentOp: string) => {
    if (!selectedSession || !sessionDraft?.template_id) {
      console.error('[DRIVING GAME SUBMIT] Cannot submit score: No template selected')
      setErrorMessage('Cannot submit score: No template selected')
      return
    }

    try {
      const scoreData = {
        template_id: sessionDraft.template_id,
        session_id: selectedSession.session_key,
        score: score,
        message_count: messageCount,
        duration_seconds: durationSeconds,
        player_option: playerOp,
        agent_option: agentOp
      }
      
      console.log('[DRIVING GAME SUBMIT] Submitting via drivingStatsAPI:', scoreData)
      
      // Use the dedicated drivingStatsAPI
      const response = await drivingStatsAPI.submitScore(scoreData)
      
      console.log('[DRIVING GAME SUBMIT] Score submitted successfully:', response.data)
    } catch (e: any) {
      console.error('[DRIVING GAME SUBMIT] Failed to submit score:', e)
      const errorMsg = e?.response?.data?.detail || e?.message || 'Unknown error'
      setErrorMessage(`Failed to submit score: ${errorMsg}`)
      throw e  // Re-throw to let caller know submission failed
    }
  }

  const sidebarStyle: CSSProperties = {
    width: isMobile ? '100%' : '280px',
    background: 'rgba(15, 23, 42, 0.45)',
    borderRight: isMobile ? 'none' : '1px solid rgba(148,163,184,0.25)',
    borderBottom: isMobile ? '1px solid rgba(148,163,184,0.25)' : 'none',
    display: isMobile && !sidebarOpen ? 'none' : 'flex',
    flexDirection: 'column',
    height: isMobile ? 'auto' : '100vh',
    maxHeight: isMobile ? '60vh' : 'auto',
    overflow: 'hidden',
    position: isMobile ? 'relative' : 'static',
    zIndex: isMobile ? 40 : 'auto'
  }

  const mainStyle: CSSProperties = {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: 'rgba(15, 23, 42, 0.25)',
    height: isMobile ? '100%' : '100vh',
    overflow: 'hidden'
  }

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100%', backdropFilter: 'blur(24px)', overflow: 'hidden', flexDirection: isMobile ? 'column' : 'row' }}>
      {/* Mobile Header */}
      {isMobile && (
        <div style={{ 
          background: 'rgba(20, 20, 35, 0.65)', 
          backdropFilter: 'blur(14px)',
          borderBottom: '1px solid rgba(255,255,255,0.12)',
          padding: '12px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          zIndex: 50
        }}>
          <button
            onClick={() => setSidebarOpen(!sidebarOpen)}
            style={{
              background: 'rgba(0,0,0,0.35)',
              color: '#fff',
              border: '1px solid rgba(255,255,255,0.25)',
              padding: '8px 12px',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.9rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <i className={`fas ${sidebarOpen ? 'fa-times' : 'fa-bars'}`}></i>
          </button>
          <div style={{ fontSize: '1rem', fontWeight: '600', color: 'white' }}>
            {selectedSession?.title || 'Chat'}
          </div>
          <div style={{ width: '44px' }}></div>
        </div>
      )}

      {/* Sidebar - hidden on mobile by default */}
      {(!isMobile || sidebarOpen) && (
        <>
          <aside style={sidebarStyle}>
            <div style={{ flexShrink: 0, padding: '22px', paddingBottom: '12px' }}>
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
            <div style={{ 
              display: 'flex', 
              flexDirection: 'column', 
              gap: '12px', 
              overflowY: 'auto', 
              overflowX: 'hidden',
              padding: '0 22px 22px 22px',
              flex: 1,
              minHeight: 0
            }}>
              {loadingSessions && <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>Loading sessions…</div>}
              {!loadingSessions && !sessions.length && (
                <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No chats yet. Create your first session to begin.</div>
              )}
              {sessions.map(session => (
                <div
                  key={session.id}
                  onClick={() => {
                    handleSelectSession(session.id)
                    if (isMobile) setSidebarOpen(false)
                  }}
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
                  <div style={{ fontWeight: 600, color: '#e2e8f0', wordBreak: 'break-word' }}>{session.title}</div>
                  {session.last_message_preview && (
                    <div style={{ fontSize: '0.75rem', color: 'rgba(148,163,184,0.85)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
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
          {isMobile && sidebarOpen && (
            <div 
              onClick={() => setSidebarOpen(false)}
              style={{
                position: 'fixed',
                inset: 0,
                background: 'rgba(0,0,0,0.4)',
                zIndex: 30
              }}
            />
          )}
        </>
      )}

      <main style={mainStyle}>
        {errorMessage && (
          <div style={{ background: 'rgba(248, 113, 113, 0.15)', borderBottom: '1px solid rgba(248,113,113,0.3)', padding: '10px 16px', color: '#fecaca', fontSize: '0.85rem' }}>
            {errorMessage}
          </div>
        )}

        {selectedSession && sessionDraft ? (
          <>
            <div style={{ padding: isMobile ? '12px 16px' : '18px 24px', borderBottom: '1px solid rgba(148,163,184,0.15)', display: 'flex', justifyContent: 'space-between', alignItems: isMobile ? 'center' : 'flex-start', gap: '10px', flexDirection: isMobile ? 'row' : 'row', flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flex: isMobile ? 1 : 'unset', minWidth: 0 }}>
                <input
                  value={sessionDraft.title}
                  onChange={(e) => {
                    setSessionDraft({ ...sessionDraft, title: e.target.value })
                    setDraftDirtyFlag(true);
                  }}
                  style={{
                    fontSize: isMobile ? '1.1rem' : '1.4rem',
                    fontWeight: 600,
                    background: 'transparent',
                    border: 'none',
                    color: '#e2e8f0',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}
                />
                {!isMobile && <div style={{ fontSize: '0.75rem', color: 'rgba(148,163,184,0.7)' }}>Session ID: {selectedSession.session_key}</div>}
              </div>
              <div style={{ display: 'flex', gap: '8px', flexWrap: isMobile ? 'wrap' : 'nowrap', justifyContent: isMobile ? 'flex-end' : 'flex-start' }}>
                <button
                  onClick={handleCopyLast}
                  disabled={!hasAssistantMessage}
                  style={{
                    ...actionButtonStyle,
                    opacity: hasAssistantMessage ? 1 : 0.5,
                    cursor: hasAssistantMessage ? 'pointer' : 'default',
                    fontSize: isMobile ? '0.65rem' : '0.75rem',
                    padding: isMobile ? '6px 10px' : '8px 14px'
                  }}
                >
                  {isMobile ? 'Copy' : 'Copy Reply'}
                </button>
                <button onClick={handleExport} style={{...actionButtonStyle, fontSize: isMobile ? '0.65rem' : '0.75rem', padding: isMobile ? '6px 10px' : '8px 14px'}}>Export</button>
                <button onClick={handleResetSession} style={{...actionButtonStyle, fontSize: isMobile ? '0.65rem' : '0.75rem', padding: isMobile ? '6px 10px' : '8px 14px'}}>Reset</button>
                {!isMobile && (
                  <>
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
                  </>
                )}
              </div>
            </div>

            <div
              ref={messageContainerRef}
              style={{ 
                flex: 1, 
                overflowY: 'auto', 
                overflowX: 'hidden',
                padding: isMobile ? '16px 12px' : '24px', 
                display: 'flex', 
                flexDirection: 'column', 
                gap: '12px', 
                minHeight: 0,
                maxHeight: '100%'
              }}
            >
              {loadingMessages ? (
                <div style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Loading conversation…</div>
              ) : messages.length ? (
                messages.map(msg => <MessageBubble key={msg.id} message={msg} />)
              ) : (
                <div style={{ color: '#94a3b8', fontSize: '0.85rem' }}>No messages yet. Start the conversation!</div>
              )}
            </div>

            <div style={{ borderTop: '1px solid rgba(148,163,184,0.15)', padding: isMobile ? '12px' : '18px 24px' }}>
              {/* File attachments display */}
              {uploadedFiles.length > 0 && (
                <div style={{ marginBottom: '12px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
                  {uploadedFiles.map((file, index) => {
                    const isImage = !!file.imageUrl
                    return (
                      <div
                        key={index}
                        style={{
                          background: isImage ? 'rgba(94,234,212,0.12)' : 'rgba(129,140,248,0.15)',
                          border: isImage ? '1px solid rgba(94,234,212,0.35)' : '1px solid rgba(129,140,248,0.35)',
                          borderRadius: '10px',
                          padding: '8px 12px',
                          display: 'flex',
                          alignItems: 'center',
                          gap: '10px',
                          fontSize: '0.8rem',
                          color: '#e2e8f0',
                          position: 'relative',
                          maxWidth: '240px'
                        }}
                      >
                        {isImage ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <div style={{ width: '42px', height: '42px', overflow: 'hidden', borderRadius: '6px', border: '1px solid rgba(94,234,212,0.3)' }}>
                              <img
                                src={file.imageUrl}
                                alt={file.name}
                                style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                              />
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              <span style={{ fontWeight: 600, wordBreak: 'break-word' }}>{file.name}</span>
                              {file.content && (
                                <span style={{ fontSize: '0.65rem', color: 'rgba(148,163,184,0.9)', maxHeight: '32px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                  OCR: {file.content.slice(0, 40)}{file.content.length > 40 ? '…' : ''}
                                </span>
                              )}
                            </div>
                          </div>
                        ) : (
                          <>
                            <i className="fas fa-file-alt" style={{ color: '#818cf8' }}></i>
                            <span style={{ fontWeight: 600, wordBreak: 'break-word' }}>{file.name}</span>
                          </>
                        )}
                        <button
                          onClick={() => handleRemoveUploadedFile(index)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: '#f87171',
                            cursor: 'pointer',
                            padding: '0 6px',
                            fontSize: '1rem',
                            position: 'absolute',
                            top: '4px',
                            right: '4px'
                          }}
                          aria-label={`Remove ${file.name}`}
                        >
                          ×
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
              
              <div style={{ display: 'flex', gap: isMobile ? '10px' : '18px', flexDirection: isMobile ? 'column' : 'row' }}>
                <div style={{ flex: 1 }}>
                  <textarea
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault()
                        if (!sending && inputValue.trim()) {
                          handleSendMessage()
                        }
                      }
                    }}
                    placeholder={sending ? 'Waiting for model response…' : 'Type your message… (Press Enter to send, Shift+Enter for new line)'}
                    disabled={sending}
                    rows={isMobile ? 2 : 3}
                    style={{
                      width: '100%',
                      resize: 'vertical',
                      background: 'rgba(15,23,42,0.55)',
                      border: '1px solid rgba(129,140,248,0.35)',
                      borderRadius: '12px',
                      padding: '14px',
                      color: '#e2e8f0',
                      fontSize: isMobile ? '0.9rem' : '1rem'
                    }}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: isMobile ? 'row' : 'column', gap: '10px' }}>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.doc,.docx,.png,.jpg,.jpeg,.gif,.webp"
                    multiple
                    onChange={handleFileUpload}
                    style={{ display: 'none' }}
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={uploading}
                    style={{
                      padding: isMobile ? '10px 14px' : '12px 18px',
                      borderRadius: '12px',
                      border: '1px solid rgba(94,234,212,0.65)',
                      background: 'linear-gradient(135deg, rgba(94,234,212,0.25), rgba(45,212,191,0.25))',
                      color: '#5eead4',
                      fontWeight: 600,
                      cursor: uploading ? 'default' : 'pointer',
                      opacity: uploading ? 0.6 : 1,
                      fontSize: isMobile ? '0.8rem' : '1rem',
                      flex: isMobile ? 1 : 'unset',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      gap: '6px'
                    }}
                  >
                    <i className="fas fa-paperclip"></i>
                    {uploading ? 'Uploading…' : (isMobile ? 'File' : 'Attach')}
                  </button>
                  <button
                    onClick={() => handleSendMessage()}
                    disabled={sending || !inputValue.trim()}
                    style={{
                      padding: isMobile ? '10px 14px' : '12px 18px',
                      borderRadius: '12px',
                      border: '1px solid rgba(129,140,248,0.65)',
                      background: 'linear-gradient(135deg, rgba(129,140,248,0.35), rgba(79,70,229,0.35))',
                      color: '#ede9fe',
                      fontWeight: 600,
                      cursor: sending || !inputValue.trim() ? 'default' : 'pointer',
                      opacity: sending || !inputValue.trim() ? 0.6 : 1,
                      fontSize: isMobile ? '0.8rem' : '1rem',
                      flex: isMobile ? 1 : 'unset'
                    }}
                  >
                    {sending ? 'Sending…' : 'Send'}
                  </button>
                  <button
                    onClick={() => setShowPromptEditor(prev => !prev)}
                    style={{ ...actionButtonStyle, flex: isMobile ? 1 : 'unset' }}
                  >
                    {showPromptEditor ? 'Hide' : 'Edit'}
                  </button>
                </div>
              </div>
            </div>

            <div style={{ borderTop: '1px solid rgba(148,163,184,0.15)', padding: isMobile ? '12px' : '18px 24px', background: 'rgba(15,23,42,0.35)', display: 'flex', flexDirection: 'column', gap: '16px', maxHeight: isMobile ? '40vh' : 'auto', overflowY: isMobile ? 'auto' : 'visible' }}>
              <div style={{ display: 'flex', gap: isMobile ? '8px' : '16px', flexWrap: 'wrap' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: isMobile ? '140px' : '200px', flex: isMobile ? 1 : 'unset' }}>
                  <label style={labelStyle}>Temp ({sessionDraft.temperature ?? 'auto'})</label>
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
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: isMobile ? '140px' : '200px', flex: isMobile ? 1 : 'unset' }}>
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
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: isMobile ? '140px' : '200px', flex: isMobile ? 1 : 'unset' }}>
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
                      padding: '8px',
                      fontSize: isMobile ? '0.9rem' : '1rem'
                    }}
                  />
                </div>
              </div>

              <div style={{ display: 'flex', gap: isMobile ? '8px' : '16px', flexWrap: 'wrap', alignItems: 'flex-end' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: isMobile ? '100%' : '220px', flex: isMobile ? 1 : 'unset' }}>
                  <label style={labelStyle}>Preset Persona</label>
                  <select
                    value={sessionDraft.preset_key ?? ''}
                    onChange={(e) => handlePresetApply(e.target.value)}
                    style={{...selectStyle, fontSize: isMobile ? '0.9rem' : '1rem'}}
                  >
                    <option value="">Choose preset…</option>
                    {presets.map(p => (
                      <option key={p.key} value={p.key}>{p.title}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: isMobile ? '100%' : '220px', flex: isMobile ? 1 : 'unset' }}>
                  <label style={labelStyle}>My Prompt Template</label>
                  <select
                    value={sessionDraft.template_id ?? ''}
                    onChange={(e) => handleTemplateChange(e.target.value ? Number(e.target.value) : null)}
                    style={{...selectStyle, fontSize: isMobile ? '0.9rem' : '1rem'}}
                  >
                    <option value="">None</option>
                    {templates.map(t => (
                      <option key={t.id} value={t.id}>{t.title}</option>
                    ))}
                  </select>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', minWidth: isMobile ? '100%' : '220px', flex: isMobile ? 1 : 'unset' }}>
                  <label style={labelStyle}>Driving Game Testing</label>
                  <div style={{ 
                    display: 'flex', 
                    alignItems: 'center', 
                    gap: '10px',
                    padding: '10px',
                    background: drivingGameMode ? 'rgba(34,197,94,0.15)' : 'rgba(15,23,42,0.55)',
                    border: `1px solid ${drivingGameMode ? 'rgba(34,197,94,0.4)' : 'rgba(148,163,184,0.3)'}`,
                    borderRadius: '10px',
                  }}>
                    <input
                      type="checkbox"
                      checked={drivingGameMode}
                      onChange={toggleDrivingGameMode}
                      disabled={!sessionDraft?.template_id}
                      style={{ cursor: sessionDraft?.template_id ? 'pointer' : 'not-allowed' }}
                    />
                    <span style={{ 
                      fontSize: isMobile ? '0.85rem' : '0.9rem', 
                      color: drivingGameMode ? '#86efac' : 'rgba(226,232,240,0.85)',
                      fontWeight: drivingGameMode ? 600 : 400
                    }}>
                      {drivingGameMode ? '🏁 Active' : 'Enable'}
                    </span>
                    {drivingGameMode && (
                      <span style={{ 
                        fontSize: '0.7rem', 
                        color: 'rgba(148,163,184,0.85)',
                        marginLeft: 'auto'
                      }}>
                        {drivingGameMessageCount} msgs
                      </span>
                    )}
                  </div>
                  {!sessionDraft?.template_id && (
                    <span style={{ fontSize: '0.65rem', color: 'rgba(248,113,113,0.8)' }}>
                      Select a template first
                    </span>
                  )}
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
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
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
                    rows={isMobile ? 4 : 6}
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

              {isMobile && (
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={handleRegenerate}
                    disabled={sending || !hasUserMessage}
                    style={{
                      ...actionButtonStyle,
                      opacity: sending || !hasUserMessage ? 0.5 : 1,
                      cursor: sending || !hasUserMessage ? 'default' : 'pointer',
                      flex: 1
                    }}
                  >
                    Regenerate
                  </button>
                  <button onClick={handleSaveDraft} disabled={!draftDirty} style={{ ...actionButtonStyle, border: '1px solid rgba(94,234,212,0.55)', color: '#bbf7d0', opacity: draftDirty ? 1 : 0.5, flex: 1 }}>Save</button>
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

      {/* Consensus Reached Modal */}
      {showConsensusModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.75)',
          backdropFilter: 'blur(8px)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: '20px'
        }}>
          <div style={{
            background: 'linear-gradient(135deg, rgba(20,20,35,0.95), rgba(30,30,50,0.95))',
            border: '2px solid rgba(34,197,94,0.5)',
            borderRadius: '20px',
            padding: isMobile ? '24px' : '40px',
            maxWidth: '500px',
            width: '100%',
            boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
            display: 'flex',
            flexDirection: 'column',
            gap: '20px'
          }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ 
                fontSize: isMobile ? '3rem' : '4rem',
                marginBottom: '10px'
              }}>
                🎉
              </div>
              <h2 style={{ 
                fontSize: isMobile ? '1.5rem' : '1.8rem',
                fontWeight: 700,
                color: '#86efac',
                margin: 0,
                marginBottom: '10px'
              }}>
                Consensus Reached!
              </h2>
              <p style={{ 
                fontSize: '0.9rem',
                color: 'rgba(226,232,240,0.8)',
                margin: 0
              }}>
                You and Cap have agreed on a strategy!
              </p>
            </div>

            <div style={{
              background: 'rgba(15,23,42,0.6)',
              border: '1px solid rgba(148,163,184,0.25)',
              borderRadius: '12px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: 'rgba(148,163,184,0.85)', fontSize: '0.85rem' }}>Your Score:</span>
                <span style={{ 
                  fontSize: isMobile ? '1.8rem' : '2.2rem',
                  fontWeight: 700,
                  color: '#fbbf24',
                  textShadow: '0 0 20px rgba(251,191,36,0.5)'
                }}>
                  {consensusScore}
                </span>
              </div>
              
              <div style={{ 
                height: '1px', 
                background: 'rgba(148,163,184,0.2)',
                margin: '4px 0'
              }} />

              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                <span style={{ color: 'rgba(148,163,184,0.85)' }}>Messages:</span>
                <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{consensusMessageCount}</span>
              </div>

              {lastPlayerOption && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                  <span style={{ color: 'rgba(148,163,184,0.85)' }}>Your Choice:</span>
                  <span style={{ color: '#93c5fd', fontWeight: 600 }}>{lastPlayerOption}</span>
                </div>
              )}

              {lastAgentOption && (
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.8rem' }}>
                  <span style={{ color: 'rgba(148,163,184,0.85)' }}>Cap's Choice:</span>
                  <span style={{ color: '#86efac', fontWeight: 600 }}>{lastAgentOption}</span>
                </div>
              )}
            </div>

            <div style={{
              background: 'rgba(59,130,246,0.1)',
              border: '1px solid rgba(59,130,246,0.3)',
              borderRadius: '10px',
              padding: '14px',
              fontSize: '0.85rem',
              color: 'rgba(226,232,240,0.9)',
              lineHeight: '1.5'
            }}>
              <strong style={{ color: '#93c5fd' }}>📊 Score submitted to leaderboard!</strong>
              <br />
              Your score has been recorded in the Driving Game section.
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
              <button
                onClick={() => {
                  setShowConsensusModal(false)
                  handleResetSession()
                }}
                style={{
                  flex: 1,
                  padding: '14px',
                  borderRadius: '12px',
                  border: '1px solid rgba(34,197,94,0.5)',
                  background: 'linear-gradient(135deg, rgba(34,197,94,0.25), rgba(22,163,74,0.25))',
                  color: '#86efac',
                  fontWeight: 600,
                  fontSize: '0.95rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'linear-gradient(135deg, rgba(34,197,94,0.35), rgba(22,163,74,0.35))'
                  e.currentTarget.style.transform = 'translateY(-2px)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'linear-gradient(135deg, rgba(34,197,94,0.25), rgba(22,163,74,0.25))'
                  e.currentTarget.style.transform = 'translateY(0)'
                }}
              >
                🔄 Try Again
              </button>
              <button
                onClick={() => setShowConsensusModal(false)}
                style={{
                  flex: 1,
                  padding: '14px',
                  borderRadius: '12px',
                  border: '1px solid rgba(148,163,184,0.35)',
                  background: 'rgba(30,41,59,0.55)',
                  color: 'rgba(226,232,240,0.85)',
                  fontWeight: 600,
                  fontSize: '0.95rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = 'rgba(30,41,59,0.75)'
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = 'rgba(30,41,59,0.55)'
                }}
              >
                Continue
              </button>
            </div>
          </div>
        </div>
      )}
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

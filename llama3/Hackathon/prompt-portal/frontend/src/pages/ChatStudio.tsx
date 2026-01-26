import { useEffect, useMemo, useRef, useState, CSSProperties } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send,
  Trash2,
  RotateCcw,
  Download,
  Plus,
  Copy,
  Check,
  MessageSquare,
  Settings,
  Image as ImageIcon,
  FileText,
  Mic,
  MicOff,
  Edit2,
  ChevronDown,
  ChevronRight,
  Brain,
  X,
  Menu,
  Zap,
  Bot,
  User as UserIcon,
  AlertTriangle,
  Loader2,
  Clock,
  PanelLeftClose,
  PanelLeftOpen,
  Square
} from 'lucide-react'
import { chatbotAPI, modelsAPI } from '../api'
import { useTemplates } from '../contexts/TemplateContext'
import { useWebSpeech } from '../hooks/useWebSpeech'
import { useRawLogs } from '../contexts/RawLogContext'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useTutorial } from '../contexts/TutorialContext'

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

type ChatPreset = { key: string; title: string; description?: string; system_prompt: string }
type ChatSession = { id: number; session_key: string; title: string; template_id?: number | null; system_prompt?: string | null; temperature?: number | null; top_p?: number | null; max_tokens?: number | null; selected_model?: string | null; message_count: number; created_at: string; updated_at: string; last_used_at: string; last_message_preview?: string | null }
type ChatMessage = { id: number; session_id: number; role: 'user' | 'assistant' | 'system' | 'tool'; content: string; thinking?: string | null; metadata?: Record<string, any> | null; request_id?: string | null; created_at: string }
type DraftState = { title: string; system_prompt: string; temperature: number | null; top_p: number | null; max_tokens: number | null; selected_model: string | null; template_id: number | null; preset_key: string | null; prompt_source: 'preset' | 'template' | 'custom' }
type ModelInfo = { name: string; provider: string; model: string; description?: string; supportsVision: boolean }

const bubbleStyles: Record<string, CSSProperties> = {
  user: { background: 'linear-gradient(135deg, rgba(99,102,241,0.25), rgba(129,140,248,0.25))', alignSelf: 'flex-end', border: '1px solid rgba(129,140,248,0.45)' },
  assistant: { background: 'rgba(15,23,42,0.45)', border: '1px solid rgba(148,163,184,0.25)', alignSelf: 'flex-start' },
  system: { background: 'rgba(94,234,212,0.18)', border: '1px solid rgba(94,234,212,0.4)', alignSelf: 'center', color: '#0f172a' }
}

function ThinkingProcess({ thinking }: { thinking: string }) {
  const [isExpanded, setIsExpanded] = useState<boolean>(false)
  const isMobile = useIsMobile()
  if (!thinking || !thinking.trim()) return null

  // Word/character count for the thinking process
  const wordCount = thinking.trim().split(/\s+/).length
  const charCount = thinking.length

  return (
    <motion.div
      initial={{ opacity: 0, y: 15, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      style={{
        width: 'fit-content',
        minWidth: '280px',
        maxWidth: isMobile ? '95%' : '85%',
        alignSelf: 'flex-start',
        marginBottom: '16px',
        borderRadius: '20px',
        overflow: 'hidden',
        border: '1px solid rgba(139, 92, 246, 0.25)',
        background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.08) 0%, rgba(168, 85, 247, 0.04) 100%)',
        backdropFilter: 'blur(12px)',
        boxShadow: '0 8px 32px rgba(139, 92, 246, 0.15), 0 0 0 1px rgba(139, 92, 246, 0.05) inset'
      }}
    >
      {/* Header Button */}
      <motion.button
        onClick={() => setIsExpanded(!isExpanded)}
        whileHover={{ backgroundColor: 'rgba(139, 92, 246, 0.12)' }}
        whileTap={{ scale: 0.995 }}
        style={{
          width: '100%',
          padding: '14px 18px',
          background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.15) 0%, rgba(168, 85, 247, 0.08) 100%)',
          border: 'none',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          color: 'rgba(196, 181, 253, 1)',
          fontSize: '0.875rem',
          fontWeight: 600,
          transition: 'all 0.25s ease',
          justifyContent: 'space-between',
          borderBottom: isExpanded ? '1px solid rgba(139, 92, 246, 0.15)' : 'none'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Animated Brain Icon */}
          <motion.div
            animate={{
              rotate: isExpanded ? [0, 10, -10, 0] : 0,
              scale: isExpanded ? [1, 1.1, 1] : 1
            }}
            transition={{ duration: 0.5 }}
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '10px',
              background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.3) 0%, rgba(168, 85, 247, 0.2) 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 4px 12px rgba(139, 92, 246, 0.25)'
            }}
          >
            <Brain size={18} color="#c4b5fd" />
          </motion.div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '2px' }}>
            <span style={{ letterSpacing: '0.02em' }}>AI Thinking Process</span>
            <span style={{ fontSize: '0.7rem', opacity: 0.6, fontWeight: 400 }}>
              {wordCount.toLocaleString()} words • {charCount.toLocaleString()} characters
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{
            fontSize: '0.7rem',
            padding: '4px 10px',
            borderRadius: '12px',
            background: isExpanded ? 'rgba(139, 92, 246, 0.25)' : 'rgba(139, 92, 246, 0.1)',
            color: 'rgba(196, 181, 253, 0.9)',
            fontWeight: 500,
            transition: 'all 0.25s ease'
          }}>
            {isExpanded ? 'Collapse' : 'Expand'}
          </span>
          <motion.div
            animate={{ rotate: isExpanded ? 180 : 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
          >
            <ChevronDown size={18} style={{ opacity: 0.7 }} />
          </motion.div>
        </div>
      </motion.button>

      {/* Expandable Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
          >
            <div style={{
              padding: '16px 18px 18px 18px',
              background: 'linear-gradient(180deg, rgba(139, 92, 246, 0.04) 0%, rgba(15, 23, 42, 0.3) 100%)',
              fontSize: '0.82rem',
              lineHeight: '1.85',
              color: 'rgba(226, 232, 240, 0.85)',
              maxHeight: '450px',
              overflowY: 'auto',
              wordBreak: 'break-word',
              fontFamily: '"JetBrains Mono", "Fira Code", "SF Mono", Monaco, monospace',
              letterSpacing: '-0.01em',
              scrollbarWidth: 'thin',
              scrollbarColor: 'rgba(139, 92, 246, 0.3) transparent'
            }} className="markdown-content">
              <Markdown
                remarkPlugins={[remarkGfm]}
              >
                {thinking}
              </Markdown>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

function extractThinkingProcess(content: string): { thinking: string | null; cleanContent: string } {
  // Match <think>...</think> tags (commonly used by many LLMs)
  const thinkTagRegex = /<think>([\s\S]*?)<\/think>/
  const thinkMatch = content.match(thinkTagRegex)
  if (thinkMatch) {
    return { thinking: thinkMatch[1].trim(), cleanContent: content.replace(thinkTagRegex, '').trim() }
  }

  // Match <thinking>...</thinking> tags
  const thinkingRegex = /<thinking>([\s\S]*?)<\/thinking>/
  const thinkingMatch = content.match(thinkingRegex)
  if (thinkingMatch) {
    return { thinking: thinkingMatch[1].trim(), cleanContent: content.replace(thinkingRegex, '').trim() }
  }

  // Match special format with |end| and |start| tokens
  const finalMessageRegex = /<\|end\|><\|start\|>assistant<\|channel\|>final<\|message\|>(.*?)$/s
  const finalMatch = content.match(finalMessageRegex)
  if (finalMatch) {
    const thinkingEnd = content.indexOf('<|end|>')
    return { thinking: content.substring(0, thinkingEnd).trim(), cleanContent: finalMatch[1].trim() }
  }

  // Match markdown-style thinking headers
  const markdownThinkingRegex = /^#{1,3}\s*(?:Thinking|思考过程)[\s\S]*?(?=^#{1,3}|$)/m
  const markdownMatch = content.match(markdownThinkingRegex)
  if (markdownMatch) {
    return { thinking: markdownMatch[0].trim(), cleanContent: content.replace(markdownThinkingRegex, '').trim() }
  }

  return { thinking: null, cleanContent: content }
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const isMobile = useIsMobile()
  const style = bubbleStyles[message.role] || bubbleStyles.assistant
  const timestamp = new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  const [copiedIndex, setCopiedIndex] = useState<number | string | null>(null)
  const copyToClipboard = async (text: string, index: number | string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedIndex(index)
      setTimeout(() => setCopiedIndex(null), 2000)
    } catch (err) { }
  }

  // Extract thinking process and clean content
  const { thinking, cleanContent } = extractThinkingProcess(message.content)
  const imageUrls = message.metadata?.image_urls as string[] | undefined
  const videoUrls = message.metadata?.video_urls as string[] | undefined

  return (
    <motion.div
      initial={{ opacity: 0, y: 15, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}
    >
      {/* Show thinking process panel for assistant messages with thinking content */}
      {thinking && message.role === 'assistant' && <ThinkingProcess thinking={thinking} />}

      {/* Message bubble with clean content (thinking tags removed) */}
      <div style={{
        width: 'fit-content',
        minWidth: '60px',
        maxWidth: isMobile ? '92%' : '80%',
        padding: '16px 20px',
        borderRadius: message.role === 'user' ? '20px 20px 4px 20px' : '20px 20px 20px 4px',
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        boxShadow: '0 4px 15px rgba(0,0,0,0.1)',
        ...style
      }}>
        {imageUrls && imageUrls.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
            {imageUrls.map((url, i) => (
              <img key={i} src={url} alt="Uploaded image" style={{ maxWidth: '100%', maxHeight: '300px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }} />
            ))}
          </div>
        )}
        {videoUrls && videoUrls.length > 0 && (
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '8px' }}>
            {videoUrls.map((url, i) => (
              <video key={i} src={url} controls style={{ maxWidth: '100%', maxHeight: '300px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }} />
            ))}
          </div>
        )}
        {/* Display clean content with markdown parsing */}
        <div className="markdown-content">
          <Markdown
            remarkPlugins={[remarkGfm]}
          >
            {cleanContent}
          </Markdown>
        </div>
        <div style={{ fontSize: '0.7rem', alignSelf: 'flex-end', opacity: 0.6, fontWeight: 500 }}>{timestamp}</div>
      </div>
    </motion.div>
  )
}

export default function ChatStudio() {
  const { templates } = useTemplates(); const isMobile = useIsMobile()
  const { addLog } = useRawLogs()
  const [sessions, setSessions] = useState<ChatSession[]>([]); const [presets, setPresets] = useState<ChatPreset[]>([])
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([])
  const [defaultModelName, setDefaultModelName] = useState<string | null>(null)
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null); const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sessionDraft, setSessionDraft] = useState<DraftState | null>(null); const [draftDirty, setDraftDirtyFlag] = useState<boolean>(false)
  const [inputValue, setInputValue] = useState<string>(''); const [loadingSessions, setLoadingSessions] = useState<boolean>(true)
  const [loadingMessages, setLoadingMessages] = useState<boolean>(false); const [sending, setSending] = useState<boolean>(false)
  const [switchingModel, setSwitchingModel] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null); const [showPromptEditor, setShowPromptEditor] = useState<boolean>(false)
  const [savingPrompt, setSavingPrompt] = useState<boolean>(false); const [sidebarOpen, setSidebarOpen] = useState<boolean>(!isMobile)
  const { runTutorial } = useTutorial();
  const [pastedMedia, setPastedMedia] = useState<{ url: string, displayUrl: string, type: 'image' | 'video' }[]>([])
  const messageContainerRef = useRef<HTMLDivElement | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const { isListening, startListening, stopListening, isSupported: speechSupported } = useWebSpeech({
    onTranscript: (t) => setInputValue(p => p + (p && !p.endsWith(' ') ? ' ' : '') + t),
    onError: (e) => setErrorMessage(`Speech recognition error: ${e}`)
  })

  const selectedSession = useMemo(() => sessions.find(s => s.id === selectedSessionId) || null, [sessions, selectedSessionId])
  const hasAssistantMessage = useMemo(() => messages.some(msg => msg.role === 'assistant'), [messages])
  const hasUserMessage = useMemo(() => messages.some(msg => msg.role === 'user'), [messages])

  useEffect(() => {
    (async () => {
      try {
        const [pRes, sRes, mRes, selectedRes] = await Promise.all([
          chatbotAPI.getPresets(),
          chatbotAPI.listSessions(),
          modelsAPI.getAvailable(),
          modelsAPI.getSelected()
        ])
        setPresets(pRes.data); setSessions(sRes.data); setAvailableModels(mRes.data); setDefaultModelName(selectedRes.data?.name ?? null)
        if (sRes.data.length && selectedSessionId === null) setSelectedSessionId(sRes.data[0].id)

        // Trigger tutorial for Chat Studio
        const hasSeenChatTutorial = localStorage.getItem('tutorial_seen_chat')
        if (!hasSeenChatTutorial) {
          setTimeout(() => {
            runTutorial([
              { target: '#chat-sidebar', title: 'Conversation History', content: 'Manage your past conversations or start fresh with a new chat.', position: 'right' },
              { target: '#chat-title-input', title: 'Context Identity', content: 'Rename your sessions to keep your workspace organized.', position: 'bottom' },
              { target: '#chat-model-selector', title: 'Engine Selection', content: 'Switch between different LLM providers to compare reasoning capabilities.', position: 'bottom' },
              { target: '#chat-reset-btn', title: 'Safe Reset', content: 'Clear the current conversation history without deleting the session settings.', position: 'bottom' },
              { target: '#chat-save-btn', title: 'Persistent State', content: 'Save your current session title and model selection.', position: 'bottom' },
              { target: '#chat-input-area', title: 'Multimodal Input', content: 'Send text, paste images, or record voice notes directly into the stream.', position: 'top' },
              { target: '#chat-mic-btn', title: 'Voice Intelligence', content: 'Hands-free interaction using built-in speech-to-text recognition.', position: 'left' },
              { target: '#chat-settings-toggle', title: 'Global Parameters', content: 'Fine-tune temperature, tokens, and system-level instructions.', position: 'top' },
            ]);
            localStorage.setItem('tutorial_seen_chat', 'true');
          }, 1000);
        }
      } catch (e) { setErrorMessage('Failed to load chat data.') }
      setLoadingSessions(false)
    })()
  }, [])

  useEffect(() => {
    if (!selectedSession) { setMessages([]); setSessionDraft(null); return }
    const ns = (selectedSession.system_prompt ?? '').trim(); const mP = presets.find(p => p.system_prompt.trim() === ns)
    const mT = selectedSession.template_id ? templates.find(t => t.id === selectedSession.template_id) : null
    let ps: 'preset' | 'template' | 'custom' = mP ? 'preset' : mT ? 'template' : 'custom'
    const availableModelNames = availableModels.map(m => m.name)
    const fallbackModel = selectedSession.selected_model && availableModelNames.includes(selectedSession.selected_model)
      ? selectedSession.selected_model
      : (defaultModelName && availableModelNames.includes(defaultModelName)
        ? defaultModelName
        : (availableModels[0]?.name || null))
    setSessionDraft({
      title: selectedSession.title,
      system_prompt: ns || (presets[0]?.system_prompt || ''),
      temperature: selectedSession.temperature ?? 0.5,
      top_p: selectedSession.top_p ?? 0.9,
      max_tokens: selectedSession.max_tokens ?? 4096,
      selected_model: fallbackModel,
      template_id: selectedSession.template_id ?? null,
      preset_key: mP?.key ?? null,
      prompt_source: ps
    })
    setDraftDirtyFlag(false); (async () => {
      try { setLoadingMessages(true); const res = await chatbotAPI.getMessages(selectedSession.id); setMessages(res.data) } catch (e) { setErrorMessage('Unable to load conversation messages.') } finally { setLoadingMessages(false) }
    })()
  }, [selectedSession?.id, presets, templates, availableModels])

  useEffect(() => { if (messageContainerRef.current) messageContainerRef.current.scrollTop = messageContainerRef.current.scrollHeight }, [messages])

  const handleCreateSession = async () => { try { const res = await chatbotAPI.createSession({}); setSessions(p => [res.data, ...p]); setSelectedSessionId(res.data.id) } catch (e) { setErrorMessage('Failed to create session.') } }
  const handleSelectSession = (id: number) => { setSelectedSessionId(id); if (isMobile) setSidebarOpen(false) }
  const handleSaveDraft = async () => { if (!selectedSession || !sessionDraft) return; try { await chatbotAPI.updateSession(selectedSession.id, sessionDraft); setSessions(p => p.map(s => s.id === selectedSession.id ? { ...s, ...sessionDraft } : s)); setDraftDirtyFlag(false) } catch (e) { setErrorMessage('Failed to save settings.') } }
  const handleResetSession = async () => { if (!selectedSession) return; try { await chatbotAPI.resetSession(selectedSession.id); setMessages([]); setDraftDirtyFlag(false) } catch (e) { setErrorMessage('Unable to reset session.') } }
  const handleDeleteSession = async (id: number) => { try { await chatbotAPI.deleteSession(id); setSessions(p => p.filter(s => s.id !== id)); if (selectedSessionId === id) setSelectedSessionId(null) } catch (e) { setErrorMessage('Failed to delete session.') } }

  const handleModelChange = async (modelName: string) => {
    if (!selectedSession) return
    const fallbackModel = sessionDraft?.selected_model ?? selectedSession.selected_model ?? null
    setSessionDraft(prev => prev ? { ...prev, selected_model: modelName } : prev)
    setSessions(prev => prev.map(s => s.id === selectedSession.id ? { ...s, selected_model: modelName } : s))
    setSwitchingModel(true)
    try {
      await chatbotAPI.updateSession(selectedSession.id, { selected_model: modelName })
      await modelsAPI.selectModel(modelName)
      setDefaultModelName(modelName)
    } catch (e: any) {
      setErrorMessage(e?.response?.data?.detail || 'Failed to switch model.')
      if (fallbackModel && fallbackModel !== modelName) {
        setSessionDraft(prev => prev ? { ...prev, selected_model: fallbackModel } : prev)
        setSessions(prev => prev.map(s => s.id === selectedSession.id ? { ...s, selected_model: fallbackModel } : s))
        try {
          await chatbotAPI.updateSession(selectedSession.id, { selected_model: fallbackModel })
        } catch {
          // Best-effort rollback; keep UI consistent.
        }
      }
    } finally {
      setSwitchingModel(false)
    }
  }

  const handleSendMessage = async () => {
    if (!selectedSession || !sessionDraft || (!inputValue.trim() && pastedMedia.length === 0) || sending || switchingModel) return
    const content = inputValue.trim(); setSending(true); setInputValue('');
    const imageUrls = pastedMedia.filter(m => m.type === 'image').map(m => m.url)
    const videoUrls = pastedMedia.filter(m => m.type === 'video').map(m => m.url)
    setPastedMedia([]); const optimisticId = -Date.now()

    // Setup abort controller
    const abortController = new AbortController()
    abortControllerRef.current = abortController

    setMessages(p => [...p, {
      id: optimisticId,
      session_id: selectedSession.id,
      role: 'user',
      content: content || (imageUrls.length > 0 || videoUrls.length > 0 ? "Sent media" : ""),
      metadata: imageUrls.length > 0 || videoUrls.length > 0 ? { image_urls: imageUrls, video_urls: videoUrls } : undefined,
      created_at: new Date().toISOString()
    }])
    try {
      let assistantMsgId: number | null = null; let fullContent = ''
      addLog({
        type: 'request', content: JSON.stringify({
          session_id: selectedSession.id,
          content,
          ...sessionDraft
        }, null, 2)
      })
      await chatbotAPI.sendMessageStream({
        session_id: selectedSession.id,
        content,
        image_urls: pastedMedia.filter(m => m.type === 'image').map(m => m.url),
        metadata: { video_urls: pastedMedia.filter(m => m.type === 'video').map(m => m.url) },
        ...sessionDraft
      }, (metadata) => {
        addLog({ type: 'metadata', content: JSON.stringify(metadata, null, 2) })
      }, (chunk) => {
        fullContent += chunk
        addLog({ type: 'chunk', content: chunk })
        if (assistantMsgId === null) { assistantMsgId = -Date.now() - 1; setMessages(p => [...p, { id: assistantMsgId!, session_id: selectedSession.id, role: 'assistant', content: chunk, created_at: new Date().toISOString() }]) }
        else setMessages(p => p.map(m => m.id === assistantMsgId ? { ...m, content: fullContent } : m))
      }, (resContent, realId) => {
        addLog({ type: 'done', content: `Final content: ${resContent.length} chars` })
        setMessages(p => p.map(m => m.id === assistantMsgId ? { ...m, id: realId, content: resContent } : m))
        chatbotAPI.listSessions().then(res => setSessions(res.data))
        abortControllerRef.current = null
      }, (err) => {
        if (err.name === 'AbortError') {
          // No log
        } else {
          setErrorMessage(err.message); setMessages(p => p.filter(m => m.id !== optimisticId && m.id !== assistantMsgId))
        }
        abortControllerRef.current = null
      }, abortController.signal)
    } catch (e: any) {
      if (e.name !== 'AbortError') {
        setErrorMessage('Failed to send message.')
      }
    } finally {
      setSending(false)
      abortControllerRef.current = null
    }
  }

  const handleStopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      setSending(false)
      abortControllerRef.current = null
    }
  }

  const handlePaste = async (e: React.ClipboardEvent) => {
    const items = e.clipboardData.items;
    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const file = items[i].getAsFile();
        if (file) {
          try {
            const res = await chatbotAPI.uploadImage(file);
            // Use file_url for display (Nginx proxy handles /uploads/)
            // Keep url as data URL for LLM API (reliability)
            setPastedMedia(prev => [...prev, {
              url: res.data.url,
              displayUrl: res.data.file_url || res.data.url,
              type: 'image'
            }]);
          } catch (err) {
            setErrorMessage('Failed to upload pasted image.');
          }
        }
      } else if (items[i].type.indexOf('video') !== -1) {
        const file = items[i].getAsFile();
        if (file) {
          try {
            const res = await chatbotAPI.uploadVideo(file);
            setPastedMedia(prev => [...prev, {
              url: res.data.url,
              displayUrl: res.data.url,  // videos use same URL
              type: 'video'
            }]);
          } catch (err) {
            setErrorMessage('Failed to upload pasted video.');
          }
        }
      }
    }
  }

  const sidebarStyle: CSSProperties = { width: isMobile ? '100%' : '280px', background: 'rgba(15, 23, 42, 0.45)', borderRight: isMobile ? 'none' : '1px solid rgba(148,163,184,0.25)', borderBottom: isMobile ? '1px solid rgba(148,163,184,0.25)' : 'none', display: isMobile && !sidebarOpen ? 'none' : 'flex', flexDirection: 'column', height: isMobile ? 'auto' : '100vh', maxHeight: isMobile ? '60vh' : 'auto', overflow: 'hidden', position: isMobile ? 'relative' : 'static', zIndex: 40 }
  const mainStyle: CSSProperties = { flex: 1, display: 'flex', flexDirection: 'column', background: 'rgba(15, 23, 42, 0.25)', height: isMobile ? '100%' : '100vh', overflow: 'hidden' }

  return (
    <div style={{ display: 'flex', height: '100vh', width: '100%', backdropFilter: 'blur(24px)', overflow: 'hidden', flexDirection: isMobile ? 'column' : 'row' }}>
      <AnimatePresence>
        {(!isMobile || sidebarOpen) && (
          <motion.aside id="chat-sidebar" initial={isMobile ? { x: '-100%' } : { width: 280 }} animate={isMobile ? { x: 0 } : { width: 280 }} exit={isMobile ? { x: '-100%' } : { width: 0 }} style={sidebarStyle}>
            <div style={{ padding: '24px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '1.2rem', fontWeight: 700, color: '#fff' }}><MessageSquare size={20} /> <span>Chats</span></div>
                {!isMobile && <button onClick={() => setSidebarOpen(false)} style={{ background: 'transparent', border: 'none', color: 'rgba(148,163,184,0.7)', cursor: 'pointer' }}><PanelLeftClose size={18} /></button>}
              </div>
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={handleCreateSession} style={newChatButtonStyle}><Plus size={18} /> New Chat</motion.button>
            </div>
            <div style={{ flex: 1, overflowY: 'auto', padding: '0 16px 24px' }}>
              {sessions.map(s => (
                <div key={s.id} onClick={() => handleSelectSession(s.id)} style={{ padding: '12px', borderRadius: '12px', background: selectedSessionId === s.id ? 'rgba(99, 102, 241, 0.15)' : 'transparent', border: '1px solid', borderColor: selectedSessionId === s.id ? 'rgba(99, 102, 241, 0.3)' : 'transparent', cursor: 'pointer', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <div style={{ fontWeight: 600, color: selectedSessionId === s.id ? '#fff' : '#cbd5e1', fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{s.title}</div>
                    <button onClick={(e) => { e.stopPropagation(); handleDeleteSession(s.id) }} style={{ background: 'transparent', border: 'none', color: 'rgba(248, 113, 113, 0.4)', cursor: 'pointer' }}><Trash2 size={14} /></button>
                  </div>
                  <div style={{ fontSize: '0.7rem', color: 'rgba(148,163,184,0.6)', marginTop: '4px' }}><Clock size={10} style={{ display: 'inline', marginRight: '4px' }} /> {new Date(s.updated_at).toLocaleDateString()}</div>
                </div>
              ))}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <main style={mainStyle}>
        {selectedSession && sessionDraft ? (
          <>
            <div style={headerStyle}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
                {isMobile && <button onClick={() => setSidebarOpen(true)} style={{ background: 'transparent', border: 'none', color: '#fff' }}><Menu size={24} /></button>}
                <div style={{ display: 'flex', flexDirection: 'column', flex: 1 }}>
                  <input id="chat-title-input" value={sessionDraft.title} onChange={e => { setSessionDraft({ ...sessionDraft, title: e.target.value }); setDraftDirtyFlag(true) }} style={titleInputStyle} />
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Bot size={12} color="#818cf8" />
                    <select
                      id="chat-model-selector"
                      value={sessionDraft.selected_model || ''}
                      onChange={e => handleModelChange(e.target.value)}
                      style={modelSelectStyle}
                    >
                      {availableModels.map(m => (
                        <option key={m.name} value={m.name}>{m.name}</option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button id="chat-reset-btn" onClick={handleResetSession} style={actionButtonStyle} title="Reset"><RotateCcw size={16} /></button>
                <button id="chat-save-btn" onClick={handleSaveDraft} disabled={!draftDirty} style={{ ...actionButtonStyle, background: draftDirty ? '#6366f1' : 'transparent', color: '#fff' }}><Check size={16} /></button>
              </div>
            </div>
            <div ref={messageContainerRef} style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              {messages.map(m => <MessageBubble key={m.id} message={m} />)}
              {loadingMessages && <div style={{ textAlign: 'center', opacity: 0.5 }}><Loader2 className="animate-spin" /></div>}
            </div>
            <div id="chat-input-area" style={inputAreaWrapperStyle}>
              <div style={{ maxWidth: '900px', margin: '0 auto', width: '100%' }}>
                {pastedMedia.length > 0 && (
                  <div style={{ display: 'flex', gap: '8px', marginBottom: '12px', flexWrap: 'wrap' }}>
                    {pastedMedia.map((m, i) => (
                      <div key={i} style={{ position: 'relative', width: '60px', height: '60px' }}>
                        {m.type === 'image' ? (
                          <img src={m.displayUrl} alt="Uploaded" style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }} />
                        ) : (
                          <video src={m.displayUrl} style={{ width: '100%', height: '100%', objectFit: 'cover', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.1)' }} />
                        )}
                        <button
                          onClick={() => setPastedMedia(pastedMedia.filter((_, idx) => idx !== i))}
                          style={{ position: 'absolute', top: '-6px', right: '-6px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: '50%', width: '16px', height: '16px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', fontSize: '10px' }}
                        >
                          <X size={10} />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
                <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-end' }}>
                  <div style={{ flex: 1, position: 'relative' }}>
                    <textarea
                      value={inputValue}
                      onChange={e => setInputValue(e.target.value)}
                      onPaste={handlePaste}
                      onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSendMessage() } }}
                      placeholder="Message AI Assistant..."
                      rows={1}
                      style={textareaStyle}
                    />
                    {speechSupported && <button id="chat-mic-btn" onClick={isListening ? stopListening : startListening} style={{ position: 'absolute', right: '12px', bottom: '10px', background: 'transparent', border: 'none', color: isListening ? '#ef4444' : '#94a3b8', cursor: 'pointer' }}>{isListening ? <MicOff size={18} /> : <Mic size={18} />}</button>}
                  </div>
                  {sending ? (
                    <button onClick={handleStopGeneration} style={{ ...sendButtonStyle, background: '#ef4444' }}>
                      <Square size={18} fill="currentColor" />
                    </button>
                  ) : (
                    <button onClick={handleSendMessage} disabled={(!inputValue.trim() && pastedMedia.length === 0) || switchingModel} style={{ ...sendButtonStyle, background: switchingModel || (!inputValue.trim() && pastedMedia.length === 0) ? 'rgba(99,102,241,0.4)' : '#6366f1' }}>
                      <Send size={20} />
                    </button>
                  )}
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '12px' }}>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button style={toolButtonStyle}><FileText size={14} /> Document</button>
                    <button style={toolButtonStyle}><ImageIcon size={14} /> Image</button>
                  </div>
                  <button id="chat-settings-toggle" onClick={() => setShowPromptEditor(!showPromptEditor)} style={{ ...toolButtonStyle, color: showPromptEditor ? '#818cf8' : '#94a3b8' }}><Settings size={14} /> Settings</button>
                </div>
              </div>
            </div>
            <AnimatePresence>
              {showPromptEditor && (
                <motion.div initial={{ height: 0 }} animate={{ height: 'auto' }} exit={{ height: 0 }} style={{ overflow: 'hidden', background: 'rgba(15,23,42,0.4)', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                  <div style={{ padding: '24px', display: 'grid', gridTemplateColumns: isMobile ? '1fr' : '1fr 1fr 1fr', gap: '20px' }}>
                    <div style={settingGroupStyle}><label style={settingLabelStyle}>Temperature: {sessionDraft.temperature}</label><input type="range" min="0" max="2" step="0.1" value={sessionDraft.temperature ?? 0.5} onChange={e => { setSessionDraft({ ...sessionDraft, temperature: parseFloat(e.target.value) }); setDraftDirtyFlag(true) }} /></div>
                    <div style={settingGroupStyle}><label style={settingLabelStyle}>Top-P: {sessionDraft.top_p}</label><input type="range" min="0" max="1" step="0.05" value={sessionDraft.top_p ?? 0.9} onChange={e => { setSessionDraft({ ...sessionDraft, top_p: parseFloat(e.target.value) }); setDraftDirtyFlag(true) }} /></div>
                    <div style={settingGroupStyle}><label style={settingLabelStyle}>Max Tokens</label><input type="number" value={sessionDraft.max_tokens ?? 4096} onChange={e => { setSessionDraft({ ...sessionDraft, max_tokens: parseInt(e.target.value) }); setDraftDirtyFlag(true) }} style={settingInputStyle} /></div>
                    <div style={{ ...settingGroupStyle, gridColumn: isMobile ? 'auto' : 'span 3' }}><label style={settingLabelStyle}>System Prompt</label><textarea value={sessionDraft.system_prompt} onChange={e => { setSessionDraft({ ...sessionDraft, system_prompt: e.target.value }); setDraftDirtyFlag(true) }} style={{ ...settingInputStyle, height: '100px', resize: 'vertical' }} /></div>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </>
        ) : <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: 0.5 }}>Select a session to start chatting</div>}
      </main>
    </div>
  )
}

const newChatButtonStyle: CSSProperties = { width: '100%', padding: '12px', borderRadius: '12px', border: '1px solid rgba(99,102,241,0.4)', background: 'linear-gradient(135deg, rgba(99,102,241,0.2), rgba(129,140,248,0.1))', color: '#e0e7ff', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }
const headerStyle: CSSProperties = { padding: '16px 24px', borderBottom: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(15,23,42,0.2)' }
const titleInputStyle: CSSProperties = { background: 'transparent', border: 'none', color: '#fff', fontSize: '1.1rem', fontWeight: 700, outline: 'none', width: '100%' }
const modelSelectStyle: CSSProperties = { background: 'transparent', border: 'none', color: '#818cf8', fontSize: '0.75rem', fontWeight: 600, outline: 'none', cursor: 'pointer', padding: 0 }
const actionButtonStyle: CSSProperties = { background: 'transparent', border: '1px solid rgba(255,255,255,0.1)', color: '#94a3b8', padding: '8px', borderRadius: '8px', cursor: 'pointer' }
const inputAreaWrapperStyle: CSSProperties = { padding: '24px', background: 'rgba(15,23,42,0.4)', borderTop: '1px solid rgba(255,255,255,0.05)' }
const textareaStyle: CSSProperties = { width: '100%', background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '12px', padding: '12px 40px 12px 12px', color: '#fff', fontSize: '0.95rem', outline: 'none', resize: 'none' }
const sendButtonStyle: CSSProperties = { width: '48px', height: '42px', borderRadius: '12px', border: 'none', color: '#fff', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }
const toolButtonStyle: CSSProperties = { background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.05)', borderRadius: '8px', padding: '6px 12px', color: '#94a3b8', fontSize: '0.8rem', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }
const settingGroupStyle: CSSProperties = { display: 'flex', flexDirection: 'column', gap: '8px' }
const settingLabelStyle: CSSProperties = { fontSize: '0.75rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }
const settingInputStyle: CSSProperties = { background: 'rgba(0,0,0,0.2)', border: '1px solid rgba(255,255,255,0.1)', borderRadius: '8px', padding: '10px', color: '#fff', fontSize: '0.9rem' }

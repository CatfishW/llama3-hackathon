import { useEffect, useState, useRef, CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'
import { chatbotAPI, ttsAPI } from '../api'
import useVoiceRecorder from '../hooks/useVoiceRecorder'
import useTTS from '../hooks/useTTS'
import VoiceVisualizer from '../components/VoiceVisualizer'

type VoiceMessage = {
  id: string
  role: 'user' | 'assistant'
  text: string
  timestamp: string
  isPlaying?: boolean
}

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

export default function VoiceChat() {
  const isMobile = useIsMobile()
  const navigate = useNavigate()
  
  // State
  const [messages, setMessages] = useState<VoiceMessage[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedVoice, setSelectedVoice] = useState('af_heart')
  const [speechRate, setSpeechRate] = useState(1.0)
  const [sessionTitle, setSessionTitle] = useState('Voice Chat Session')
  const [showSettings, setShowSettings] = useState(false)
  const [playingMessageId, setPlayingMessageId] = useState<string | null>(null)
  const [sessionId, setSessionId] = useState<number | null>(null)
  const [isInitializingSession, setIsInitializingSession] = useState(true)
  
  // Refs
  const messageContainerRef = useRef<HTMLDivElement>(null)
  const recordingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  
  // Hooks
  const {
    isRecording,
    isListening,
    isTranscribing,
    transcript,
    isFinal,
    confidence,
    startRecording,
    stopRecording,
    getAudioVisualizerData,
    cleanup: cleanupRecorder
  } = useVoiceRecorder({
    language: 'en',
    onError: (error) => setError(error)
  })
  
  const {
    isPlaying,
    isSynthesizing,
    synthesizeAndPlay,
    stop: stopTTS,
    cleanup: cleanupTTS
  } = useTTS({
    voice: selectedVoice,
    speed: speechRate,
    onError: (error) => setError(error)
  })
  
  // State for visualization
  const [visualizerData, setVisualizerData] = useState<{ frequency: number[]; waveform: Uint8Array }>({ 
    frequency: [], 
    waveform: new Uint8Array() 
  })
  
  // Update visualizer data while recording
  useEffect(() => {
    if (!isRecording) return
    
    recordingIntervalRef.current = setInterval(() => {
      const data = getAudioVisualizerData()
      setVisualizerData(data)
    }, 50)
    
    return () => {
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current)
    }
  }, [isRecording, getAudioVisualizerData])
  
  // Auto-scroll to latest message
  useEffect(() => {
    if (messageContainerRef.current) {
      messageContainerRef.current.scrollTop = messageContainerRef.current.scrollHeight
    }
  }, [messages])
  
  // Initialize chatbot session
  useEffect(() => {
    const initSession = async () => {
      try {
        setIsInitializingSession(true)
        const response = await chatbotAPI.createSession({
          title: 'Voice Chat Session',
          system_prompt: 'You are a helpful voice assistant. Keep responses concise and conversational. Respond in 1-2 sentences.'
        })
        setSessionId(response.data.id)
        console.log('[VoiceChat] Session created:', response.data.id)
      } catch (err) {
        console.error('[VoiceChat] Failed to create session:', err)
        setError('Failed to initialize chat session')
      } finally {
        setIsInitializingSession(false)
      }
    }
    
    initSession()
  }, [])
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupRecorder()
      cleanupTTS()
      if (recordingIntervalRef.current) clearInterval(recordingIntervalRef.current)
    }
  }, [cleanupRecorder, cleanupTTS])
  
  // Handle mouse events for Talk button
  const handleMouseDown = async () => {
    try {
      setError(null)
      await startRecording()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start recording')
    }
  }
  
  const handleMouseUp = async () => {
    try {
      console.log('[VoiceChat] handleMouseUp called')
      const finalTranscript = await stopRecording()
      console.log('[VoiceChat] stopRecording returned:', finalTranscript)
      console.log('[VoiceChat] Type:', typeof finalTranscript)
      console.log('[VoiceChat] Length:', finalTranscript?.length)
      console.log('[VoiceChat] Trimmed length:', finalTranscript?.trim?.().length)
      console.log('[VoiceChat] Final transcript received:', finalTranscript)
      
      if (finalTranscript && finalTranscript.trim()) {
        console.log('[VoiceChat] Transcript is valid, proceeding')
        // Add user message
        const userMessageId = Date.now().toString()
        const userMessage: VoiceMessage = {
          id: userMessageId,
          role: 'user',
          text: finalTranscript,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
        
        setMessages(prev => [...prev, userMessage])
        setIsProcessing(true)
        setError(null)
        
        try {
          // Send to chatbot API using the created session
          if (!sessionId) {
            throw new Error('Chat session not initialized')
          }
          
          console.log('[VoiceChat] Sending to chatbot API with session:', sessionId)
          console.log('[VoiceChat] Message content:', finalTranscript)
          const response = await chatbotAPI.sendMessage({
            session_id: sessionId,
            content: finalTranscript,
            system_prompt: 'You are a helpful voice assistant. Keep responses concise and conversational. Respond in 1-2 sentences.'
          })
          
          console.log('[VoiceChat] Chatbot response:', response)
          console.log('[VoiceChat] Response data:', response.data)
          
          // Extract assistant text from nested assistant_message object
          let assistantText = ''
          if (response.data?.assistant_message?.content) {
            assistantText = response.data.assistant_message.content
          } else if (response.data?.content) {
            assistantText = response.data.content
          } else if (response.data?.message) {
            assistantText = response.data.message
          } else if (response.data?.text) {
            assistantText = response.data.text
          } else if (response.data?.assistant_message?.text) {
            assistantText = response.data.assistant_message.text
          }
          
          console.log('[VoiceChat] Extracted text:', assistantText)
          console.log('[VoiceChat] Text type:', typeof assistantText)
          console.log('[VoiceChat] Text length:', assistantText?.length)
          console.log('[VoiceChat] Full assistant_message object:', JSON.stringify(response.data?.assistant_message, null, 2))
          
          if (!assistantText || !assistantText.trim()) {
            throw new Error('LLM returned empty response')
          }
          
          console.log('[VoiceChat] Got response from LLM:', assistantText)
          
          // Add assistant message
          const assistantMessageId = Date.now().toString() + '_assistant'
          const assistantMessage: VoiceMessage = {
            id: assistantMessageId,
            role: 'assistant',
            text: assistantText.trim(),
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          }
          
          setMessages(prev => [...prev, assistantMessage])
          
          // Synthesize and play response
          try {
            console.log('[VoiceChat] Starting TTS synthesis...')
            const textToSpeak = assistantText.trim()
            console.log('[VoiceChat] Text to speak:', textToSpeak)
            if (textToSpeak) {
              await synthesizeAndPlay(textToSpeak, selectedVoice, speechRate)
              setPlayingMessageId(assistantMessageId)
            }
          } catch (ttsError) {
            console.error('TTS Error:', ttsError)
            // Don't fail the entire interaction if TTS fails
            setError('Could not play audio response, but text is available')
          }
        } catch (apiError) {
          console.error('[VoiceChat] API Error:', apiError)
          setError(apiError instanceof Error ? apiError.message : 'Failed to get response from LLM')
        } finally {
          setIsProcessing(false)
        }
      } else {
        console.log('[VoiceChat] Empty transcript received')
        console.log('[VoiceChat] Empty transcript')
        setError('No speech detected. Please try again.')
      }
    } catch (err) {
      console.error('[VoiceChat] Error:', err)
      setError(err instanceof Error ? err.message : 'Failed to process speech')
      setIsProcessing(false)
    }
  }
  
  const handleTouchStart = handleMouseDown
  const handleTouchEnd = handleMouseUp
  
  const styles = {
    container: {
      display: 'flex',
      flexDirection: 'column' as const,
      height: '100vh',
      background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e3a8a 100%)',
      color: '#e2e8f0',
      fontFamily: 'Inter, system-ui, sans-serif'
    },
    header: {
      padding: isMobile ? '12px 16px' : '16px 24px',
      borderBottom: '1px solid rgba(148,163,184,0.2)',
      background: 'rgba(15,23,42,0.8)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      gap: '16px'
    } as CSSProperties,
    headerLeft: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      flex: 1
    } as CSSProperties,
    headerTitle: {
      fontSize: isMobile ? '1.2rem' : '1.5rem',
      fontWeight: 700,
      color: '#e2e8f0',
      margin: 0
    } as CSSProperties,
    backButton: {
      padding: '8px 12px',
      borderRadius: '8px',
      border: '1px solid rgba(148,163,184,0.3)',
      background: 'rgba(30,41,59,0.5)',
      color: 'rgba(226,232,240,0.8)',
      fontSize: '1rem',
      cursor: 'pointer',
      transition: 'all 0.2s',
      display: 'flex',
      alignItems: 'center',
      gap: '6px'
    } as CSSProperties,
    mainContent: {
      flex: 1,
      display: 'flex',
      flexDirection: 'column' as const,
      overflow: 'hidden'
    } as CSSProperties,
    messagesContainer: {
      flex: 1,
      overflowY: 'auto' as const,
      padding: isMobile ? '16px 12px' : '24px',
      display: 'flex',
      flexDirection: 'column' as const,
      gap: '16px',
      backgroundColor: 'rgba(15, 23, 42, 0.4)'
    } as CSSProperties,
    messageBubble: {
      maxWidth: isMobile ? '85%' : '65%',
      padding: '14px 18px',
      borderRadius: '18px',
      display: 'flex',
      flexDirection: 'column' as const,
      gap: '8px',
      wordWrap: 'break-word' as const
    } as CSSProperties,
    userBubble: {
      background: 'linear-gradient(135deg, rgba(59,130,246,0.3), rgba(99,102,241,0.3))',
      border: '1px solid rgba(129,140,248,0.5)',
      alignSelf: 'flex-end',
      marginRight: '8px'
    } as CSSProperties,
    assistantBubble: {
      background: 'linear-gradient(135deg, rgba(34,197,94,0.2), rgba(16,185,129,0.2))',
      border: '1px solid rgba(34,197,94,0.4)',
      alignSelf: 'flex-start',
      marginLeft: '8px'
    } as CSSProperties,
    messageText: {
      fontSize: '0.95rem',
      lineHeight: '1.6',
      color: '#e2e8f0'
    } as CSSProperties,
    messageTime: {
      fontSize: '0.7rem',
      color: 'rgba(148,163,184,0.7)',
      alignSelf: 'flex-end'
    } as CSSProperties,
    controlsContainer: {
      padding: isMobile ? '16px 12px' : '24px',
      borderTop: '1px solid rgba(148,163,184,0.2)',
      background: 'rgba(20,20,35,0.5)',
      backdropFilter: 'blur(10px)',
      display: 'flex',
      flexDirection: 'column' as const,
      gap: '16px'
    } as CSSProperties,
    talkButton: {
      width: isMobile ? '100%' : '200px',
      height: isMobile ? '80px' : '100px',
      borderRadius: '50%',
      border: isRecording ? '2px solid rgba(248,113,113,0.5)' : '2px solid rgba(34,197,94,0.5)',
      background: isRecording
        ? 'linear-gradient(135deg, rgba(248,113,113,0.4), rgba(239,68,68,0.4))'
        : 'linear-gradient(135deg, rgba(34,197,94,0.3), rgba(16,185,129,0.3))',
      color: isRecording ? '#fecaca' : '#86efac',
      fontSize: isMobile ? '1.5rem' : '2rem',
      fontWeight: 600,
      cursor: 'pointer',
      transition: 'all 0.2s ease',
      boxShadow: isRecording
        ? '0 0 30px rgba(248,113,113,0.3)'
        : '0 0 20px rgba(34,197,94,0.2)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      margin: '0 auto',
      animation: isRecording ? 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite' : 'none'
    } as CSSProperties,
    statusText: {
      textAlign: 'center' as const,
      fontSize: isMobile ? '0.9rem' : '1rem',
      color: isRecording ? '#fecaca' : '#86efac',
      fontWeight: 500,
      minHeight: '24px'
    } as CSSProperties,
    settingsPanel: {
      padding: isMobile ? '12px' : '16px',
      background: 'rgba(30,41,59,0.4)',
      border: '1px solid rgba(148,163,184,0.2)',
      borderRadius: '12px',
      display: 'flex',
      flexDirection: 'column' as const,
      gap: '12px'
    } as CSSProperties,
    settingRow: {
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      flexWrap: 'wrap' as const
    } as CSSProperties,
    settingLabel: {
      fontSize: '0.85rem',
      fontWeight: 500,
      minWidth: '100px'
    } as CSSProperties,
    select: {
      padding: '8px 12px',
      borderRadius: '8px',
      border: '1px solid rgba(148,163,184,0.3)',
      background: 'rgba(15,23,42,0.55)',
      color: '#e2e8f0',
      fontSize: '0.85rem',
      cursor: 'pointer'
    } as CSSProperties,
    slider: {
      flex: 1,
      minWidth: '120px'
    } as CSSProperties,
    errorMessage: {
      padding: '12px 16px',
      background: 'rgba(248,113,113,0.15)',
      border: '1px solid rgba(248,113,113,0.3)',
      borderRadius: '8px',
      color: '#fecaca',
      fontSize: '0.85rem'
    } as CSSProperties
  }
  
  const buttonStyle = (isActive: boolean): CSSProperties => ({
    padding: '8px 14px',
    borderRadius: '8px',
    border: '1px solid rgba(148,163,184,0.3)',
    background: isActive ? 'rgba(34,197,94,0.2)' : 'rgba(30,41,59,0.5)',
    color: isActive ? '#86efac' : 'rgba(226,232,240,0.8)',
    fontSize: isMobile ? '0.75rem' : '0.85rem',
    cursor: 'pointer',
    transition: 'all 0.2s',
    fontWeight: 500
  })
  
  return (
    <div style={styles.container}>
      {/* Add CSS animation for pulse effect */}
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.7; }
        }
      `}</style>
      
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerLeft}>
          <button
            onClick={() => navigate(-1)}
            style={styles.backButton}
            title="Go back"
          >
            ← Back
          </button>
          <input
            type="text"
            value={sessionTitle}
            onChange={(e) => setSessionTitle(e.target.value)}
            style={{
              fontSize: isMobile ? '1.2rem' : '1.5rem',
              fontWeight: 700,
              background: 'transparent',
              border: 'none',
              color: '#e2e8f0',
              outline: 'none',
              flex: 1,
              minWidth: '0'
            }}
          />
        </div>
        <button
          onClick={() => setShowSettings(!showSettings)}
          style={buttonStyle(showSettings)}
        >
          {showSettings ? '⌛ Hide' : '⚙️ Settings'}
        </button>
      </div>
      
      {/* Error Message */}
      {error && (
        <div style={styles.errorMessage}>
          {error}
          <button
            onClick={() => setError(null)}
            style={{
              marginLeft: 'auto',
              background: 'transparent',
              border: 'none',
              color: '#fecaca',
              cursor: 'pointer',
              fontSize: '1rem'
            }}
          >
            ✕
          </button>
        </div>
      )}
      
      {/* Loading Indicator */}
      {isInitializingSession && (
        <div style={{
          padding: '12px 16px',
          background: 'rgba(59,130,246,0.2)',
          color: '#93c5fd',
          textAlign: 'center',
          fontSize: '0.9rem',
          borderBottom: '1px solid rgba(59,130,246,0.3)'
        }}>
          ⏳ Initializing chat session...
        </div>
      )}
      
      {/* Main Content */}
      <div style={styles.mainContent}>
        {/* Messages */}
        <div ref={messageContainerRef} style={styles.messagesContainer}>
          {messages.length === 0 ? (
            <div style={{
              display: 'flex',
              flexDirection: 'column' as const,
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: 'rgba(148,163,184,0.7)',
              gap: '12px'
            }}>
              <div style={{ fontSize: isMobile ? '2rem' : '3rem' }}>🎤</div>
              <div style={{ fontSize: isMobile ? '0.95rem' : '1.1rem', textAlign: 'center', maxWidth: '300px' }}>
                Hold the Talk button and speak your message to start a conversation
              </div>
            </div>
          ) : (
            messages.map((msg) => (
              <div
                key={msg.id}
                style={{
                  display: 'flex',
                  flexDirection: 'column' as const,
                  alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                  alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start'
                }}
              >
                <div style={{ fontSize: '0.75rem', color: 'rgba(148,163,184,0.8)', marginBottom: '4px', marginLeft: msg.role === 'assistant' ? '8px' : '0', marginRight: msg.role === 'user' ? '8px' : '0' }}>
                  {msg.role === 'user' ? '👤 You' : '🤖 Assistant'}
                </div>
                <div
                  style={{
                    ...styles.messageBubble,
                    ...(msg.role === 'user' ? styles.userBubble : styles.assistantBubble)
                  }}
                >
                  <div style={styles.messageText}>{msg.text}</div>
                  <div style={styles.messageTime}>{msg.timestamp}</div>
                  {msg.role === 'assistant' && (
                    <button
                      onClick={() => {
                        if (playingMessageId === msg.id) {
                          stopTTS()
                          setPlayingMessageId(null)
                        } else {
                          synthesizeAndPlay(msg.text, selectedVoice, speechRate)
                          setPlayingMessageId(msg.id)
                        }
                      }}
                      style={{
                        alignSelf: 'flex-start',
                        padding: '4px 8px',
                        borderRadius: '6px',
                        border: '1px solid rgba(148,163,184,0.3)',
                        background: playingMessageId === msg.id
                          ? 'rgba(59,130,246,0.2)'
                          : 'rgba(30,41,59,0.4)',
                        color: playingMessageId === msg.id ? '#93c5fd' : 'rgba(226,232,240,0.7)',
                        fontSize: '0.75rem',
                        cursor: 'pointer',
                        transition: 'all 0.2s'
                      }}
                    >
                      {playingMessageId === msg.id ? '⏸ Stop' : '▶ Play'}
                    </button>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
        
        {/* Visualizer and Status */}
        {(isRecording || isListening || isTranscribing) && (
          <div style={{
            padding: isMobile ? '12px' : '16px',
            borderTop: '1px solid rgba(148,163,184,0.2)',
            display: 'flex',
            flexDirection: 'column' as const,
            gap: '12px',
            background: 'rgba(20,20,35,0.5)'
          }}>
            {(isRecording || isListening) && (
              <VoiceVisualizer
                isActive={isRecording}
                frequency={visualizerData.frequency}
                waveform={visualizerData.waveform}
              />
            )}
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              fontSize: '0.8rem',
              color: 'rgba(148,163,184,0.85)'
            }}>
              <span>{isTranscribing ? '✨ Transcribing...' : isRecording ? '🎙️ Recording...' : '👂 Listening...'}</span>
              {confidence > 0 && !isTranscribing && (
                <span>
                  Confidence: {(confidence * 100).toFixed(0)}%
                </span>
              )}
            </div>
            {transcript && !isTranscribing && (
              <div style={{
                padding: '8px 12px',
                background: 'rgba(30,41,59,0.4)',
                borderRadius: '8px',
                fontSize: '0.85rem',
                color: '#e2e8f0'
              }}>
                <span style={{ color: 'rgba(148,163,184,0.7)', fontSize: '0.75rem' }}>
                  {isFinal ? '✓ Final:' : '~ Interim:'}
                </span>
                {' '}{transcript}
              </div>
            )}
          </div>
        )}
      </div>
      
      {/* Controls */}
      <div style={styles.controlsContainer}>
        {/* Settings Panel */}
        {showSettings && (
          <div style={styles.settingsPanel}>
            <div style={styles.settingRow}>
              <label style={styles.settingLabel}>Voice:</label>
              <select
                value={selectedVoice}
                onChange={(e) => setSelectedVoice(e.target.value)}
                style={styles.select}
              >
                <option value="af_heart">AF Heart (Female Warm)</option>
                <option value="af">AF (Female)</option>
                <option value="am">AM (Male)</option>
                <option value="bf">BF (Female Brit)</option>
                <option value="bm">BM (Male Brit)</option>
              </select>
            </div>
            <div style={styles.settingRow}>
              <label style={styles.settingLabel}>Speed: {speechRate.toFixed(1)}x</label>
              <input
                type="range"
                min="0.5"
                max="2"
                step="0.1"
                value={speechRate}
                onChange={(e) => setSpeechRate(parseFloat(e.target.value))}
                style={{
                  ...styles.slider,
                  cursor: 'pointer'
                }}
              />
            </div>
          </div>
        )}
        
        {/* Status Text */}
        <div style={styles.statusText}>
          {isProcessing ? '🔄 Processing...' : isSynthesizing ? '🔊 Generating audio...' : isTranscribing ? '✨ Transcribing...' : isRecording ? '🎙️ Recording...' : 'Ready to talk'}
        </div>
        
        {/* Talk Button */}
        <button
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
          disabled={isProcessing || isSynthesizing || isTranscribing || isInitializingSession}
          style={{
            ...styles.talkButton,
            opacity: isProcessing || isSynthesizing || isTranscribing || isInitializingSession ? 0.6 : 1,
            cursor: isProcessing || isSynthesizing || isTranscribing || isInitializingSession ? 'not-allowed' : 'pointer'
          }}
          title={isInitializingSession ? "Initializing session..." : "Hold to record, release to send"}
        >
          {isRecording ? '🎤' : isInitializingSession ? '⏳' : '💬'}
        </button>
        
        {/* Quick Actions */}
        <div style={{
          display: 'flex',
          gap: '8px',
          justifyContent: 'center',
          flexWrap: 'wrap' as const
        }}>
          <button
            onClick={() => {
              setMessages([])
              setError(null)
            }}
            style={buttonStyle(false)}
          >
            🗑️ Clear
          </button>
          {messages.length > 0 && (
            <button
              onClick={() => {
                const transcript = messages
                  .map(m => `${m.role === 'user' ? 'You' : 'Assistant'}: ${m.text}`)
                  .join('\n\n')
                navigator.clipboard.writeText(transcript)
                setError(null)
              }}
              style={buttonStyle(false)}
            >
              📋 Copy All
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

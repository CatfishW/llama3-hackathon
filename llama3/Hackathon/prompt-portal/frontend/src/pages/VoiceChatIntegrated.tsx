/*
 * Improved Voice Chat Page - SST→LLM→TTS Pipeline
 * Direct integration with backend /api/voice/message endpoint
 */

import React, { useEffect, useState, useRef, CSSProperties } from 'react'
import { useNavigate } from 'react-router-dom'

interface Message {
  id: string
  role: 'user' | 'assistant'
  text: string
  timestamp: string
  audio_base64?: string
}

interface ProcessingStep {
  step: 'sst' | 'llm' | 'tts'
  label: string
  icon: string
}

export default function VoiceChatPage() {
  const navigate = useNavigate()
  
  // State
  const [messages, setMessages] = useState<Message[]>([])
  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [currentProcessingStep, setCurrentProcessingStep] = useState<ProcessingStep | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedVoice, setSelectedVoice] = useState('af_heart')
  const [speed, setSpeed] = useState(1.0)
  const [language, setLanguage] = useState('en')
  
  // Refs
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  
  const processingSteps: Record<string, ProcessingStep> = {
    sst: { step: 'sst', label: 'Transcribing...', icon: '🎤' },
    llm: { step: 'llm', label: 'Thinking...', icon: '🧠' },
    tts: { step: 'tts', label: 'Generating Audio...', icon: '🔊' }
  }
  
  // Format time
  function getTime(): string {
    return new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false
    })
  }
  
  // Auto-scroll to bottom
  useEffect(() => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight
    }
  }, [messages])
  
  // Start recording
  async function startRecording() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      
      audioChunksRef.current = []
      const mediaRecorder = new MediaRecorder(stream)
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }
      
      mediaRecorderRef.current = mediaRecorder
      mediaRecorder.start()
      setIsRecording(true)
      setError(null)
      
      console.log('🎤 Recording started')
    } catch (e) {
      const errMsg = e instanceof Error ? e.message : 'Failed to access microphone'
      setError(`Microphone error: ${errMsg}`)
      console.error('Microphone error:', e)
    }
  }
  
  // Stop recording and send
  async function stopRecording() {
    if (!mediaRecorderRef.current) return
    
    setIsRecording(false)
    setIsProcessing(true)
    setError(null)
    
    const recorder = mediaRecorderRef.current
    
    recorder.onstop = async () => {
      try {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' })
        
        if (audioBlob.size === 0) {
          setError('No audio recorded. Please try again.')
          setIsProcessing(false)
          return
        }
        
        // Convert to base64
        const reader = new FileReader()
        reader.onload = async (e) => {
          try {
            const base64Audio = (e.target?.result as string)?.split(',')[1]
            
            if (!base64Audio) {
              setError('Failed to encode audio')
              setIsProcessing(false)
              return
            }
            
            console.log('📤 Sending voice to backend...')
            setCurrentProcessingStep(processingSteps.sst)
            
            // Get auth token
            const token = localStorage.getItem('token')
            if (!token) {
              setError('Not authenticated. Please login.')
              setIsProcessing(false)
              return
            }
            
            // Send to voice/message endpoint
            const response = await fetch('/api/voice/message', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
              },
              body: JSON.stringify({
                audio_base64: base64Audio,
                language: language,
                voice: selectedVoice,
                speed: speed,
                system_prompt: 'You are a helpful voice assistant. Respond concisely and conversationally.'
              })
            })
            
            if (!response.ok) {
              const errorData = await response.json()
              throw new Error(errorData.detail || `HTTP ${response.status}`)
            }
            
            // Update processing step
            setCurrentProcessingStep(processingSteps.llm)
            const data = await response.json()
            setCurrentProcessingStep(processingSteps.tts)
            
            console.log('✅ Pipeline complete')
            
            // Add user message
            const userMessage: Message = {
              id: `msg-${Date.now()}`,
              role: 'user',
              text: data.user_text,
              timestamp: getTime()
            }
            
            setMessages((prev) => [...prev, userMessage])
            
            // Add assistant message
            const assistantMessage: Message = {
              id: `msg-${Date.now()}-assistant`,
              role: 'assistant',
              text: data.assistant_text,
              timestamp: getTime(),
              audio_base64: data.audio_base64
            }
            
            setMessages((prev) => [...prev, assistantMessage])
            
            // Auto-play response
            if (data.audio_base64) {
              try {
                const audioElement = new Audio(
                  `data:audio/wav;base64,${data.audio_base64}`
                )
                audioElement.play().catch((e) => {
                  console.warn('Auto-play blocked:', e)
                })
              } catch (e) {
                console.error('Audio play error:', e)
              }
            }
          } catch (err) {
            const errMsg = err instanceof Error ? err.message : 'Pipeline failed'
            console.error('Pipeline error:', err)
            setError(`Processing error: ${errMsg}`)
          } finally {
            setIsProcessing(false)
            setCurrentProcessingStep(null)
          }
        }
        
        reader.readAsDataURL(audioBlob)
      } catch (err) {
        const errMsg = err instanceof Error ? err.message : 'Error processing audio'
        console.error('Processing error:', err)
        setError(errMsg)
        setIsProcessing(false)
      }
    }
    
    recorder.stop()
    recorder.stream.getTracks().forEach((track) => track.stop())
    mediaRecorderRef.current = null
  }
  
  // Handle mouse/touch for recording
  const handleMouseDown = async () => {
    if (!isProcessing && !isRecording) {
      await startRecording()
    }
  }
  
  const handleMouseUp = () => {
    if (isRecording) {
      stopRecording()
    }
  }
  
  const handleTouchStart = handleMouseDown
  const handleTouchEnd = handleMouseUp
  
  // Clear chat
  function clearChat() {
    setMessages([])
    setError(null)
  }
  
  // Play audio
  function playAudio(audio_base64: string) {
    try {
      const audioElement = new Audio(`data:audio/wav;base64,${audio_base64}`)
      audioElement.play()
    } catch (e) {
      setError('Failed to play audio')
    }
  }
  
  // Styles
  const styles: Record<string, CSSProperties> = {
    container: {
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      color: '#fff',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      overflow: 'hidden'
    },
    header: {
      padding: '20px',
      background: 'rgba(0, 0, 0, 0.1)',
      borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      backdropFilter: 'blur(10px)'
    },
    title: {
      margin: 0,
      fontSize: '24px',
      fontWeight: 600
    },
    backButton: {
      padding: '8px 12px',
      background: 'rgba(255, 255, 255, 0.1)',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      borderRadius: '6px',
      color: '#fff',
      cursor: 'pointer',
      fontSize: '14px',
      transition: 'all 0.2s'
    },
    messagesContainer: {
      flex: 1,
      overflowY: 'auto' as const,
      padding: '20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '12px'
    },
    emptyState: {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      height: '100%',
      opacity: 0.7,
      textAlign: 'center'
    },
    messageBubble: {
      maxWidth: '70%',
      padding: '12px 16px',
      borderRadius: '12px',
      wordWrap: 'break-word' as const,
      animation: 'slideIn 0.3s ease-out'
    },
    userMessage: {
      alignSelf: 'flex-end',
      background: 'rgba(255, 255, 255, 0.2)',
      border: '1px solid rgba(255, 255, 255, 0.3)'
    },
    assistantMessage: {
      alignSelf: 'flex-start',
      background: 'rgba(0, 0, 0, 0.2)',
      border: '1px solid rgba(255, 255, 255, 0.2)'
    },
    processingStatus: {
      padding: '16px',
      background: 'rgba(0, 0, 0, 0.15)',
      borderTop: '1px solid rgba(255, 255, 255, 0.1)',
      display: 'flex',
      justifyContent: 'space-around',
      gap: '20px'
    },
    processingStep: {
      display: 'flex',
      flexDirection: 'column' as const,
      alignItems: 'center',
      gap: '8px',
      opacity: 0.5,
      transition: 'opacity 0.3s'
    },
    processingStepActive: {
      opacity: 1,
      animation: 'bounce 0.6s infinite'
    },
    stepIcon: {
      fontSize: '24px'
    },
    stepLabel: {
      fontSize: '12px',
      fontWeight: 500
    },
    controls: {
      padding: '20px',
      background: 'rgba(0, 0, 0, 0.2)',
      borderTop: '1px solid rgba(255, 255, 255, 0.1)',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
      alignItems: 'center'
    },
    micButton: {
      width: '80px',
      height: '80px',
      borderRadius: '50%',
      border: '3px solid rgba(255, 255, 255, 0.3)',
      background: isRecording
        ? 'linear-gradient(135deg, #ef4444, #dc2626)'
        : 'linear-gradient(135deg, #667eea, #764ba2)',
      color: '#fff',
      fontSize: '32px',
      cursor: isProcessing ? 'not-allowed' : 'pointer',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      transition: 'all 0.3s',
      opacity: isProcessing ? 0.6 : 1,
      boxShadow: isRecording ? '0 0 30px rgba(239, 68, 68, 0.5)' : 'none',
      animation: isRecording ? 'pulse-button 1s infinite' : 'none'
    },
    settingsPanel: {
      display: 'flex',
      gap: '16px',
      padding: '12px',
      background: 'rgba(0, 0, 0, 0.15)',
      borderRadius: '8px',
      flexWrap: 'wrap' as const
    },
    settingGroup: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px'
    },
    label: {
      fontSize: '12px',
      fontWeight: 500,
      minWidth: '60px'
    },
    select: {
      padding: '6px 10px',
      borderRadius: '6px',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      background: 'rgba(0, 0, 0, 0.2)',
      color: '#fff',
      fontSize: '12px',
      cursor: 'pointer'
    },
    slider: {
      width: '100px',
      cursor: 'pointer'
    },
    errorMessage: {
      padding: '12px 16px',
      background: 'rgba(239, 68, 68, 0.2)',
      border: '1px solid rgba(239, 68, 68, 0.4)',
      borderRadius: '8px',
      color: '#fecaca',
      fontSize: '12px',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center'
    },
    actionButtons: {
      display: 'flex',
      gap: '8px',
      justifyContent: 'center',
      flexWrap: 'wrap' as const
    },
    button: {
      padding: '8px 12px',
      borderRadius: '6px',
      border: '1px solid rgba(255, 255, 255, 0.2)',
      background: 'rgba(255, 255, 255, 0.1)',
      color: '#fff',
      fontSize: '12px',
      cursor: 'pointer',
      transition: 'all 0.2s'
    }
  }
  
  return (
    <div style={styles.container}>
      <style>{`
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        @keyframes pulse-button {
          0%, 100% { box-shadow: 0 0 30px rgba(239, 68, 68, 0.5); }
          50% { box-shadow: 0 0 50px rgba(239, 68, 68, 0.8); }
        }
        @keyframes bounce {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.1); }
        }
      `}</style>
      
      {/* Header */}
      <div style={styles.header}>
        <button
          onClick={() => navigate(-1)}
          style={styles.backButton}
        >
          ← Back
        </button>
        <h1 style={styles.title}>🎤 Voice Chat</h1>
        <div style={{ width: '80px' }} />
      </div>
      
      {/* Error Message */}
      {error && (
        <div style={styles.errorMessage}>
          <span>❌ {error}</span>
          <button
            onClick={() => setError(null)}
            style={{
              background: 'none',
              border: 'none',
              color: '#fecaca',
              cursor: 'pointer',
              fontSize: '16px'
            }}
          >
            ×
          </button>
        </div>
      )}
      
      {/* Messages */}
      <div ref={messagesContainerRef} style={styles.messagesContainer}>
        {messages.length === 0 ? (
          <div style={styles.emptyState}>
            <div style={{ fontSize: '48px', marginBottom: '16px' }}>🎤</div>
            <p style={{ margin: 0 }}>Hold the microphone button and speak</p>
            <p style={{ margin: '8px 0 0 0', fontSize: '12px', opacity: 0.7 }}>
              Your voice will be transcribed, processed by AI, and spoken back to you
            </p>
          </div>
        ) : (
          messages.map((msg) => (
            <div key={msg.id} style={{ display: 'flex', flexDirection: msg.role === 'user' ? 'row-reverse' : 'row' }}>
              <div
                style={{
                  ...styles.messageBubble,
                  ...(msg.role === 'user' ? styles.userMessage : styles.assistantMessage)
                }}
              >
                <div style={{ fontSize: '13px', lineHeight: 1.4 }}>{msg.text}</div>
                {msg.audio_base64 && (
                  <button
                    onClick={() => playAudio(msg.audio_base64!)}
                    style={{
                      marginTop: '8px',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      border: '1px solid rgba(255, 255, 255, 0.3)',
                      background: 'rgba(255, 255, 255, 0.1)',
                      color: '#fff',
                      fontSize: '11px',
                      cursor: 'pointer'
                    }}
                  >
                    ▶ Play
                  </button>
                )}
                <div style={{ fontSize: '10px', opacity: 0.6, marginTop: '4px' }}>
                  {msg.timestamp}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
      
      {/* Processing Status */}
      {isProcessing && currentProcessingStep && (
        <div style={styles.processingStatus}>
          {Object.values(processingSteps).map((step) => (
            <div
              key={step.step}
              style={{
                ...styles.processingStep,
                ...(currentProcessingStep.step === step.step ? styles.processingStepActive : {})
              }}
            >
              <div style={styles.stepIcon}>{step.icon}</div>
              <div style={styles.stepLabel}>{step.label}</div>
            </div>
          ))}
        </div>
      )}
      
      {/* Controls */}
      <div style={styles.controls}>
        <div style={styles.settingsPanel}>
          <div style={styles.settingGroup}>
            <label style={styles.label}>Voice:</label>
            <select
              value={selectedVoice}
              onChange={(e) => setSelectedVoice(e.target.value)}
              style={styles.select}
            >
              <option value="af_heart">AF Heart</option>
              <option value="af">AF</option>
              <option value="am">AM</option>
              <option value="bf">BF</option>
              <option value="bm">BM</option>
            </select>
          </div>
          
          <div style={styles.settingGroup}>
            <label style={styles.label}>Speed:</label>
            <input
              type="range"
              min="0.5"
              max="2"
              step="0.1"
              value={speed}
              onChange={(e) => setSpeed(parseFloat(e.target.value))}
              style={styles.slider}
            />
            <span style={{ fontSize: '12px', minWidth: '30px' }}>
              {speed.toFixed(1)}x
            </span>
          </div>
          
          <div style={styles.settingGroup}>
            <label style={styles.label}>Lang:</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              style={styles.select}
            >
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
            </select>
          </div>
        </div>
        
        <button
          onMouseDown={handleMouseDown}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onTouchStart={handleTouchStart}
          onTouchEnd={handleTouchEnd}
          disabled={isProcessing}
          style={styles.micButton}
          title="Hold to record"
        >
          {isRecording ? '🎤' : '💬'}
        </button>
        
        <div style={styles.actionButtons}>
          <button
            onClick={clearChat}
            disabled={messages.length === 0 || isProcessing}
            style={styles.button}
          >
            🗑️ Clear
          </button>
          {messages.length > 0 && (
            <button
              onClick={() => {
                const text = messages
                  .map((m) => `${m.role === 'user' ? 'You' : 'Assistant'}: ${m.text}`)
                  .join('\n\n')
                navigator.clipboard.writeText(text)
              }}
              style={styles.button}
            >
              📋 Copy
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

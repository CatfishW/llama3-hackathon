import { useEffect, useRef, useState } from 'react'
import { api } from '../api'

type Template = { id: number; title: string }

interface MQTTMessage {
  id: string
  timestamp: number
  topic: string
  hint?: any
  raw?: string
  parsed?: boolean
}

export default function TestMQTT() {
  const [templates, setTemplates] = useState<Template[]>([])
  const [templateId, setTemplateId] = useState<number | null>(null)
  const [sessionId, setSessionId] = useState('session-' + Math.random().toString(36).slice(2, 8))
  const [messages, setMessages] = useState<MQTTMessage[]>([])
  const wsRef = useRef<WebSocket | null>(null)
  const [connected, setConnected] = useState(false)
  const [loading, setLoading] = useState(false)
  const [connectionAttempts, setConnectionAttempts] = useState(0)
  const [lastMessageTime, setLastMessageTime] = useState<Date | null>(null)
  const [autoReconnect, setAutoReconnect] = useState(true)
  const reconnectTimeoutRef = useRef<number | null>(null)

  // Auto-reconnect effect
  useEffect(() => {
    if (!connected && autoReconnect && connectionAttempts < 5) {
      reconnectTimeoutRef.current = window.setTimeout(() => {
        // Auto-reconnect attempt ${connectionAttempts + 1}/5 (logging disabled)
        connectWS()
      }, Math.min(1000 * Math.pow(2, connectionAttempts), 10000)) // Exponential backoff, max 10s
    }
    
    return () => {
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [connected, autoReconnect, connectionAttempts])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnectWS()
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current)
      }
    }
  }, [])

  useEffect(() => {
    (async () => {
      try {
        const res = await api.get('/api/templates')
        setTemplates(res.data.map((t: any) => ({ id: t.id, title: t.title })))
        if (res.data.length > 0) setTemplateId(res.data[0].id)
      } catch (e) {
        // Failed to load templates (logging disabled)
      }
    })()
  }, [])

  function connectWS() {
    // Clear any pending reconnection
    if (reconnectTimeoutRef.current) {
      window.clearTimeout(reconnectTimeoutRef.current)
      reconnectTimeoutRef.current = null
    }

    const base = (import.meta as any).env?.VITE_WS_BASE || 'ws://localhost:8000'
    const ws = new WebSocket(base + '/api/mqtt/ws/hints/' + sessionId)
    
    ws.onopen = () => {
      setConnected(true)
      setConnectionAttempts(0)
      // WebSocket connected to session (logging disabled)
    }
    
    ws.onclose = () => {
      setConnected(false)
      // WebSocket disconnected (logging disabled)
    }
    
    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data)
        const newMessage: MQTTMessage = {
          id: Math.random().toString(36).substr(2, 9),
          timestamp: Date.now(),
          topic: data.topic || 'unknown',
          hint: data.hint,
          raw: evt.data,
          parsed: true
        }
        setMessages(prev => [newMessage, ...prev].slice(0, 100))
        setLastMessageTime(new Date())
      } catch (error) {
        // Fallback for non-JSON messages
        const newMessage: MQTTMessage = {
          id: Math.random().toString(36).substr(2, 9),
          timestamp: Date.now(),
          topic: 'raw',
          raw: evt.data,
          parsed: false
        }
        setMessages(prev => [newMessage, ...prev].slice(0, 100))
        setLastMessageTime(new Date())
      }
    }
    
    ws.onerror = (err) => {
      // WebSocket error (logging disabled)
      setConnectionAttempts(prev => prev + 1)
    }
    
    wsRef.current = ws
  }

  function disconnectWS() {
    wsRef.current?.close()
    wsRef.current = null
  }

  function clearMessages() {
    setMessages([])
    setLastMessageTime(null)
  }

  function generateNewSessionId() {
    const newId = 'session-' + Math.random().toString(36).slice(2, 8)
    setSessionId(newId)
    // Reconnect if currently connected
    if (connected) {
      disconnectWS()
      setTimeout(() => connectWS(), 100)
    }
  }

  async function publishDummyState() {
    if (!templateId) {
      alert('Please select a template first')
      return
    }
    
    setLoading(true)
    try {
      // Generate a more realistic maze state that matches your LAM expectations
      const mazeSize = 10
      const maze = Array(mazeSize).fill(null).map(() => Array(mazeSize).fill(1))
      
      // Add some walls (0 = wall, 1 = floor)
      for (let i = 0; i < mazeSize; i++) {
        for (let j = 0; j < mazeSize; j++) {
          if (Math.random() < 0.3) { // 30% chance of wall
            maze[i][j] = 0
          }
        }
      }
      
      // Ensure player and exit positions are on floor
      const playerPos = [1, 1]
      const exitPos = [mazeSize - 2, mazeSize - 2]
      maze[playerPos[1]][playerPos[0]] = 1
      maze[exitPos[1]][exitPos[0]] = 1
      
      const dummyState = {
        sessionId: sessionId,
        player_pos: playerPos,
        exit_pos: exitPos,
        visible_map: maze,
        oxygenPellets: [
          { x: 3, y: 3 },
          { x: 6, y: 4 },
          { x: 2, y: 7 }
        ],
        germs: [
          { x: 4, y: 2 },
          { x: 7, y: 6 }
        ],
        tick: Date.now(),
        health: 100,
        oxygen: 80
      }
      
      await api.post('/api/mqtt/publish_state', {
        session_id: sessionId,
        template_id: templateId,
        state: dummyState
      })
      
      alert(`Successfully published maze state for session ${sessionId}`)
    } catch (e) {
      alert('Failed to publish state. Check console for details.')
      // Publish error (logging disabled)
    } finally {
      setLoading(false)
    }
  }

  const containerStyle = {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '40px 20px'
  }

  const headerStyle = {
    textAlign: 'center' as const,
    marginBottom: '40px'
  }

  const controlPanelStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '15px',
    padding: '30px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    marginBottom: '30px'
  }

  const inputStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    border: '1px solid rgba(255, 255, 255, 0.3)',
    borderRadius: '8px',
    padding: '10px 15px',
    color: 'white',
    fontSize: '1rem',
    minWidth: '150px'
  }

  const selectStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    border: '1px solid rgba(255, 255, 255, 0.3)',
    borderRadius: '8px',
    padding: '10px 15px',
    color: 'white',
    fontSize: '1rem',
    minWidth: '200px'
  }

  const buttonStyle = (variant: 'primary' | 'secondary' | 'success' | 'danger') => {
    const variants = {
      primary: 'linear-gradient(45deg, #4ecdc4, #44a08d)',
      secondary: 'rgba(255, 255, 255, 0.2)',
      success: 'linear-gradient(45deg, #4caf50, #45a049)',
      danger: 'linear-gradient(45deg, #ff6b6b, #ee5a52)'
    }
    
    return {
      background: variants[variant],
      color: 'white',
      border: 'none',
      padding: '12px 20px',
      borderRadius: '8px',
      fontSize: '1rem',
      fontWeight: '600',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      display: 'inline-flex',
      alignItems: 'center',
      gap: '8px'
    }
  }

  const messagesStyle = {
    background: 'rgba(0, 0, 0, 0.4)',
    borderRadius: '15px',
    padding: '20px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    maxHeight: '400px',
    overflow: 'auto'
  }

  const messageStyle = {
    background: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '8px',
    padding: '15px',
    marginBottom: '10px',
    fontSize: '0.9rem',
    fontFamily: 'Monaco, Consolas, monospace',
    lineHeight: '1.4',
    color: 'rgba(255, 255, 255, 0.9)',
    border: '1px solid rgba(255, 255, 255, 0.1)'
  }

  const statusStyle = (isConnected: boolean) => ({
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 16px',
    borderRadius: '20px',
    fontSize: '0.9rem',
    fontWeight: '600',
    background: isConnected ? 'rgba(76, 175, 80, 0.3)' : 'rgba(255, 107, 107, 0.3)',
    color: isConnected ? '#4caf50' : '#ff6b6b',
    border: `1px solid ${isConnected ? 'rgba(76, 175, 80, 0.5)' : 'rgba(255, 107, 107, 0.5)'}`
  })

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={{ fontSize: '2.5rem', fontWeight: '700', marginBottom: '20px' }}>
          <i className="fas fa-vial" style={{ marginRight: '15px' }}></i>
          Test & Monitor
        </h1>
        <p style={{ fontSize: '1.2rem', opacity: '0.8', maxWidth: '600px', margin: '0 auto' }}>
          Test your prompt templates in real-time and monitor MQTT communication with the LAM system
        </p>
      </div>

      <div style={controlPanelStyle}>
        <h3 style={{ fontSize: '1.5rem', marginBottom: '25px', fontWeight: '600' }}>
          <i className="fas fa-cog" style={{ marginRight: '10px' }}></i>
          Control Panel
        </h3>
        
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
          gap: '20px',
          marginBottom: '25px'
        }}>
          <div>
            <label style={{
              display: 'block',
              marginBottom: '8px',
              fontSize: '1rem',
              fontWeight: '500',
              color: 'rgba(255, 255, 255, 0.9)'
            }}>
              <i className="fas fa-gamepad" style={{ marginRight: '8px' }}></i>
              Session ID
            </label>
            <div style={{ display: 'flex', gap: '8px', alignItems: 'stretch' }}>
              <input
                value={sessionId}
                onChange={e => setSessionId(e.target.value)}
                style={{ ...inputStyle, flex: 1 }}
                placeholder="Enter session ID"
              />
              <button
                onClick={generateNewSessionId}
                style={{
                  ...buttonStyle('secondary'),
                  padding: '10px 15px',
                  fontSize: '0.9rem'
                }}
                title="Generate new session ID"
              >
                <i className="fas fa-refresh"></i>
              </button>
            </div>
          </div>

          <div>
            <label style={{
              display: 'block',
              marginBottom: '8px',
              fontSize: '1rem',
              fontWeight: '500',
              color: 'rgba(255, 255, 255, 0.9)'
            }}>
              <i className="fas fa-file-code" style={{ marginRight: '8px' }}></i>
              Template
            </label>
            <select
              value={templateId ?? ''}
              onChange={e => setTemplateId(parseInt(e.target.value))}
              style={selectStyle}
            >
              <option value="" disabled>Select a template</option>
              {templates.map(t => (
                <option key={t.id} value={t.id} style={{ background: '#333', color: 'white' }}>
                  {t.title}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label style={{
              display: 'block',
              marginBottom: '8px',
              fontSize: '1rem',
              fontWeight: '500',
              color: 'rgba(255, 255, 255, 0.9)'
            }}>
              <i className="fas fa-wifi" style={{ marginRight: '8px' }}></i>
              Connection Status
            </label>
            <div style={statusStyle(connected)}>
              <i className={`fas ${connected ? 'fa-check-circle' : 'fa-times-circle'}`}></i>
              {connected ? 'Connected' : 'Disconnected'}
            </div>
            {lastMessageTime && (
              <div style={{ 
                fontSize: '0.8rem', 
                marginTop: '4px', 
                opacity: '0.7',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                <i className="fas fa-clock"></i>
                Last message: {lastMessageTime.toLocaleTimeString()}
              </div>
            )}
            {connectionAttempts > 0 && !connected && (
              <div style={{ 
                fontSize: '0.8rem', 
                marginTop: '4px', 
                color: '#ff9800',
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                <i className="fas fa-exclamation-triangle"></i>
                Reconnect attempts: {connectionAttempts}/5
              </div>
            )}
          </div>

          <div>
            <label style={{
              display: 'block',
              marginBottom: '8px',
              fontSize: '1rem',
              fontWeight: '500',
              color: 'rgba(255, 255, 255, 0.9)'
            }}>
              <i className="fas fa-cog" style={{ marginRight: '8px' }}></i>
              Settings
            </label>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'rgba(255, 255, 255, 0.1)',
              padding: '8px 12px',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.2)'
            }}>
              <input
                type="checkbox"
                id="autoReconnect"
                checked={autoReconnect}
                onChange={(e) => setAutoReconnect(e.target.checked)}
                style={{ marginRight: '4px' }}
              />
              <label htmlFor="autoReconnect" style={{ fontSize: '0.9rem', cursor: 'pointer' }}>
                Auto-reconnect
              </label>
            </div>
          </div>
        </div>

        <div style={{
          display: 'flex',
          gap: '15px',
          flexWrap: 'wrap',
          alignItems: 'center'
        }}>
          {!connected ? (
            <button
              onClick={connectWS}
              style={buttonStyle('success')}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 4px 15px rgba(76, 175, 80, 0.4)'
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              <i className="fas fa-plug"></i>
              Connect WebSocket
            </button>
          ) : (
            <button
              onClick={disconnectWS}
              style={buttonStyle('danger')}
              onMouseOver={(e) => {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 4px 15px rgba(255, 107, 107, 0.4)'
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = 'none'
              }}
            >
              <i className="fas fa-unlink"></i>
              Disconnect
            </button>
          )}

          <button
            onClick={publishDummyState}
            disabled={loading}
            style={{
              ...buttonStyle('primary'),
              opacity: loading ? 0.6 : 1,
              cursor: loading ? 'not-allowed' : 'pointer'
            }}
            onMouseOver={(e) => {
              if (!loading) {
                e.currentTarget.style.transform = 'translateY(-2px)'
                e.currentTarget.style.boxShadow = '0 4px 15px rgba(78, 205, 196, 0.4)'
              }
            }}
            onMouseOut={(e) => {
              if (!loading) {
                e.currentTarget.style.transform = 'translateY(0)'
                e.currentTarget.style.boxShadow = 'none'
              }
            }}
          >
            {loading ? (
              <>
                <i className="fas fa-spinner fa-spin"></i>
                Publishing...
              </>
            ) : (
              <>
                <i className="fas fa-paper-plane"></i>
                Publish Dummy State
              </>
            )}
          </button>

          <button
            onClick={clearMessages}
            style={buttonStyle('secondary')}
            onMouseOver={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)'
              e.currentTarget.style.boxShadow = '0 4px 15px rgba(255, 255, 255, 0.2)'
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.transform = 'translateY(0)'
              e.currentTarget.style.boxShadow = 'none'
            }}
          >
            <i className="fas fa-trash"></i>
            Clear Messages
          </button>
        </div>
      </div>

      <div>
        <h3 style={{
          fontSize: '1.5rem',
          marginBottom: '20px',
          fontWeight: '600',
          display: 'flex',
          alignItems: 'center',
          gap: '10px'
        }}>
          <i className="fas fa-comments"></i>
          Incoming Hints
          <span style={{
            background: 'rgba(78, 205, 196, 0.3)',
            color: '#4ecdc4',
            padding: '4px 12px',
            borderRadius: '12px',
            fontSize: '0.8rem',
            fontWeight: '500'
          }}>
            {messages.length} messages
          </span>
        </h3>
        
        <div style={messagesStyle}>
          {messages.length === 0 ? (
            <div style={{
              textAlign: 'center',
              padding: '40px',
              opacity: '0.6'
            }}>
              <i className="fas fa-inbox" style={{ fontSize: '2rem', marginBottom: '15px' }}></i>
              <p style={{ fontSize: '1.1rem' }}>
                No messages received yet. Connect and publish a state to see hints appear here.
              </p>
            </div>
          ) : (
            messages.map((message, index) => (
              <div key={message.id} style={messageStyle}>
                <div style={{
                  fontSize: '0.8rem',
                  opacity: '0.7',
                  marginBottom: '8px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <i className="fas fa-clock"></i>
                  {new Date(message.timestamp).toLocaleTimeString()}
                  <span style={{
                    background: 'rgba(78, 205, 196, 0.3)',
                    padding: '2px 8px',
                    borderRadius: '8px',
                    fontSize: '0.7rem'
                  }}>
                    #{index + 1}
                  </span>
                  <span style={{
                    background: message.parsed ? 'rgba(76, 175, 80, 0.3)' : 'rgba(255, 152, 0, 0.3)',
                    color: message.parsed ? '#4caf50' : '#ff9800',
                    padding: '2px 8px',
                    borderRadius: '8px',
                    fontSize: '0.7rem'
                  }}>
                    {message.topic}
                  </span>
                </div>
                <div style={{
                  whiteSpace: 'pre-wrap',
                  margin: 0,
                  wordBreak: 'break-word'
                }}>
                  {message.parsed && message.hint ? (
                    <div>
                      <div style={{ 
                        marginBottom: '10px', 
                        padding: '10px', 
                        background: 'rgba(78, 205, 196, 0.1)',
                        borderRadius: '8px',
                        border: '1px solid rgba(78, 205, 196, 0.3)'
                      }}>
                        <h4 style={{ margin: '0 0 8px 0', color: '#4ecdc4' }}>Parsed Hint:</h4>
                        <pre style={{ margin: 0, fontSize: '0.9rem' }}>
                          {JSON.stringify(message.hint, null, 2)}
                        </pre>
                      </div>
                      <details style={{ marginTop: '8px' }}>
                        <summary style={{ cursor: 'pointer', opacity: '0.7' }}>Raw Message</summary>
                        <pre style={{ 
                          marginTop: '8px', 
                          padding: '8px', 
                          background: 'rgba(255, 255, 255, 0.05)',
                          borderRadius: '4px',
                          fontSize: '0.8rem'
                        }}>
                          {message.raw}
                        </pre>
                      </details>
                    </div>
                  ) : (
                    <pre style={{ margin: 0 }}>
                      {message.raw}
                    </pre>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  )
}

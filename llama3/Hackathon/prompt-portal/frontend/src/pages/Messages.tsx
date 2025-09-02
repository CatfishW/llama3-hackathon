import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api } from '../api'

type Message = {
  id: number
  sender_id: number
  receiver_id: number
  content: string
  created_at: string
  sender: {
    id: number
    email: string
    display_name?: string
    profile_picture?: string
  }
}

type Conversation = {
  user_id: number
  user_email: string
  user_display_name?: string
  user_profile_picture?: string
  last_message?: string
  last_message_at?: string
  unread_count: number
}

export default function Messages() {
  const { userId } = useParams<{ userId: string }>()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [messages, setMessages] = useState<Message[]>([])
  const [newMessage, setNewMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [isMobile, setIsMobile] = useState(false)
  const [showSidebar, setShowSidebar] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    loadConversations()
    return () => {
      wsRef.current?.close()
    }
  }, [])

  useEffect(() => {
    if (userId) {
      loadMessages(parseInt(userId))
      connectWebSocket(parseInt(userId))
    }
  }, [userId])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    const upd = () => {
      const m = window.innerWidth < 860
      setIsMobile(m)
      if (m) setShowSidebar(false)
      else setShowSidebar(true)
    }
    upd()
    window.addEventListener('resize', upd)
    window.addEventListener('orientationchange', upd)
    return () => {
      window.removeEventListener('resize', upd)
      window.removeEventListener('orientationchange', upd)
    }
  }, [])

  async function loadConversations() {
    try {
      const res = await api.get('/api/messages/conversations')
      setConversations(res.data)
    } catch (e) {
      console.error('Failed to load conversations', e)
    } finally {
      setLoading(false)
    }
  }

  async function loadMessages(withUserId: number) {
    try {
      const res = await api.get(`/api/messages/conversation/${withUserId}`)
      setMessages(res.data)

      // Mark conversation as read
      await api.put(`/api/messages/mark-conversation-read/${withUserId}`)

      // Update conversation unread count
      setConversations((prev) =>
        prev.map((conv) =>
          conv.user_id === withUserId
            ? { ...conv, unread_count: 0 }
            : conv
        )
      )
    } catch (e) {
      console.error('Failed to load messages', e)
    }
  }

  function connectWebSocket(withUserId: number) {
    wsRef.current?.close()

    const base = (import.meta as any).env?.VITE_WS_BASE || 'ws://localhost:8000'
    const ws = new WebSocket(`${base}/api/messages/ws/${withUserId}`)

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data)
      setMessages((prev) => [...prev, message])

      // Update conversation list
      setConversations((prev) => {
        const updated = prev.map((conv) =>
          conv.user_id === message.sender_id
            ? {
                ...conv,
                last_message: message.content,
                last_message_at: message.created_at,
                unread_count:
                  conv.user_id === parseInt(userId || '0')
                    ? 0
                    : conv.unread_count + 1,
              }
            : conv
        )

        // Move conversation to top
        const activeConv = updated.find((c) => c.user_id === message.sender_id)
        if (activeConv) {
          return [activeConv, ...updated.filter((c) => c.user_id !== message.sender_id)]
        }
        return updated
      })
    }

    wsRef.current = ws
  }

  async function sendMessage() {
    if (!newMessage.trim() || !userId) return

    try {
      setSending(true)
      await api.post('/api/messages/send', {
        recipient_id: parseInt(userId),
        content: newMessage.trim(),
      })
      setNewMessage('')
    } catch (e) {
      console.error('Failed to send message', e)
    } finally {
      setSending(false)
    }
  }

  function scrollToBottom() {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const containerStyle: React.CSSProperties = {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: isMobile? '12px 10px':'20px',
    height: isMobile? 'calc(100vh - 120px)': 'calc(100vh - 140px)',
    display: 'flex',
    gap: isMobile? '12px':'20px',
    position: 'relative'
  }

  const sidebarStyle: React.CSSProperties = {
    width: isMobile? '100%':'350px',
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '15px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    position: isMobile? 'absolute':'relative',
    left: 0,
    top: 0,
    bottom: 0,
    zIndex: 40,
    boxShadow: isMobile? '0 6px 24px -4px rgba(0,0,0,0.5)':'none',
    transform: isMobile? (showSidebar? 'translateY(0)':'translateY(-110%)'):'none',
    transition: 'transform .35s ease'
  }

  const chatStyle = {
    flex: 1,
    background: 'rgba(255, 255, 255, 0.1)',
    backdropFilter: 'blur(10px)',
    borderRadius: '15px',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    display: 'flex',
    flexDirection: 'column' as const,
    overflow: 'hidden',
  }

  const messageStyle = (isOwn: boolean) => ({
    maxWidth: '70%',
    marginBottom: '15px',
    alignSelf: isOwn ? 'flex-end' : 'flex-start',
    background: isOwn
      ? 'linear-gradient(45deg, #4ecdc4, #44a08d)'
      : 'rgba(255, 255, 255, 0.1)',
    color: 'white',
    padding: '12px 16px',
    borderRadius: isOwn ? '18px 18px 5px 18px' : '18px 18px 18px 5px',
    wordBreak: 'break-word' as const,
  })

  const currentConversation = conversations.find((c) => c.user_id === parseInt(userId || '0'))

  return (
    <div style={containerStyle}>
      {isMobile && (
        <button onClick={()=>setShowSidebar(s=>!s)} style={{ position:'absolute', top:6, right:6, zIndex:45, background:'rgba(0,0,0,0.55)', color:'#fff', border:'1px solid rgba(255,255,255,0.3)', padding:'6px 10px', borderRadius:8, fontSize:12 }}>
          {showSidebar? 'Hide Chats':'Chats'}
        </button>
      )}
      {/* Conversations Sidebar */}
      <div style={sidebarStyle}>
        <div
          style={{
            padding: '20px',
            borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          <h3 style={{ fontSize: '1.3rem', marginBottom: '10px' }}>
            <i className="fas fa-comments" style={{ marginRight: '10px' }}></i>
            Messages
          </h3>
          <Link
            to="/friends"
            style={{
              color: '#4ecdc4',
              textDecoration: 'none',
              fontSize: '0.9rem',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
            }}
          >
            <i className="fas fa-user-plus"></i>
            Find Friends
          </Link>
        </div>

        <div style={{ flex: 1, overflow: 'auto' }}>
          {loading ? (
            <div style={{ padding: '40px', textAlign: 'center' }}>
              <i
                className="fas fa-spinner fa-spin"
                style={{ fontSize: '1.5rem', marginBottom: '10px' }}
              ></i>
              <p style={{ fontSize: '0.9rem', opacity: '0.8' }}>
                Loading conversations...
              </p>
            </div>
          ) : conversations.length === 0 ? (
            <div style={{ padding: '40px', textAlign: 'center' }}>
              <i
                className="fas fa-comment-slash"
                style={{
                  fontSize: '2rem',
                  marginBottom: '15px',
                  opacity: '0.5',
                }}
              ></i>
              <h4 style={{ marginBottom: '10px', fontSize: '1.1rem' }}>
                No conversations
              </h4>
              <p style={{ fontSize: '0.9rem', opacity: '0.7' }}>
                Start a conversation with your friends!
              </p>
            </div>
          ) : (
            conversations.map((conv) => (
              <Link
                key={conv.user_id}
                to={`/messages/${conv.user_id}`}
                style={{
                  display: 'block',
                  padding: '15px 20px',
                  textDecoration: 'none',
                  color: 'inherit',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
                  background:
                    conv.user_id === parseInt(userId || '0')
                      ? 'rgba(78, 205, 196, 0.2)'
                      : 'transparent',
                  transition: 'background 0.3s ease',
                }}
                onMouseOver={(e) => {
                  if (conv.user_id !== parseInt(userId || '0')) {
                    e.currentTarget.style.background = 'rgba(255, 255, 255, 0.05)'
                  }
                }}
                onMouseOut={(e) => {
                  if (conv.user_id !== parseInt(userId || '0')) {
                    e.currentTarget.style.background = 'transparent'
                  }
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div
                    style={{
                      width: '45px',
                      height: '45px',
                      borderRadius: '50%',
                      background: conv.user_profile_picture
                        ? `url(${conv.user_profile_picture})`
                        : 'linear-gradient(45deg, #4ecdc4, #44a08d)',
                      backgroundSize: 'cover',
                      backgroundPosition: 'center',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      color: 'white',
                      fontSize: '1rem',
                      position: 'relative',
                    }}
                  >
                    {!conv.user_profile_picture && <i className="fas fa-user"></i>}
                    {conv.unread_count > 0 && (
                      <div
                        style={{
                          position: 'absolute',
                          top: '-2px',
                          right: '-2px',
                          background: '#ff6b6b',
                          color: 'white',
                          borderRadius: '50%',
                          minWidth: '18px',
                          height: '18px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          fontSize: '0.7rem',
                          fontWeight: '600',
                        }}
                      >
                        {conv.unread_count > 9 ? '9+' : conv.unread_count}
                      </div>
                    )}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <h4
                      style={{
                        fontSize: '1rem',
                        marginBottom: '4px',
                        fontWeight: conv.unread_count > 0 ? '600' : '500',
                      }}
                    >
                      {conv.user_display_name || conv.user_email}
                    </h4>

                    {conv.last_message && (
                      <p
                        style={{
                          fontSize: '0.85rem',
                          opacity: '0.7',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          whiteSpace: 'nowrap',
                          fontWeight: conv.unread_count > 0 ? '500' : 'normal',
                        }}
                      >
                        {conv.last_message}
                      </p>
                    )}

                    {conv.last_message_at && (
                      <p
                        style={{
                          fontSize: '0.75rem',
                          opacity: '0.5',
                          marginTop: '2px',
                        }}
                      >
                        {new Date(conv.last_message_at).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>

  {/* Chat Area */}
      <div style={chatStyle}>
        {userId ? (
          <>
            {/* Chat Header */}
            {currentConversation && (
              <div
                style={{
                  padding: '20px',
                  borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '15px',
                }}
              >
                <div
                  style={{
                    width: '45px',
                    height: '45px',
                    borderRadius: '50%',
                    background: currentConversation.user_profile_picture
                      ? `url(${currentConversation.user_profile_picture})`
                      : 'linear-gradient(45deg, #4ecdc4, #44a08d)',
                    backgroundSize: 'cover',
                    backgroundPosition: 'center',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white',
                    fontSize: '1.2rem',
                  }}
                >
                  {!currentConversation.user_profile_picture && <i className="fas fa-user"></i>}
                </div>

                <div>
                  <h3 style={{ fontSize: '1.3rem', marginBottom: '2px' }}>
                    {currentConversation.user_display_name || currentConversation.user_email}
                  </h3>
                  <p style={{ fontSize: '0.9rem', opacity: '0.7' }}>
                    {currentConversation.user_email}
                  </p>
                </div>
              </div>
            )}

            {/* Messages */}
            <div
              style={{
                flex: 1,
                padding: '20px',
                overflow: 'auto',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              {messages.length === 0 ? (
                <div
                  style={{
                    flex: 1,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    textAlign: 'center',
                    opacity: '0.6',
                  }}
                >
                  <div>
                    <i
                      className="fas fa-comment"
                      style={{ fontSize: '3rem', marginBottom: '15px' }}
                    ></i>
                    <h4 style={{ marginBottom: '10px' }}>Start a conversation</h4>
                    <p>Send your first message below!</p>
                  </div>
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    style={{
                      display: 'flex',
                      flexDirection: 'column',
                      alignItems:
                        message.sender_id === parseInt(userId)
                          ? 'flex-end'
                          : 'flex-start',
                      marginBottom: '15px',
                    }}
                  >
                    <div style={messageStyle(message.sender_id !== parseInt(userId))}>
                      <p style={{ margin: 0, lineHeight: '1.4' }}>{message.content}</p>
                      <div
                        style={{
                          fontSize: '0.75rem',
                          opacity: '0.7',
                          marginTop: '5px',
                          textAlign:
                            message.sender_id !== parseInt(userId) ? 'right' : 'left',
                        }}
                      >
                        {new Date(message.created_at).toLocaleTimeString()}
                      </div>
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            <div
              style={{
                padding: '20px',
                borderTop: '1px solid rgba(255, 255, 255, 0.1)',
              }}
            >
              <div style={{ display: 'flex', gap: '15px' }}>
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
                  placeholder="Type a message..."
                  style={{
                    flex: 1,
                    padding: '12px 16px',
                    borderRadius: '25px',
                    border: '1px solid rgba(255, 255, 255, 0.3)',
                    background: 'rgba(255, 255, 255, 0.1)',
                    color: 'white',
                    fontSize: '1rem',
                  }}
                />
                <button
                  onClick={sendMessage}
                  disabled={sending || !newMessage.trim()}
                  style={{
                    background: 'linear-gradient(45deg, #4ecdc4, #44a08d)',
                    color: 'white',
                    border: 'none',
                    padding: '12px 20px',
                    borderRadius: '25px',
                    cursor: sending || !newMessage.trim() ? 'not-allowed' : 'pointer',
                    opacity: sending || !newMessage.trim() ? 0.6 : 1,
                    transition: 'all 0.3s ease',
                  }}
                >
                  {sending ? (
                    <i className="fas fa-spinner fa-spin"></i>
                  ) : (
                    <i className="fas fa-paper-plane"></i>
                  )}
                </button>
              </div>
            </div>
          </>
        ) : (
          <div
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              opacity: '0.6',
            }}
          >
            <div>
              <i
                className="fas fa-comments"
                style={{ fontSize: '4rem', marginBottom: '20px' }}
              ></i>
              <h3 style={{ marginBottom: '10px', fontSize: '1.5rem' }}>
                Select a conversation
              </h3>
              <p style={{ fontSize: '1.1rem' }}>
                Choose a friend from the sidebar to start messaging
              </p>
            </div>
          </div>
        )}
      </div>

    </div>
  )
}

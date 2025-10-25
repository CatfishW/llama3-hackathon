import { useEffect, useState } from 'react'

interface Announcement {
  id: number
  title: string
  content: string
  announcement_type: 'info' | 'warning' | 'success' | 'error'
  priority: number
  created_at: string
}

interface AnnouncementPopupProps {
  announcements: Announcement[]
  onDismiss: (id: number) => void
}

export default function AnnouncementPopup({ announcements, onDismiss }: AnnouncementPopupProps) {
  const [visibleAnnouncements, setVisibleAnnouncements] = useState<number[]>([])
  const [dismissing, setDismissing] = useState<number[]>([])

  useEffect(() => {
    // Show new announcements
    const newAnnouncements = announcements.filter(
      a => !visibleAnnouncements.includes(a.id) && !dismissing.includes(a.id)
    )

    if (newAnnouncements.length > 0) {
      setVisibleAnnouncements(prev => [...prev, ...newAnnouncements.map(a => a.id)])

      // Auto-dismiss after 15 seconds
      newAnnouncements.forEach(announcement => {
        setTimeout(() => {
          handleDismiss(announcement.id)
        }, 15000)
      })
    }
  }, [announcements])

  const handleDismiss = (id: number) => {
    setDismissing(prev => [...prev, id])
    setTimeout(() => {
      setVisibleAnnouncements(prev => prev.filter(announcementId => announcementId !== id))
      setDismissing(prev => prev.filter(announcementId => announcementId !== id))
      onDismiss(id)
    }, 300) // Animation duration
  }

  const getTypeStyles = (type: string) => {
    switch (type) {
      case 'success':
        return {
          background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
          icon: '✓',
          iconBg: 'rgba(255, 255, 255, 0.2)'
        }
      case 'warning':
        return {
          background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
          icon: '⚠',
          iconBg: 'rgba(255, 255, 255, 0.2)'
        }
      case 'error':
        return {
          background: 'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',
          icon: '✕',
          iconBg: 'rgba(255, 255, 255, 0.2)'
        }
      default: // info
        return {
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          icon: 'ℹ',
          iconBg: 'rgba(255, 255, 255, 0.2)'
        }
    }
  }

  const visibleAnnouncementsList = announcements.filter(a => 
    visibleAnnouncements.includes(a.id)
  )

  if (visibleAnnouncementsList.length === 0) return null

  return (
    <div style={{
      position: 'fixed',
      top: '80px',
      right: '20px',
      zIndex: 9999,
      display: 'flex',
      flexDirection: 'column',
      gap: '12px',
      maxWidth: '420px',
      pointerEvents: 'none'
    }}>
      {visibleAnnouncementsList.map(announcement => {
        const typeStyles = getTypeStyles(announcement.announcement_type)
        const isDismissing = dismissing.includes(announcement.id)

        return (
          <div
            key={announcement.id}
            style={{
              background: typeStyles.background,
              borderRadius: '16px',
              padding: '20px 24px',
              boxShadow: '0 10px 40px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(255, 255, 255, 0.1)',
              color: 'white',
              position: 'relative',
              overflow: 'hidden',
              transform: isDismissing ? 'translateX(450px)' : 'translateX(0)',
              opacity: isDismissing ? 0 : 1,
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              animation: isDismissing ? 'none' : 'slideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
              pointerEvents: 'auto',
              backdropFilter: 'blur(10px)',
              minWidth: '320px'
            }}
          >
            {/* Animated background gradient */}
            <div style={{
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              background: 'linear-gradient(45deg, transparent 30%, rgba(255, 255, 255, 0.1) 50%, transparent 70%)',
              backgroundSize: '200% 200%',
              animation: 'shimmer 3s ease-in-out infinite',
              pointerEvents: 'none'
            }} />

            {/* Close button */}
            <button
              onClick={() => handleDismiss(announcement.id)}
              style={{
                position: 'absolute',
                top: '12px',
                right: '12px',
                background: 'rgba(255, 255, 255, 0.2)',
                border: 'none',
                borderRadius: '8px',
                width: '28px',
                height: '28px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer',
                color: 'white',
                fontSize: '16px',
                transition: 'all 0.2s',
                backdropFilter: 'blur(5px)',
                zIndex: 1
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.3)'
                e.currentTarget.style.transform = 'scale(1.1)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'rgba(255, 255, 255, 0.2)'
                e.currentTarget.style.transform = 'scale(1)'
              }}
            >
              ✕
            </button>

            {/* Content */}
            <div style={{ position: 'relative', zIndex: 1 }}>
              <div style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '14px',
                marginBottom: '10px'
              }}>
                <div style={{
                  background: typeStyles.iconBg,
                  borderRadius: '10px',
                  width: '36px',
                  height: '36px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '18px',
                  flexShrink: 0,
                  fontWeight: 'bold'
                }}>
                  {typeStyles.icon}
                </div>
                <div style={{ flex: 1, paddingRight: '20px' }}>
                  <h3 style={{
                    margin: '0 0 8px 0',
                    fontSize: '18px',
                    fontWeight: '700',
                    lineHeight: '1.3',
                    textShadow: '0 1px 2px rgba(0, 0, 0, 0.1)'
                  }}>
                    {announcement.title}
                  </h3>
                  <p style={{
                    margin: 0,
                    fontSize: '14px',
                    lineHeight: '1.5',
                    opacity: 0.95,
                    whiteSpace: 'pre-wrap'
                  }}>
                    {announcement.content}
                  </p>
                </div>
              </div>

              {/* Auto-close progress bar */}
              <div style={{
                marginTop: '14px',
                height: '3px',
                background: 'rgba(255, 255, 255, 0.2)',
                borderRadius: '2px',
                overflow: 'hidden'
              }}>
                <div style={{
                  height: '100%',
                  background: 'rgba(255, 255, 255, 0.5)',
                  borderRadius: '2px',
                  animation: 'progress 15s linear',
                  transformOrigin: 'left'
                }} />
              </div>
            </div>
          </div>
        )
      })}

      <style>{`
        @keyframes slideIn {
          from {
            transform: translateX(450px);
            opacity: 0;
          }
          to {
            transform: translateX(0);
            opacity: 1;
          }
        }

        @keyframes progress {
          from {
            transform: scaleX(1);
          }
          to {
            transform: scaleX(0);
          }
        }

        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }
      `}</style>
    </div>
  )
}

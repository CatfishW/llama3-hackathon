import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Terminal, X, Trash2, List } from 'lucide-react'
import { useRawLogs } from '../contexts/RawLogContext'

import { useParticles } from '../hooks/useParticles'

export const RawLogPanel: React.FC = () => {
    const { logs, clearLogs, unreadCount, resetUnread } = useRawLogs()
    const [isExpanded, setIsExpanded] = useState(false)
    const scrollRef = useRef<HTMLDivElement>(null)
    const { canvasRef, spawnParticles } = useParticles()
    const constraintsRef = useRef(null)

    // Auto-scroll to bottom of logs
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight
        }
    }, [logs, isExpanded])

    const togglePanel = () => {
        if (!isExpanded) {
            resetUnread()
        }
        setIsExpanded(!isExpanded)
    }

    const handleToggle = (e: React.MouseEvent) => {
        const rect = (e.target as HTMLElement).getBoundingClientRect()
        spawnParticles(rect.left + rect.width / 2, rect.top + rect.height / 2)
        togglePanel()
    }

    return (
        <>
            <canvas
                ref={canvasRef}
                style={{ position: 'fixed', top: 0, left: 0, width: '100%', height: '100%', pointerEvents: 'none', zIndex: 9999 }}
            />
            <div ref={constraintsRef} style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', pointerEvents: 'none', zIndex: 1000 }}>
                <AnimatePresence mode="wait">
                    {!isExpanded ? (
                        <motion.button
                            key="bubble"
                            layoutId="raw-log-root"
                            drag
                            dragConstraints={constraintsRef}
                            dragElastic={0.1}
                            dragMomentum={false}
                            // Initial position handled by style (bottom right), dragging overrides transform
                            initial={{ scale: 0, rotate: -45, opacity: 0 }}
                            animate={{ scale: 1, rotate: 0, opacity: 1 }}
                            exit={{ scale: 0, rotate: 45, opacity: 0 }}
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                            onClick={handleToggle}
                            style={{
                                pointerEvents: 'auto',
                                position: 'absolute',
                                bottom: '24px',
                                right: '24px',
                                width: '64px',
                                height: '64px',
                                borderRadius: '50%',
                                background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
                                border: 'none',
                                boxShadow: '0 8px 32px rgba(99, 102, 241, 0.4), inset 0 2px 4px rgba(255, 255, 255, 0.3)',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: 'white',
                                cursor: 'grab',
                                touchAction: 'none'
                            }}
                        >
                            <Terminal size={28} />

                            {/* Unread Badge */}
                            <AnimatePresence>
                                {unreadCount > 0 && (
                                    <motion.div
                                        initial={{ scale: 0 }}
                                        animate={{ scale: 1 }}
                                        exit={{ scale: 0 }}
                                        style={{
                                            position: 'absolute',
                                            top: '-4px',
                                            right: '-4px',
                                            background: '#ef4444',
                                            color: 'white',
                                            fontSize: '12px',
                                            fontWeight: 'bold',
                                            minWidth: '22px',
                                            height: '22px',
                                            borderRadius: '11px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            justifyContent: 'center',
                                            padding: '0 6px',
                                            border: '2px solid #0f172a',
                                            boxShadow: '0 4px 12px rgba(239, 68, 68, 0.5)'
                                        }}
                                    >
                                        {unreadCount > 99 ? '99+' : unreadCount}
                                    </motion.div>
                                )}
                            </AnimatePresence>

                            {/* Pulsing effect when new messages arrive */}
                            {unreadCount > 0 && (
                                <motion.div
                                    animate={{
                                        scale: [1, 1.2, 1],
                                        opacity: [0.3, 0, 0.3]
                                    }}
                                    transition={{
                                        duration: 2,
                                        repeat: Infinity,
                                        ease: "easeInOut"
                                    }}
                                    style={{
                                        position: 'absolute',
                                        top: 0,
                                        left: 0,
                                        right: 0,
                                        bottom: 0,
                                        borderRadius: '50%',
                                        background: 'white',
                                        zIndex: -1
                                    }}
                                />
                            )}
                        </motion.button>
                    ) : (
                        <motion.div
                            key="panel"
                            layoutId="raw-log-root"
                            drag
                            dragConstraints={constraintsRef}
                            dragElastic={0.1}
                            dragMomentum={false}
                            dragListener={false} // Only drag on handle
                            dragControls={undefined} // We'll use a handle
                            initial={{ opacity: 0, scale: 0.9, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.9, y: 20 }}
                            transition={{ type: 'spring', damping: 30, stiffness: 500, mass: 0.8 }}
                            style={{
                                pointerEvents: 'auto',
                                position: 'absolute',
                                bottom: '24px',
                                right: '24px',
                                width: '400px',
                                height: '500px',
                                maxWidth: 'calc(100vw - 48px)',
                                maxHeight: 'calc(100vh - 100px)',
                                background: 'rgba(15, 23, 42, 0.95)',
                                backdropFilter: 'blur(20px)',
                                borderRadius: '24px',
                                border: '1px solid rgba(255, 255, 255, 0.1)',
                                boxShadow: '0 24px 48px rgba(0, 0, 0, 0.4)',
                                display: 'flex',
                                flexDirection: 'column',
                                overflow: 'hidden',
                                color: '#e2e8f0'
                            }}
                        >
                            {/* Header - Drag Handle */}
                            <motion.div
                                className="drag-handle"
                                whileHover={{ cursor: 'grab' }}
                                whileTap={{ cursor: 'grabbing' }}
                                style={{
                                    padding: '16px 20px',
                                    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'space-between',
                                    background: 'rgba(255, 255, 255, 0.03)',
                                    touchAction: 'none' // Important for drag
                                }}>
                                <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                                    <div style={{
                                        width: '32px',
                                        height: '32px',
                                        borderRadius: '8px',
                                        background: 'linear-gradient(135deg, #6366f1 0%, #a855f7 100%)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center'
                                    }}>
                                        <Terminal size={18} color="white" />
                                    </div>
                                    <span style={{ fontWeight: 600, fontSize: '0.95rem', letterSpacing: '0.01em' }}>LLM Raw Output</span>
                                </div>
                                <div style={{ display: 'flex', gap: '8px' }}>
                                    <button
                                        onClick={clearLogs}
                                        style={{
                                            background: 'transparent',
                                            border: 'none',
                                            color: 'rgba(148, 163, 184, 0.6)',
                                            cursor: 'pointer',
                                            padding: '6px',
                                            borderRadius: '6px',
                                            display: 'flex',
                                            alignItems: 'center',
                                            transition: 'all 0.2s'
                                        }}
                                        title="Clear Logs"
                                    >
                                        <Trash2 size={16} />
                                    </button>
                                    <button
                                        onClick={togglePanel}
                                        style={{
                                            background: 'rgba(255, 255, 255, 0.05)',
                                            border: 'none',
                                            color: 'white',
                                            cursor: 'pointer',
                                            padding: '6px',
                                            borderRadius: '6px',
                                            display: 'flex',
                                            alignItems: 'center'
                                        }}
                                    >
                                        <X size={18} />
                                    </button>
                                </div>
                            </motion.div>

                            {/* Logs Area */}
                            <div
                                ref={scrollRef}
                                onPointerDown={e => e.stopPropagation()} // Prevent dragging when interacting with logs
                                style={{
                                    flex: 1,
                                    overflowY: 'auto',
                                    padding: '16px',
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: '8px',
                                    fontFamily: '"Fira Code", "JetBrains Mono", monospace',
                                    fontSize: '0.75rem',
                                    lineHeight: '1.5',
                                    cursor: 'text'
                                }}
                            >
                                {logs.length === 0 ? (
                                    <div style={{
                                        flex: 1,
                                        display: 'flex',
                                        flexDirection: 'column',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        opacity: 0.3,
                                        gap: '12px'
                                    }}>
                                        <List size={40} />
                                        <span>No logs to display</span>
                                    </div>
                                ) : (
                                    logs.map((log) => (
                                        <div key={log.id} style={{
                                            padding: '8px 12px',
                                            borderRadius: '8px',
                                            background: log.type === 'request' ? 'rgba(99, 102, 241, 0.1)' :
                                                log.type === 'error' ? 'rgba(239, 68, 68, 0.1)' :
                                                    log.type === 'metadata' ? 'rgba(168, 85, 247, 0.1)' :
                                                        log.type === 'chunk' ? 'rgba(6, 182, 212, 0.1)' :
                                                            log.type === 'full' ? 'rgba(71, 85, 105, 0.15)' :
                                                                'rgba(255, 255, 255, 0.03)',
                                            borderLeft: `3px solid ${log.type === 'request' ? '#6366f1' :
                                                log.type === 'error' ? '#ef4444' :
                                                    log.type === 'metadata' ? '#a855f7' :
                                                        log.type === 'chunk' ? '#06b6d4' :
                                                            log.type === 'full' ? '#475569' :
                                                                log.type === 'done' ? '#10b981' :
                                                                    'rgba(255, 255, 255, 0.1)'
                                                }`,
                                            wordBreak: 'break-all'
                                        }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', opacity: 0.5, fontSize: '0.65rem' }}>
                                                <span style={{ fontWeight: 600, textTransform: 'uppercase' }}>{log.type}</span>
                                                <span>{new Date(log.timestamp).toLocaleTimeString()}</span>
                                            </div>
                                            <div style={{ color: log.type === 'error' ? '#fca5a5' : '#cbd5e1' }}>
                                                {log.content}
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>

                            {/* Footer / Status */}
                            <div style={{
                                padding: '10px 16px',
                                fontSize: '0.7rem',
                                color: 'rgba(148, 163, 184, 0.5)',
                                borderTop: '1px solid rgba(255, 255, 255, 0.05)',
                                display: 'flex',
                                justifyContent: 'space-between',
                                pointerEvents: 'none'
                            }}>
                                <span>{logs.length} entries</span>
                                <span>v1.0.0-raw-debugger</span>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </>
    )
}

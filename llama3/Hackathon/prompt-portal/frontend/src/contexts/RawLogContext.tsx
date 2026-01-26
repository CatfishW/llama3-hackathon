import React, { createContext, useContext, useState, useCallback, useRef, useEffect } from 'react'

export interface RawLogEntry {
    id: string
    timestamp: string
    type: 'request' | 'chunk' | 'metadata' | 'done' | 'error' | 'full'
    content: string
    sessionId?: number | string
}

interface RawLogContextType {
    logs: RawLogEntry[]
    addLog: (entry: Omit<RawLogEntry, 'id' | 'timestamp'>) => void
    clearLogs: () => void
    unreadCount: number
    resetUnread: () => void
}

const RawLogContext = createContext<RawLogContextType | undefined>(undefined)

export const RawLogProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [logs, setLogs] = useState<RawLogEntry[]>([])
    const [unreadCount, setUnreadCount] = useState(0)
    const [isPanelOpen, setIsPanelOpen] = useState(false)

    const addLog = useCallback((entry: Omit<RawLogEntry, 'id' | 'timestamp'>) => {
        const newEntry: RawLogEntry = {
            ...entry,
            id: Math.random().toString(36).substring(2, 11),
            timestamp: new Date().toISOString(),
        }
        setLogs(prev => [...prev, newEntry])
        setUnreadCount(prev => prev + 1)
    }, [])

    const clearLogs = useCallback(() => {
        setLogs([])
        setUnreadCount(0)
    }, [])

    const resetUnread = useCallback(() => {
        setUnreadCount(0)
    }, [])

    return (
        <RawLogContext.Provider value={{ logs, addLog, clearLogs, unreadCount, resetUnread }}>
            {children}
        </RawLogContext.Provider>
    )
}

export const useRawLogs = () => {
    const context = useContext(RawLogContext)
    if (!context) {
        throw new Error('useRawLogs must be used within a RawLogProvider')
    }
    return context
}

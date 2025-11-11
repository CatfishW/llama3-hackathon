/**
 * Completion Provider Component
 * 
 * This component initializes the SSE-based completion client when the app starts
 * and provides completion functionality to all child components.
 */

import React, { createContext, useContext, useEffect, useState } from 'react'
import { CompletionClient } from './CompletionClient'

interface CompletionContextType {
  client: CompletionClient | null
  isConnected: boolean
  error: string | null
}

const CompletionContext = createContext<CompletionContextType>({
  client: null,
  isConnected: false,
  error: null
})

export const useCompletionContext = () => useContext(CompletionContext)

interface CompletionProviderProps {
  children: React.ReactNode
  apiBase?: string
}

export const CompletionProvider: React.FC<CompletionProviderProps> = ({
  children,
  apiBase = ''
}) => {
  const [client, setClient] = useState<CompletionClient | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const initClient = async () => {
      try {
        console.log('Initializing completion client (SSE mode)...')
        const completionClient = new CompletionClient({ apiBase, timeout: 30000 })
        await completionClient.connect()
        
        setClient(completionClient)
        setIsConnected(completionClient.isConnected())
        setError(null)
        
        console.log('✅ Completion client initialized successfully')
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to initialize completion client'
        setError(errorMessage)
        console.error('❌ Failed to initialize completion client:', errorMessage)
      }
    }

    initClient()

    // Cleanup on unmount
    return () => {
      if (client) {
        client.disconnect()
      }
    }
  }, [apiBase])

  const contextValue: CompletionContextType = {
    client,
    isConnected,
    error
  }

  return (
    <CompletionContext.Provider value={contextValue}>
      {children}
    </CompletionContext.Provider>
  )
}

export default CompletionProvider

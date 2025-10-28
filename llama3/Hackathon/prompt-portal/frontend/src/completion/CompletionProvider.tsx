/**
 * Completion Provider Component
 * 
 * This component initializes the MQTT completion client when the app starts
 * and provides completion functionality to all child components.
 */

import React, { createContext, useContext, useEffect, useState } from 'react'
import { initializeCompletionClient, getCompletionClient, CompletionClient } from './CompletionClient'

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
  broker?: string
  port?: number
  username?: string
  password?: string
}

export const CompletionProvider: React.FC<CompletionProviderProps> = ({
  children,
  broker = '47.89.252.2',
  port = 1883,
  username = 'TangClinic',
  password = 'Tang123'
}) => {
  const [client, setClient] = useState<CompletionClient | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const initClient = async () => {
      try {
        console.log('Initializing completion client...')
        const completionClient = await initializeCompletionClient({
          broker,
          port,
          username,
          password
        })
        
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
  }, [broker, port, username, password])

  // Monitor connection status
  useEffect(() => {
    if (!client) return

    const checkConnection = () => {
      setIsConnected(client.isConnected())
    }

    const interval = setInterval(checkConnection, 5000) // Check every 5 seconds

    return () => clearInterval(interval)
  }, [client])

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

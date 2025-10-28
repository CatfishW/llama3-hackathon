/**
 * MQTT-based TAB Completion Client
 * 
 * This client provides intelligent TAB completion for all input fields
 * using the local LLM via MQTT. It integrates with llamacpp_mqtt_deploy.py
 * to provide real-time completion suggestions.
 */

import mqtt, { MqttClient } from 'mqtt'

// Handle browser compatibility
if (typeof window !== 'undefined') {
  // Browser environment - ensure MQTT is available
  if (!mqtt) {
    console.error('MQTT client not available. Please ensure mqtt package is installed.')
  }
}

export interface CompletionRequest {
  text: string
  completion_type?: 'general' | 'code' | 'prompt' | 'message' | 'search' | 'email' | 'description'
  temperature?: number
  top_p?: number
  max_tokens?: number
}

export interface CompletionResponse {
  request_id: string
  completion: string
  error?: string
  timestamp: number
}

export interface CompletionOptions {
  broker?: string
  port?: number
  username?: string
  password?: string
  timeout?: number
  maxRetries?: number
}

export class CompletionClient {
  private client: MqttClient | null = null
  private clientId: string
  private connected: boolean = false
  private pendingRequests: Map<string, {
    resolve: (value: CompletionResponse) => void
    reject: (error: Error) => void
    timeout: NodeJS.Timeout
  }> = new Map()
  private options: Required<CompletionOptions>

  constructor(options: CompletionOptions = {}) {
    this.clientId = `completion-client-${Math.random().toString(36).substr(2, 9)}`
    this.options = {
      broker: options.broker || '47.89.252.2',
      port: options.port || 1883,
      username: options.username || 'TangClinic',
      password: options.password || 'Tang123',
      timeout: options.timeout || 5000,
      maxRetries: options.maxRetries || 3
    }
  }

  async connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const connectUrl = `mqtt://${this.options.broker}:${this.options.port}`
        
        this.client = mqtt.connect(connectUrl, {
          clientId: this.clientId,
          username: this.options.username,
          password: this.options.password,
          keepalive: 60,
          reconnectPeriod: 1000,
          connectTimeout: 10000
        })

        this.client.on('connect', () => {
          console.log('✅ Connected to MQTT broker for completions')
          this.connected = true
          resolve()
        })

        this.client.on('error', (error) => {
          console.error('❌ MQTT connection error:', error)
          this.connected = false
          reject(error)
        })

        this.client.on('disconnect', () => {
          console.log('⚠️ Disconnected from MQTT broker')
          this.connected = false
        })

        this.client.on('message', (topic, message) => {
          this.handleMessage(topic, message)
        })

        // Subscribe to responses
        this.client.subscribe(`completion/response/${this.clientId}/+`, (err) => {
          if (err) {
            console.error('Failed to subscribe to completion responses:', err)
            reject(err)
          }
        })

      } catch (error) {
        reject(error)
      }
    })
  }

  private handleMessage(topic: string, message: Buffer): void {
    try {
      const response: CompletionResponse = JSON.parse(message.toString())
      
      // Extract request ID from topic: completion/response/{clientId}/{requestId}
      const topicParts = topic.split('/')
      const requestId = topicParts[3]
      
      const pendingRequest = this.pendingRequests.get(requestId)
      if (pendingRequest) {
        clearTimeout(pendingRequest.timeout)
        this.pendingRequests.delete(requestId)
        
        if (response.error) {
          pendingRequest.reject(new Error(response.error))
        } else {
          pendingRequest.resolve(response)
        }
      }
    } catch (error) {
      console.error('Error handling completion response:', error)
    }
  }

  async getCompletion(request: CompletionRequest): Promise<string> {
    if (!this.connected || !this.client) {
      throw new Error('Completion client not connected')
    }

    const requestId = Math.random().toString(36).substr(2, 9)
    const requestTopic = `completion/request/${this.clientId}/${requestId}`

    return new Promise((resolve, reject) => {
      // Set up timeout
      const timeout = setTimeout(() => {
        this.pendingRequests.delete(requestId)
        reject(new Error('Completion request timeout'))
      }, this.options.timeout)

      // Store pending request
      this.pendingRequests.set(requestId, {
        resolve: (response) => resolve(response.completion),
        reject,
        timeout
      })

      // Send request
      const requestPayload = {
        text: request.text,
        completion_type: request.completion_type || 'general',
        temperature: request.temperature,
        top_p: request.top_p,
        max_tokens: request.max_tokens
      }

      this.client!.publish(requestTopic, JSON.stringify(requestPayload), (err) => {
        if (err) {
          clearTimeout(timeout)
          this.pendingRequests.delete(requestId)
          reject(err)
        }
      })
    })
  }

  disconnect(): void {
    if (this.client) {
      this.client.end()
      this.client = null
      this.connected = false
    }
    
    // Clear all pending requests
    this.pendingRequests.forEach(({ reject, timeout }) => {
      clearTimeout(timeout)
      reject(new Error('Client disconnected'))
    })
    this.pendingRequests.clear()
  }

  isConnected(): boolean {
    return this.connected
  }
}

// Global completion client instance
let globalCompletionClient: CompletionClient | null = null

export async function initializeCompletionClient(options?: CompletionOptions): Promise<CompletionClient> {
  if (!globalCompletionClient) {
    globalCompletionClient = new CompletionClient(options)
    await globalCompletionClient.connect()
  }
  return globalCompletionClient
}

export function getCompletionClient(): CompletionClient | null {
  return globalCompletionClient
}

export function disconnectCompletionClient(): void {
  if (globalCompletionClient) {
    globalCompletionClient.disconnect()
    globalCompletionClient = null
  }
}

// React hook for completion
import { useState, useEffect, useCallback } from 'react'

export interface UseCompletionOptions {
  completionType?: CompletionRequest['completion_type']
  temperature?: number
  top_p?: number
  max_tokens?: number
  debounceMs?: number
}

export function useCompletion(options: UseCompletionOptions = {}) {
  const [client, setClient] = useState<CompletionClient | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    initializeCompletionClient()
      .then(setClient)
      .catch((err) => {
        console.error('Failed to initialize completion client:', err)
        setError(err.message)
      })

    return () => {
      disconnectCompletionClient()
    }
  }, [])

  const getCompletion = useCallback(async (text: string): Promise<string> => {
    if (!client || !text.trim()) {
      return ''
    }

    setLoading(true)
    setError(null)

    try {
      const completion = await client.getCompletion({
        text,
        completion_type: options.completionType,
        temperature: options.temperature,
        top_p: options.top_p,
        max_tokens: options.max_tokens
      })
      return completion
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Completion failed'
      setError(errorMessage)
      return ''
    } finally {
      setLoading(false)
    }
  }, [client, options])

  return {
    getCompletion,
    loading,
    error,
    isConnected: client?.isConnected() || false
  }
}

// React hook for TAB completion on input fields
export function useTabCompletion(
  inputRef: React.RefObject<HTMLInputElement | HTMLTextAreaElement>,
  options: UseCompletionOptions = {}
) {
  const { getCompletion, loading, error } = useCompletion(options)
  const [suggestion, setSuggestion] = useState<string>('')
  const [showSuggestion, setShowSuggestion] = useState(false)

  const handleKeyDown = useCallback(async (e: React.KeyboardEvent) => {
    if (e.key === 'Tab' && !e.shiftKey) {
      e.preventDefault()
      
      const input = inputRef.current
      if (!input) return

      const currentText = input.value
      const cursorPosition = input.selectionStart || 0
      const textBeforeCursor = currentText.substring(0, cursorPosition)

      if (textBeforeCursor.trim()) {
        try {
          const completion = await getCompletion(textBeforeCursor)
          if (completion) {
            const newText = textBeforeCursor + completion + currentText.substring(cursorPosition)
            input.value = newText
            
            // Set cursor position after the completion
            const newCursorPosition = cursorPosition + completion.length
            input.setSelectionRange(newCursorPosition, newCursorPosition)
            
            // Trigger change event
            input.dispatchEvent(new Event('input', { bubbles: true }))
          }
        } catch (err) {
          console.error('Tab completion failed:', err)
        }
      }
    }
  }, [getCompletion, inputRef])

  const handleInput = useCallback(async (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const text = e.target.value
    const cursorPosition = e.target.selectionStart || 0
    const textBeforeCursor = text.substring(0, cursorPosition)

    if (textBeforeCursor.trim() && textBeforeCursor.length > 3) {
      try {
        const completion = await getCompletion(textBeforeCursor)
        if (completion) {
          setSuggestion(completion)
          setShowSuggestion(true)
        } else {
          setShowSuggestion(false)
        }
      } catch (err) {
        setShowSuggestion(false)
      }
    } else {
      setShowSuggestion(false)
    }
  }, [getCompletion])

  const handleBlur = useCallback(() => {
    setShowSuggestion(false)
  }, [])

  return {
    handleKeyDown,
    handleInput,
    handleBlur,
    suggestion,
    showSuggestion,
    loading,
    error
  }
}

export default CompletionClient

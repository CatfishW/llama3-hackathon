/**
 * SSE-based TAB Completion Client
 * 
 * This client provides intelligent TAB completion for all input fields
 * using Server-Sent Events (SSE) for real-time streaming completions.
 */

export interface CompletionRequest {
  text: string
  completion_type?: 'general' | 'code' | 'prompt' | 'message' | 'search' | 'email' | 'description'
  temperature?: number
  top_p?: number
  max_tokens?: number
}

export interface CompletionResponse {
  completion: string
  error?: string
  timestamp: number
}

export interface CompletionOptions {
  apiBase?: string
  timeout?: number
}

export class CompletionClient {
  private connected: boolean = true // SSE is always "connected" after init
  private pendingRequests: Map<string, AbortController> = new Map()
  private options: Required<CompletionOptions>

  constructor(options: CompletionOptions = {}) {
    this.options = {
      apiBase: options.apiBase || '',
      timeout: options.timeout || 30000
    }
  }

  async connect(): Promise<void> {
    // SSE doesn't require explicit connection setup
    this.connected = true
    console.log('✅ Completion client initialized (SSE mode)')
  }

  async getCompletion(request: CompletionRequest): Promise<string> {
    if (!this.connected) {
      throw new Error('Completion client not initialized')
    }

    // TAB completion is currently disabled - endpoint not implemented
    throw new Error('TAB completion not available')
  }

  disconnect(): void {
    // Cancel all pending requests
    this.pendingRequests.forEach((controller) => {
      controller.abort()
    })
    this.pendingRequests.clear()
    this.connected = false
  }

  isConnected(): boolean {
    return this.connected
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
  client?: CompletionClient | null
}

export function useCompletion(options: UseCompletionOptions = {}) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const client = options.client

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

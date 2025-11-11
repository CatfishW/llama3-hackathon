/**
 * TAB Completion Input Component
 * 
 * A React component that provides intelligent TAB completion for input fields
 * using SSE for real-time completion suggestions.
 */

import React, { forwardRef, useImperativeHandle, useRef, useState, useEffect } from 'react'
import { useTabCompletion } from './CompletionClient'
import { useCompletionContext } from './CompletionProvider'

export interface TabCompletionInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  completionType?: 'general' | 'code' | 'prompt' | 'message' | 'search' | 'email' | 'description'
  temperature?: number
  top_p?: number
  max_tokens?: number
  showSuggestion?: boolean
  suggestionStyle?: React.CSSProperties
  onCompletion?: (completion: string) => void
}

export interface TabCompletionInputRef {
  focus: () => void
  blur: () => void
  select: () => void
  setSelectionRange: (start: number, end: number) => void
}

export const TabCompletionInput = forwardRef<TabCompletionInputRef, TabCompletionInputProps>(
  ({ 
    completionType = 'general',
    temperature,
    top_p,
    max_tokens,
    showSuggestion = true,
    suggestionStyle,
    onCompletion,
    style,
    className,
    ...props 
  }, ref) => {
    const inputRef = useRef<HTMLInputElement>(null)
    const [isFocused, setIsFocused] = useState(false)
    const { client } = useCompletionContext()
    
    const {
      handleKeyDown,
      handleInput,
      handleBlur,
      suggestion,
      showSuggestion: showSuggestionState,
      loading,
      error
    } = useTabCompletion(inputRef, {
      completionType,
      temperature,
      top_p,
      max_tokens,
      client: client || undefined
    })

    useImperativeHandle(ref, () => ({
      focus: () => inputRef.current?.focus(),
      blur: () => inputRef.current?.blur(),
      select: () => inputRef.current?.select(),
      setSelectionRange: (start: number, end: number) => inputRef.current?.setSelectionRange(start, end)
    }))

    const handleKeyDownWithCompletion = (e: React.KeyboardEvent<HTMLInputElement>) => {
      handleKeyDown(e)
      props.onKeyDown?.(e)
    }

    const handleInputWithCompletion = (e: React.ChangeEvent<HTMLInputElement>) => {
      handleInput(e)
      props.onChange?.(e)
    }

    const handleBlurWithCompletion = (e: React.FocusEvent<HTMLInputElement>) => {
      handleBlur()
      setIsFocused(false)
      props.onBlur?.(e)
    }

    const handleFocus = (e: React.FocusEvent<HTMLInputElement>) => {
      setIsFocused(true)
      props.onFocus?.(e)
    }

    const handleSuggestionClick = () => {
      if (inputRef.current && suggestion) {
        const currentText = inputRef.current.value
        const cursorPosition = inputRef.current.selectionStart || 0
        const textBeforeCursor = currentText.substring(0, cursorPosition)
        const newText = textBeforeCursor + suggestion + currentText.substring(cursorPosition)
        
        inputRef.current.value = newText
        inputRef.current.setSelectionRange(
          cursorPosition + suggestion.length,
          cursorPosition + suggestion.length
        )
        
        // Trigger change event
        inputRef.current.dispatchEvent(new Event('input', { bubbles: true }))
        
        onCompletion?.(suggestion)
      }
    }

    const defaultSuggestionStyle: React.CSSProperties = {
      position: 'absolute',
      top: '100%',
      left: 0,
      right: 0,
      backgroundColor: '#ffffff',
      border: '1px solid #e5e7eb',
      borderTop: 'none',
      borderRadius: '0 0 6px 6px',
      padding: '10px 12px',
      fontSize: '13px',
      color: '#374151',
      cursor: 'pointer',
      zIndex: 1000,
      boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
      backdropFilter: 'blur(10px)',
      transition: 'all 0.2s ease',
      ...suggestionStyle
    }

    const containerStyle: React.CSSProperties = {
      position: 'relative',
      ...style
    }

    return (
      <div style={containerStyle} className={className}>
        <input
          ref={inputRef}
          {...props}
          style={{
            width: '100%',
            ...(props as any).style
          }}
          onKeyDown={handleKeyDownWithCompletion}
          onChange={handleInputWithCompletion}
          onBlur={handleBlurWithCompletion}
          onFocus={handleFocus}
        />
        
        {showSuggestion && showSuggestionState && suggestion && isFocused && (
          <div
            style={defaultSuggestionStyle}
            onClick={handleSuggestionClick}
            onMouseDown={(e) => e.preventDefault()} // Prevent input blur
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ color: '#9ca3af', fontSize: '11px', fontWeight: '600', textTransform: 'uppercase' }}>
                {loading ? '⏳' : '✨'}
              </span>
              <span style={{ flex: 1, fontFamily: 'system-ui' }}>{suggestion}</span>
              <span style={{ color: '#9ca3af', fontSize: '11px' }}>Tab</span>
            </div>
          </div>
        )}
        
        {error && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            backgroundColor: '#fee2e2',
            border: '1px solid #fecaca',
            borderRadius: '0 0 6px 6px',
            padding: '10px 12px',
            fontSize: '12px',
            color: '#991b1b',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}
      </div>
    )
  }
)

TabCompletionInput.displayName = 'TabCompletionInput'

// Textarea version
export interface TabCompletionTextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  completionType?: 'general' | 'code' | 'prompt' | 'message' | 'search' | 'email' | 'description'
  temperature?: number
  top_p?: number
  max_tokens?: number
  showSuggestion?: boolean
  suggestionStyle?: React.CSSProperties
  onCompletion?: (completion: string) => void
}

export interface TabCompletionTextareaRef {
  focus: () => void
  blur: () => void
  select: () => void
  setSelectionRange: (start: number, end: number) => void
}

export const TabCompletionTextarea = forwardRef<TabCompletionTextareaRef, TabCompletionTextareaProps>(
  ({ 
    completionType = 'general',
    temperature,
    top_p,
    max_tokens,
    showSuggestion = true,
    suggestionStyle,
    onCompletion,
    style,
    className,
    ...props 
  }, ref) => {
    const textareaRef = useRef<HTMLTextAreaElement>(null)
    const [isFocused, setIsFocused] = useState(false)
    const { client } = useCompletionContext()
    
    const {
      handleKeyDown,
      handleInput,
      handleBlur,
      suggestion,
      showSuggestion: showSuggestionState,
      loading,
      error
    } = useTabCompletion(textareaRef, {
      completionType,
      temperature,
      top_p,
      max_tokens,
      client: client || undefined
    })

    useImperativeHandle(ref, () => ({
      focus: () => textareaRef.current?.focus(),
      blur: () => textareaRef.current?.blur(),
      select: () => textareaRef.current?.select(),
      setSelectionRange: (start: number, end: number) => textareaRef.current?.setSelectionRange(start, end)
    }))

    const handleKeyDownWithCompletion = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      handleKeyDown(e)
      props.onKeyDown?.(e)
    }

    const handleInputWithCompletion = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      handleInput(e)
      props.onChange?.(e)
    }

    const handleBlurWithCompletion = (e: React.FocusEvent<HTMLTextAreaElement>) => {
      handleBlur()
      setIsFocused(false)
      props.onBlur?.(e)
    }

    const handleFocus = (e: React.FocusEvent<HTMLTextAreaElement>) => {
      setIsFocused(true)
      props.onFocus?.(e)
    }

    const handleSuggestionClick = () => {
      if (textareaRef.current && suggestion) {
        const currentText = textareaRef.current.value
        const cursorPosition = textareaRef.current.selectionStart || 0
        const textBeforeCursor = currentText.substring(0, cursorPosition)
        const newText = textBeforeCursor + suggestion + currentText.substring(cursorPosition)
        
        textareaRef.current.value = newText
        textareaRef.current.setSelectionRange(
          cursorPosition + suggestion.length,
          cursorPosition + suggestion.length
        )
        
        // Trigger change event
        textareaRef.current.dispatchEvent(new Event('input', { bubbles: true }))
        
        onCompletion?.(suggestion)
      }
    }

    const defaultSuggestionStyle: React.CSSProperties = {
      position: 'absolute',
      top: '100%',
      left: 0,
      right: 0,
      backgroundColor: '#ffffff',
      border: '1px solid #e5e7eb',
      borderTop: 'none',
      borderRadius: '0 0 6px 6px',
      padding: '10px 12px',
      fontSize: '13px',
      color: '#374151',
      cursor: 'pointer',
      zIndex: 1000,
      boxShadow: '0 4px 12px rgba(0,0,0,0.08)',
      backdropFilter: 'blur(10px)',
      transition: 'all 0.2s ease',
      ...suggestionStyle
    }

    const containerStyle: React.CSSProperties = {
      position: 'relative',
      ...style
    }

    return (
      <div style={containerStyle} className={className}>
        <textarea
          ref={textareaRef}
          {...props}
          style={{
            width: '100%',
            resize: 'vertical',
            ...(props as any).style
          }}
          onKeyDown={handleKeyDownWithCompletion}
          onChange={handleInputWithCompletion}
          onBlur={handleBlurWithCompletion}
          onFocus={handleFocus}
        />
        
        {showSuggestion && showSuggestionState && suggestion && isFocused && (
          <div
            style={defaultSuggestionStyle}
            onClick={handleSuggestionClick}
            onMouseDown={(e) => e.preventDefault()} // Prevent textarea blur
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <span style={{ color: '#9ca3af', fontSize: '11px', fontWeight: '600', textTransform: 'uppercase' }}>
                {loading ? '⏳' : '✨'}
              </span>
              <span style={{ flex: 1, fontFamily: 'system-ui' }}>{suggestion}</span>
              <span style={{ color: '#9ca3af', fontSize: '11px' }}>Tab</span>
            </div>
          </div>
        )}
        
        {error && (
          <div style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            backgroundColor: '#fee2e2',
            border: '1px solid #fecaca',
            borderRadius: '0 0 6px 6px',
            padding: '10px 12px',
            fontSize: '12px',
            color: '#991b1b',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}>
            <span>⚠️</span>
            <span>{error}</span>
          </div>
        )}
      </div>
    )
  }
)

TabCompletionTextarea.displayName = 'TabCompletionTextarea'

export default TabCompletionInput

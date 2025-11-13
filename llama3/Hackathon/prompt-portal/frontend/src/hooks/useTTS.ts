import { useCallback, useRef, useState } from 'react'
import { ttsAPI } from '../api'

interface UseTTSProps {
  voice?: string
  speed?: number
  onError?: (error: string) => void
}

const useTTS = (props: UseTTSProps = {}) => {
  const { voice = 'af_heart', speed = 1.0, onError } = props
  
  const [isPlaying, setIsPlaying] = useState(false)
  const [isSynthesizing, setIsSynthesizing] = useState(false)
  const [currentText, setCurrentText] = useState('')
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  
  const synthesizeAndPlay = useCallback(
    async (text: string, voiceOverride?: string, speedOverride?: number) => {
      // Validate text input
      if (!text || typeof text !== 'string' || !text.trim()) {
        console.warn('[TTS] Cannot synthesize empty or invalid text:', text)
        return
      }
      
      try {
        setIsSynthesizing(true)
        setCurrentText(text)
        
        // Create a temporary audio element
        if (!audioRef.current) {
          audioRef.current = new Audio()
          audioRef.current.onplay = () => setIsPlaying(true)
          audioRef.current.onended = () => setIsPlaying(false)
          audioRef.current.onerror = () => {
            setIsPlaying(false)
            if (onError) onError('Failed to play audio')
          }
        }
        
        const response = await ttsAPI.synthesize({
          text: text.trim(),
          voice: voiceOverride || voice,
          lang_code: 'a',
          speed: speedOverride || speed
        })
        
        if (response.data.audio_base64) {
          // Decode base64 to blob
          const binaryString = atob(response.data.audio_base64)
          const bytes = new Uint8Array(binaryString.length)
          
          for (let i = 0; i < binaryString.length; i++) {
            bytes[i] = binaryString.charCodeAt(i)
          }
          
          const blob = new Blob([bytes], { type: 'audio/wav' })
          const url = URL.createObjectURL(blob)
          
          // Play audio
          audioRef.current.src = url
          audioRef.current.play()
          
          setIsSynthesizing(false)
          
          return {
            url,
            duration: response.data.audio_duration_seconds,
            sampleRate: response.data.audio_sample_rate
          }
        }
      } catch (error) {
        setIsSynthesizing(false)
        const errorMsg = error instanceof Error ? error.message : 'TTS synthesis failed'
        console.error('TTS Error:', errorMsg)
        if (onError) onError(errorMsg)
        throw error
      }
    },
    [voice, speed, onError]
  )
  
  const stop = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      setIsPlaying(false)
    }
  }, [])
  
  const pause = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      setIsPlaying(false)
    }
  }, [])
  
  const resume = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.play()
      setIsPlaying(true)
    }
  }, [])
  
  const cleanup = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.src = ''
    }
    if (audioContextRef.current) {
      audioContextRef.current.close()
    }
  }, [])
  
  return {
    isPlaying,
    isSynthesizing,
    currentText,
    synthesizeAndPlay,
    stop,
    pause,
    resume,
    cleanup
  }
}

export default useTTS

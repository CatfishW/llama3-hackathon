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
        
        console.log('[TTS] Starting synthesis for text:', text.substring(0, 50) + '...')
        
        // Create a temporary audio element
        if (!audioRef.current) {
          audioRef.current = new Audio()
          audioRef.current.onplay = () => {
            console.log('[TTS] Audio playback started')
            setIsPlaying(true)
          }
          audioRef.current.onended = () => {
            console.log('[TTS] Audio playback ended')
            setIsPlaying(false)
          }
          audioRef.current.onerror = (e) => {
            console.error('[TTS] Audio element error:', audioRef.current?.error, e)
            setIsPlaying(false)
            if (onError) onError('Failed to play audio: ' + audioRef.current?.error?.message)
          }
        }
        
        console.log('[TTS] Calling TTS API with voice:', voiceOverride || voice)
        const response = await ttsAPI.synthesize({
          text: text.trim(),
          voice: voiceOverride || voice,
          lang_code: 'a',
          speed: speedOverride || speed
        })
        
        console.log('[TTS] TTS response received:', {
          has_audio_base64: !!response.data.audio_base64,
          base64_length: response.data.audio_base64?.length,
          audio_sample_rate: response.data.audio_sample_rate,
          audio_duration_seconds: response.data.audio_duration_seconds,
          voice: response.data.voice
        })
        
        if (response.data.audio_base64) {
          try {
            // Decode base64 to blob
            console.log('[TTS] Decoding base64 audio...')
            const binaryString = atob(response.data.audio_base64)
            console.log('[TTS] Binary string length:', binaryString.length)
            
            const bytes = new Uint8Array(binaryString.length)
            for (let i = 0; i < binaryString.length; i++) {
              bytes[i] = binaryString.charCodeAt(i)
            }
            
            console.log('[TTS] Created Uint8Array, length:', bytes.length)
            console.log('[TTS] First 20 bytes (hex):', Array.from(bytes.slice(0, 20)).map(b => b.toString(16).padStart(2, '0')).join(' '))
            
            // Detect audio format from header
            const header = String.fromCharCode(...bytes.slice(0, 4))
            console.log('[TTS] Audio header:', header)
            
            let mimeType = 'audio/wav'
            if (header === 'RIFF') {
              console.log('[TTS] Detected WAV format')
              mimeType = 'audio/wav'
            } else if (header === 'ID3' || bytes[0] === 0xFF) {
              console.log('[TTS] Detected MP3 format')
              mimeType = 'audio/mpeg'
            }
            
            const blob = new Blob([bytes], { type: mimeType })
            console.log('[TTS] Created blob - Type:', blob.type, 'Size:', blob.size)
            
            const url = URL.createObjectURL(blob)
            console.log('[TTS] Created object URL:', url)
            
            // Set source and wait for canplay before playing
            audioRef.current.src = url
            console.log('[TTS] Set audio src, readyState:', audioRef.current.readyState)
            
            // Add event listeners for debugging
            const onCanPlay = () => {
              console.log('[TTS] Audio canplay event - duration:', audioRef.current?.duration)
              audioRef.current?.removeEventListener('canplay', onCanPlay)
              audioRef.current?.play().catch(e => {
                console.error('[TTS] Failed to play audio:', e)
                if (onError) onError('Failed to play audio: ' + e.message)
              })
            }
            
            const onLoadedMetadata = () => {
              console.log('[TTS] Audio loadedmetadata - duration:', audioRef.current?.duration)
            }
            
            audioRef.current.addEventListener('canplay', onCanPlay, { once: true })
            audioRef.current.addEventListener('loadedmetadata', onLoadedMetadata, { once: true })
            
            // Try to load the audio
            audioRef.current.load()
            console.log('[TTS] Called audio.load()')
            
            setIsSynthesizing(false)
            
            return {
              url,
              duration: response.data.audio_duration_seconds,
              sampleRate: response.data.audio_sample_rate
            }
          } catch (decodeError) {
            console.error('[TTS] Failed to decode audio:', decodeError)
            setIsSynthesizing(false)
            throw new Error(`Audio decoding failed: ${decodeError instanceof Error ? decodeError.message : 'Unknown error'}`)
          }
        } else {
          console.error('[TTS] No audio_base64 in response')
          setIsSynthesizing(false)
          throw new Error('No audio data received from TTS service')
        }
      } catch (error) {
        setIsSynthesizing(false)
        const errorMsg = error instanceof Error ? error.message : 'TTS synthesis failed'
        console.error('[TTS] Error:', errorMsg, error)
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

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
            
            // Check if data is already WAV or raw PCM
            const header = String.fromCharCode(...bytes.slice(0, 4))
            console.log('[TTS] Audio header:', header)
            
            let audioBlob: Blob
            
            if (header === 'RIFF') {
              // Already a WAV file
              console.log('[TTS] Data is already WAV format')
              audioBlob = new Blob([bytes], { type: 'audio/wav' })
            } else {
              // Raw PCM data - need to wrap in WAV header
              console.log('[TTS] Data appears to be raw PCM, wrapping in WAV header...')
              const sampleRate = response.data.audio_sample_rate || 24000
              const numChannels = 1 // Kokoro outputs MONO audio (not stereo)
              const bitsPerSample = 32 // Float32 PCM
              const bytesPerSample = bitsPerSample / 8
              const byteRate = sampleRate * numChannels * bytesPerSample
              const blockAlign = numChannels * bytesPerSample
              
              // Create WAV header
              const wavHeaderSize = 44
              const audioDataSize = bytes.length
              const wavBuffer = new ArrayBuffer(wavHeaderSize + audioDataSize)
              const wavView = new DataView(wavBuffer)
              
              // Helper to write string
              const writeString = (offset: number, string: string) => {
                for (let i = 0; i < string.length; i++) {
                  wavView.setUint8(offset + i, string.charCodeAt(i))
                }
              }
              
              // RIFF header
              writeString(0, 'RIFF')
              wavView.setUint32(4, wavHeaderSize + audioDataSize - 8, true)
              writeString(8, 'WAVE')
              
              // fmt subchunk
              writeString(12, 'fmt ')
              wavView.setUint32(16, 16, true) // fmt chunk size
              wavView.setUint16(20, 3, true) // Audio format (3 = IEEE Float)
              wavView.setUint16(22, numChannels, true) // Number of channels
              wavView.setUint32(24, sampleRate, true) // Sample rate
              wavView.setUint32(28, byteRate, true) // Byte rate
              wavView.setUint16(32, blockAlign, true) // Block align
              wavView.setUint16(34, bitsPerSample, true) // Bits per sample
              
              // data subchunk
              writeString(36, 'data')
              wavView.setUint32(40, audioDataSize, true) // Data size
              
              // Copy audio data
              const audioDataView = new Uint8Array(wavBuffer, wavHeaderSize)
              audioDataView.set(bytes)
              
              console.log('[TTS] WAV header created - format: Float32 Mono, sample rate:', sampleRate, 'Hz, header:', wavHeaderSize, 'bytes, data:', audioDataSize, 'bytes, total:', wavBuffer.byteLength)
              audioBlob = new Blob([wavBuffer], { type: 'audio/wav' })
            }
            
            console.log('[TTS] Created blob - Type:', audioBlob.type, 'Size:', audioBlob.size)

            const url = URL.createObjectURL(audioBlob)
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

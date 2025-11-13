import { useEffect, useRef, useState, useCallback } from 'react'

interface AudioVisualizerData {
  frequency: number[]
  waveform: Uint8Array
}

interface UseVoiceRecorderProps {
  onTranscription?: (text: string) => void
  onError?: (error: string) => void
  language?: string
  apiUrl?: string
}

const useVoiceRecorder = (props: UseVoiceRecorderProps = {}) => {
  const { 
    onTranscription, 
    onError, 
    language = 'en',
    apiUrl = '/api/stt'
  } = props
  
  const [isRecording, setIsRecording] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [isFinal, setIsFinal] = useState(false)
  const [confidence, setConfidence] = useState(0)
  const [isTranscribing, setIsTranscribing] = useState(false)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const chunksRef = useRef<Blob[]>([])
  
  // Initialize audio context for recording
  const initializeAudioContext = useCallback(async () => {
    if (audioContextRef.current) return
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      })
      
      micStreamRef.current = stream
      
      // Create audio context for visualization
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      const source = audioContext.createMediaStreamSource(stream)
      const analyser = audioContext.createAnalyser()
      
      analyser.fftSize = 2048
      analyser.smoothingTimeConstant = 0.8
      source.connect(analyser)
      
      audioContextRef.current = audioContext
      analyserRef.current = analyser
      
      // Set up media recorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      })
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }
      
      mediaRecorderRef.current = mediaRecorder
      
      return { audioContext, analyser, stream, mediaRecorder }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to access microphone'
      console.error('[STT] Microphone access error:', errorMsg)
      if (onError) onError(errorMsg)
      throw error
    }
  }, [onError])
  
  const startRecording = useCallback(async () => {
    try {
      console.log('[STT] Starting recording...')
      
      // Initialize if needed
      if (!audioContextRef.current) {
        await initializeAudioContext()
      }
      
      setIsRecording(true)
      setIsListening(true)
      setTranscript('')
      setIsFinal(false)
      setConfidence(0)
      chunksRef.current = []
      
      // Start media recorder
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.start()
        console.log('[STT] MediaRecorder started')
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to start recording'
      console.error('[STT] Start recording error:', errorMsg)
      setIsRecording(false)
      setIsListening(false)
      if (onError) onError(errorMsg)
    }
  }, [initializeAudioContext, onError])
  
  const stopRecording = useCallback(async (): Promise<string> => {
    return new Promise((resolve, reject) => {
      if (!mediaRecorderRef.current) {
        console.log('[STT] No media recorder available')
        setIsRecording(false)
        setIsListening(false)
        resolve('')
        return
      }
      
      console.log('[STT] Stopping recording...')
      setIsRecording(false)
      setIsTranscribing(true)
      
      const handleStopEvent = async () => {
        try {
          // Get audio blob
          const audioBlob = new Blob(chunksRef.current, { type: 'audio/webm' })
          console.log('[STT] Audio blob created, size:', audioBlob.size)
          
          if (audioBlob.size === 0) {
            console.warn('[STT] Empty audio blob')
            setIsListening(false)
            setIsTranscribing(false)
            resolve('')
            return
          }
          
          // Send to backend for transcription
          console.log('[STT] Sending audio to backend for transcription...')
          setTranscript('🔄 Transcribing...')
          
          const formData = new FormData()
          formData.append('file', audioBlob, 'audio.webm')
          formData.append('language', language)
          
          const response = await fetch(`${apiUrl}/transcribe`, {
            method: 'POST',
            body: formData
          })
          
          if (!response.ok) {
            const errorData = await response.json()
            throw new Error(errorData.detail || `HTTP ${response.status}`)
          }
          
          const result = await response.json()
          let transcribedText = result.text || ''
          
          // Filter out invalid Whisper.cpp artifacts
          const invalidPatterns = [
            /^\s*\[MUSIC PLAYING\]\s*$/i,
            /^\s*\[SILENCE\]\s*$/i,
            /^\s*\[BLANK[_\s]*AUDIO\]\s*$/i,
            /^\s*\[\s*\]\s*$/,
            /^\s*\.+\s*$/,
          ]
          
          if (invalidPatterns.some(pattern => pattern.test(transcribedText))) {
            console.log('[STT] Filtered out invalid pattern:', transcribedText)
            transcribedText = ''
          }
          
          console.log('[STT] Transcription complete:', transcribedText)
          setTranscript(transcribedText)
          setIsFinal(true)
          setConfidence(result.confidence || 0.95)
          
          if (transcribedText && onTranscription) {
            onTranscription(transcribedText)
          }
          
          setIsListening(false)
          setIsTranscribing(false)
          resolve(transcribedText)
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : 'Transcription failed'
          console.error('[STT] Transcription error:', errorMsg)
          
          // Fallback: try to use Web Speech API as backup
          console.log('[STT] Attempting Web Speech API fallback...')
          attemptWebSpeechFallback().then(resolve).catch(() => {
            setIsListening(false)
            setIsTranscribing(false)
            if (onError) onError(errorMsg)
            resolve('')
          })
        }
      }
      
      mediaRecorderRef.current.addEventListener('stop', handleStopEvent, { once: true })
      mediaRecorderRef.current.stop()
    })
  }, [language, apiUrl, onTranscription, onError])
  
  // Fallback: Web Speech API
  const attemptWebSpeechFallback = useCallback((): Promise<string> => {
    return new Promise((resolve) => {
      const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
      
      if (!SpeechRecognition) {
        console.warn('[STT] Web Speech API not available')
        resolve('')
        return
      }
      
      try {
        const recognition = new SpeechRecognition()
        recognition.continuous = false
        recognition.interimResults = false
        recognition.language = language
        
        let hasResolved = false
        
        recognition.onstart = () => {
          console.log('[STT] Web Speech API started (fallback)')
          setTranscript('🎤 Listening...')
        }
        
        recognition.onresult = (event: any) => {
          let finalTranscript = ''
          for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript
            if (event.results[i].isFinal) {
              finalTranscript += transcript + ' '
            }
          }
          
          if (finalTranscript && !hasResolved) {
            hasResolved = true
            console.log('[STT] Web Speech fallback result:', finalTranscript.trim())
            setTranscript(finalTranscript.trim())
            setIsFinal(true)
            resolve(finalTranscript.trim())
          }
        }
        
        recognition.onerror = (event: any) => {
          console.error('[STT] Web Speech error:', event.error)
          if (!hasResolved) {
            hasResolved = true
            resolve('')
          }
        }
        
        recognition.onend = () => {
          if (!hasResolved) {
            hasResolved = true
            console.log('[STT] Web Speech ended')
            resolve('')
          }
        }
        
        recognition.start()
        
        // Timeout after 10 seconds
        setTimeout(() => {
          if (!hasResolved) {
            hasResolved = true
            recognition.abort()
            console.log('[STT] Web Speech timeout')
            resolve('')
          }
        }, 10000)
      } catch (error) {
        console.error('[STT] Web Speech setup error:', error)
        resolve('')
      }
    })
  }, [language])
  
  const getAudioVisualizerData = useCallback((): AudioVisualizerData => {
    const data: AudioVisualizerData = {
      frequency: [],
      waveform: new Uint8Array()
    }
    
    if (analyserRef.current) {
      // Frequency data
      const freqData = new Uint8Array(analyserRef.current.frequencyBinCount)
      analyserRef.current.getByteFrequencyData(freqData)
      data.frequency = Array.from(freqData).slice(0, 32)
      
      // Waveform data
      const waveformData = new Uint8Array(analyserRef.current.fftSize)
      analyserRef.current.getByteTimeDomainData(waveformData)
      data.waveform = waveformData
    }
    
    return data
  }, [])
  
  const cleanup = useCallback(() => {
    if (mediaRecorderRef.current) {
      try {
        mediaRecorderRef.current.stop()
      } catch (e) {
        // ignore
      }
      mediaRecorderRef.current = null
    }
    
    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach(track => track.stop())
      micStreamRef.current = null
    }
    
    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }
    
    analyserRef.current = null
    chunksRef.current = []
    
    setIsRecording(false)
    setIsListening(false)
    setIsTranscribing(false)
  }, [])
  
  return {
    isRecording,
    isListening,
    isTranscribing,
    transcript,
    isFinal,
    confidence,
    startRecording,
    stopRecording,
    getAudioVisualizerData,
    cleanup
  }
}

export default useVoiceRecorder

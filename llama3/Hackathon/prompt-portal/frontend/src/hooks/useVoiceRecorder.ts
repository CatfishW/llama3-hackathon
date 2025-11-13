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
  
  // Decode WebM to raw PCM and immediately convert to WAV in one step
  const recordingToWav = useCallback(async (webmBlob: Blob): Promise<Blob> => {
    console.log('[STT] Converting recording to WAV format...')
    console.log('[STT] WebM blob size:', webmBlob.size)
    
    if (!audioContextRef.current) {
      throw new Error('Audio context not available')
    }
    
    try {
      // Decode WebM to AudioBuffer
      const arrayBuffer = await webmBlob.arrayBuffer()
      const audioBuffer = await audioContextRef.current.decodeAudioData(arrayBuffer)
      console.log('[STT] Decoded - sampleRate:', audioBuffer.sampleRate, 'duration:', audioBuffer.duration)
      
      // Get raw audio data (float32)
      const rawData = audioBuffer.getChannelData(0)
      console.log('[STT] Raw data length:', rawData.length, 'samples')
      
      // Downsample from 48kHz to 16kHz if needed
      const targetSampleRate = 16000
      const sourceSampleRate = audioBuffer.sampleRate
      let pcmData: Int16Array
      
      if (sourceSampleRate === targetSampleRate) {
        // No downsampling needed
        console.log('[STT] No downsampling needed (already 16kHz)')
        pcmData = new Int16Array(rawData.length)
        for (let i = 0; i < rawData.length; i++) {
          const sample = Math.max(-1, Math.min(1, rawData[i]))
          pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
        }
      } else {
        // Downsample using simple linear interpolation
        const ratio = sourceSampleRate / targetSampleRate
        const downsampledLength = Math.floor(rawData.length / ratio)
        console.log('[STT] Downsampling from', sourceSampleRate, 'Hz to', targetSampleRate, 'Hz')
        console.log('[STT] Samples:', rawData.length, '→', downsampledLength)
        
        pcmData = new Int16Array(downsampledLength)
        for (let i = 0; i < downsampledLength; i++) {
          const sourceIndex = i * ratio
          const sourceIndexFloor = Math.floor(sourceIndex)
          const sourceIndexFraction = sourceIndex - sourceIndexFloor
          
          // Linear interpolation between samples
          let sample = rawData[sourceIndexFloor]
          if (sourceIndexFloor + 1 < rawData.length) {
            sample = sample * (1 - sourceIndexFraction) + rawData[sourceIndexFloor + 1] * sourceIndexFraction
          }
          
          // Convert float32 [-1, 1] to int16
          sample = Math.max(-1, Math.min(1, sample))
          pcmData[i] = sample < 0 ? sample * 0x8000 : sample * 0x7FFF
        }
      }
      
      console.log('[STT] Converted to PCM - size:', pcmData.byteLength, 'bytes')
      
      // Create WAV file with proper header
      const sampleRate = 16000
      const numChannels = 1
      const bitsPerSample = 16
      const bytesPerSample = bitsPerSample / 8
      const byteRate = sampleRate * numChannels * bytesPerSample
      const blockAlign = numChannels * bytesPerSample
      
      const wavDataSize = pcmData.byteLength
      const wavHeaderSize = 44
      const wavTotal = wavHeaderSize + wavDataSize
      
      const wav = new ArrayBuffer(wavTotal)
      const view = new DataView(wav)
      
      // Helper to write ASCII string
      const writeString = (offset: number, string: string) => {
        for (let i = 0; i < string.length; i++) {
          view.setUint8(offset + i, string.charCodeAt(i))
        }
      }
      
      // RIFF header
      writeString(0, 'RIFF')
      view.setUint32(4, wavTotal - 8, true) // File size minus RIFF header
      writeString(8, 'WAVE')
      
      // fmt subchunk
      writeString(12, 'fmt ')
      view.setUint32(16, 16, true) // fmt chunk size
      view.setUint16(20, 1, true) // Audio format (PCM = 1)
      view.setUint16(22, numChannels, true) // Number of channels
      view.setUint32(24, sampleRate, true) // Sample rate
      view.setUint32(28, byteRate, true) // Byte rate
      view.setUint16(32, blockAlign, true) // Block align
      view.setUint16(34, bitsPerSample, true) // Bits per sample
      
      // data subchunk
      writeString(36, 'data')
      view.setUint32(40, wavDataSize, true) // Data size
      
      // Copy PCM data
      const pcmView = new Uint8Array(wav, 44)
      pcmView.set(new Uint8Array(pcmData.buffer))
      
      console.log('[STT] WAV created - header:', wavHeaderSize, 'bytes, data:', wavDataSize, 'bytes, total:', wavTotal, 'bytes')
      return new Blob([wav], { type: 'audio/wav' })
    } catch (error) {
      console.error('[STT] Failed to convert to WAV:', error)
      throw new Error(`WAV conversion failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }, [])

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
      const recorder = mediaRecorderRef.current
      let stopHandled = false
      let forceTimeout: ReturnType<typeof setTimeout>

      const finalizeTranscription = async () => {
        if (stopHandled) {
          return
        }
        stopHandled = true
        if (forceTimeout) {
          clearTimeout(forceTimeout)
        }

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
          
          // Convert recording to WAV format directly
          console.log('[STT] Converting recording to WAV format...')
          const wavBlob = await recordingToWav(audioBlob)
          console.log('[STT] WAV conversion complete, size:', wavBlob.size)
          
          // Send WAV to backend for transcription
          console.log('[STT] Sending WAV to backend...')
          setTranscript('🔄 Transcribing...')
          
          const formData = new FormData()
          formData.append('file', wavBlob, 'audio.wav')
          formData.append('language', language)
          
          console.log('[STT] FormData prepared - WAV blob type:', wavBlob.type, 'Size:', wavBlob.size)
          
          const response = await fetch(`${apiUrl}/transcribe`, {
            method: 'POST',
            body: formData
          })
          
          console.log('[STT] Response received - Status:', response.status)
          
          if (!response.ok) {
            const errorData = await response.json()
            console.error('[STT] Error response:', errorData)
            throw new Error(errorData.detail || `HTTP ${response.status}`)
          }
          
          const result = await response.json()
          console.log('[STT] Parsed result:', result)
          
          let transcribedText = result.text || ''
          console.log('[STT] Extracted text:', transcribedText, '(length:', transcribedText.length, ')')
          
          // Filter out invalid Whisper.cpp artifacts - comprehensive list
          const invalidPatterns = [
            /^\s*\[MUSIC\]\s*$/i,
            /^\s*\[SOUND\]\s*$/i,
            /^\s*\[snaps fingers\]\s*$/i,
            /^\s*\[snap\]\s*$/i,
            /^\s*\[MUSIC\s+PLAYING\]\s*$/i,
            /^\s*\[SILENCE\]\s*$/i,
            /^\s*\[BLANK[_\s]*AUDIO\]\s*$/i,
            /^\s*\[applause\]\s*$/i,
            /^\s*\[\s*\]\s*$/,
            /^\s*\.+\s*$/,
          ]
          
          const matchedPattern = invalidPatterns.find(pattern => pattern.test(transcribedText))
          if (matchedPattern) {
            console.log('[STT] Filtered artifact:', transcribedText)
            transcribedText = ''
          }
          
          console.log('[STT] Final text after filtering:', transcribedText, '(length:', transcribedText.length, ')')
          
          setTranscript(transcribedText)
          setIsFinal(true)
          setConfidence(result.confidence || 0.95)
          
          if (transcribedText && onTranscription) {
            console.log('[STT] Calling onTranscription with:', transcribedText)
            onTranscription(transcribedText)
          }
          
          setIsListening(false)
          setIsTranscribing(false)
          resolve(transcribedText)
        } catch (error) {
          const errorMsg = error instanceof Error ? error.message : 'Transcription failed'
          console.error('[STT] Transcription error:', errorMsg)
          
          setIsListening(false)
          setIsTranscribing(false)
          
          // Fallback: try to use Web Speech API as backup
          console.log('[STT] Attempting Web Speech API fallback...')
          attemptWebSpeechFallback().then(resolve).catch(() => {
            if (onError) onError(errorMsg)
            resolve('')
          })
        }
      }

      const onStop = () => {
        void finalizeTranscription()
      }

      recorder.addEventListener('stop', onStop, { once: true })

      if (recorder.state !== 'inactive') {
        try {
          if (typeof recorder.requestData === 'function') {
            recorder.requestData()
          }
        } catch (requestError) {
          console.warn('[STT] requestData failed, continuing with stop():', requestError)
        }

        recorder.stop()
      } else {
        console.log('[STT] MediaRecorder already inactive when stop requested')
        void finalizeTranscription()
        return
      }

      forceTimeout = setTimeout(() => {
        if (!stopHandled) {
          console.warn('[STT] MediaRecorder stop event timeout, forcing transcription immediately')
          void finalizeTranscription()
        }
      }, 1200)
    })
  }, [language, apiUrl, onTranscription, onError, recordingToWav])
  
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

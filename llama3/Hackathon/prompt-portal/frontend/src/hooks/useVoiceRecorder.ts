import { useEffect, useRef, useState, useCallback } from 'react'

interface AudioVisualizerData {
  frequency: number[]
  waveform: Uint8Array
}

interface UseVoiceRecorderProps {
  onTranscription?: (text: string) => void
  onError?: (error: string) => void
  language?: string
}

const useVoiceRecorder = (props: UseVoiceRecorderProps = {}) => {
  const { onTranscription, onError, language = 'en-US' } = props
  
  const [isRecording, setIsRecording] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [isFinal, setIsFinal] = useState(false)
  const [confidence, setConfidence] = useState(0)
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const micStreamRef = useRef<MediaStream | null>(null)
  const recognitionRef = useRef<any>(null)
  const chunksRef = useRef<Blob[]>([])
  
  // Initialize Web Speech API
  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    
    if (!SpeechRecognition) {
      console.warn('Web Speech API not supported in this browser')
      return
    }
    
    const recognition = new SpeechRecognition()
    recognition.continuous = true
    recognition.interimResults = true
    recognition.language = language
    
    recognition.onstart = () => {
      setIsListening(true)
      setTranscript('')
      setIsFinal(false)
      setConfidence(0)
    }
    
    recognition.onresult = (event: any) => {
      let interimTranscript = ''
      let finalTranscript = ''
      let maxConfidence = 0
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript
        const conf = event.results[i][0].confidence
        
        maxConfidence = Math.max(maxConfidence, conf)
        
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' '
        } else {
          interimTranscript += transcript
        }
      }
      
      setTranscript(finalTranscript || interimTranscript)
      setIsFinal(!!finalTranscript)
      setConfidence(maxConfidence)
      
      // Callback for final transcription
      if (finalTranscript && onTranscription) {
        onTranscription(finalTranscript.trim())
      }
    }
    
    recognition.onerror = (event: any) => {
      const errorMessage = `Speech recognition error: ${event.error}`
      console.error(errorMessage)
      if (onError) onError(errorMessage)
      setIsListening(false)
    }
    
    recognition.onend = () => {
      setIsListening(false)
    }
    
    recognitionRef.current = recognition
    
    return () => {
      recognition.abort()
    }
  }, [language, onTranscription, onError])
  
  // Initialize audio context for visualization
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
      
      // Create audio context
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)()
      const source = audioContext.createMediaStreamSource(stream)
      const analyser = audioContext.createAnalyser()
      
      analyser.fftSize = 2048
      analyser.smoothingTimeConstant = 0.8
      source.connect(analyser)
      
      audioContextRef.current = audioContext
      analyserRef.current = analyser
      
      return { audioContext, analyser, stream }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to access microphone'
      console.error(errorMsg)
      if (onError) onError(errorMsg)
      throw error
    }
  }, [onError])
  
  const startRecording = useCallback(async () => {
    try {
      // Initialize audio context if not already done
      if (!audioContextRef.current) {
        await initializeAudioContext()
      }
      
      setIsRecording(true)
      setTranscript('')
      setIsFinal(false)
      chunksRef.current = []
      
      // Start speech recognition
      if (recognitionRef.current) {
        recognitionRef.current.start()
      }
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Failed to start recording'
      setIsRecording(false)
      if (onError) onError(errorMsg)
    }
  }, [initializeAudioContext, onError])
  
  const stopRecording = useCallback(async (): Promise<string> => {
    return new Promise((resolve) => {
      setIsRecording(false)
      
      if (recognitionRef.current) {
        // Stop speech recognition and wait for final result
        const handleFinalResult = (event: any) => {
          if (event.results.length > 0) {
            let finalTranscript = ''
            for (let i = 0; i < event.results.length; i++) {
              if (event.results[i].isFinal) {
                finalTranscript += event.results[i][0].transcript
              }
            }
            recognitionRef.current.removeEventListener('result', handleFinalResult)
            setTranscript(finalTranscript.trim())
            resolve(finalTranscript.trim())
          }
        }
        
        recognitionRef.current.addEventListener('result', handleFinalResult)
        recognitionRef.current.stop()
        
        // Timeout in case no final result
        setTimeout(() => {
          recognitionRef.current.removeEventListener('result', handleFinalResult)
          resolve(transcript)
        }, 500)
      } else {
        resolve(transcript)
      }
    })
  }, [transcript])
  
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
      mediaRecorderRef.current.stop()
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
    recognitionRef.current?.abort()
    
    setIsRecording(false)
    setIsListening(false)
  }, [])
  
  return {
    isRecording,
    isListening,
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

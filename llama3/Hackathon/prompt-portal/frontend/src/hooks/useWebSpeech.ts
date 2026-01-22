import { useState, useCallback, useRef, useEffect } from 'react';

interface UseWebSpeechOptions {
  onTranscript?: (transcript: string) => void;
  onError?: (error: string) => void;
  language?: string;
}

export const useWebSpeech = (options: UseWebSpeechOptions = {}) => {
  const { onTranscript, onError, language = 'en-US' } = options;
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = language;

      recognitionRef.current.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        if (onTranscript) {
          onTranscript(transcript);
        }
      };

      recognitionRef.current.onerror = (event: any) => {
        if (onError) {
          onError(event.error);
        }
        setIsListening(false);
      };

      recognitionRef.current.onend = () => {
        setIsListening(false);
      };
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, [language, onTranscript, onError]);

  const startListening = useCallback(() => {
    if (!recognitionRef.current) {
      if (onError) onError('Speech recognition not supported in this browser.');
      return;
    }

    try {
      recognitionRef.current.start();
      setIsListening(true);
    } catch (err) {
      console.error('Speech recognition start error:', err);
    }
  }, [onError]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
    }
  }, []);

  return {
    isListening,
    startListening,
    stopListening,
    isSupported: !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition)
  };
};

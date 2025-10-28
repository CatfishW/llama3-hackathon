import { useEffect, useRef } from 'react'

export function useSSE(url: string | null, onMessage: (evt: MessageEvent) => void) {
  const ref = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!url) return
    const es = new EventSource(url)
    ref.current = es
    es.onmessage = onMessage
    es.onerror = () => {
      es.close()
    }
    return () => {
      es.close()
      ref.current = null
    }
  }, [url])
}



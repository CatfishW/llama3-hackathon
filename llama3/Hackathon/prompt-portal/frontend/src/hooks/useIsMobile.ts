import { useEffect, useState } from 'react'

/**
 * useIsMobile - simple responsive hook with resize + orientation listeners.
 * Default breakpoint: 768px.
 */
export function useIsMobile(breakpoint: number = 768): boolean {
  const [isMobile, setIsMobile] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false
    return window.innerWidth <= breakpoint || /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent)
  })
  useEffect(() => {
    function onResize() {
      setIsMobile(window.innerWidth <= breakpoint)
    }
    window.addEventListener('resize', onResize)
    window.addEventListener('orientationchange', onResize)
    return () => {
      window.removeEventListener('resize', onResize)
      window.removeEventListener('orientationchange', onResize)
    }
  }, [breakpoint])
  return isMobile
}

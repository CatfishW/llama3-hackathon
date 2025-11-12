import { useEffect, useRef } from 'react'

interface VoiceVisualizerProps {
  isActive: boolean
  frequency: number[]
  waveform?: Uint8Array
  style?: React.CSSProperties
  barCount?: number
  barColor?: string
  backgroundColor?: string
}

export const VoiceVisualizer = ({
  isActive,
  frequency,
  waveform,
  style,
  barCount = 16,
  barColor = '#60a5fa',
  backgroundColor = 'rgba(15, 23, 42, 0.35)'
}: VoiceVisualizerProps) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    
    const width = canvas.width
    const height = canvas.height
    
    // Clear canvas
    ctx.fillStyle = backgroundColor
    ctx.fillRect(0, 0, width, height)
    
    if (!isActive || frequency.length === 0) {
      return
    }
    
    // Draw frequency bars
    const barWidth = width / barCount
    const maxFrequency = Math.max(...frequency)
    
    frequency.slice(0, barCount).forEach((freq, i) => {
      const normalizedFreq = Math.min(freq / (maxFrequency || 1), 1)
      const barHeight = normalizedFreq * height
      const barX = (i * width) / barCount
      const barY = height - barHeight
      
      // Gradient effect
      const gradient = ctx.createLinearGradient(barX, barY, barX, height)
      gradient.addColorStop(0, barColor)
      gradient.addColorStop(1, barColor + '80')
      
      ctx.fillStyle = gradient
      ctx.fillRect(barX + 2, barY, barWidth - 4, barHeight)
    })
    
    // Draw waveform if available
    if (waveform && waveform.length > 0) {
      ctx.strokeStyle = barColor
      ctx.lineWidth = 2
      ctx.beginPath()
      
      const sampleCount = Math.min(waveform.length, width)
      for (let i = 0; i < sampleCount; i++) {
        const x = (i / sampleCount) * width
        const normalizedValue = (waveform[Math.floor((i / sampleCount) * waveform.length)] - 128) / 128
        const y = height / 2 + normalizedValue * (height / 2 - 5)
        
        if (i === 0) {
          ctx.moveTo(x, y)
        } else {
          ctx.lineTo(x, y)
        }
      }
      
      ctx.stroke()
    }
  }, [isActive, frequency, waveform, barCount, barColor, backgroundColor])
  
  return (
    <canvas
      ref={canvasRef}
      width={300}
      height={60}
      style={{
        borderRadius: '12px',
        border: `1px solid rgba(129,140,248,0.3)`,
        ...style
      }}
    />
  )
}

export default VoiceVisualizer

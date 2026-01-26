import React, { useRef, useEffect } from 'react'

interface Particle {
    x: number
    y: number
    vx: number
    vy: number
    life: number
    color: string
}

export function useParticles() {
    const canvasRef = useRef<HTMLCanvasElement>(null)
    const particles = useRef<Particle[]>([])
    const animationFrame = useRef<number>()

    const spawnParticles = (x: number, y: number, color: string = '#6366f1') => {
        for (let i = 0; i < 12; i++) {
            const angle = Math.random() * Math.PI * 2
            const speed = 1 + Math.random() * 3
            particles.current.push({
                x,
                y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                life: 1.0,
                color
            })
        }
        if (!animationFrame.current) {
            animate()
        }
    }

    const animate = () => {
        const canvas = canvasRef.current
        if (!canvas) return
        const ctx = canvas.getContext('2d')
        if (!ctx) return

        ctx.clearRect(0, 0, canvas.width, canvas.height)

        for (let i = particles.current.length - 1; i >= 0; i--) {
            const p = particles.current[i]
            p.x += p.vx
            p.y += p.vy
            p.life -= 0.02
            p.vy += 0.1 // gravity

            if (p.life <= 0) {
                particles.current.splice(i, 1)
                continue
            }

            ctx.globalAlpha = p.life
            ctx.fillStyle = p.color
            ctx.beginPath()
            ctx.arc(p.x, p.y, 2, 0, Math.PI * 2)
            ctx.fill()
        }

        if (particles.current.length > 0) {
            animationFrame.current = requestAnimationFrame(animate)
        } else {
            animationFrame.current = undefined
        }
    }

    useEffect(() => {
        const handleResize = () => {
            if (canvasRef.current) {
                canvasRef.current.width = window.innerWidth
                canvasRef.current.height = window.innerHeight
            }
        }
        handleResize()
        window.addEventListener('resize', handleResize)
        return () => {
            window.removeEventListener('resize', handleResize)
            if (animationFrame.current) cancelAnimationFrame(animationFrame.current)
        }
    }, [])

    return {
        canvasRef,
        spawnParticles
    }
}

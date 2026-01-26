import React, { useMemo } from 'react';
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

export const seededRandom = (seed: number) => {
  const x = Math.sin(seed) * 10000;
  return x - Math.floor(x);
};

export const NeuralBackground: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  
  const particles = useMemo(() => {
    return Array.from({ length: 50 }).map((_, i) => ({
      x: seededRandom(i * 10) * width,
      y: seededRandom(i * 20) * height,
      size: seededRandom(i * 30) * 4 + 1,
      speedX: (seededRandom(i * 40) - 0.5) * 2,
      speedY: (seededRandom(i * 50) - 0.5) * 2,
      color: i % 3 === 0 ? '#6366f1' : i % 3 === 1 ? '#06b6d4' : '#10b981',
    }));
  }, [width, height]);

  return (
    <div className="absolute inset-0 z-0">
      {particles.map((p, i) => {
        const x = (p.x + p.speedX * frame * 0.5 + width) % width;
        const y = (p.y + p.speedY * frame * 0.5 + height) % height;
        const opacity = interpolate(
          Math.sin(frame / 30 + i),
          [-1, 1],
          [0.1, 0.4]
        );

        return (
          <div
            key={i}
            className="absolute rounded-full blur-[1px]"
            style={{
              left: x,
              top: y,
              width: p.size,
              height: p.size,
              backgroundColor: p.color,
              opacity,
              boxShadow: `0 0 10px ${p.color}`,
            }}
          />
        );
      })}
      
      {/* Grid Overlay */}
      <div 
        className="absolute inset-0 opacity-[0.03]" 
        style={{
          backgroundImage: `linear-gradient(#6366f1 1px, transparent 1px), linear-gradient(90deg, #6366f1 1px, transparent 1px)`,
          backgroundSize: '100px 100px'
        }}
      />
    </div>
  );
};

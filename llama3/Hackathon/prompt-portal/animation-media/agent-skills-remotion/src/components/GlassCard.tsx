import React from 'react';

export const GlassCard: React.FC<{
  children: React.ReactNode;
  className?: string;
  glowColor?: string;
}> = ({ children, className = '', glowColor = 'rgba(99, 102, 241, 0.2)' }) => {
  return (
    <div 
      className={`relative overflow-hidden backdrop-blur-xl bg-slate-900/40 border border-white/10 rounded-[2rem] shadow-2xl ${className}`}
      style={{
        boxShadow: `0 20px 50px rgba(0,0,0,0.5), 0 0 40px ${glowColor}`,
      }}
    >
      {/* Inner Highlight Line */}
      <div className="absolute inset-0 pointer-events-none border border-white/5 rounded-[2rem]" />
      
      {/* Glass Reflection */}
      <div className="absolute -top-[50%] -left-[50%] w-[200%] h-[200%] bg-gradient-to-br from-white/5 to-transparent rotate-12 pointer-events-none" />
      
      <div className="relative z-10">
        {children}
      </div>
    </div>
  );
};

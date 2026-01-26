import React from 'react';
import { Series, Audio, AbsoluteFill, useVideoConfig, useCurrentFrame, interpolate, spring, staticFile } from 'remotion';
import { motion, AnimatePresence } from 'framer-motion';
import { SEGMENTS, Segment } from './Segments';
import { LucideIcon, Brain, Settings, Database, Code, FileText, Layers, Share2, Globe, Cpu, CheckCircle2 } from 'lucide-react';
import { NeuralBackground, seededRandom } from './components/NeuralBackground';
import { GlassCard } from './components/GlassCard';

const Scene: React.FC<{ segment: Segment; index: number }> = ({ segment, index }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  
  const opacity = interpolate(
    frame, 
    [0, 10, (segment.duration * 30) - 10, (segment.duration * 30)], 
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
  );
  
  return (
    <AbsoluteFill className="bg-[#05050a] text-white">
      <Audio src={staticFile(`audio/${segment.hash}.ogg`)} />
      
      <NeuralBackground />
      
      <div style={{ opacity }} className="relative w-full h-full flex flex-col items-center justify-center">
        <div className="z-10 w-full max-w-6xl flex flex-col items-center justify-center">
          <SceneContent index={index} segment={segment} frame={frame} />
        </div>

        {/* Subtitles - Glassmorphism style */}
        <div 
          className="absolute bottom-16 w-full flex justify-center px-32"
          style={{
            transform: `translateY(${interpolate(frame, [0, 10], [20, 0], { extrapolateRight: 'clamp' })}px)`,
            opacity: interpolate(frame, [0, 10], [0, 1], { extrapolateRight: 'clamp' })
          }}
        >
          <div className="bg-slate-900/60 backdrop-blur-2xl border border-white/10 px-10 py-5 rounded-3xl shadow-2xl max-w-4xl">
            <p className="text-3xl font-medium text-center leading-relaxed bg-clip-text text-transparent bg-gradient-to-b from-white to-indigo-200">
              {segment.text}
            </p>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

const SceneContent: React.FC<{ index: number; segment: Segment; frame: number }> = ({ index, segment, frame }) => {
  // Intro Scene
  if (index === 0) {
    return (
      <div className="text-center">
        <motion.div
          initial={{ scale: 0.8, opacity: 0, y: 20 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          transition={{ duration: 1, ease: "easeOut" }}
        >
          <h1 className="text-[12rem] font-black tracking-tighter mb-8 bg-clip-text text-transparent bg-gradient-to-r from-indigo-500 via-cyan-400 to-emerald-400 drop-shadow-[0_0_30px_rgba(99,102,241,0.5)]">
            AGENT SKILLS
          </h1>
        </motion.div>
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5, duration: 1 }}
        >
          <div className="h-1 w-64 bg-gradient-to-r from-indigo-500 to-emerald-500 mx-auto mb-8 rounded-full shadow-[0_0_20px_rgba(99,102,241,1)]" />
          <p className="text-4xl font-light text-indigo-200 tracking-[0.4em] uppercase opacity-70">
            Modular Intelligence Ecosystem
          </p>
        </motion.div>
      </div>
    );
  }

  // Formula Scene
  if (index === 1 || index === 2) {
    return (
      <div className="flex flex-col items-center gap-16 w-full">
        <div className="flex items-center gap-10 text-7xl font-bold italic tracking-tight">
          <GlassCard className="px-12 py-8" glowColor="rgba(56, 189, 248, 0.3)">
             <span className="text-cyan-400 drop-shadow-[0_0_15px_rgba(34,211,238,0.5)]">Intelligence</span>
          </GlassCard>
          
          <span className="text-white/30 text-8xl not-italic">=</span>
          
          <div className="flex flex-col gap-6">
            <motion.div 
              animate={index >= 2 ? { x: 0, opacity: 1, scale: 1 } : { x: -50, opacity: 0, scale: 0.9 }}
              transition={{ type: 'spring', damping: 15 }}
            >
              <GlassCard className="px-12 py-6" glowColor="rgba(16, 185, 129, 0.3)">
                <span className="text-emerald-400">Reasoning</span>
              </GlassCard>
            </motion.div>
            
            <motion.div 
              className="self-center text-5xl opacity-40"
              animate={index >= 2 ? { opacity: 0.6 } : { opacity: 0 }}
            >+</motion.div>

            <motion.div 
              animate={index >= 2 ? { x: 0, opacity: 1, scale: 1 } : { x: 50, opacity: 0, scale: 0.9 }}
              transition={{ type: 'spring', damping: 15, delay: 0.2 }}
            >
              <GlassCard className="px-12 py-6" glowColor="rgba(245, 158, 11, 0.3)">
                <span className="text-amber-400">Capability</span>
              </GlassCard>
            </motion.div>
          </div>
        </div>
      </div>
    );
  }

  // Anatomy / Container
  if (index >= 3 && index <= 7) {
    return (
      <div className="relative w-full max-w-5xl">
        <GlassCard className="p-16" glowColor="rgba(99,102,241,0.15)">
          <div className="absolute top-0 left-0 w-full h-1.5 bg-gradient-to-r from-transparent via-indigo-500 to-transparent" />
          
          <div className="flex justify-between items-center mb-16">
            <h2 className="text-4xl font-black tracking-widest text-indigo-300 uppercase">Skill Container</h2>
            <div className="px-6 py-2 rounded-full border border-indigo-500/30 bg-indigo-500/10 text-indigo-400 text-sm font-mono tracking-tighter">
              v2.4.0-STABLE
            </div>
          </div>

          <div className="grid grid-cols-3 gap-10">
            <SkillModule icon={Brain} title="Logic" color="emerald" delay={0.1} active={index >= 5} />
            <SkillModule icon={Settings} title="Tools" color="cyan" delay={0.2} active={index >= 5} />
            <SkillModule icon={Database} title="Data" color="amber" delay={0.3} active={index >= 5} />
          </div>

          <AnimatePresence>
            {index >= 6 && (
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="mt-16 pt-10 border-t border-white/5 flex items-center justify-around"
              >
                <div className="flex items-center gap-4 text-emerald-400/80">
                  <CheckCircle2 size={24} />
                  <span className="font-semibold tracking-wide">Self-Contained</span>
                </div>
                <div className="h-8 w-px bg-white/10" />
                <div className="flex items-center gap-4 text-cyan-400/80">
                  <CheckCircle2 size={24} />
                  <span className="font-semibold tracking-wide">Platform Agnostic</span>
                </div>
                <div className="h-8 w-px bg-white/10" />
                <div className="flex items-center gap-4 text-amber-400/80">
                  <CheckCircle2 size={24} />
                  <span className="font-semibold tracking-wide">Zero Overload</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </GlassCard>
      </div>
    );
  }

  // Blueprint Scene
  if (index >= 8 && index <= 12) {
    return (
      <div className="w-full max-w-4xl perspective-[2000px]">
        <motion.div
          initial={{ rotateY: -15, rotateX: 5, y: 20, opacity: 0 }}
          animate={{ rotateY: -5, rotateX: 2, y: 0, opacity: 1 }}
          transition={{ duration: 1 }}
          className="bg-[#0f0f1a]/95 border border-white/10 rounded-3xl shadow-[0_50px_100px_rgba(0,0,0,0.8)] overflow-hidden"
        >
          <div className="bg-[#1a1a2e] px-8 py-5 flex items-center justify-between border-b border-white/5">
            <div className="flex gap-3">
              <div className="w-4 h-4 rounded-full bg-[#ff5f56]" />
              <div className="w-4 h-4 rounded-full bg-[#ffbd2e]" />
              <div className="w-4 h-4 rounded-full bg-[#27c93f]" />
            </div>
            <div className="text-sm font-mono text-slate-400 flex items-center gap-3 bg-slate-800/50 px-4 py-1.5 rounded-lg">
              <FileText size={16} className="text-indigo-400" />
              SKILL.MD
            </div>
            <div className="w-12" />
          </div>
          <div className="p-12 font-mono text-2xl leading-[1.8]">
            <CodeLine label="1" indent={0} text="# Legal Researcher" color="text-rose-400 font-bold" active={index >= 10} />
            <CodeLine label="2" indent={0} text="" active={index >= 10} />
            <CodeLine label="3" indent={0} text="## Description" color="text-amber-400" active={index >= 10} />
            <CodeLine label="4" indent={1} text="Analyzes legal documents and precedents." color="text-slate-400" active={index >= 10} />
            <CodeLine label="5" indent={0} text="" active={index >= 11} />
            <CodeLine label="6" indent={0} text="## Tools" color="text-amber-400" active={index >= 11} />
            <CodeLine label="7" indent={1} text="- search_case_law(query)" color="text-emerald-400" active={index >= 11} />
            <CodeLine label="8" indent={1} text="- summarize_document(doc_id)" color="text-emerald-400" active={index >= 11} />
            <CodeLine label="9" indent={0} text="" active={index >= 12} />
            <CodeLine label="10" indent={0} text="## Context Rules" color="text-amber-400" active={index >= 12} />
            <CodeLine label="11" indent={1} text="Load only relevant jurisdiction data." color="text-cyan-400" active={index >= 12} />
          </div>
        </motion.div>
      </div>
    );
  }

  // Progressive Disclosure Scene
  if (index >= 13 && index <= 17) {
    return (
      <div className="relative w-full h-[700px] flex items-center justify-center">
        {/* Background Noise with deterministic distribution */}
        <div className="absolute inset-0 z-0">
          {Array.from({ length: 200 }).map((_, i) => {
             const seed = i * 137.5;
             const x = seededRandom(seed) * 100;
             const y = seededRandom(seed + 1) * 100;
             const isActive = index >= 15 && (x > 35 && x < 65 && y > 35 && y < 65);
             
             return (
               <motion.div 
                 key={i}
                 animate={{
                   opacity: isActive ? 1 : 0.1,
                   scale: isActive ? 1.5 : 1,
                   backgroundColor: isActive ? '#10b981' : '#334155'
                 }}
                 className="absolute w-1.5 h-1.5 rounded-full"
                 style={{ left: `${x}%`, top: `${y}%` }}
               />
             );
          })}
        </div>

        <motion.div 
          animate={{ scale: index >= 15 ? 1.1 : 1 }}
          className="relative z-10 flex flex-col items-center"
        >
          <div className={`w-64 h-64 rounded-full border-4 flex items-center justify-center transition-all duration-1000 ${index >= 15 ? 'border-emerald-500 bg-emerald-500/20 shadow-[0_0_100px_rgba(16,185,129,0.4)]' : 'border-rose-500/50 bg-rose-500/10'}`}>
             <motion.div
               animate={index >= 14 ? { rotate: [0, 10, -10, 0], scale: [1, 1.1, 1] } : {}}
               transition={{ repeat: Infinity, duration: 2 }}
             >
                {index >= 15 ? <Cpu size={120} className="text-emerald-400" /> : <Brain size={120} className="text-rose-400 opacity-50" />}
             </motion.div>
          </div>
          
          {index >= 15 && (
            <motion.div 
              initial={{ scale: 0, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="absolute -inset-16 border-[1px] border-emerald-500/30 rounded-full animate-[spin_20s_linear_infinite]"
            />
          )}
        </motion.div>

        {index >= 17 && (
          <motion.div 
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            className="absolute bottom-0 flex gap-12"
          >
            <StatBox label="Token Cost" value="-70%" color="emerald" />
            <StatBox label="Accuracy" value="+45%" color="emerald" />
            <StatBox label="Speed" value="3x" color="emerald" />
          </motion.div>
        )}
      </div>
    );
  }

  // Platform Interoperability Scene
  if (index >= 18 && index <= 20) {
    return (
      <div className="w-full flex flex-col items-center gap-32">
        <div className="grid grid-cols-4 gap-12 w-full">
          <PlatformCard icon={Code} title="VS Code" color="cyan" delay={0.1} />
          <PlatformCard icon={Cpu} title="CLI Tools" color="emerald" delay={0.2} />
          <PlatformCard icon={Share2} title="Social Bots" color="purple" delay={0.3} />
          <PlatformCard icon={Globe} title="Cloud APIs" color="amber" delay={0.4} />
        </div>
        
        <div className="relative">
           <motion.div 
             animate={{ rotate: 360 }}
             transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
             className="w-40 h-40 bg-indigo-500 rounded-[2.5rem] flex items-center justify-center shadow-[0_0_100px_rgba(99,102,241,0.6)] border-4 border-white/20"
           >
             <div className="font-black text-7xl text-white">S</div>
           </motion.div>
           
           {/* Dynamic Pulsing Connections */}
           <svg className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[1200px] h-[600px] -z-10 pointer-events-none overflow-visible">
             <ConnectionLine x1={600} y1={300} x2={150} y2={-50} color="#22d3ee" delay={0} />
             <ConnectionLine x1={600} y1={300} x2={450} y2={-50} color="#10b981" delay={0.5} />
             <ConnectionLine x1={600} y1={300} x2={750} y2={-50} color="#a855f7" delay={1} />
             <ConnectionLine x1={600} y1={300} x2={1050} y2={-50} color="#f59e0b" delay={1.5} />
           </svg>
        </div>
      </div>
    );
  }

  // Ecosystem / Finale
  return (
    <div className="text-center">
       <motion.div
         initial={{ scale: 0.9, opacity: 0 }}
         animate={{ scale: 1, opacity: 1 }}
         transition={{ duration: 1 }}
       >
         <h2 className="text-[10rem] font-black mb-12 bg-clip-text text-transparent bg-gradient-to-br from-indigo-400 via-cyan-400 to-emerald-400 drop-shadow-[0_0_40px_rgba(99,102,241,0.3)]">
           AgentSkills.io
         </h2>
         <div className="h-1.5 w-96 bg-gradient-to-r from-transparent via-indigo-500 to-transparent mx-auto mb-12" />
         <p className="text-5xl text-indigo-100/60 font-light max-w-4xl mx-auto leading-relaxed tracking-wide">
           Modular Intelligence. <br/> 
           <span className="text-white font-medium italic mt-4 block">The Next Generation Standard.</span>
         </p>
       </motion.div>
    </div>
  );
};

// Helper Components
const SkillModule: React.FC<{ icon: LucideIcon; title: string; color: string; delay: number; active: boolean }> = ({ icon: Icon, title, color, delay, active }) => {
  const colors: any = {
    emerald: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
    cyan: 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20',
    amber: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  };

  return (
    <motion.div
      initial={{ y: 30, opacity: 0 }}
      animate={active ? { y: 0, opacity: 1, scale: 1 } : { y: 30, opacity: 0.2, scale: 0.95 }}
      transition={{ delay, duration: 0.8, type: 'spring' }}
      className={`p-10 rounded-3xl border-2 flex flex-col items-center gap-8 ${active ? colors[color] : 'bg-slate-800/20 border-white/5 opacity-20'}`}
    >
      <div className={`w-24 h-24 rounded-2xl flex items-center justify-center ${active ? 'bg-white/10 shadow-inner' : ''}`}>
        <Icon size={56} strokeWidth={1.5} />
      </div>
      <h3 className="text-2xl font-black tracking-[0.2em] uppercase">{title}</h3>
    </motion.div>
  );
};

const CodeLine: React.FC<{ label: string; indent: number; text: string; color?: string; active: boolean }> = ({ label, indent, text, color = "text-slate-300", active }) => (
  <motion.div 
    animate={{ opacity: active ? 1 : 0.1, x: active ? 0 : -10 }}
    className="flex gap-10 hover:bg-white/5 transition-colors rounded-lg px-4"
  >
    <span className="text-slate-600 w-12 text-right select-none">{label}</span>
    <span className={`${color}`} style={{ paddingLeft: `${indent * 3}rem` }}>{text}</span>
  </motion.div>
);

const StatBox: React.FC<{ label: string; value: string; color: string }> = ({ label, value, color }) => (
  <GlassCard className="px-10 py-6 text-center" glowColor="rgba(16, 185, 129, 0.2)">
    <span className="text-sm uppercase tracking-[0.3em] text-slate-500 mb-2 block">{label}</span>
    <span className={`text-5xl font-black text-emerald-400`}>{value}</span>
  </GlassCard>
);

const PlatformCard: React.FC<{ icon: LucideIcon; title: string; color: string; delay: number }> = ({ icon: Icon, title, color, delay }) => {
  const colorMap: any = {
    cyan: 'text-cyan-400 border-cyan-500/30 bg-cyan-500/5',
    emerald: 'text-emerald-400 border-emerald-500/30 bg-emerald-500/5',
    purple: 'text-purple-400 border-purple-500/30 bg-purple-500/5',
    amber: 'text-amber-400 border-amber-500/30 bg-amber-500/5',
  };

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ delay, duration: 1 }}
      className="flex flex-col items-center gap-6"
    >
      <div className={`w-40 h-40 rounded-[2.5rem] border-2 flex items-center justify-center shadow-2xl backdrop-blur-md ${colorMap[color]}`}>
        <Icon size={72} strokeWidth={1} />
      </div>
      <span className="text-lg font-bold text-slate-400 tracking-[0.2em] uppercase">{title}</span>
    </motion.div>
  );
};

const ConnectionLine: React.FC<{ x1: number; y1: number; x2: number; y2: number; color: string; delay: number }> = ({ x1, y1, x2, y2, color, delay }) => {
  const frame = useCurrentFrame();
  const dashOffset = (frame * 5 + delay * 100) % 100;

  return (
    <g>
      <path 
        d={`M ${x1} ${y1} C ${x1} ${y1-100}, ${x2} ${y2+100}, ${x2} ${y2}`} 
        stroke={color} 
        strokeWidth="2" 
        fill="none" 
        opacity="0.1" 
      />
      <path 
        d={`M ${x1} ${y1} C ${x1} ${y1-100}, ${x2} ${y2+100}, ${x2} ${y2}`} 
        stroke={color} 
        strokeWidth="4" 
        fill="none" 
        strokeDasharray="10 90" 
        strokeDashoffset={-dashOffset}
        opacity="0.8"
      />
    </g>
  );
};

export const AgentSkillsComposition: React.FC = () => {
  return (
    <Series>
      {SEGMENTS.map((segment, i) => (
        <Series.Sequence key={i} durationInFrames={Math.ceil(segment.duration * 30)}>
          <Scene segment={segment} index={i} />
        </Series.Sequence>
      ))}
    </Series>
  );
};

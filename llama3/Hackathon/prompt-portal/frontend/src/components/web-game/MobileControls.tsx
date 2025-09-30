import React from 'react';

const mobileBtnStyle = () => ({
  width: 56,
  height: 56,
  borderRadius: 12,
  border: '1px solid rgba(255,255,255,0.25)',
  background: 'rgba(0,0,0,0.45)',
  color: '#fff',
  fontSize: 22,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 600,
  backdropFilter: 'blur(4px)',
  boxShadow: '0 4px 12px -2px rgba(0,0,0,0.5)',
  touchAction: 'none'
} as React.CSSProperties);

const mobileCenterBtnStyle = (active: boolean) => ({
  width: 56,
  height: 56,
  borderRadius: 28,
  border: '2px solid ' + (active ? '#4ade80' : 'rgba(255,255,255,0.35)'),
  background: active ? 'linear-gradient(135deg,#059669,#10b981)' : 'rgba(0,0,0,0.55)',
  color: '#fff',
  fontSize: 11,
  letterSpacing: '.5px',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 700,
  lineHeight: 1.1,
  padding: 4,
  textAlign: 'center',
  backdropFilter: 'blur(6px)',
  boxShadow: active ? '0 0 14px -2px rgba(16,185,129,0.7)' : '0 4px 12px -2px rgba(0,0,0,0.5)',
  touchAction: 'none'
} as React.CSSProperties);

const pillBtnStyle = (grad?: string) => ({
  minWidth: 120,
  padding: '12px 16px',
  borderRadius: 30,
  border: '1px solid rgba(255,255,255,0.25)',
  background: grad || 'rgba(0,0,0,0.55)',
  color: '#fff',
  fontSize: 14,
  fontWeight: 600,
  backdropFilter: 'blur(6px)',
  boxShadow: '0 4px 10px -2px rgba(0,0,0,0.5)',
  touchAction: 'none'
} as React.CSSProperties);

interface MobileControlsProps {
  isMobile: boolean;
  showControlsSettings: boolean;
  setShowControlsSettings: React.Dispatch<React.SetStateAction<boolean>>;
  mobileControlsOpacity: number;
  setMobileControlsOpacity: (opacity: number) => void;
  pressDir: (dir: 'up' | 'down' | 'left' | 'right') => void;
  releaseDir: (dir: 'up' | 'down' | 'left' | 'right') => void;
  autoPilot: boolean;
  setAutoPilot: React.Dispatch<React.SetStateAction<boolean>>;
  paused: boolean;
  setPaused: React.Dispatch<React.SetStateAction<boolean>>;
  startGame: () => void;
  showMiniMap: boolean;
  setShowMiniMap: React.Dispatch<React.SetStateAction<boolean>>;
  currentTheme: any;
}

const MobileControls: React.FC<MobileControlsProps> = ({
  isMobile,
  showControlsSettings,
  setShowControlsSettings,
  mobileControlsOpacity,
  setMobileControlsOpacity,
  pressDir,
  releaseDir,
  autoPilot,
  setAutoPilot,
  paused,
  setPaused,
  startGame,
  showMiniMap,
  setShowMiniMap,
  currentTheme
}) => {
  if (!isMobile) return null;

  return (
    <>
      <button
        aria-label="Control Settings"
        onClick={() => setShowControlsSettings(s => !s)}
        style={{ position: 'absolute', top: 8, left: 8, zIndex: 5, background: 'rgba(0,0,0,0.5)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)', borderRadius: 8, padding: '6px 10px', fontSize: 12, cursor: 'pointer' }}
      >⚙</button>
      {showControlsSettings && (
        <div style={{ position: 'absolute', top: 48, left: 8, zIndex: 5, background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(6px)', border: '1px solid rgba(255,255,255,0.25)', borderRadius: 12, padding: '10px 12px', width: 180, fontSize: 12, color: '#fff' }}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>Controls Opacity</div>
          <input
            aria-label="Mobile controls opacity"
            type="range"
            min={0.2}
            max={1}
            step={0.05}
            value={mobileControlsOpacity}
            onChange={e => setMobileControlsOpacity(parseFloat(e.target.value))}
            style={{ width: '100%' }}
          />
          <div style={{ textAlign: 'right', marginTop: 4 }}>{Math.round(mobileControlsOpacity * 100)}%</div>
          <button onClick={() => setShowControlsSettings(false)} style={{ marginTop: 8, width: '100%', background: 'rgba(255,255,255,0.15)', border: '1px solid rgba(255,255,255,0.3)', color: '#fff', padding: '4px 8px', borderRadius: 6, cursor: 'pointer' }}>Close</button>
        </div>
      )}
      <div style={{ position: 'absolute', left: 4, bottom: 4, right: 4, display: 'flex', justifyContent: 'space-between', gap: 12, pointerEvents: 'none', opacity: mobileControlsOpacity }}>
        {/* D-Pad */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,56px)', gridTemplateRows: 'repeat(3,56px)', gap: 4, opacity: 0.95, pointerEvents: 'auto' }}>
          <div></div>
          <button aria-label="Move Up" onPointerDown={() => pressDir('up')} onPointerUp={() => releaseDir('up')} onPointerLeave={() => releaseDir('up')} style={mobileBtnStyle()}>▲</button>
          <div></div>
          <button aria-label="Move Left" onPointerDown={() => pressDir('left')} onPointerUp={() => releaseDir('left')} onPointerLeave={() => releaseDir('left')} style={mobileBtnStyle()}>◀</button>
          <button aria-label="Auto Pilot" onClick={() => setAutoPilot(a => !a)} style={mobileCenterBtnStyle(autoPilot)}>{autoPilot ? 'AUTO' : 'MAN'}</button>
          <button aria-label="Move Right" onPointerDown={() => pressDir('right')} onPointerUp={() => releaseDir('right')} onPointerLeave={() => releaseDir('right')} style={mobileBtnStyle()}>▶</button>
          <div></div>
          <button aria-label="Move Down" onPointerDown={() => pressDir('down')} onPointerUp={() => releaseDir('down')} onPointerLeave={() => releaseDir('down')} style={mobileBtnStyle()}>▼</button>
          <div></div>
        </div>
        {/* Action Buttons */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, pointerEvents: 'auto' }}>
          <button onClick={() => setPaused(p => !p)} style={pillBtnStyle()}>{paused ? 'Resume' : 'Pause'}</button>
          <button onClick={() => startGame()} style={pillBtnStyle(currentTheme.buttonPrimary)}>Restart</button>
          <button onClick={() => setShowMiniMap(m => !m)} style={pillBtnStyle()}>{showMiniMap ? 'Hide Map' : 'Show Map'}</button>
        </div>
      </div>
      <div style={{ position: 'absolute', top: 8, right: 8, background: 'rgba(0,0,0,0.45)', color: '#fff', fontSize: 10, padding: '4px 8px', borderRadius: 12, pointerEvents: 'none', letterSpacing: .5 }}>
        Swipe inside board to move • Scroll outside to page
      </div>
    </>
  );
};

export default MobileControls;

import React from 'react';
import { LamFlowEvent } from './types';

interface LamFlowPanelProps {
  show: boolean;
  lamFlow: LamFlowEvent[];
  lamFlowPos: { x: number; y: number };
  lamFlowWidth: number;
  dragInfoRef: React.MutableRefObject<{ panel: string | null; offX: number; offY: number; startW?: number }>;
  setLamFlow: (flow: LamFlowEvent[]) => void;
  setShowLamFlowPanel: (show: boolean) => void;
}

const LamFlowPanel: React.FC<LamFlowPanelProps> = ({
  show,
  lamFlow,
  lamFlowPos,
  lamFlowWidth,
  dragInfoRef,
  setLamFlow,
  setShowLamFlowPanel,
}) => {
  if (!show) {
    return (
      <div style={{ position: 'fixed', left: 16, top: 16, zIndex: 40 }}>
        <button onClick={() => setShowLamFlowPanel(true)} style={{ background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(4px)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)', padding: '6px 12px', borderRadius: 8, fontSize: 12, cursor: 'pointer' }}>Show Flow</button>
      </div>
    );
  }

  return (
    <div
      style={{ position: 'fixed', left: lamFlowPos.x, top: lamFlowPos.y, width: lamFlowWidth, maxHeight: '70vh', overflow: 'auto', background: 'linear-gradient(160deg, rgba(10,20,30,0.85), rgba(40,15,55,0.8))', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.18)', borderRadius: 20, padding: 14, boxShadow: '0 10px 40px -8px rgba(0,0,0,0.55)', zIndex: 50, cursor: 'move' }}
      onMouseDown={e => { dragInfoRef.current.panel = 'flow'; dragInfoRef.current.offX = e.clientX - lamFlowPos.x; dragInfoRef.current.offY = e.clientY - lamFlowPos.y; }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
        <strong style={{ fontSize: 13, letterSpacing: '.5px' }}>LAM Prompt → Response Flow</strong>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => setLamFlow([])} style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', border: '1px solid rgba(255,255,255,0.25)', padding: '3px 8px', borderRadius: 6, cursor: 'pointer', fontSize: 10 }}>Clear</button>
          <button onClick={() => setShowLamFlowPanel(false)} style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', border: '1px solid rgba(255,255,255,0.25)', padding: '3px 8px', borderRadius: 6, cursor: 'pointer', fontSize: 10 }}>Hide</button>
        </div>
      </div>
      <div style={{ fontSize: 10, opacity: .7, marginBottom: 8 }}>Each state publish tracked until hint arrives; shows latency & action application timeline.</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {[...lamFlow].slice().reverse().map(evt => {
          const lat = evt.latencyMs != null ? `${evt.latencyMs.toFixed(0)} ms` : '—';
          return (
            <div key={evt.id} style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 12, padding: '8px 10px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                <div style={{ fontWeight: 600, fontSize: 11 }}>Publish #{evt.id}</div>
                <div style={{ fontSize: 10, opacity: .65 }}>{lat}</div>
              </div>
              <div style={{ fontSize: 10, lineHeight: 1.4 }}>
                <div><span style={{ opacity: .6 }}>Declared:</span> {evt.actionsDeclared.length ? evt.actionsDeclared.join(', ') : '—'}</div>
                <div><span style={{ opacity: .6 }}>Applied:</span> {evt.actionsApplied.length ? evt.actionsApplied.map(a => a.action).join(', ') : '—'}</div>
                <div><span style={{ opacity: .6 }}>Hint:</span> {evt.hintExcerpt || '—'}</div>
                {evt.error && <div style={{ color: '#ff9d9d' }}><span style={{ opacity: .6 }}>Error:</span> {evt.error}</div>}
              </div>
              {evt.actionsApplied.length > 0 && (
                <div style={{ marginTop: 6, display: 'grid', gap: 4 }}>
                  {evt.actionsApplied.map((a, i) => {
                    const dt = evt.receivedAt ? (a.at - evt.receivedAt) : 0;
                    return <div key={i} style={{ background: 'rgba(255,255,255,0.05)', padding: '3px 6px', borderRadius: 6, display: 'flex', justifyContent: 'space-between', fontSize: 10 }}>
                      <span style={{ fontFamily: 'monospace' }}>{a.action}</span>
                      <span style={{ opacity: .6 }}>{dt.toFixed(0)}ms</span>
                    </div>;
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
      <div
        style={{ position: 'absolute', right: 4, top: 0, bottom: 0, width: 10, cursor: 'ew-resize' }}
        onMouseDown={e => { e.stopPropagation(); dragInfoRef.current.panel = 'flow-resize'; dragInfoRef.current.offX = e.clientX; dragInfoRef.current.startW = lamFlowWidth; }}
      />
    </div>
  );
};

export default LamFlowPanel;

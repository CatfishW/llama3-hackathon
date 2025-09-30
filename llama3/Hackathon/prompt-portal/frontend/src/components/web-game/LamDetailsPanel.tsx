import React from 'react';
import { Vec2 } from './types';

interface LamDetailsPanelProps {
  show: boolean;
  lamDetailsPos: { x: number; y: number } | null;
  lamExpanded: boolean;
  lamData: {
    hint: string;
    path: Vec2[];
    breaks: number;
    error: string;
    raw: any;
    rawMessage: any;
    updatedAt: number;
    showPath: boolean;
  };
  autoPilot: boolean;
  dragInfoRef: React.MutableRefObject<{ panel: string | null; offX: number; offY: number; startW?: number }>;
  setLamExpanded: (expanded: boolean) => void;
  setShowLamDetails: (show: boolean) => void;
}

const LamDetailsPanel: React.FC<LamDetailsPanelProps> = ({
  show,
  lamDetailsPos,
  lamExpanded,
  lamData,
  autoPilot,
  dragInfoRef,
  setLamExpanded,
  setShowLamDetails,
}) => {
  if (!show || !lamDetailsPos) {
    return (
      <div style={{ position: 'fixed', left: 16, top: 16, zIndex: 40 }}>
        <button onClick={() => setShowLamDetails(true)} style={{ background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(4px)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)', padding: '6px 12px', borderRadius: 8, fontSize: 12, cursor: 'pointer' }}>Show LAM Output</button>
      </div>
    );
  }

  return (
    <div
      style={{ position: 'fixed', left: lamDetailsPos.x, top: lamDetailsPos.y, width: lamExpanded ? 460 : 320, maxHeight: '70vh', overflow: 'auto', background: 'linear-gradient(165deg, rgba(15,15,25,0.85) 0%, rgba(55,25,65,0.78) 100%)', backdropFilter: 'blur(10px)', border: '1px solid rgba(255,255,255,0.18)', borderRadius: 20, padding: 16, boxShadow: '0 10px 40px -8px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.05)', zIndex: 50, cursor: 'move' }}
      onMouseDown={e => { dragInfoRef.current.panel = 'details'; dragInfoRef.current.offX = e.clientX - lamDetailsPos.x; dragInfoRef.current.offY = e.clientY - lamDetailsPos.y; }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <strong style={{ fontSize: 15, letterSpacing: '.5px' }}>LAM Intelligence Output</strong>
        <div style={{ display: 'flex', gap: 6 }}>
          <button onClick={() => setLamExpanded(!lamExpanded)} style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)', padding: '4px 8px', borderRadius: 6, cursor: 'pointer', fontSize: 11 }}>{lamExpanded ? 'Collapse' : 'Expand'}</button>
          <button onClick={() => setShowLamDetails(false)} style={{ background: 'rgba(255,255,255,0.15)', color: '#fff', border: '1px solid rgba(255,255,255,0.3)', padding: '4px 8px', borderRadius: 6, cursor: 'pointer', fontSize: 11 }}>Hide</button>
        </div>
      </div>
      {lamData.error && <div style={{ background: 'linear-gradient(135deg, rgba(255,60,60,0.15), rgba(120,30,30,0.25))', border: '1px solid rgba(255,90,90,0.4)', padding: 8, borderRadius: 10, fontSize: 12, marginBottom: 10 }}><strong style={{ color: '#ffb3b3' }}>Error:</strong> {lamData.error}</div>}
      <div style={{ fontSize: 12, lineHeight: 1.5, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <section>
          <div style={{ fontWeight: 600, marginBottom: 4, letterSpacing: '.5px', fontSize: 12, opacity: .85 }}>Hint</div>
          <div style={{ whiteSpace: 'pre-wrap', background: 'rgba(255,255,255,0.06)', padding: 8, borderRadius: 10 }}>{lamData.hint || '—'}</div>
        </section>
        {lamData.showPath && (
          <section>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <div style={{ fontWeight: 600, letterSpacing: '.5px', opacity: .85 }}>Path <span style={{ opacity: .6 }}>({lamData.path.length})</span></div>
              {lamData.path.length > 0 && <div style={{ fontSize: 11, opacity: .7 }}>Next: ({lamData.path[0].x},{lamData.path[0].y})</div>}
            </div>
            <div style={{ fontFamily: 'monospace', fontSize: 11, maxHeight: lamExpanded ? 220 : 80, overflow: 'auto', padding: '6px 8px', background: 'rgba(255,255,255,0.07)', borderRadius: 8, lineHeight: 1.35 }}>
              {lamData.path.length ? lamData.path.map((p, i) => (i && i % 8 === 0 ? `\n(${p.x},${p.y})` : `(${p.x},${p.y})`)).join(' → ') : '—'}
            </div>
          </section>
        )}
        <section>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            <div style={{ background: 'rgba(255,255,255,0.08)', padding: '6px 10px', borderRadius: 20 }}><span style={{ opacity: .65 }}>Breaks</span>: {lamData.breaks}</div>
            <div style={{ background: 'rgba(255,255,255,0.08)', padding: '6px 10px', borderRadius: 20 }}><span style={{ opacity: .65 }}>Autopilot</span>: {autoPilot ? 'On' : 'Off'}</div>
            <div style={{ background: 'rgba(255,255,255,0.08)', padding: '6px 10px', borderRadius: 20 }}><span style={{ opacity: .65 }}>Updated</span>: {lamData.updatedAt ? `${((Date.now() - lamData.updatedAt) / 1000).toFixed(1)}s ago` : '—'}</div>
          </div>
        </section>
        <section>
          <div style={{ fontWeight: 600, marginBottom: 4, opacity: .85 }}>Detected Actions</div>
          {(() => {
            const r = lamData.raw || {};
            const keys: string[] = [];
            const push = (k: string, c: boolean) => { if (c) keys.push(k); };
            push('break_wall', !!r.break_wall);
            push('break_walls', Array.isArray(r.break_walls) && r.break_walls.length > 0);
            push('show_path', !!r.show_path);
            push('speed_boost', !!r.speed_boost_ms);
            push('slow_germs', !!r.slow_germs_ms);
            push('freeze_germs', !!r.freeze_germs_ms);
            push('teleport_player', !!r.teleport_player);
            push('spawn_oxygen', Array.isArray(r.spawn_oxygen) && r.spawn_oxygen.length > 0);
            push('move_exit', !!r.move_exit);
            push('highlight_zone', Array.isArray(r.highlight_zone) && r.highlight_zone.length > 0);
            push('toggle_autopilot', r.toggle_autopilot !== undefined);
            push('reveal_map', r.reveal_map !== undefined);
            return <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>{keys.length ? keys.map(k => <span key={k} style={{ background: 'linear-gradient(135deg,#433,#655)', padding: '4px 8px', borderRadius: 14, fontSize: 11 }}>{k}</span>) : <span style={{ opacity: .6 }}>None</span>}</div>;
          })()}
        </section>
        {lamExpanded && (
          <section>
            <div style={{ fontWeight: 600, marginBottom: 4, opacity: .85 }}>Raw Hint JSON</div>
            <pre style={{ margin: 0, fontSize: 11, lineHeight: 1.3, maxHeight: 200, overflow: 'auto', background: 'rgba(255,255,255,0.05)', padding: 8, border: '1px solid rgba(255,255,255,0.12)', borderRadius: 10 }}>{JSON.stringify(lamData.raw, null, 2)}</pre>
          </section>
        )}
        {lamExpanded && (
          <section>
            <div style={{ fontWeight: 600, marginBottom: 4, opacity: .85 }}>Raw Message Envelope</div>
            <pre style={{ margin: 0, fontSize: 11, lineHeight: 1.3, maxHeight: 200, overflow: 'auto', background: 'rgba(255,255,255,0.05)', padding: 8, border: '1px solid rgba(255,255,255,0.12)', borderRadius: 10 }}>{JSON.stringify(lamData.rawMessage, null, 2)}</pre>
          </section>
        )}
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={() => navigator.clipboard.writeText(JSON.stringify(lamData.raw, null, 2))} style={{ background: 'linear-gradient(45deg,#6366f1,#7c3aed)', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: 8, fontSize: 12, cursor: 'pointer' }}>Copy Hint JSON</button>
          {lamData.showPath && <button onClick={() => navigator.clipboard.writeText(JSON.stringify(lamData.path, null, 2))} style={{ background: 'linear-gradient(45deg,#0ea5e9,#2563eb)', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: 8, fontSize: 12, cursor: 'pointer' }}>Copy Path</button>}
          <button onClick={() => navigator.clipboard.writeText(JSON.stringify(lamData.rawMessage, null, 2))} style={{ background: 'linear-gradient(45deg,#64748b,#475569)', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: 8, fontSize: 12, cursor: 'pointer' }}>Copy Envelope</button>
        </div>
      </div>
    </div>
  );
};

export default LamDetailsPanel;

# Runtime Game State Display & Debug Panels

## 📺 Overview

This document covers **what happens AFTER the game starts and template is published**:
- How the game loop renders the maze
- The top control panel with template, session, connection info
- The left "LAM Prompt → Response Flow" debug panel
- The right "LAM Intelligence Output" debug panel
- How game state flows through the system during runtime
- How effects and actions are visualized

---

## 🎮 Game Loop Architecture

### Main Loop Structure (WebGame.tsx, Lines 1220-1380)

```tsx
useEffect(() => {
  if (!gameRunning) return
  
  let raf: number
  const now = performance.now()
  const stepMs = 16 // ~60fps
  
  const loop = () => {
    const now = performance.now()
    const s = stateRef.current
    
    // 1. Input handling (manual mode)
    if (gameMode === 'manual') {
      if (keysRef.current['ArrowUp'] || keysRef.current['w']) tryMove(0,-1)
      if (keysRef.current['ArrowDown'] || keysRef.current['s']) tryMove(0,1)
      if (keysRef.current['ArrowLeft'] || keysRef.current['a']) tryMove(-1,0)
      if (keysRef.current['ArrowRight'] || keysRef.current['d']) tryMove(1,0)
    }
    // 2. LAM mode: follow LAM path or BFS
    else if (gameMode === 'lam') {
      const speedActive = now < s.effects.speedBoostUntil
      let maxStepsThisTick = speedActive ? 2 : 1
      
      // Follow LAM-provided path
      for (let step=0; step<maxStepsThisTick; step++) {
        const path = (s.lam.path && s.lam.path.length) ? s.lam.path : []
        if (path.length <= 1) break
        const next = path[1]
        // Move along path...
      }
    }
    
    // 3. Physics & collisions
    // 4. Render
    draw()
    
    raf = requestAnimationFrame(loop)
  }
  
  raf = requestAnimationFrame(loop)
  return () => cancelAnimationFrame(raf)
}, [gameMode, boardCols, boardRows, germCount, publishState, width, height])
```

### Key State Variables
```tsx
const stateRef = useRef<GameState>({
  started: true,              // Game is running
  grid: generated,            // Maze grid [rows][cols]
  player: { x, y },           // Player position
  exit: { x, y },             // Exit position
  oxy: [...],                 // Oxygen pickup locations
  germs: [...],               // Germ positions and directions
  lam: {
    path: [],                 // Path from LAM
    bfsSteps: 0,              // BFS move count
  },
  effects: {
    speedBoostUntil: 0,       // Timestamp for speed boost
    freezeGermsUntil: 0,      // Timestamp for freeze
    slowGermsUntil: 0,        // Timestamp for slow
  },
  revealMap: false,           // Map reveal flag
  metrics: {
    visitedTiles,             // Set of visited tile keys
    backtrackCount: 0,
    actionLatencies: [],
    lastActionTime: 0,
  },
  wallBreakParts: [],         // Animation particles
  fxSparkles: [],             // Visual effects
  fxRings: [],
  fxBursts: [],
  cameraShake: 0,             // Shake magnitude
  // ... more
})
```

---

## 🎨 Top Control Panel

### Location & Structure
**File**: `frontend/src/pages/WebGame.tsx`, Lines 1825-1920

**HTML Structure**:
```
┌─────────────────────────────────────────────────────────────┐
│ Template | Session ID | Germs | MQTT Rate | Mode | Connection │
│ [Dropdown] | [Input] | [Number] | [Slider] | [Badge] | [Status] │
└─────────────────────────────────────────────────────────────┘
```

### Code: Template Selector

```tsx
<div>
  <label style={{ display: 'block', marginBottom: 6 }}>Template</label>
  <select 
    value={templateId ?? ''} 
    onChange={(e)=>setTemplateId(parseInt(e.target.value))} 
    style={{ 
      width:'100%', 
      padding:'8px', 
      borderRadius: 8, 
      background:'rgba(255,255,255,0.1)', 
      color:'#fff', 
      border:'1px solid rgba(255,255,255,0.3)',
    }}
  >
    <option value="" disabled>Select a template</option>
    {templates.map(t => (
      <option key={t.id} value={t.id} style={{ background:'#333' }}>
        {t.title.length > 30 ? t.title.substring(0, 30) + '...' : t.title}
      </option>
    ))}
  </select>
</div>
```

### Code: Session ID Control

```tsx
<div>
  <label style={{ display: 'block', marginBottom: 6 }}>Session ID</label>
  <div style={{ display:'flex', gap:8 }}>
    <input 
      value={sessionId} 
      onChange={(e)=>setSessionId(e.target.value)} 
      style={{ 
        flex:1, 
        padding:'8px', 
        borderRadius: 8, 
        background:'rgba(255,255,255,0.1)', 
        color:'#fff', 
        border:'1px solid rgba(255,255,255,0.3)' 
      }} 
    />
    <button 
      onClick={()=>setSessionId('session-' + Math.random().toString(36).slice(2,8))} 
      style={buttonStyle('secondary') as any}
    >
      New
    </button>
  </div>
</div>
```

### Code: Germs Counter

```tsx
<div>
  <label style={{ display: 'block', marginBottom: 6 }}>Germs</label>
  <input 
    type="number" 
    min={0} 
    max={20} 
    value={germCount} 
    onChange={(e)=>setGermCount(parseInt(e.target.value||'0'))} 
    style={{ 
      width:'100%', 
      padding:'8px', 
      borderRadius: 8, 
      background:'rgba(255,255,255,0.1)', 
      color:'#fff', 
      border:'1px solid rgba(255,255,255,0.3)' 
    }} 
  />
</div>
```

### Code: MQTT Send Rate Slider

```tsx
<div>
  <label style={{ display: 'block', marginBottom: 6 }}>MQTT Send Rate (ms)</label>
  <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
    <input 
      type="range" 
      min={500} 
      max={60000} 
      step={500} 
      value={mqttSendRate} 
      onChange={(e)=>setMqttSendRate(parseInt(e.target.value))}
      style={{ flex: 1 }}
    />
    <span style={{ 
      padding: '4px 10px', 
      borderRadius: 6, 
      background: 'rgba(255,255,255,0.1)', 
      fontSize: '12px', 
      minWidth: '60px', 
      textAlign: 'center' 
    }}>
      {mqttSendRate}ms
    </span>
  </div>
  <div style={{ fontSize: '11px', opacity: 0.7, marginTop: 4 }}>0.5s - 60s</div>
</div>
```

### Code: Mode Display

```tsx
<div>
  <label style={{ display: 'block', marginBottom: 6 }}>Mode</label>
  <div style={{ display:'flex', alignItems:'center', gap:8 }}>
    <div style={{ 
      padding: '6px 10px', 
      borderRadius: 20, 
      border:'1px solid rgba(255,255,255,0.3)', 
      background: 'rgba(0,0,0,0.25)' 
    }}>
      { (showTemplatePicker ? selectedMode : gameMode) === 'lam' 
        ? 'LAM Mode (no user control)' 
        : 'Manual Mode (user control + LAM hints)'}
    </div>
  </div>
</div>
```

### Code: Connection Status

```tsx
<div>
  <label style={{ display: 'block', marginBottom: 6 }}>Connection</label>
  <div style={{ display:'flex', alignItems:'center', gap:8 }}>
    <div style={{ 
      padding: '6px 10px', 
      borderRadius: 20, 
      border:'1px solid rgba(255,255,255,0.3)', 
      background: connected ? 'rgba(76,175,80,.3)' : 'rgba(255,107,107,.3)' 
    }}>
      {connected ? 'WebSocket Connected' : 'Disconnected'}
    </div>
    {!connected 
      ? <button style={buttonStyle('success')} onClick={connectWS}>Connect</button> 
      : <button style={buttonStyle('danger')} onClick={disconnectWS}>Disconnect</button>
    }
  </div>
</div>
```

### Code: Action Buttons

```tsx
<div style={{ 
  position:'sticky', 
  top: 0, 
  zIndex: 2, 
  background: 'transparent', 
  marginTop: 12, 
  display:'flex', 
  gap: 10, 
  flexWrap:'wrap', 
  alignItems: 'center', 
  justifyContent: 'flex-start'
}}>
  <button onClick={startGame} style={buttonStyle('primary')}>
    <i className="fas fa-play"/> Start Game
  </button>
  <button onClick={()=>publishState(true)} style={buttonStyle('secondary')}>
    Publish State
  </button>
  <button onClick={()=>startGame()} style={buttonStyle('restart')}>
    Restart
  </button>
  <button onClick={()=>navigate('/leaderboard')} style={buttonStyle('leaderboard')}>
    🏆 Leaderboard
  </button>
  <button onClick={()=>navigate('/dashboard')} style={buttonStyle('exit')}>
    Exit to Dashboard
  </button>
  <span style={{ opacity:.85, flexShrink: 0 }}>{status}</span>
</div>
```

---

## 🔍 Right Panel: "LAM Intelligence Output"

### Location & Structure
**File**: `frontend/src/pages/WebGame.tsx`, Lines 2050-2150

**Display Panel**:
```
┌─────────────────────────────┐
│ LAM Intelligence Output │ ⊟ ⊠
├─────────────────────────────┤
│ Hint                        │
│ [Hint text displayed here]  │
├─────────────────────────────┤
│ Path (N)                    │
│ (x0,y0)→(x1,y1)→(x2,y2)... │
├─────────────────────────────┤
│ Breaks: N  Mode: LAM  0.0s  │
├─────────────────────────────┤
│ Detected Actions            │
│ [action1] [action2] [...]   │
├─────────────────────────────┤
│ [Copy Hint JSON] [Envelope] │
└─────────────────────────────┘
```

### Code: Main Panel Container

```tsx
{showLamDetails && lamDetailsPos && (
  <div
    style={{ 
      position:'fixed', 
      left:lamDetailsPos.x, 
      top:lamDetailsPos.y, 
      width: lamExpanded? 460: 320, 
      maxHeight:'70vh', 
      overflow:'auto', 
      background:'linear-gradient(165deg, rgba(15,15,25,0.85) 0%, rgba(55,25,65,0.78) 100%)', 
      backdropFilter:'blur(10px)', 
      border:'1px solid rgba(255,255,255,0.18)', 
      borderRadius:20, 
      padding:16, 
      boxShadow:'0 10px 40px -8px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.05)', 
      zIndex:50, 
      cursor:'move' 
    }}
    onMouseDown={e=>{ 
      dragInfoRef.current.panel='details'
      dragInfoRef.current.offX = e.clientX - lamDetailsPos.x
      dragInfoRef.current.offY = e.clientY - lamDetailsPos.y 
    }}
  >
    {/* Header with controls */}
    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
      <strong style={{ fontSize:15, letterSpacing:'.5px' }}>LAM Intelligence Output</strong>
      <div style={{ display:'flex', gap:6 }}>
        <button 
          onClick={()=>setLamExpanded(e=>!e)} 
          style={{ 
            background:'rgba(255,255,255,0.15)', 
            color:'#fff', 
            border:'1px solid rgba(255,255,255,0.3)', 
            padding:'4px 8px', 
            borderRadius:6, 
            cursor:'pointer', 
            fontSize:11 
          }}
        >
          {lamExpanded? 'Collapse':'Expand'}
        </button>
        <button 
          onClick={()=>setShowLamDetails(false)} 
          style={{ 
            background:'rgba(255,255,255,0.15)', 
            color:'#fff', 
            border:'1px solid rgba(255,255,255,0.3)', 
            padding:'4px 8px', 
            borderRadius:6, 
            cursor:'pointer', 
            fontSize:11 
          }}
        >
          Hide
        </button>
      </div>
    </div>

    {/* Error display (if any) */}
    {lamData.error && (
      <div style={{ 
        background:'linear-gradient(135deg, rgba(255,60,60,0.15), rgba(120,30,30,0.25))', 
        border:'1px solid rgba(255,90,90,0.4)', 
        padding:8, 
        borderRadius:10, 
        fontSize:12, 
        marginBottom:10 
      }}>
        <strong style={{ color:'#ffb3b3' }}>Error:</strong> {lamData.error}
      </div>
    )}

    {/* Main content */}
    <div style={{ fontSize:12, lineHeight:1.5, display:'flex', flexDirection:'column', gap:10 }}>
      {/* Hint section */}
      <section>
        <div style={{ fontWeight:600, marginBottom:4, letterSpacing:'.5px', fontSize:12, opacity:.85 }}>
          Hint
        </div>
        <div style={{ whiteSpace:'pre-wrap', background:'rgba(255,255,255,0.06)', padding:8, borderRadius:10 }}>
          {lamData.hint || '—'}
        </div>
      </section>

      {/* Path display */}
      {lamData.showPath && (
        <section>
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:4 }}>
            <div style={{ fontWeight:600, letterSpacing:'.5px', opacity:.85 }}>
              Path <span style={{ opacity:.6 }}>({lamData.path.length})</span>
            </div>
            {lamData.path.length>0 && (
              <div style={{ fontSize:11, opacity:.7 }}>
                Next: ({lamData.path[0].x},{lamData.path[0].y})
              </div>
            )}
          </div>
          <div style={{ 
            fontFamily:'monospace', 
            fontSize:11, 
            maxHeight: lamExpanded? 220: 80, 
            overflow:'auto', 
            padding:'6px 8px', 
            background:'rgba(255,255,255,0.07)', 
            borderRadius:8, 
            lineHeight:1.35 
          }}>
            {lamData.path.length 
              ? lamData.path.map((p,i)=> 
                  (i && i%8===0? `\n(${p.x},${p.y})`:`(${p.x},${p.y})`)
                ).join(' → ') 
              : '—'
            }
          </div>
        </section>
      )}

      {/* Metrics */}
      <section>
        <div style={{ display:'flex', flexWrap:'wrap', gap:8 }}>
          <div style={{ background:'rgba(255,255,255,0.08)', padding:'6px 10px', borderRadius:20 }}>
            <span style={{ opacity:.65 }}>Breaks</span>: {lamData.breaks}
          </div>
          <div style={{ background:'rgba(255,255,255,0.08)', padding:'6px 10px', borderRadius:20 }}>
            <span style={{ opacity:.65 }}>Mode</span>: {gameMode==='lam'? 'LAM':'Manual'}
          </div>
          <div style={{ background:'rgba(255,255,255,0.08)', padding:'6px 10px', borderRadius:20 }}>
            <span style={{ opacity:.65 }}>Updated</span>: {
              lamData.updatedAt 
                ? `${((Date.now()-lamData.updatedAt)/1000).toFixed(1)}s ago`
                : '—'
            }
          </div>
        </div>
      </section>

      {/* Detected Actions */}
      <section>
        <div style={{ fontWeight:600, marginBottom:4, opacity:.85 }}>Detected Actions</div>
        {(() => {
          const r = lamData.raw || {}
          const keys: string[] = []
          const push = (k:string,c:boolean)=>{ if(c) keys.push(k) }
          push('break_wall', !!r.break_wall)
          push('break_walls', Array.isArray(r.break_walls) && r.break_walls.length>0)
          push('show_path', !!r.show_path)
          push('speed_boost', !!r.speed_boost_ms)
          push('slow_germs', !!r.slow_germs_ms)
          push('freeze_germs', !!r.freeze_germs_ms)
          push('teleport_player', !!r.teleport_player)
          push('spawn_oxygen', Array.isArray(r.spawn_oxygen) && r.spawn_oxygen.length>0)
          push('move_exit', !!r.move_exit)
          push('highlight_zone', Array.isArray(r.highlight_zone) && r.highlight_zone.length>0)
          push('toggle_autopilot', r.toggle_autopilot!==undefined)
          push('reveal_map', r.reveal_map!==undefined)
          
          return (
            <div style={{ display:'flex', flexWrap:'wrap', gap:6 }}>
              {keys.length 
                ? keys.map(k=> (
                    <span key={k} style={{ 
                      background:'linear-gradient(135deg,#433,#655)', 
                      padding:'4px 8px', 
                      borderRadius:14, 
                      fontSize:11 
                    }}>
                      {k}
                    </span>
                  )) 
                : <span style={{ opacity:.6 }}>None</span>
              }
            </div>
          )
        })()}
      </section>

      {/* Raw JSON (expanded only) */}
      {lamExpanded && (
        <section>
          <div style={{ fontWeight:600, marginBottom:4, opacity:.85 }}>Raw Hint JSON</div>
          <pre style={{ 
            margin:0, 
            fontSize:11, 
            lineHeight:1.3, 
            maxHeight:200, 
            overflow:'auto', 
            background:'rgba(255,255,255,0.05)', 
            padding:8, 
            border:'1px solid rgba(255,255,255,0.12)', 
            borderRadius:10 
          }}>
            {JSON.stringify(lamData.raw, null, 2)}
          </pre>
        </section>
      )}

      {/* Raw Envelope (expanded only) */}
      {lamExpanded && (
        <section>
          <div style={{ fontWeight:600, marginBottom:4, opacity:.85 }}>Raw Message Envelope</div>
          <pre style={{ 
            margin:0, 
            fontSize:11, 
            lineHeight:1.3, 
            maxHeight:200, 
            overflow:'auto', 
            background:'rgba(255,255,255,0.05)', 
            padding:8, 
            border:'1px solid rgba(255,255,255,0.12)', 
            borderRadius:10 
          }}>
            {JSON.stringify(lamData.rawMessage, null, 2)}
          </pre>
        </section>
      )}

      {/* Action buttons */}
      <div style={{ display:'flex', gap:8, flexWrap:'wrap' }}>
        <button 
          onClick={()=>navigator.clipboard.writeText(JSON.stringify(lamData.raw, null, 2))} 
          style={{ 
            background:'linear-gradient(45deg,#6366f1,#7c3aed)', 
            color:'#fff', 
            border:'none', 
            padding:'6px 12px', 
            borderRadius:8, 
            fontSize:12, 
            cursor:'pointer' 
          }}
        >
          Copy Hint JSON
        </button>
        {lamData.showPath && (
          <button 
            onClick={()=>navigator.clipboard.writeText(JSON.stringify(lamData.path, null, 2))} 
            style={{ 
              background:'linear-gradient(45deg,#0ea5e9,#2563eb)', 
              color:'#fff', 
              border:'none', 
              padding:'6px 12px', 
              borderRadius:8, 
              fontSize:12, 
              cursor:'pointer' 
            }}
          >
            Copy Path
          </button>
        )}
        <button 
          onClick={()=>navigator.clipboard.writeText(JSON.stringify(lamData.rawMessage, null, 2))} 
          style={{ 
            background:'linear-gradient(45deg,#64748b,#475569)', 
            color:'#fff', 
            border:'none', 
            padding:'6px 12px', 
            borderRadius:8, 
            fontSize:12, 
            cursor:'pointer' 
          }}
        >
          Copy Envelope
        </button>
      </div>
    </div>
  </div>
)}

{/* Show button when panel is hidden */}
{!showLamDetails && (
  <div style={{ position:'fixed', left:16, top:16, zIndex:40 }}>
    <button 
      onClick={()=>setShowLamDetails(true)} 
      style={{ 
        background:'rgba(0,0,0,0.55)', 
        backdropFilter:'blur(4px)', 
        color:'#fff', 
        border:'1px solid rgba(255,255,255,0.3)', 
        padding:'6px 12px', 
        borderRadius:8, 
        fontSize:12, 
        cursor:'pointer' 
      }}
    >
      Show LAM Output
    </button>
  </div>
)}
```

### LAM Data Structure

```tsx
interface LamData {
  hint: string                          // Hint text from LAM
  path: Array<{x: number, y: number}>   // Suggested path
  breaks: number                        // Wall breaks remaining
  showPath: boolean                     // Should show path
  updatedAt: number                     // Timestamp of last update
  error?: string                        // Error message if any
  raw: any                              // Raw LAM response JSON
  rawMessage: any                       // Full MQTT envelope
}
```

---

## 📊 Left Panel: "LAM Prompt → Response Flow"

### Location & Structure
**File**: `frontend/src/pages/WebGame.tsx`, Lines 2155-2220

**Display Panel**:
```
┌─────────────────────────────────────────┐
│ LAM Prompt → Response Flow │ [Clear][Hide]
├─────────────────────────────────────────┤
│ Publish #9                        38 ms │
│ Declared: show_path               [~]  │
│ Applied: show_path                     │
│ Hint: Path blocked by walls...         │
│                                        │
│ Publish #8                      2563 ms│
│ Declared: break_wall, move_exit  [~]  │
│ Applied: break_wall (1200ms)           │
│ Hint: Breaking obstacle...             │
└─────────────────────────────────────────┘
```

### Code: Flow Panel Container

```tsx
{showLamFlowPanel && (
  <div
    style={{ 
      position:'fixed', 
      left:lamFlowPos.x, 
      top:lamFlowPos.y, 
      width:lamFlowWidth, 
      maxHeight:'70vh', 
      overflow:'auto', 
      background:'linear-gradient(160deg, rgba(10,20,30,0.85), rgba(40,15,55,0.8))', 
      backdropFilter:'blur(10px)', 
      border:'1px solid rgba(255,255,255,0.18)', 
      borderRadius:20, 
      padding:14, 
      boxShadow:'0 10px 40px -8px rgba(0,0,0,0.55)', 
      zIndex:50, 
      cursor:'move' 
    }}
    onMouseDown={e=>{ 
      dragInfoRef.current.panel='flow'
      dragInfoRef.current.offX = e.clientX - lamFlowPos.x
      dragInfoRef.current.offY = e.clientY - lamFlowPos.y 
    }}
  >
    {/* Header */}
    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:6 }}>
      <strong style={{ fontSize:13, letterSpacing:'.5px' }}>LAM Prompt → Response Flow</strong>
      <div style={{ display:'flex', gap:6 }}>
        <button 
          onClick={()=>setLamFlow([])} 
          style={{ 
            background:'rgba(255,255,255,0.15)', 
            color:'#fff', 
            border:'1px solid rgba(255,255,255,0.25)', 
            padding:'3px 8px', 
            borderRadius:6, 
            cursor:'pointer', 
            fontSize:10 
          }}
        >
          Clear
        </button>
        <button 
          onClick={()=>setShowLamFlowPanel(false)} 
          style={{ 
            background:'rgba(255,255,255,0.15)', 
            color:'#fff', 
            border:'1px solid rgba(255,255,255,0.25)', 
            padding:'3px 8px', 
            borderRadius:6, 
            cursor:'pointer', 
            fontSize:10 
          }}
        >
          Hide
        </button>
      </div>
    </div>

    {/* Description */}
    <div style={{ fontSize:10, opacity:.7, marginBottom:8 }}>
      Each state publish tracked until hint arrives; shows latency & action application timeline.
    </div>

    {/* Flow items (reversed chronological order) */}
    <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
      {[...lamFlow].slice().reverse().map(evt => {
        const lat = evt.latencyMs!=null? `${evt.latencyMs.toFixed(0)} ms` : '—'
        return (
          <div key={evt.id} style={{ 
            background:'rgba(255,255,255,0.06)', 
            border:'1px solid rgba(255,255,255,0.12)', 
            borderRadius:12, 
            padding:'8px 10px' 
          }}>
            {/* Publish header */}
            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
              <div style={{ fontWeight:600, fontSize:11 }}>Publish #{evt.id}</div>
              <div style={{ fontSize:10, opacity:.65 }}>{lat}</div>
            </div>

            {/* Details */}
            <div style={{ fontSize:10, lineHeight:1.4 }}>
              <div>
                <span style={{ opacity:.6 }}>Declared:</span> {
                  evt.actionsDeclared.length 
                    ? evt.actionsDeclared.join(', ') 
                    : '—'
                }
              </div>
              <div>
                <span style={{ opacity:.6 }}>Applied:</span> {
                  evt.actionsApplied.length 
                    ? evt.actionsApplied.map(a=>a.action).join(', ') 
                    : '—'
                }
              </div>
              <div>
                <span style={{ opacity:.6 }}>Hint:</span> {evt.hintExcerpt || '—'}
              </div>
              {evt.error && (
                <div style={{ color:'#ff9d9d' }}>
                  <span style={{ opacity:.6 }}>Error:</span> {evt.error}
                </div>
              )}
            </div>

            {/* Applied actions timeline */}
            {evt.actionsApplied.length>0 && (
              <div style={{ marginTop:6, display:'grid', gap:4 }}>
                {evt.actionsApplied.map((a,i)=> {
                  const dt = evt.receivedAt? (a.at - evt.receivedAt) : 0
                  return (
                    <div 
                      key={i} 
                      style={{ 
                        background:'rgba(255,255,255,0.05)', 
                        padding:'3px 6px', 
                        borderRadius:6, 
                        display:'flex', 
                        justifyContent:'space-between', 
                        fontSize:10 
                      }}
                    >
                      <span style={{ fontFamily:'monospace' }}>{a.action}</span>
                      <span style={{ opacity:.6 }}>{dt.toFixed(0)}ms</span>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        )
      })}
    </div>

    {/* Resize handle */}
    <div
      style={{ position:'absolute', right:4, top:0, bottom:0, width:10, cursor:'ew-resize' }}
      onMouseDown={e=>{ 
        e.stopPropagation()
        dragInfoRef.current.panel='flow-resize'
        dragInfoRef.current.offX = e.clientX
        dragInfoRef.current.startW = lamFlowWidth 
      }}
    />
  </div>
)}
```

### Flow Event Structure

```tsx
interface LamFlowEvent {
  id: number                          // Publish event ID
  publishedAt: number                 // Timestamp when state was published
  receivedAt?: number                 // Timestamp when hint arrived
  latencyMs?: number                  // (receivedAt - publishedAt)
  actionsDeclared: string[]           // Actions in state payload
  actionsApplied: Array<{
    action: string
    at: number                        // When action was applied
  }>
  hintExcerpt?: string                // First line of hint
  error?: string                      // Any error during processing
}
```

---

## 🎮 Canvas Rendering

### Main Draw Function
**File**: `frontend/src/pages/WebGame.tsx`, Lines 1550-1730

The canvas renders the following layers (in order):

```tsx
function draw() {
  const canvas = canvasRef.current
  const ctx = canvas.getContext('2d')
  const s = stateRef.current
  
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  
  // 1. Camera shake transform
  if (s.cameraShake > 0) {
    ctx.save()
    const offX = (Math.random()*2-1)*s.cameraShake
    const offY = (Math.random()*2-1)*s.cameraShake
    ctx.translate(offX, offY)
  }
  
  // 2. Background effects
  drawVignette(ctx)                    // Dark vignette edges
  drawPlasma(ctx)                      // Animated plasma background
  
  // 3. Game world
  drawGrid(ctx, s)                     // Maze walls (red/dark)
  drawOxygen(ctx, s)                   // Oxygen pickups (cyan glow)
  drawGerms(ctx, s)                    // Enemy germs (green)
  drawPlayer(ctx, s)                   // Player avatar (blue dot)
  drawExit(ctx, s)                     // Exit indicator (yellow target)
  
  // 4. Visual effects
  drawWallBreakParticles(ctx, s)       // Debris from broken walls
  drawSparkles(ctx, s)                 // Sparkle effects
  drawRings(ctx, s)                    // Ring effects
  drawBursts(ctx, s)                   // Burst effects
  drawPopups(ctx, s)                   // "+100 O₂" text
  
  // 5. Active effects UI
  renderActiveEffects(ctx, s)          // Speed, Freeze, Slow labels
  
  // 6. Mini-map (optional)
  if (showMiniMap) drawMiniMap(ctx, s)
  
  // 7. Overlays
  if (s.hitFlash > 0) {
    ctx.fillStyle = `rgba(255,50,50,${(s.hitFlash*0.4).toFixed(2)})`
    ctx.fillRect(0, 0, width, height)  // Flash red on collision
  }
  
  // 8. Pause/Menu overlay
  if (paused || showMenu) {
    ctx.fillStyle = 'rgba(0,0,0,0.55)'
    ctx.fillRect(0, 0, width, height)
    ctx.fillStyle = '#fff'
    ctx.font = '20px Inter'
    ctx.fillText(paused ? 'Paused' : 'Menu', width/2 - 40, height/2 - 40)
  }
  
  // 9. Game over screen
  if (s.gameOver) {
    ctx.fillStyle = 'rgba(0,0,0,0.75)'
    ctx.fillRect(0, 0, width, height)
    ctx.fillStyle = '#fff'
    ctx.font = '32px Inter'
    const winText = s.win ? 'You Win!' : 'Game Over'
    ctx.fillText(winText, width/2 - ctx.measureText(winText).width/2, height/2 - 60)
    
    // Score
    ctx.font = '20px Inter'
    ctx.fillText(`Final Score: ${score}`, width/2 - ctx.measureText(`Final Score: ${score}`).width/2, height/2 - 20)
    
    // Stats
    ctx.font = '16px Inter'
    const statsText = `Oxygen: ${s.oxygenCollected} | Time: ${elapsed.toFixed(1)}s | Germs: ${s.germs.length}`
    ctx.fillText(statsText, width/2 - ctx.measureText(statsText).width/2, height/2 + 10)
    
    // Score submission status
    if (user && templateId) {
      ctx.font = '14px Inter'
      ctx.fillStyle = scoreSubmitted ? '#4ade80' : '#fbbf24'
      const statusText = scoreSubmitted ? 'Score submitted to leaderboard!' : 'Submitting score...'
      ctx.fillText(statusText, width/2 - ctx.measureText(statusText).width/2, height/2 + 40)
    } else if (!user) {
      ctx.font = '14px Inter'
      ctx.fillStyle = '#f87171'
      const loginText = 'Login to submit your score to leaderboard'
      ctx.fillText(loginText, width/2 - ctx.measureText(loginText).width/2, height/2 + 40)
    }
  }
  
  // 10. Start screen
  if (!s.started) {
    ctx.fillStyle = 'rgba(0,0,0,0.55)'
    ctx.fillRect(0, 0, width, height)
    ctx.fillStyle = '#fff'
    ctx.font = '24px Inter'
    ctx.fillText('Click Start Game to Begin', width/2 - 170, height/2)
  }
  
  // Restore after shake
  if (s.cameraShake > 0) ctx.restore()
}

raf = requestAnimationFrame(loop)
```

### Active Effects Display

```tsx
function renderActiveEffects(ctx: CanvasRenderingContext2D, s: GameState) {
  const now = performance.now()
  const effs: Array<{ label: string; color: string; remaining: number }> = []
  
  // Build effect list with remaining time
  const rSpeed = rem(s.effects.speedBoostUntil)
  if (rSpeed > 0.05) effs.push({ 
    label: `Speed ${rSpeed.toFixed(1)}s`, 
    color: '#f59e0b', 
    remaining: rSpeed 
  })
  
  const rFreeze = rem(s.effects.freezeGermsUntil)
  if (rFreeze > 0.05) effs.push({ 
    label: `Freeze ${rFreeze.toFixed(1)}s`, 
    color: '#60a5fa', 
    remaining: rFreeze 
  })
  
  const rSlow = rem(s.effects.slowGermsUntil)
  if (rSlow > 0.05) effs.push({ 
    label: `Slow ${rSlow.toFixed(1)}s`, 
    color: '#fbbf24', 
    remaining: rSlow 
  })
  
  if (s.revealMap) effs.push({ 
    label: 'Reveal', 
    color: '#a3e635', 
    remaining: 0 
  })
  
  // Render effect tags in top-left
  if (effs.length) {
    let x = 10, y = 40
    ctx.font = '12px Inter, system-ui, sans-serif'
    
    for (const e of effs) {
      const padX = 8, padY = 4
      const w = ctx.measureText(e.label).width + padX*2
      
      // Background
      ctx.fillStyle = 'rgba(0,0,0,0.45)'
      ctx.fillRect(x, y-12, w, 20)
      
      // Border
      ctx.strokeStyle = e.color
      ctx.lineWidth = 1
      ctx.strokeRect(x+0.5, y-11.5, w-1, 19)
      
      // Text
      ctx.fillStyle = e.color
      ctx.fillText(e.label, x+padX, y+2)
      
      x += w + 6
    }
  }
  
  const rem = (until: number) => Math.max(0, (until - performance.now())/1000)
}
```

---

## 🎯 Game State Updates During Runtime

### Oxygen Collection

```tsx
// When player moves onto oxygen tile
const idx = s.oxy.findIndex(o => o.x === s.player.x && o.y === s.player.y)
if (idx >= 0) {
  s.oxy.splice(idx, 1)                    // Remove oxygen
  s.oxygenCollected++                     // Increment counter
  
  // Visual feedback
  s.fxPopups.push({ 
    x: s.player.x, 
    y: s.player.y, 
    text: '+100 O₂', 
    t0: performance.now(), 
    ttl: 700 
  })
  
  s.emotion = 'happy'                     // Update emotion
}
```

### Germ Movement & Physics

```tsx
// Germs move randomly in maze
if (!freezeActive) {
  const allowStep = slowActive ? (s.germStepFlip = !s.germStepFlip) : true
  
  if (allowStep) {
    for (const g of s.germs) {
      // Random direction change
      if (Math.random() < 0.1) { 
        const dirs = [
          {x:1,y:0}, {x:-1,y:0}, 
          {x:0,y:1}, {x:0,y:-1}
        ]
        g.dir = dirs[randInt(4)] 
      }
      
      // Move germ
      const nx = clamp(g.pos.x + g.dir.x, 0, boardCols-1)
      const ny = clamp(g.pos.y + g.dir.y, 0, boardRows-1)
      
      if (s.grid[ny][nx] === 0) { 
        g.pos.x = nx
        g.pos.y = ny 
      } else { 
        // Hit wall, bounce
        g.dir.x *= -1
        g.dir.y *= -1 
      }
      
      // Detect collision with player
      if (g.pos.x === s.player.x && g.pos.y === s.player.y) {
        s.hitFlash = 1  // Red flash
      }
    }
  }
}
```

### Collision Detection

```tsx
// Germ collision with player = game over
if (s.germs.some(g => g.pos.x === s.player.x && g.pos.y === s.player.y)) {
  if (!s.gameOver) {
    s.gameOver = true
    s.win = false
    s.endTime = performance.now()
    const elapsedSec = (s.endTime - s.startTime)/1000
    
    // Compute final score
    const oxygenScore = s.oxygenCollected * 100
    const timePenalty = Math.round(elapsedSec * 5)
    s.finalScore = Math.max(0, Math.round(oxygenScore - timePenalty))
    
    setGameOverTrigger(prev => prev + 1)
  }
}

// Exit reached = win
if (s.player.x === s.exit.x && s.player.y === s.exit.y) {
  if (!s.gameOver) {
    s.gameOver = true
    s.win = true
    s.endTime = performance.now()
    const elapsedSec = (s.endTime - s.startTime)/1000
    
    // Compute final score with bonuses
    const oxygenScore = s.oxygenCollected * 100
    const timeBonus = Math.round(1500 / (1 + elapsedSec / 20))
    
    if (gameMode === 'lam') {
      const winBonus = 2500  // LAM gets huge bonus
      const germFactor = Math.min(1.5, 0.5 + s.germs.length / 10)
      s.finalScore = Math.max(0, Math.round((oxygenScore + winBonus + timeBonus) * 2.0 * germFactor))
    } else {
      const winBonus = 400  // Manual gets less bonus
      const germFactor = Math.max(0.5, 1 - (10 - s.germs.length) * 0.05)
      s.finalScore = Math.max(0, Math.round((oxygenScore + winBonus + timeBonus) * 0.7 * germFactor))
    }
    
    setGameOverTrigger(prev => prev + 1)
  }
}
```

---

## 🔄 Runtime Communication Flow

### Periodic State Publishing

```tsx
// Effect hook: publish state every N milliseconds
useEffect(() => {
  if (!gameRunning) return
  
  const interval = setInterval(() => {
    publishState(false)  // Don't force if nothing changed
  }, mqttSendRate)  // Default 3000ms
  
  return () => clearInterval(interval)
}, [gameRunning, mqttSendRate, publishState])
```

### State Publishing Function

```tsx
const publishState = useCallback(async (force = false) => {
  const s = stateRef.current
  if (!s.started) return
  
  // Get current state
  const gameState = {
    grid: s.grid,
    player: s.player,
    exit: s.exit,
    oxy: s.oxy,
    germs: s.germs,
    oxygenCollected: s.oxygenCollected,
    metrics: s.metrics,
    lam: s.lam,
    effects: s.effects,
  }
  
  // HTTP POST to backend
  try {
    const response = await api.post('/api/mqtt/publish_state', {
      session_id: sessionId,
      template_id: templateId,
      state: gameState
    })
    
    // Track in flow history
    const now = performance.now()
    setLamFlow(prev => [...prev, {
      id: ++flowIdRef.current,
      publishedAt: now,
      actionsDeclared: detectActions(gameState),
      actionsApplied: [],
      hintExcerpt: undefined,
      error: undefined
    }])
  } catch (err) {
    console.error('Publish error:', err)
  }
}, [sessionId, templateId])
```

---

## 📈 Metrics & Scoring

### Metrics Tracking

```tsx
interface GameMetrics {
  visitedTiles: Set<string>           // Tiles stepped on
  backtrackCount: number              // Times revisited a tile
  actionLatencies: number[]           // Move latencies (ms)
  lastActionTime: number              // Last move timestamp
  lastPosition: {x: number, y: number} // Previous position
  deadEndCount: number                // Dead ends entered
  collisionCount: number              // Germ collisions
  totalSteps: number                  // Movement count
  optimalSteps: number                // Shortest path length
}
```

### Score Calculation (Win)

**LAM Mode (2.0x multiplier)**:
```
oxygenScore = oxygenCollected * 100
timeBonus = 1500 / (1 + elapsed / 20)  // Capped at 1500
winBonus = 2500  // Fixed bonus
germFactor = min(1.5, 0.5 + germCount / 10)
finalScore = (oxygenScore + winBonus + timeBonus) * 2.0 * germFactor
```

**Manual Mode (0.7x multiplier)**:
```
oxygenScore = oxygenCollected * 100
timeBonus = 1500 / (1 + elapsed / 20)
winBonus = 400  # Lower bonus
germFactor = max(0.5, 1 - (10 - germCount) * 0.05)
finalScore = (oxygenScore + winBonus + timeBonus) * 0.7 * germFactor
```

### Score Calculation (Loss)

```
oxygenScore = oxygenCollected * 100
timePenalty = elapsed_seconds * 5
finalScore = max(0, oxygenScore - timePenalty)
```

---

## 📱 Mobile Controls

### Touch Input Handling

```tsx
// Touch movement for mobile
useEffect(() => {
  const handleTouchStart = (e: TouchEvent) => {
    if (gameMode !== 'manual') return
    
    const touch = e.touches[0]
    touchStartRef.current = { x: touch.clientX, y: touch.clientY }
  }
  
  const handleTouchEnd = (e: TouchEvent) => {
    if (!touchStartRef.current) return
    
    const touch = e.changedTouches[0]
    const dx = touch.clientX - touchStartRef.current.x
    const dy = touch.clientY - touchStartRef.current.y
    
    if (Math.abs(dx) > Math.abs(dy)) {
      tryMove(Math.sign(dx), 0)  // Horizontal swipe
    } else {
      tryMove(0, Math.sign(dy))  // Vertical swipe
    }
  }
  
  document.addEventListener('touchstart', handleTouchStart)
  document.addEventListener('touchend', handleTouchEnd)
  
  return () => {
    document.removeEventListener('touchstart', handleTouchStart)
    document.removeEventListener('touchend', handleTouchEnd)
  }
}, [gameMode])
```

---

## 🎨 Theme Configuration

### Available Themes

**Default (Purple)**:
```tsx
{
  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
  canvasBorder: 'rgba(255,255,255,0.15)',
  canvasBackground: 'rgba(0,0,0,0.25)',
  canvasShadow: '0 20px 60px rgba(220,38,38,0.25), inset 0 0 80px rgba(127,29,29,0.35)',
  buttonPrimary: 'linear-gradient(45deg,#4ecdc4,#44a08d)',
  buttonDanger: 'linear-gradient(45deg,#ff6b6b,#ee5a52)',
  buttonSuccess: 'linear-gradient(45deg,#4caf50,#45a049)',
  buttonSecondary: 'rgba(255,255,255,0.2)',
  leaderboardButton: 'linear-gradient(45deg,#fbbf24,#f59e0b)',
  restartButton: 'linear-gradient(45deg,#f59e0b,#ef4444)',
  exitButton: 'linear-gradient(45deg,#6366f1,#7c3aed)'
}
```

**Orange Sunset**:
```tsx
{
  background: 'linear-gradient(135deg, #ff9a56 0%, #ff6b35 50%, #f7931e 100%)',
  canvasBorder: 'rgba(255,255,255,0.2)',
  canvasBackground: 'rgba(139,69,19,0.2)',
  canvasShadow: '0 20px 60px rgba(255,140,0,0.25), inset 0 0 80px rgba(139,69,19,0.35)',
  buttonPrimary: 'linear-gradient(45deg,#ff8c42,#ff6b35)',
  buttonDanger: 'linear-gradient(45deg,#ff4757,#ff3742)',
  buttonSuccess: 'linear-gradient(45deg,#2ed573,#1e90ff)',
  buttonSecondary: 'rgba(255,255,255,0.25)',
  leaderboardButton: 'linear-gradient(45deg,#ffa726,#ff9800)',
  restartButton: 'linear-gradient(45deg,#ff7043,#ff5722)',
  exitButton: 'linear-gradient(45deg,#8e24aa,#7b1fa2)'
}
```

---

## 📋 Summary Table

| Component | Location | Purpose |
|-----------|----------|---------|
| Top Panel | Lines 1825-1920 | Template, Session, Mode, Connection info |
| Canvas Rendering | Lines 1550-1730 | Game world, effects, overlays |
| LAM Output Panel | Lines 2050-2150 | Current hint, path, actions, metrics |
| LAM Flow Panel | Lines 2155-2220 | Timeline of state publishes and responses |
| Game Loop | Lines 1220-1380 | Input, physics, scoring, state updates |
| Score Display | Lines 1680-1710 | Game over screen with final score |
| Effects UI | Lines 1600-1630 | Active speed/freeze/slow labels |

---

## 🔗 Related Files

- **Frontend**: `frontend/src/pages/WebGame.tsx` (2221 lines)
- **Backend**: `backend/app/mqtt_bridge.py` (HTTP endpoints)
- **Backend**: `backend/app/mqtt.py` (MQTT handlers)
- **Documentation**: `HINT_POLLING_LAM_RESPONSE_FLOW.md` (polling logic)
- **Documentation**: `COMPLETE_BACKEND_FLOW_SUMMARY.md` (full architecture)

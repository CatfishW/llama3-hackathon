# Game Startup Modals - Detailed Breakdown

## Screenshot 1: Step 1 of 2 - Choose Mode

### Visual Elements

```
┌─────────────────────────────────────────────────┐
│  Start Game                          Step 1 of 2 │
├─────────────────────────────────────────────────┤
│                                                   │
│  Choose Mode                                     │
│                                                   │
│  ┌──────────────────┐    ┌──────────────────┐   │
│  │ Manual Mode      │    │ LAM Mode         │   │
│  │ You move with    │    │ LLM controls     │   │
│  │ WASD/Arrows.     │    │ movement (user   │   │
│  │ LAM gives hints  │    │ input disabled). │   │
│  │ and can take     │    │ Higher scoring   │   │
│  │ actions.         │    │ on win.          │   │
│  └──────────────────┘    └──────────────────┘   │
│                                                   │
│                         Cancel      Next         │
└─────────────────────────────────────────────────┘
```

### State Variables Used
- `startStep === 'mode'`
- `selectedMode` ('manual' or 'lam')

### Code Location
**File**: `frontend/src/pages/WebGame.tsx`
**Lines**: 1912-1930

### JSX (Simplified)

```tsx
<div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.55)', display:'flex', alignItems:'center', justifyContent:'center', zIndex: 1000 }}>
  <div style={{ background:'linear-gradient(165deg, #1f2937, #0f172a)', color:'#fff', borderRadius:16, padding:20, width: 'min(92vw, 620px)', boxShadow:'0 20px 60px rgba(0,0,0,.45)', border:'1px solid rgba(255,255,255,0.08)' }}>
    {/* Header */}
    <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
      <h3 style={{ margin:0, fontSize:18, letterSpacing:.3 }}>Start Game</h3>
      <div style={{ fontSize:12, opacity:.8 }}>Step 1 of 2</div>
    </div>
    
    {/* Choose Mode */}
    <div style={{ fontWeight:600, marginBottom:8, opacity:.9 }}>Choose Mode</div>
    
    {/* Grid: Manual & LAM options */}
    <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))', gap:12 }}>
      {/* Manual Mode Option */}
      <div onClick={()=>setSelectedMode('manual')} style={{ 
        cursor:'pointer', 
        border:'1px solid '+(selectedMode==='manual'?'#22c55e66':'rgba(255,255,255,0.12)'), 
        borderRadius:12, 
        padding:12, 
        background: selectedMode==='manual'? 'linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05))':'rgba(255,255,255,0.04)' 
      }}>
        <div style={{ fontWeight:700, marginBottom:4 }}>Manual Mode</div>
        <div style={{ fontSize:13, opacity:.8 }}>You move with WASD/Arrows. LAM gives hints and can take actions.</div>
      </div>
      
      {/* LAM Mode Option */}
      <div onClick={()=>setSelectedMode('lam')} style={{ 
        cursor:'pointer', 
        border:'1px solid '+(selectedMode==='lam'?'#f59e0b66':'rgba(255,255,255,0.12)'), 
        borderRadius:12, 
        padding:12, 
        background: selectedMode==='lam'? 'linear-gradient(135deg, rgba(245,158,11,0.12), rgba(245,158,11,0.06))':'rgba(255,255,255,0.04)' 
      }}>
        <div style={{ fontWeight:700, marginBottom:4 }}>LAM Mode</div>
        <div style={{ fontSize:13, opacity:.8 }}>LLM controls movement (user input disabled). Higher scoring on win.</div>
      </div>
    </div>
    
    {/* Action Buttons */}
    <div style={{ display:'flex', justifyContent:'flex-end', gap:10, marginTop:16 }}>
      <button onClick={()=>{ setShowTemplatePicker(false) }} style={{ background:'transparent', border:'1px solid rgba(255,255,255,0.25)', color:'#fff', padding:'8px 14px', borderRadius:8 }}>Cancel</button>
      <button onClick={()=>setStartStep('template')} style={{ background:'linear-gradient(45deg,#6366f1,#7c3aed)', color:'#fff', border:'none', padding:'10px 16px', borderRadius:8, fontWeight:700 }}>Next</button>
    </div>
  </div>
</div>
```

---

## Screenshot 2: Step 2 of 2 - Select Template

### Visual Elements

```
┌─────────────────────────────────────────────────┐
│  Start Game                          Step 2 of 2 │
├─────────────────────────────────────────────────┤
│  Mode: LAM (LLM controls)                        │
│                                                   │
│  ┌─────────────────────────────────────────┐   │
│  │ ○ DRIVING                               │   │
│  ├─────────────────────────────────────────┤   │
│  │ ● SPARC DRIVING LLM AGENT PROMPT        │   │
│  │   driving                               │   │
│  ├─────────────────────────────────────────┤   │
│  │ ○ QwenGoodTemplate                      │   │
│  ├─────────────────────────────────────────┤   │
│  │ ○ TestBad                               │   │
│  ├─────────────────────────────────────────┤   │
│  │ ○ T                                     │   │
│  ├─────────────────────────────────────────┤   │
│  │ ○ Bad Template                          │   │
│  │   Bad Template TEST                     │   │
│  ├─────────────────────────────────────────┤   │
│  │ ○ ExampleTemplate                       │   │
│  └─────────────────────────────────────────┘   │
│                                                   │
│       Back              Cancel   Publish & Start │
└─────────────────────────────────────────────────┘
```

### State Variables Used
- `startStep === 'template'`
- `selectedMode` (from Step 1)
- `selectedTemplateId` (selected radio)
- `templates[]` (template list from context)

### Code Location
**File**: `frontend/src/pages/WebGame.tsx`
**Lines**: 1932-1980

### JSX (Simplified)

```tsx
<div>
  {/* Mode Display */}
  <div style={{ marginBottom:10, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
    <div style={{ fontSize:12, opacity:.8 }}>
      Mode: <strong>{selectedMode==='lam'? 'LAM (LLM controls)': 'Manual (You control)'}</strong>
    </div>
  </div>
  
  {/* Template List Container */}
  <div style={{ maxHeight:320, overflowY:'auto', border:'1px solid rgba(255,255,255,0.1)', borderRadius:10 }}>
    {templates.length === 0 ? (
      <div style={{ padding:16, opacity:.8 }}>
        No templates found. Please create one first.
      </div>
    ) : (
      <ul style={{ listStyle:'none', margin:0, padding:0 }}>
        {templates.map(t => (
          <li 
            key={t.id} 
            onClick={()=>setSelectedTemplateId(t.id)} 
            style={{ 
              padding:'10px 12px', 
              borderBottom:'1px solid rgba(255,255,255,0.08)', 
              display:'flex', 
              alignItems:'center', 
              gap:10, 
              cursor:'pointer', 
              background: selectedTemplateId===t.id? 'rgba(255,255,255,0.06)':'transparent' 
            }}>
            <input 
              type="radio" 
              name="tpl" 
              checked={selectedTemplateId===t.id} 
              onChange={()=>setSelectedTemplateId(t.id)} 
            />
            <div>
              <div style={{ fontWeight:700 }}>{t.title}</div>
              {t.description && <div style={{ opacity:.7, fontSize:'.9rem' }}>{t.description}</div>}
            </div>
          </li>
        ))}
      </ul>
    )}
  </div>
  
  {/* Action Buttons */}
  <div style={{ display:'flex', justifyContent:'space-between', gap:10, marginTop:14 }}>
    <div>
      <button onClick={()=>setStartStep('mode')} style={{ background:'transparent', border:'1px solid rgba(255,255,255,0.25)', color:'#fff', padding:'8px 14px', borderRadius:8 }}>Back</button>
    </div>
    <div style={{ display:'flex', gap:10 }}>
      <button onClick={()=>{ setShowTemplatePicker(false) }} style={{ background:'transparent', border:'1px solid rgba(255,255,255,0.25)', color:'#fff', padding:'8px 14px', borderRadius:8 }}>Cancel</button>
      <button
        disabled={!selectedTemplateId}
        onClick={()=>{
          if (!selectedTemplateId) return
          setTemplateId(selectedTemplateId)
          setShowTemplatePicker(false)
          const chosenMode = selectedMode
          setGameMode(chosenMode)
          publishSelectedTemplate(selectedTemplateId).finally(() => {
            const targetCols = (chosenMode === 'lam') ? 10 : 33
            const targetRows = (chosenMode === 'lam') ? 10 : 21
            doStartGame(targetCols, targetRows)
          })
        }}
        style={{ 
          background:'linear-gradient(45deg,#4ecdc4,#44a08d)', 
          color:'#fff', 
          border:'none', 
          padding:'10px 16px', 
          borderRadius:8, 
          fontWeight:700,
          opacity: !selectedTemplateId ? 0.5 : 1,
          cursor: !selectedTemplateId ? 'not-allowed' : 'pointer'
        }}>
        Publish & Start
      </button>
    </div>
  </div>
</div>
```

---

## 🔄 State Flow Diagram

```
┌─────────────────────────────────────┐
│     showTemplatePicker = true        │
│     startStep = 'mode'              │
│     selectedMode = null             │
└─────────────────────────────────────┘
              ↓ (User clicks mode)
┌─────────────────────────────────────┐
│  setSelectedMode('manual'|'lam')    │
│  (Green or Amber border highlights)  │
└─────────────────────────────────────┘
              ↓ (User clicks Next)
┌─────────────────────────────────────┐
│     startStep = 'template'          │
│     Show template list              │
│     Mode displayed in header         │
└─────────────────────────────────────┘
              ↓ (User selects template)
┌─────────────────────────────────────┐
│  setSelectedTemplateId(t.id)        │
│  (Radio checked, background highlight)
└─────────────────────────────────────┘
              ↓ (User clicks Publish & Start)
┌─────────────────────────────────────┐
│  1. Close modal                     │
│  2. setGameMode(chosenMode)         │
│  3. publishSelectedTemplate()       │
│  4. doStartGame(cols, rows)         │
│  5. Game starts!                    │
└─────────────────────────────────────┘
```

---

## 🎨 Styling Reference

### Modal Backdrop
```typescript
position: 'fixed'
inset: 0                              // top: 0, right: 0, bottom: 0, left: 0
background: 'rgba(0,0,0,0.55)'
display: 'flex'
alignItems: 'center'
justifyContent: 'center'
zIndex: 1000
```

### Modal Card
```typescript
background: 'linear-gradient(165deg, #1f2937, #0f172a)'
color: '#fff'
borderRadius: 16
padding: 20
width: 'min(92vw, 620px)'             // 92% on mobile, max 620px
boxShadow: '0 20px 60px rgba(0,0,0,.45)'
border: '1px solid rgba(255,255,255,0.08)'
```

### Mode Card (Unselected)
```typescript
cursor: 'pointer'
border: '1px solid rgba(255,255,255,0.12)'
borderRadius: 12
padding: 12
background: 'rgba(255,255,255,0.04)'
```

### Mode Card - Manual (Selected)
```typescript
border: '1px solid #22c55e66'          // Green
background: 'linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05))'
borderRadius: 12
padding: 12
```

### Mode Card - LAM (Selected)
```typescript
border: '1px solid #f59e0b66'          // Amber
background: 'linear-gradient(135deg, rgba(245,158,11,0.12), rgba(245,158,11,0.06))'
borderRadius: 12
padding: 12
```

### Template List Item (Unselected)
```typescript
padding: '10px 12px'
borderBottom: '1px solid rgba(255,255,255,0.08)'
display: 'flex'
alignItems: 'center'
gap: 10
cursor: 'pointer'
background: 'transparent'
```

### Template List Item (Selected)
```typescript
padding: '10px 12px'
borderBottom: '1px solid rgba(255,255,255,0.08)'
display: 'flex'
alignItems: 'center'
gap: 10
cursor: 'pointer'
background: 'rgba(255,255,255,0.06)'  // Subtle highlight
```

### Button - Next / Publish & Start
```typescript
background: 'linear-gradient(45deg,#4ecdc4,#44a08d)' // Cyan to Teal
color: '#fff'
border: 'none'
padding: '10px 16px'
borderRadius: 8
fontWeight: 700
cursor: 'pointer'
```

### Button - Cancel / Back
```typescript
background: 'transparent'
border: '1px solid rgba(255,255,255,0.25)'
color: '#fff'
padding: '8px 14px'
borderRadius: 8
cursor: 'pointer'
```

### Button - Disabled (Publish & Start)
```typescript
opacity: 0.5
cursor: 'not-allowed'
disabled: true
```

---

## 📋 Form Accessibility

### Radio Button Group
```tsx
<input 
  type="radio" 
  name="tpl"                           // Same name for group
  checked={selectedTemplateId===t.id}  // Checked state
  onChange={()=>setSelectedTemplateId(t.id)}
/>
```

### ARIA Labels
```tsx
<div 
  role="button"
  aria-label="Manual Mode"            // Screen reader label
  onClick={()=>setSelectedMode('manual')}
/>
```

---

## 🎯 Interaction Handlers

### Mode Selection Click
```typescript
onClick={()=>setSelectedMode('manual'|'lam')}
```

### Next Button
```typescript
onClick={()=>setStartStep('template')}
```

### Template Selection Click
```typescript
onClick={()=>setSelectedTemplateId(t.id)}
```

### Publish & Start Click
```typescript
onClick={()=>{
  if (!selectedTemplateId) return
  setTemplateId(selectedTemplateId)
  setShowTemplatePicker(false)
  const chosenMode = selectedMode
  setGameMode(chosenMode)
  publishSelectedTemplate(selectedTemplateId).finally(() => {
    const targetCols = (chosenMode === 'lam') ? 10 : 33
    const targetRows = (chosenMode === 'lam') ? 10 : 21
    doStartGame(targetCols, targetRows)
  })
}}
```

### Cancel Button
```typescript
onClick={()=>{ setShowTemplatePicker(false) }}
```

### Back Button
```typescript
onClick={()=>setStartStep('mode')}
```

---

## 📊 Data Structures

### Template Object (from context)
```typescript
type Template = {
  id: number
  title: string
  description?: string
  content: string
  is_active: boolean
  version: number
  created_at: string
  updated_at: string
  user_id: number
}
```

### Mode Type
```typescript
type GameMode = 'manual' | 'lam'
```

### Start Step Type
```typescript
type StartStep = 'mode' | 'template'
```

---

## 🚀 Key Implementation Points

1. **Two-Step Modal**: Uses `startStep` state to show/hide each section
2. **Selected Mode Indicator**: Shows which mode was selected in Step 2 header
3. **Template Scrolling**: Max height 320px with overflow auto for long template lists
4. **Radio Selection**: Native radio buttons with custom styling
5. **Disabled Submit**: "Publish & Start" disabled until template selected
6. **MQTT Publishing**: Template published before game starts
7. **Dynamic Dimensions**: Board size changes based on mode
8. **Color Coding**: Green for Manual, Amber for LAM for visual distinction

---

## 📱 Responsive Behavior

- Modal width: `min(92vw, 620px)` - adapts to screen size
- Mode cards: `gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))'` - responsive grid
- Template list: `maxHeight:320, overflowY:'auto'` - scrollable on mobile
- Action buttons: `display:'flex'` with wrapping for small screens


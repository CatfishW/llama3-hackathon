# Game Startup Modal - Code Snippets Reference

This document maps the game startup UI screens to the corresponding code snippets from the Prompt Portal.

---

## 📱 Overview

The game startup flow consists of **2 modals**:

1. **Step 1 of 2 - Choose Mode**: Manual Mode vs LAM Mode selection
2. **Step 2 of 2 - Select Template**: Choose a prompt template and start the game

Both modals are conditionally rendered based on `showTemplatePicker` state.

---

## 🎮 Modal Container & State Management

### File: `frontend/src/pages/WebGame.tsx`
**Lines**: 1-30

```typescript
export default function WebGame() {
  // State for template picker modal
  const [showTemplatePicker, setShowTemplatePicker] = useState(false)
  const [selectedTemplateId, setSelectedTemplateId] = useState<number | null>(null)
  
  // Game mode selection
  const [gameMode, setGameMode] = useState<'manual'|'lam'>('manual')
  const [selectedMode, setSelectedMode] = useState<'manual'|'lam'>('manual')
  const [startStep, setStartStep] = useState<'mode'|'template'>('mode')
  
  // Other state...
  const [templateId, setTemplateId] = useState<number | null>(null)
  const [sessionId, setSessionId] = useState('session-' + Math.random().toString(36).slice(2, 8))
  const [connected, setConnected] = useState(false)
  const [germCount, setGermCount] = useState(0)
```

---

## 📍 Start Game Button Handler

### File: `frontend/src/pages/WebGame.tsx`
**Lines**: ~1110-1125

Trigger function to open the modal:

```typescript
function startGame() {
  setSelectedMode(gameMode)        // Initialize with current game mode
  setSelectedTemplateId(templateId) // Initialize with current template
  setStartStep('mode')              // Reset to step 1
  setTimeout(() => setShowTemplatePicker(true), 0)
}
```

---

## 🎨 Full Modal JSX

### File: `frontend/src/pages/WebGame.tsx`
**Lines**: 1908-1980

### Outer Container (Backdrop)

```tsx
{showTemplatePicker && (
  <div style={{ 
    position:'fixed', 
    inset:0, 
    background:'rgba(0,0,0,0.55)', 
    display:'flex', 
    alignItems:'center', 
    justifyContent:'center', 
    zIndex: 1000 
  }}>
```

### Modal Card

```tsx
    <div style={{ 
      background:'linear-gradient(165deg, #1f2937, #0f172a)', 
      color:'#fff', 
      borderRadius:16, 
      padding:20, 
      width: 'min(92vw, 620px)', 
      boxShadow:'0 20px 60px rgba(0,0,0,.45)', 
      border:'1px solid rgba(255,255,255,0.08)' 
    }}>
```

### Header with Step Counter

```tsx
      <div style={{ 
        display:'flex', 
        justifyContent:'space-between', 
        alignItems:'center', 
        marginBottom:12 
      }}>
        <h3 style={{ margin:0, fontSize:18, letterSpacing:.3 }}>
          Start Game
        </h3>
        <div style={{ fontSize:12, opacity:.8 }}>
          Step {startStep==='mode'? '1':'2'} of 2
        </div>
      </div>
```

---

## 📋 STEP 1: Choose Mode

### Conditional Rendering

```tsx
{startStep === 'mode' ? (
  <div>
    <div style={{ fontWeight:600, marginBottom:8, opacity:.9 }}>
      Choose Mode
    </div>
```

### Mode Selection Grid

```tsx
    <div style={{ 
      display:'grid', 
      gridTemplateColumns:'repeat(auto-fit, minmax(220px, 1fr))', 
      gap:12 
    }}>
```

#### Manual Mode Card

```tsx
      <div 
        onClick={()=>setSelectedMode('manual')} 
        role="button" 
        aria-label="Manual Mode" 
        style={{ 
          cursor:'pointer', 
          border:'1px solid '+(selectedMode==='manual'?'#22c55e66':'rgba(255,255,255,0.12)'), 
          borderRadius:12, 
          padding:12, 
          background: selectedMode==='manual'? 
            'linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05))':
            'rgba(255,255,255,0.04)' 
        }}>
        <div style={{ fontWeight:700, marginBottom:4 }}>Manual Mode</div>
        <div style={{ fontSize:13, opacity:.8 }}>
          You move with WASD/Arrows. LAM gives hints and can take actions.
        </div>
      </div>
```

#### LAM Mode Card

```tsx
      <div 
        onClick={()=>setSelectedMode('lam')} 
        role="button" 
        aria-label="LAM Mode" 
        style={{ 
          cursor:'pointer', 
          border:'1px solid '+(selectedMode==='lam'?'#f59e0b66':'rgba(255,255,255,0.12)'), 
          borderRadius:12, 
          padding:12, 
          background: selectedMode==='lam'? 
            'linear-gradient(135deg, rgba(245,158,11,0.12), rgba(245,158,11,0.06))':
            'rgba(255,255,255,0.04)' 
        }}>
        <div style={{ fontWeight:700, marginBottom:4 }}>LAM Mode</div>
        <div style={{ fontSize:13, opacity:.8 }}>
          LLM controls movement (user input disabled). Higher scoring on win.
        </div>
      </div>
    </div>
```

#### Step 1 Action Buttons

```tsx
    <div style={{ 
      display:'flex', 
      justifyContent:'flex-end', 
      gap:10, 
      marginTop:16 
    }}>
      <button 
        onClick={()=>{ setShowTemplatePicker(false) }} 
        style={{ 
          background:'transparent', 
          border:'1px solid rgba(255,255,255,0.25)', 
          color:'#fff', 
          padding:'8px 14px', 
          borderRadius:8 
        }}>
        Cancel
      </button>
      <button 
        onClick={()=>setStartStep('template')} 
        style={{ 
          background:'linear-gradient(45deg,#6366f1,#7c3aed)', 
          color:'#fff', 
          border:'none', 
          padding:'10px 16px', 
          borderRadius:8, 
          fontWeight:700 
        }}>
        Next
      </button>
    </div>
  </div>
) : (
```

---

## 🎯 STEP 2: Select Template

### Step 2 Header

```tsx
  <div>
    <div style={{ marginBottom:10, display:'flex', justifyContent:'space-between', alignItems:'center' }}>
      <div style={{ fontSize:12, opacity:.8 }}>
        Mode: <strong>{selectedMode==='lam'? 'LAM (LLM controls)': 'Manual (You control)'}</strong>
      </div>
    </div>
```

### Template List Container

```tsx
    <div style={{ 
      maxHeight:320, 
      overflowY:'auto', 
      border:'1px solid rgba(255,255,255,0.1)', 
      borderRadius:10 
    }}>
```

#### Empty State

```tsx
      {templates.length === 0 ? (
        <div style={{ padding:16, opacity:.8 }}>
          No templates found. Please create one first.
        </div>
      ) : (
```

#### Template Radio List

```tsx
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
```

### Step 2 Action Buttons

```tsx
    <div style={{ 
      display:'flex', 
      justifyContent:'space-between', 
      gap:10, 
      marginTop:14 
    }}>
      <div>
        <button 
          onClick={()=>setStartStep('mode')} 
          style={{ 
            background:'transparent', 
            border:'1px solid rgba(255,255,255,0.25)', 
            color:'#fff', 
            padding:'8px 14px', 
            borderRadius:8 
          }}>
          Back
        </button>
      </div>
      <div style={{ display:'flex', gap:10 }}>
        <button 
          onClick={()=>{ setShowTemplatePicker(false) }} 
          style={{ 
            background:'transparent', 
            border:'1px solid rgba(255,255,255,0.25)', 
            color:'#fff', 
            padding:'8px 14px', 
            borderRadius:8 
          }}>
          Cancel
        </button>
```

#### Publish & Start Button

```tsx
        <button
          disabled={!selectedTemplateId}
          onClick={()=>{
            if (!selectedTemplateId) return
            setTemplateId(selectedTemplateId)
            setShowTemplatePicker(false)
            
            // Apply mode first, then publish and start
            const chosenMode = selectedMode
            setGameMode(chosenMode)
            
            publishSelectedTemplate(selectedTemplateId).finally(() => {
              const targetCols = (chosenMode === 'lam') ? 10 : 33
              const targetRows = (chosenMode === 'lam') ? 10 : 21
              // Pass mode explicitly to ensure it's used
              doStartGame(targetCols, targetRows)
            })
          }}
          style={{ 
            background:'linear-gradient(45deg,#4ecdc4,#44a08d)', 
            color:'#fff', 
            border:'none', 
            padding:'10px 16px', 
            borderRadius:8, 
            fontWeight:700 
          }}>
          Publish & Start
        </button>
      </div>
    </div>
  </div>
)}
```

---

## 🔌 Key Handler Functions

### Publish Selected Template

**File**: `frontend/src/pages/WebGame.tsx`
**Purpose**: Publishes the selected template via MQTT to the backend

```typescript
async function publishSelectedTemplate(templateId: number) {
  // Retrieves template content and publishes to MQTT
  // Sets up LAM integration
}
```

### Do Start Game

**File**: `frontend/src/pages/WebGame.tsx`
**Purpose**: Initializes game with chosen dimensions

```typescript
function doStartGame(cols: number, rows: number) {
  // Generates maze with specified dimensions
  // For LAM mode: 10x10
  // For Manual mode: 33x21
  // Starts game loop
}
```

---

## 📊 Mode-Based Dimensions

| Mode | Columns | Rows | Purpose |
|------|---------|------|---------|
| **Manual** | 33 | 21 | Larger maze for player exploration |
| **LAM** | 10 | 10 | Smaller maze for LLM navigation |

Implementation:
```typescript
const targetCols = (chosenMode === 'lam') ? 10 : 33
const targetRows = (chosenMode === 'lam') ? 10 : 21
```

---

## 🎨 Color Scheme

### Mode Selection Borders & Backgrounds

**Manual Mode (Green)**
- Selected Border: `#22c55e66` (green with alpha)
- Selected Background: `linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05))`
- Unselected: `rgba(255,255,255,0.04)`

**LAM Mode (Amber/Orange)**
- Selected Border: `#f59e0b66` (amber with alpha)
- Selected Background: `linear-gradient(135deg, rgba(245,158,11,0.12), rgba(245,158,11,0.06))`
- Unselected: `rgba(255,255,255,0.04)`

### Buttons

**Next Button**: `linear-gradient(45deg,#6366f1,#7c3aed)` (Indigo to Purple)

**Publish & Start Button**: `linear-gradient(45deg,#4ecdc4,#44a08d)` (Cyan to Teal)

**Cancel/Back Buttons**: Transparent with `rgba(255,255,255,0.25)` border

---

## 🔗 Related State Management

### Template Context

**File**: `frontend/src/contexts/TemplateContext.tsx`

Provides:
- `templates`: Array of available templates
- `loading`: Loading state
- `refreshTemplates()`: Fetches templates from API

```typescript
const { templates, loading: templatesLoading } = useTemplates()
```

### Authentication Context

**File**: `frontend/src/auth/AuthContext.tsx`

Provides:
- `user`: Current authenticated user
- `user.email`: User email address

```typescript
const { user } = useAuth()
```

---

## 📈 Game Flow

```
1. User clicks "Start Game" button
   ↓
2. Modal opens with startStep='mode'
   ↓
3. User selects Manual or LAM mode
   ↓
4. Click "Next" → startStep='template'
   ↓
5. User selects a template from list
   ↓
6. Click "Publish & Start"
   ↓
7. Template published to MQTT
   ↓
8. Game board initialized with:
   - selectedMode dimensions
   - selectedTemplateId content
   ↓
9. Game starts!
```

---

## 🎮 Gameplay Differences by Mode

### Manual Mode
- **Board Size**: 33×21 (larger)
- **User Input**: ✓ Full control (WASD/Arrow keys)
- **LLM Role**: Advisory (hints only)
- **Score Multiplier**: 1.0x
- **Description**: "You move with WASD/Arrows. LAM gives hints and can take actions."

### LAM Mode
- **Board Size**: 10×10 (smaller)
- **User Input**: ✗ Disabled (ignored)
- **LLM Role**: Full control
- **Score Multiplier**: 1.5x (bonus)
- **Description**: "LLM controls movement (user input disabled). Higher scoring on win."

---

## 🚀 Styling Patterns

### Glass Morphism Container
```typescript
background:'linear-gradient(165deg, #1f2937, #0f172a)'
border:'1px solid rgba(255,255,255,0.08)'
boxShadow:'0 20px 60px rgba(0,0,0,.45)'
borderRadius:16
```

### Interactive Card (Unselected)
```typescript
background: 'rgba(255,255,255,0.04)'
border: '1px solid rgba(255,255,255,0.12)'
borderRadius: 12
padding: 12
cursor: 'pointer'
```

### Interactive Card (Selected - Green)
```typescript
background: 'linear-gradient(135deg, rgba(34,197,94,0.1), rgba(34,197,94,0.05))'
border: '1px solid #22c55e66'
borderRadius: 12
padding: 12
```

---

## ⚡ Key Features

✅ **Two-Step Process**: Ensures users select mode before template

✅ **Visual Feedback**: Selected options have distinct border colors and gradients

✅ **Description Hints**: Each mode has clear explanation of what to expect

✅ **Keyboard Accessible**: Radio buttons for standard form interaction

✅ **Mobile Responsive**: `min(92vw, 620px)` width adapts to screen size

✅ **Disabled State**: "Publish & Start" disabled until template selected

✅ **Mode Display**: Selected mode always shown on Step 2 header

✅ **MQTT Integration**: Template published to backend on start

✅ **Dynamic Dimensions**: Game board size varies by mode

---

## 📝 Template Selection Data Flow

```
templates array (from context)
    ↓
    ├→ Mapped to radio list items
    ├→ Each template shows: title + description
    ├→ Click handler: setSelectedTemplateId(t.id)
    ↓
selectedTemplateId state
    ↓
    ├→ Radio checked state: checked={selectedTemplateId===t.id}
    ├→ Background highlight: background: selectedTemplateId===t.id? '...' : '...'
    ↓
Button disabled check: disabled={!selectedTemplateId}
    ↓
On "Publish & Start": 
    setTemplateId(selectedTemplateId)
    publishSelectedTemplate(selectedTemplateId)
    doStartGame(cols, rows)
```


# Prompt Portal UI - Code Snippets Reference

This document maps the UI interface shown in the screenshot to the corresponding code snippets across the frontend and backend.

---

## 🎨 UI Layout Overview

The screenshot shows three main sections:
1. **Left Panel**: "Manage Templates" card (Dashboard)
2. **Center Panel**: "Create New Template" form
3. **Right Panel**: "Active Template" status/save button

---

## 📍 Left Panel: Manage Templates Card

### Location
- **File**: `frontend/src/pages/Dashboard.tsx`
- **Lines**: 77-101

### Code Snippet
```tsx
<Link to="/templates" style={{ textDecoration: 'none', color: 'inherit' }}>
  <div 
    style={cardStyle}
    onMouseOver={(e) => {
      e.currentTarget.style.transform = 'translateY(-5px)'
      e.currentTarget.style.boxShadow = '0 10px 30px rgba(0,0,0,0.2)'
    }}
    onMouseOut={(e) => {
      e.currentTarget.style.transform = 'translateY(0)'
      e.currentTarget.style.boxShadow = 'none'
    }}
  >
    <i className="fas fa-file-code" style={{ ...iconStyle, fontSize: isMobile ? '2.4rem' : '3rem' }}></i>
    <h3 style={{ fontSize: isMobile ? '1.3rem':'1.5rem', marginBottom: '15px', fontWeight: '600' }}>
      Manage Templates
    </h3>
    <p style={{ opacity: '0.8', lineHeight: 1.5, marginBottom: '20px', fontSize: isMobile ? '.95rem':'1rem' }}>
      Create, edit, and organize your prompt templates. Design intelligent prompts 
      that guide AI agents through complex maze challenges.
    </p>
    <span style={buttonStyle}>
      <i className="fas fa-plus"></i>
      Create New Template
    </span>
  </div>
</Link>
```

### Key Features
- Glassmorphism styling: `backdrop-filter: blur(10px)`
- Hover effect with Y-axis translation
- Links to `/templates` route
- Font Awesome icons for visual appeal

---

## 🎯 Center Panel: Template Form

### Entry Point
- **File**: `frontend/src/pages/NewTemplate.tsx`
- **Form Component**: `frontend/src/components/TemplateForm.tsx`

### NewTemplate Page (Container)
- **File**: `frontend/src/pages/NewTemplate.tsx`
- **Lines**: Full file

```tsx
export default function NewTemplate() {
  const nav = useNavigate()
  const isMobile = useIsMobile()
  const { addTemplate } = useTemplates()
  
  async function onSubmit(data: any) {
    const res = await templatesAPI.createTemplate(data)
    addTemplate(res.data)
    nav('/templates')
  }

  return (
    <div style={containerStyle}>
      <div style={headerStyle}>
        <h1 style={titleStyle}>
          <i className="fas fa-magic" style={{ marginRight: '15px', color: '#4ecdc4' }}></i>
          Create New Template
        </h1>
        <p style={subtitleStyle}>
          Design powerful prompt templates for Large Action Models in maze environments
        </p>
      </div>
      <TemplateForm onSubmit={onSubmit} />
    </div>
  )
}
```

### Form Component Structure

#### Field 1: Template Title Input
- **File**: `frontend/src/components/TemplateForm.tsx`
- **Lines**: 241-258

```tsx
<div style={fieldGroupStyle}>
  <label style={labelStyle}>
    <i className="fas fa-tag"></i>
    Template Title
  </label>
  <input 
    value={title} 
    onChange={e => setTitle(e.target.value)} 
    required 
    style={inputStyle}
    placeholder="Enter a descriptive title for your template"
    onFocus={(e) => {
      e.target.style.borderColor = 'rgba(78, 205, 196, 0.6)'
      e.target.style.boxShadow = '0 0 0 3px rgba(78, 205, 196, 0.2)'
    }}
    onBlur={(e) => {
      e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)'
      e.target.style.boxShadow = 'none'
    }}
  />
</div>
```

#### Field 2: Description Textarea
- **File**: `frontend/src/components/TemplateForm.tsx`
- **Lines**: 260-280

```tsx
<div style={fieldGroupStyle}>
  <label style={labelStyle}>
    <i className="fas fa-align-left"></i>
    Description
  </label>
  <textarea 
    value={description} 
    onChange={e => setDescription(e.target.value)} 
    rows={3} 
    style={textareaStyle}
    placeholder="Briefly describe what this template does and when to use it"
    onFocus={(e) => {
      e.target.style.borderColor = 'rgba(78, 205, 196, 0.6)'
      e.target.style.boxShadow = '0 0 0 3px rgba(78, 205, 196, 0.2)'
    }}
    onBlur={(e) => {
      e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)'
      e.target.style.boxShadow = 'none'
    }}
  />
</div>
```

#### Field 3: Prompt Template (Large Textarea)
- **File**: `frontend/src/components/TemplateForm.tsx`
- **Lines**: 282-330

```tsx
<div style={fieldGroupStyle}>
  <label style={labelStyle}>
    <i className="fas fa-code"></i>
    Prompt Template
  </label>
  <textarea 
    value={content} 
    onChange={e => setContent(e.target.value)} 
    rows={12} 
    style={promptTextareaStyle}
    placeholder={placeholderText}
    required
    onFocus={(e) => {
      e.target.style.borderColor = 'rgba(78, 205, 196, 0.6)'
      e.target.style.boxShadow = '0 0 0 3px rgba(78, 205, 196, 0.2)'
    }}
    onBlur={(e) => {
      e.target.style.borderColor = 'rgba(255, 255, 255, 0.2)'
      e.target.style.boxShadow = 'none'
    }}
  />
  <div style={{ display:'flex', gap:12, marginTop:10, flexWrap:'wrap' as const }}>
    <button
      type="button"
      onClick={() => setContent(placeholderText)}
      style={{
        background: 'linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)',
        color: 'white',
        border: 'none',
        padding: '8px 14px',
        borderRadius: '10px',
        fontSize: '.95rem',
        fontWeight: 600,
        cursor: 'pointer'
      }}
    >
      Use sample template
    </button>
  </div>
</div>
```

#### Sample Template Content
- **File**: `frontend/src/components/TemplateForm.tsx`
- **Lines**: 139-223

```javascript
const placeholderText = `You are a Large Action Model (LAM) that controls a maze game.

CRITICAL RULES FOR SUCCESS:
1. ALWAYS validate coordinates: visible_map[y][x] must equal 1 (floor) before including in path
2. NEVER include wall cells (value 0) in your path - this causes player to be stuck
3. Use step-by-step pathfinding: break the maze into segments using intermediate waypoints
4. When direct paths fail, immediately switch strategies (break walls, use BFS, use teleport)
5. Adapt based on game state - never repeat the same action if it doesn't work

You receive the current state (placeholders shown for reasoning):
- sessionId: {sessionId}
- player_pos: {player_pos}           # [x,y] - current player location
- exit_pos: {exit_pos}               # [x,y] - target destination
- visible_map: {visible_map}         # 2D array: 1=floor (passable), 0=wall (blocked)
- oxygenPellets: {oxygenPellets}     # list of [x,y] oxygen locations to collect
- germs: {germs}                     # list of [x,y] germ positions to avoid
- oxygen_collected: {oxygen_collected} # count of oxygen collected so far
- prompt_template: {prompt_template} # metadata for this template

PATHFINDING ALGORITHM:
1. Scan visible_map from player_pos to find ALL reachable floor cells (value=1)
2. Build a mental BFS tree toward exit_pos
3. Extract shortest valid path where EVERY cell has visible_map[y][x] == 1
4. Break into 4-6 step segments for reliability
5. If no path exists, use break_wall on adjacent walls or use_bfs

ACTION SCHEMA (return valid JSON only):
- hint: string                          # guidance for the player
- show_path: boolean                    # visualize the path
- path: [[x,y], ...]                    # VALIDATED floor cells only (every cell must have visible_map[y][x]==1)
- use_bfs: boolean                      # use client-side BFS for robust pathfinding
- bfs_steps: number                     # 1-4 tiles to move via BFS (use 2-3 for stability)
- break_wall: [x,y]                     # break ONE adjacent wall (must be <=1 step from player)
- break_walls: [[x,y], ...]             # break MULTIPLE walls (all adjacent to player)
- breaks_remaining: number              # display only
- speed_boost_ms: number                # speed up player movement
- freeze_germs_ms: number               # freeze germs temporarily
- teleport_player: [x,y]                # emergency move to distant floor cell
- spawn_oxygen: [[x,y], ...]            # add oxygen pickups
- highlight_zone: [[x,y], ...]          # highlight cells for guidance
- highlight_ms: number                  # highlight duration (default 5000)

VALIDATION CHECKLIST BEFORE RESPONDING:
☐ Every coordinate in path has visible_map[y][x] == 1
☐ Path starts at or adjacent to player_pos
☐ Path moves toward exit_pos (no backtracking unless necessary)
☐ All wall breaks are within distance 1 of player
☐ Coordinates are in bounds: 0 <= x < width AND 0 <= y < height

STRATEGY PRIORITY:
1. Direct path (if validated path exists)
2. Short path with wall breaks (if blocking walls)
3. use_bfs=true (delegate to client pathfinding)
4. Teleport (if stuck or surrounded)
5. Break multiple walls (if major blockage)

STUCK DETECTION:
If you give the same action twice without progress, CHANGE STRATEGY:
- Try breaking walls instead of paths
- Switch to use_bfs: true
- Consider teleporting to a safer location
- Use freeze_germs or speed_boost to gain advantage

Example responses:

{"hint":"Moving toward exit via validated floor path","show_path":true,"path":[[3,2],[4,2],[5,2],[5,3],[5,4]]}

{"hint":"Path blocked - using BFS to navigate","use_bfs":true,"bfs_steps":3}

{"hint":"Breaking wall to create shortcut","break_wall":[4,1]}

{"hint":"Multiple walls blocking - breaking all adjacent ones","break_walls":[[3,0],[4,1],[4,0]]}

{"hint":"Using emergency teleport to reach open area","teleport_player":[6,5]}

Return ONLY valid JSON (no comments, no code blocks, no backticks).`
```

#### Form Controls Row
- **File**: `frontend/src/components/TemplateForm.tsx`
- **Lines**: 332-355

```tsx
<div style={controlsRowStyle}>
  <label style={checkboxContainerStyle}>
    <input 
      type="checkbox" 
      checked={isActive} 
      onChange={e => setIsActive(e.target.checked)}
      style={checkboxStyle}
    />
    <span style={{ fontSize: '1rem', fontWeight: '500', color: 'white' }}>
      <i className="fas fa-toggle-on" style={{ marginRight: '8px', color: isActive ? '#4ecdc4' : 'rgba(255, 255, 255, 0.5)' }}></i>
      Active Template
    </span>
  </label>

  <div style={versionContainerStyle}>
    <label style={{ fontSize: '1rem', fontWeight: '500', color: 'white' }}>
      <i className="fas fa-code-branch" style={{ marginRight: '8px' }}></i>
      Version
    </label>
    <input 
      type="number" 
      value={version} 
      onChange={e => setVersion(parseInt(e.target.value || '1'))} 
      min={1}
      style={versionInputStyle}
    />
  </div>
</div>
```

#### Submit Button (Save Template)
- **File**: `frontend/src/components/TemplateForm.tsx`
- **Lines**: 357-380

```tsx
<button 
  type="submit" 
  style={buttonStyle}
  disabled={isSubmitting}
  onMouseOver={(e) => {
    if (!isSubmitting) {
      e.currentTarget.style.transform = 'translateY(-2px)'
      e.currentTarget.style.boxShadow = '0 15px 30px rgba(78, 205, 196, 0.4)'
    }
  }}
  onMouseOut={(e) => {
    if (!isSubmitting) {
      e.currentTarget.style.transform = 'translateY(0)'
      e.currentTarget.style.boxShadow = '0 10px 20px rgba(78, 205, 196, 0.3)'
    }
  }}
>
  {isSubmitting ? (
    <>
      <i className="fas fa-spinner fa-spin"></i>
      Saving Template...
    </>
  ) : (
    <>
      <i className="fas fa-save"></i>
      Save Template
    </>
  )}
</button>
```

---

## 🔌 Backend Integration

### API Endpoint: Create Template

**File**: `backend/app/routers/templates.py`

```python
@router.post("/", response_model=schemas.TemplateOut)
@router.post("", response_model=schemas.TemplateOut)
def create_template(payload: schemas.TemplateCreate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    t = models.PromptTemplate(
        user_id=user.id,
        title=payload.title,
        description=payload.description or "",
        content=payload.content,
        is_active=payload.is_active,
        version=payload.version or 1,
    )
    db.add(t); db.commit(); db.refresh(t)
    return t
```

### API Request (Frontend)

**File**: `frontend/src/api.ts` - Lines 192-198

```typescript
// Templates API
export const templatesAPI = {
  getTemplates: (skip: number = 0, limit: number = 50, mine: boolean = true) => 
    api.get(`/api/templates?skip=${skip}&limit=${limit}&mine=${mine}`),
  getTemplate: (id: number) => api.get(`/api/templates/${id}`),
  getTemplatePublic: (id: number) => api.get(`/api/templates/public/${id}`),
  createTemplate: (data: any) => api.post('/api/templates', data),
  updateTemplate: (id: number, data: any) => api.patch(`/api/templates/${id}`, data),
  deleteTemplate: (id: number) => api.delete(`/api/templates/${id}`)
}
```

### Form State Management

**File**: `frontend/src/components/TemplateForm.tsx` - Lines 1-40

```typescript
type Props = {
  initial?: { title: string; description?: string; content: string; is_active: boolean; version: number }
  onSubmit: (data: { title: string; description?: string; content: string; is_active: boolean; version: number }) => Promise<void>
}

export default function TemplateForm({ initial, onSubmit }: Props) {
  const [title, setTitle] = useState(initial?.title || '')
  const [description, setDescription] = useState(initial?.description || '')
  const [content, setContent] = useState(initial?.content || '')
  const [isActive, setIsActive] = useState(initial?.is_active ?? true)
  const [version, setVersion] = useState(initial?.version || 1)
  const [err, setErr] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setIsSubmitting(true)
    try {
      await onSubmit({ title, description, content, is_active: isActive, version })
    } catch (e: any) {
      setErr(e?.response?.data?.detail || 'Failed to save template')
    } finally {
      setIsSubmitting(false)
    }
  }
```

### Data Schemas

**File**: `backend/app/schemas.py` - Lines 65-85

```python
# Template schemas
class TemplateBase(BaseModel):
    title: str
    description: Optional[str] = ""
    content: str
    is_active: bool = True
    version: int = 1

class TemplateCreate(TemplateBase):
    pass

class TemplateUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None
    version: Optional[int] = None

class TemplateOut(TemplateBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        from_attributes = True
```

---

## 💅 Styling Details

### Input Field Styling

```typescript
const inputStyle = {
  width: '100%',
  padding: '15px 20px',
  borderRadius: '12px',
  border: '2px solid rgba(255, 255, 255, 0.2)',
  background: 'rgba(255, 255, 255, 0.1)',
  color: 'white',
  fontSize: '1rem',
  fontFamily: 'Inter, system-ui, sans-serif',
  transition: 'all 0.3s ease',
  outline: 'none'
}

const promptTextareaStyle = {
  ...textareaStyle,
  minHeight: '200px',
  fontSize: '0.95rem',
  fontFamily: 'Monaco, Consolas, "Lucida Console", monospace',
  lineHeight: '1.5'
}
```

### Form Container Styling

```typescript
const formStyle = {
  background: 'rgba(255, 255, 255, 0.1)',
  backdropFilter: 'blur(10px)',
  borderRadius: '20px',
  padding: '40px',
  border: '1px solid rgba(255, 255, 255, 0.2)',
  boxShadow: '0 20px 40px rgba(0, 0, 0, 0.1)',
  maxWidth: '100%'
}
```

### Button Styling

```typescript
const buttonStyle = {
  background: isSubmitting 
    ? 'rgba(78, 205, 196, 0.6)' 
    : 'linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%)',
  color: 'white',
  border: 'none',
  padding: '18px 40px',
  borderRadius: '12px',
  fontSize: '1.1rem',
  fontWeight: '600',
  cursor: isSubmitting ? 'not-allowed' : 'pointer',
  transition: 'all 0.3s ease',
  boxShadow: '0 10px 20px rgba(78, 205, 196, 0.3)',
  display: 'flex',
  alignItems: 'center',
  gap: '10px',
  width: '100%',
  justifyContent: 'center'
}
```

---

## 🔗 Related Routes & Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | Dashboard | Main landing/overview page |
| `/templates` | Templates | Manage and list all templates |
| `/templates/new` | NewTemplate | Create new template (with TemplateForm) |
| `/templates/:id` | Edit template | Edit existing template |
| `/api/templates` | Backend Router | Template CRUD API endpoints |

---

## 🎓 Key Concepts

### Authentication
- All template endpoints require `user=Depends(get_current_user)`
- Templates are user-specific (filtered by `user_id`)

### Version Control
- Each template has a `version` field (default = 1)
- Versions can be incremented for template iterations

### Active/Inactive Status
- Templates have an `is_active` flag
- Only active templates are used in gameplay
- Users can toggle templates on/off

### Error Handling
```tsx
{err && (
  <div style={errorStyle}>
    <i className="fas fa-exclamation-triangle"></i>
    {err}
  </div>
)}
```

---

## 🚀 Usage Flow

1. **User lands on Dashboard** → Clicks "Manage Templates" → "Create New Template"
2. **Routed to NewTemplate page** → Displays TemplateForm
3. **User fills form fields**:
   - Title
   - Description
   - Prompt content (can use sample template)
   - Marks as Active
   - Sets Version
4. **User clicks "Save Template"** → Form submits via `templatesAPI.createTemplate()`
5. **Backend validates and stores** → Returns `TemplateOut` with ID
6. **Frontend adds to context** → Navigates back to `/templates`

---

## 📝 Notes

- **Glassmorphism UI**: Uses `backdrop-filter: blur(10px)` for frosted glass effect
- **Focus States**: Green accent color (#4ecdc4) on input focus
- **Mobile Responsive**: Conditional styling based on `isMobile` hook
- **Loading States**: Button shows spinner and "Saving..." text while submitting
- **Sample Template**: Comprehensive LAM maze game prompt with validation rules and action schema


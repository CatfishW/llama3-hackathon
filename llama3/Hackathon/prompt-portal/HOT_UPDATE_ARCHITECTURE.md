# Hot Update Architecture Diagram

## State Flow

```
DraftState (sessionDraft)
    ↓
User selects preset/template
    ↓
┌─────────────────────────────────────┐
│  handlePresetApply() OR             │
│  handleTemplateChange()             │
│  - Updates sessionDraft immediately │
│  - Sets prompt_source               │
│  - Calls hotUpdatePrompt()           │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  hotUpdatePrompt()                  │
│  - Shows "Saving..." indicator      │
│  - Debounces with 500ms timeout     │
│  - Queues API call                  │
└─────────────────────────────────────┘
    ↓
  (500ms passes)
    ↓
┌─────────────────────────────────────┐
│  PATCH /api/chatbot/sessions/{id}   │
│  Body: {                            │
│    template_id: number | null       │
│    system_prompt: string            │
│  }                                  │
└─────────────────────────────────────┘
    ↓
Backend updates session
    ↓
Response: Updated ChatSession
    ↓
┌─────────────────────────────────────┐
│  setSessions() - update list        │
│  setSavingPrompt(false) - hide      │
│  indicator                          │
└─────────────────────────────────────┘
    ↓
UI reflects persisted changes
```

## Component Hierarchy

```
ChatStudio
├── States
│   ├── savingPrompt (boolean)           ← tracks hot update status
│   ├── sessionDraft (DraftState)        ← UI-level prompt config
│   ├── sessions (ChatSession[])         ← persisted in backend
│   └── ...
│
├── Effects
│   ├── Rehydrate draft from session     ← on session change
│   ├── Auto-detect preset matches       ← when system_prompt changes
│   └── Auto-scroll messages             ← on new messages
│
├── Functions
│   ├── hotUpdatePrompt()                ← NEW: debounced hot save
│   ├── handlePresetApply()              ← UPDATED: calls hotUpdatePrompt
│   ├── handleTemplateChange()           ← UPDATED: calls hotUpdatePrompt
│   ├── handleSaveDraft()                ← still available for bulk saves
│   └── ...
│
└── UI Sections
    ├── Sidebar (Sessions)
    ├── Header (Title + Action buttons)
    ├── Message Container
    ├── Input Area
    └── Settings Panel
        ├── Temperature slider
        ├── Top-P slider
        ├── Max Tokens input
        ├── Preset selector    ← triggers hotUpdatePrompt
        ├── Template selector  ← triggers hotUpdatePrompt
        ├── "Saving..." indicator ← shows when savingPrompt=true
        └── System Prompt editor
```

## Debounce Mechanism

```
Timeline of rapid template selections:

Time    Action                          Effect
----    ------                          ------
0ms     User selects Template A         hotUpdateTimeoutRef set (500ms timer)
                                        savingPrompt = true

150ms   User selects Template B         Timer cancelled ❌
                                        New hotUpdateTimeoutRef set (500ms timer)

300ms   User selects Template C         Timer cancelled ❌
                                        New hotUpdateTimeoutRef set (500ms timer)

800ms   (500ms since last selection)    Timer fires ✓
                                        API call with Template C
                                        savingPrompt = false
```

## Saving Indicator Component

```
Preset/Template Section:
┌────────────────────────────────────────────────────┐
│ Preset Persona: [Dropdown ▼]                        │
│ My Prompt Template: [Dropdown ▼]                    │
│                                           [● Saving]│  ← Only visible if savingPrompt
└────────────────────────────────────────────────────┘
     ↓ (alignment: flex, alignItems: 'flex-end')
     └─ Indicator positioned at same vertical level as dropdowns
```

## Pulse Animation

```css
@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.4;
  }
}
/* Applied to the dot: animation: 'pulse 2s infinite' */
```

Result: Smoothly pulsing blue dot that repeats every 2 seconds, clearly visible when saving is in progress.

## Error Handling

```
Hot Update Flow with Error:

hotUpdatePrompt() called
  ↓
setTimeout(async () => {
  try {
    API call to PATCH session
    if success:
      - Update sessions list
      - setSavingPrompt(false)
      - Success! (silent - no notification)
    if error:
      - console.error() logged
      - setSavingPrompt(false)
      - User sees no error message
      - Note: App continues working
  } finally {
    setSavingPrompt(false)  ← Always reset indicator
  }
}, 500)
```

**Strategy**: Fail silently for hot updates since they're not critical operations. If template switch fails to save, user can manually click "Save" button with the full draft, or their next browser refresh will reload the correct state from server.

## Comparison: Before vs After

### Before (Manual Save)
```
User action: Select Preset A
  ↓
UI updates immediately
  ↓
User manually clicks "Save" button
  ↓
Payload: { title, system_prompt, temperature, top_p, max_tokens, template_id }
  ↓
Full session updated
  ↓
Dirty flag cleared
```

### After (Hot Update)
```
User action: Select Preset A
  ↓
UI updates immediately
  ↓
500ms debounce
  ↓
Automatic API call (hidden from user)
  ↓
Payload: { template_id, system_prompt } ← Only changed fields
  ↓
Session updated
  ↓
"Saving..." indicator auto-hides
  ↓
Dirty flag NOT affected (manual save still possible for other changes)
```

## Key Implementation Points

1. **Separate from Manual Save**: `hotUpdatePrompt()` is independent of `handleSaveDraft()`
   - Users can still manually save all parameters
   - Hot updates don't clear the dirty flag unnecessarily

2. **Optimistic UI**: State updates happen immediately (`setSessionDraft`)
   - User sees changes before API confirms
   - Reduces perceived latency

3. **Debounce Pattern**: Cancels previous timeout when new selection made
   - Uses `useRef` to persist timeout ID across renders
   - Prevents multiple concurrent API calls

4. **Fire-and-Forget**: Errors are silently logged
   - Templates are nice-to-haves, not critical
   - App remains responsive even if save fails
   - User can manually retry with "Save" button

5. **Visual Clarity**: "Saving..." indicator 
   - Blue pulsing dot matches "Send" button loading state
   - Positioned inline with controls (no blocking modals)
   - Auto-dismisses on completion

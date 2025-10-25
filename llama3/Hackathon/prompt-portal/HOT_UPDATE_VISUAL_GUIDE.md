# Hot Update Feature - Visual Guide

## User Interface Changes

### Before
```
┌─────────────────────────────────────────────┐
│ Settings Panel                              │
├─────────────────────────────────────────────┤
│ Temperature: [====●====]                    │
│ Top-P:       [=====●===]                    │
│ Max Tokens:  [3000          ]               │
│                                              │
│ Preset Persona: [Select preset...     ▼]   │
│ My Prompt Template: [None             ▼]   │
│                                              │
│ [ Edit Prompt ]  [ Save ]                   │
│ (requires manual                            │
│  click to save)                             │
└─────────────────────────────────────────────┘
```

### After
```
┌─────────────────────────────────────────────┐
│ Settings Panel                              │
├─────────────────────────────────────────────┤
│ Temperature: [====●====]                    │
│ Top-P:       [=====●===]                    │
│ Max Tokens:  [3000          ]               │
│                                              │
│ Preset Persona: [Select preset...     ▼]   │
│ My Prompt Template: [None             ▼] [● Saving…]
│                    └─ Hot update!              │
│ [ Edit Prompt ]  [ Save ]                   │
│ (Preset/Template                            │
│  changes auto-save)                         │
└─────────────────────────────────────────────┘
```

---

## State Machine Diagram

```
                    ┌─────────────────┐
                    │   Idle State    │
                    │ savingPrompt=false
                    └────────┬────────┘
                             │
                    User selects preset/template
                             │
                             ▼
                    ┌─────────────────┐
                    │ Update State    │
                    │ savingPrompt=true
                    │ (UI updates)    │
                    │ Timer started   │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
        User makes     500ms elapsed   
        another         (no more changes)
        selection            │
              │               ▼
              │      ┌─────────────────┐
              │      │ API Call State  │
              │      │ PATCH session   │
              │      └────────┬────────┘
              │               │
              └──────────────┬┘
                             │
                      Success/Error
                             │
                             ▼
                    ┌─────────────────┐
                    │   Idle State    │
                    │ savingPrompt=false
                    │ Indicator hidden
                    └─────────────────┘
```

---

## Data Flow Diagram

```
React Component: ChatStudio
│
├─ State: sessionDraft
│  └─ { system_prompt, template_id, ... }
│
├─ State: savingPrompt (boolean)
│
├─ useRef: hotUpdateTimeoutRef
│  └─ tracks debounce timer
│
└─ Function: hotUpdatePrompt()
   │
   ├─ Input: (templateId, systemPrompt, presetKey)
   │
   ├─ Clear previous timeout
   │  └─ clearTimeout(hotUpdateTimeoutRef.current)
   │
   ├─ Set savingPrompt = true
   │  └─ Triggers UI re-render with indicator
   │
   ├─ Start 500ms debounce
   │  │
   │  └─ setTimeout(() => {
   │     │
   │     ├─ Create payload
   │     │  └─ { template_id, system_prompt }
   │     │
   │     ├─ API Call
   │     │  └─ PATCH /api/chatbot/sessions/{id}
   │     │
   │     ├─ On Success
   │     │  ├─ setSessions() ← update list
   │     │  └─ setSavingPrompt(false) ← hide indicator
   │     │
   │     └─ On Error
   │        ├─ console.error()
   │        └─ setSavingPrompt(false) ← hide indicator anyway
   │
   └─ Return (non-blocking, returns before API completes)
```

---

## Event Timeline

```
Timeline                  Action                    UI State
─────────────────────────────────────────────────────────────────

0ms                  ┌─ User clicks dropdown
                     │
                     └─ Selects "Expert Analyst"
                           │
                           ▼
                   sessionDraft.preset_key = "expert"
                   sessionDraft.system_prompt = "You are an expert..."
                   hotUpdatePrompt() called
                           │
                           ▼
                   ┌─────────────────────┐
                   │ "Saving…" indicator │  ← [● Saving…] appears
                   │ visible             │
                   │ savingPrompt = true │
                   └─────────────────────┘
                   
                   Timer starts (500ms)
                           │
                           │ (100ms passes)
                           │
                   User clicks dropdown again
                           │
                           ▼
500ms hasn't elapsed, so:
                   - Previous timer cancelled
                   - Select "Creative Writer"
                   - New timer starts (500ms)
                           │
                           │ (500ms passes)
                           │
                           ▼
                   ┌─────────────────────┐
                   │ API Call fires:     │
                   │ PATCH /sessions/    │
                   │ Body: {             │
                   │   template_id: null │
                   │   system_prompt:... │
                   │ }                   │
                   └────────┬────────────┘
                            │
                            ▼
                   ┌─────────────────────┐
                   │ Backend processes   │
                   │ and responds        │
                   └────────┬────────────┘
                            │
                            ▼
                   ┌─────────────────────┐
                   │ "Saving…" hidden    │  ← [● Saving…] disappears
                   │ savingPrompt = false│
                   │ UI stable           │
                   └─────────────────────┘
```

---

## Component Integration

```
ChatStudio Component
│
├─ [Sidebar] - Session list
│  └─ Unchanged
│
├─ [Header] - Title and action buttons
│  └─ Unchanged
│
├─ [Messages Container] - Chat history
│  └─ Unchanged
│
├─ [Input Area] - Message input
│  └─ Unchanged
│
└─ [Settings Panel] ◄─── HOT UPDATES HERE
   │
   ├─ Parameter Sliders
   │  └─ Temperature, Top-P, Max Tokens
   │     (Still require manual Save)
   │
   ├─ Preset & Template Selectors ◄─── Hot update on change
   │  ├─ Preset Persona dropdown
   │  │  └─ onChange: handlePresetApply()
   │  │     └─ calls hotUpdatePrompt()
   │  │
   │  ├─ My Prompt Template dropdown
   │  │  └─ onChange: handleTemplateChange()
   │  │     └─ calls hotUpdatePrompt()
   │  │
   │  └─ [● Saving…] indicator ◄─── New visual element
   │     └─ Only shown when savingPrompt = true
   │
   ├─ [Edit Prompt] button
   │  └─ Shows/hides System Prompt editor
   │
   ├─ [Hide Prompt] button
   │  └─ Collapses editor
   │
   ├─ System Prompt Editor
   │  ├─ Large textarea
   │  ├─ Shows prompt source badge (📌 Preset, 📄 Template, ✏️ Custom)
   │  └─ Manual edits require "Save" button
   │
   └─ [Save] button
      └─ Still available for bulk parameter updates
```

---

## Hot Update Call Stack

```
User Event: onChange on preset select
│
└─ handlePresetApply(presetKey)
   │
   ├─ Find preset object
   ├─ setSessionDraft() ◄─── Optimistic update (immediate UI feedback)
   │  └─ Renders with new prompt_source, system_prompt, preset_key
   │
   ├─ setDraftDirtyFlag(true)
   │
   ├─ setShowPromptEditor(true)
   │
   └─ hotUpdatePrompt(null, preset.system_prompt, preset.key)
      │
      ├─ if (!selectedSession) return
      │
      ├─ Clear existing timeout
      │  └─ clearTimeout(hotUpdateTimeoutRef.current)
      │
      ├─ setSavingPrompt(true)
      │  └─ Triggers re-render with [● Saving…] visible
      │
      └─ hotUpdateTimeoutRef.current = setTimeout(async () => {
         │
         ├─ Create payload { template_id: null, system_prompt }
         │
         ├─ const res = await chatbotAPI.updateSession(id, payload)
         │  │
         │  ├─ Network latency happens here
         │  │
         │  └─ Backend returns updated ChatSession
         │
         ├─ setSessions(prev => prev.map(...)) ◄─── Update cache
         │
         └─ finally: setSavingPrompt(false)
            └─ Triggers re-render with [● Saving…] hidden
      }, 500)
```

---

## Hot Update vs Manual Save

### Hot Update Path (Template/Preset changes)
```
User Action → Optimistic UI Update → Debounced Auto-Save → Silently Complete
```
- **Payload**: { template_id, system_prompt }
- **Triggered by**: Dropdown change
- **User feedback**: "Saving..." indicator
- **Error handling**: Silent (can retry with Save button)
- **Dirty flag**: Set but not cleared

### Manual Save Path (Title/Parameters changes)
```
User Action → UI Update → Manual "Save" Click → Explicit Feedback
```
- **Payload**: { title, system_prompt, temperature, top_p, max_tokens, template_id }
- **Triggered by**: "Save" button click
- **User feedback**: Implicit (dirty flag clears)
- **Error handling**: Error message shown
- **Dirty flag**: Cleared on success

---

## Performance Considerations

### Without Hot Update
```
Multiple template switches = User friction
│
User clicks preset A → Manual save → User clicks preset B → Manual save → ...
│
Result: Each change requires 2 actions (select + click save)
```

### With Hot Update
```
Multiple template switches = Seamless experience
│
User clicks preset A → Auto-save in background → User clicks preset B → Auto-save in background → ...
│
Result: Each change requires 1 action (select only)
Debounce ensures: Only 1 API call despite rapid selections
```

### Network Impact
```
Worst case (rapid switching):
- Without hot update: User must wait after each selection for manual save
- With hot update: Debounce batches changes, only 1 API call per "pause"

Example (5 template switches in 2 seconds):
- Without: 5 manual saves required, user must wait for each
- With: 1 API call after 500ms of inactivity, happens in background
```

---

## Accessibility

```
[● Saving…] Indicator
├─ Color: Blue (matches loading state)
├─ Animation: Pulsing (easy to notice)
├─ Text: "Saving…" (clear intent)
├─ Position: Inline (no layout shift)
└─ Dismissed: Auto-hides (no interaction required)

Keyboard Navigation
├─ Tab to preset dropdown → Arrow keys to select
├─ Tab to template dropdown → Arrow keys to select
├─ No blocking during save (can navigate elsewhere)
├─ Indicator not keyboard-focusable (informational only)
└─ Can still click Save button during hot update
```

---

## Browser DevTools Debugging

To observe hot update in action:

### Network Tab
```
1. Open DevTools → Network tab
2. Filter: XHR/Fetch
3. Select preset/template in ChatStudio
4. Observe: Single PATCH request appears ~500ms later
5. Payload shows: { template_id, system_prompt }
6. Response shows: Updated ChatSession
```

### Console Tab
```
Watch for logs:
- No success message (intentional - silent success)
- If error occurs: "Failed to hot update prompt: [error details]"
```

### Rendering Performance
```
Timeline of re-renders on preset change:
- t0: Component re-renders (setSessionDraft)
  └─ Shows new system_prompt, preset_key
  └─ Indicator not visible yet
  
- t1: savingPrompt state updates
  └─ Shows [● Saving…] indicator
  
- t500: API response received
  └─ setSessions() causes re-render
  └─ Indicator remains visible during this
  
- t501: setSavingPrompt(false)
  └─ Indicator disappears

Total: ~3-4 re-renders per hot update (normal React behavior)
```

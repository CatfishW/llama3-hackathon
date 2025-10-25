# Hot Update Implementation for Template Switching

## Overview
Implemented **hot updates** for template and preset switching in ChatStudio. When a user switches templates or presets, the changes are now automatically saved to the backend with visual feedback, eliminating the need for manual "Save" clicks for these specific operations.

## Features

### 1. **Automatic Persistence on Template/Preset Switch**
- When user selects a different preset or template, the change is immediately queued for backend sync
- 500ms debounce prevents excessive API calls while user is rapidly switching options
- Automatically updates the session with the new `template_id` and `system_prompt`

### 2. **Visual Feedback**
- A "Saving…" indicator appears next to the dropdowns when a hot update is in progress
- Blue pulsing dot provides clear visual feedback that the change is being persisted
- Indicator disappears once the save completes

### 3. **User Flow**
```
User selects preset/template in dropdown
  ↓
Hot update triggered (UI updates immediately)
  ↓
500ms debounce window (to handle multiple rapid selections)
  ↓
"Saving..." indicator appears
  ↓
API call to PATCH /api/chatbot/sessions/{id} with new template_id & system_prompt
  ↓
Sessions list updated with new session data
  ↓
"Saving..." indicator disappears
```

### 4. **Prompt Source Tracking**
Hot updates respect the existing `prompt_source` field:
- **Preset**: When a preset is applied via `handlePresetApply()`
- **Template**: When a template is selected via `handleTemplateChange()`
- **Custom**: When switching to custom or clearing both

## Implementation Details

### State Addition
```typescript
const [savingPrompt, setSavingPrompt] = useState<boolean>(false)
```
Tracks whether a hot update is currently in progress.

### Core Function: `hotUpdatePrompt()`
```typescript
const hotUpdatePrompt = async (
  templateId: number | null,
  systemPrompt: string,
  presetKey: string | null
) => {
  // Debounces with 500ms timeout
  // Shows "Saving..." indicator
  // Makes PATCH request to backend
  // Updates sessions list on success
  // Silently handles errors (logged to console)
}
```

### Handler Integration

#### `handlePresetApply(key: string)`
- Sets `prompt_source: 'preset'`
- Clears `template_id`
- Calls `hotUpdatePrompt(null, preset.system_prompt, preset.key)`

#### `handleTemplateChange(templateId: number | null)`
- Sets `prompt_source: templateId ? 'template' : 'custom'`
- Clears `preset_key`
- Calls `hotUpdatePrompt(templateId, template.content, null)`

### UI Indicator
Located below the preset/template dropdowns, shows only when `savingPrompt === true`:
```tsx
{savingPrompt && (
  <div style={{...}}>
    <span style={{ animation: 'pulse 2s infinite' }} />
    Saving…
  </div>
)}
```

## Key Benefits

✅ **Instant Feedback**: Changes are applied immediately in UI  
✅ **Automatic Persistence**: No need to click "Save" button for template/preset switches  
✅ **Debounced**: Prevents API spam if user rapidly switches options  
✅ **Non-blocking**: Other operations continue normally during save  
✅ **Error Resilient**: Fails silently (logged to console) without disrupting UX  
✅ **Visual Clarity**: "Saving..." indicator shows what's happening  

## API Endpoint Used

**PATCH** `/api/chatbot/sessions/{id}`

Request payload:
```json
{
  "template_id": 5,
  "system_prompt": "You are a helpful assistant..."
}
```

Response: Updated `ChatSession` object

## Debounce Timing

- **Debounce Window**: 500ms
- **Reason**: Gives users time to select multiple options quickly without each one triggering separate saves
- **Timeout Cleanup**: Previous pending timeout is cleared when new selection is made

## Browser Compatibility

- Uses `setTimeout` and `clearTimeout` (widely supported)
- CSS `@keyframes` for pulse animation injected at runtime
- No external animation libraries required

## Testing Checklist

- [ ] Select a preset → verify "Saving..." appears briefly
- [ ] Switch to another preset → verify previous save completes before new one starts
- [ ] Check backend: Verify session.template_id updated correctly
- [ ] Check backend: Verify session.system_prompt updated correctly
- [ ] Switch preset → template → custom → verify prompt_source updates correctly
- [ ] Network throttling: Select preset and quickly switch while saving (should debounce)
- [ ] Verify "Save" button for title/parameters still works independently

## Files Modified

- `frontend/src/pages/ChatStudio.tsx`
  - Added `savingPrompt` state
  - Added `hotUpdatePrompt()` function with debouncer
  - Updated `handlePresetApply()` to call hot update
  - Updated `handleTemplateChange()` to call hot update
  - Added visual "Saving..." indicator in dropdown section
  - Added pulse animation CSS injection

## Future Enhancements

- [ ] Add success/error toast notifications
- [ ] Add undo capability for template switches
- [ ] Add keyboard shortcuts for quick template switching (e.g., Ctrl+T)
- [ ] Cache last N template selections for quick cycling
- [ ] Add template search/filter if list becomes large

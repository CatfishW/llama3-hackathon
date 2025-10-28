# Template Preference Persistence

## Feature Overview

The selected template is now saved to browser localStorage and automatically restored when:
- Page is refreshed
- Browser is closed and reopened
- New sessions are created

## Implementation

### Storage Key
```typescript
const TEMPLATE_STORAGE_KEY = 'owogpt_selected_template'
```

### When Template is Selected
```typescript
// TemplateSwitcher.tsx - applyTemplate()
localStorage.setItem(TEMPLATE_STORAGE_KEY, templateId)
```

### When Templates Load
```typescript
// TemplateSwitcher.tsx - loadTemplates()
const savedTemplateId = localStorage.getItem(TEMPLATE_STORAGE_KEY)
if (savedTemplateId) {
  const exists = templates.find(t => t.id === Number(savedTemplateId))
  if (exists) {
    setValue(savedTemplateId) // Restore dropdown selection
  }
}
```

### When New Session is Created
```typescript
// Chat.tsx - useEffect()
const savedTemplateId = localStorage.getItem('owogpt_selected_template')
if (savedTemplateId) {
  // Create session
  const created = await createSession('New Chat')
  
  // Fetch template and apply it
  const template = templates.find(t => t.id === Number(savedTemplateId))
  if (template) {
    await api.patch(`/chat/sessions/${created.id}`, {
      template_id: Number(savedTemplateId),
      system_prompt: template.content
    })
  }
}
```

## User Experience

### Scenario 1: Page Refresh
```
1. User selects "Physics Tutor" template
2. Has conversation with template
3. Page refreshes (F5 or reload)
4. ✅ "Physics Tutor" still selected in dropdown
5. ✅ Can continue conversation with same template
```

### Scenario 2: New Session Creation
```
1. User selects "Developer Mode" template
2. Uses it for a while
3. Clicks "New Session" button
4. ✅ New session automatically uses "Developer Mode"
5. No need to re-select template
```

### Scenario 3: Browser Restart
```
1. User selects "Code Assistant" template
2. Closes browser completely
3. Opens browser again, visits app
4. ✅ "Code Assistant" is pre-selected
5. New sessions use this template by default
```

### Scenario 4: Template Deleted
```
1. User has "Custom Template" selected (saved in localStorage)
2. Template is deleted by user or admin
3. Page reloads
4. ✅ Dropdown shows empty (template not found)
5. ✅ No errors, gracefully handles missing template
6. User can select a different template
```

## localStorage Data

### Stored Value
```
Key: "owogpt_selected_template"
Value: "5" (template ID as string)
```

### Inspecting in DevTools
```javascript
// Console
localStorage.getItem('owogpt_selected_template')
// Returns: "5"

// Set manually
localStorage.setItem('owogpt_selected_template', '3')

// Clear preference
localStorage.removeItem('owogpt_selected_template')
```

## Edge Cases Handled

✅ **Template doesn't exist anymore**
- Checks if saved ID exists in current template list
- If not found, shows empty dropdown (no error)

✅ **First time user (no saved preference)**
- Dropdown shows placeholder "Template"
- New sessions use default system prompt
- Once user selects, preference is saved

✅ **Multiple browser tabs**
- Each tab has access to same localStorage
- Changing template in one tab affects new sessions in other tabs
- Existing sessions keep their original template

✅ **Private/Incognito mode**
- localStorage still works within session
- Cleared when private window closes
- Expected behavior for privacy mode

## Benefits

1. **Better UX**: No need to re-select template after every reload
2. **Consistency**: New sessions automatically use preferred template
3. **Persistence**: Survives browser restarts
4. **Simple**: No backend changes needed
5. **Private**: Stored locally, not sent to server

## Clearing Preference

User can clear preference by:
1. Selecting placeholder option (if implemented)
2. Clearing browser data
3. Using DevTools console:
   ```javascript
   localStorage.removeItem('owogpt_selected_template')
   ```

## Future Enhancements

Possible improvements:
- [ ] Add "Clear Template Preference" button in UI
- [ ] Store template per-session (different tabs, different preferences)
- [ ] Sync to server (requires authentication)
- [ ] Remember last N templates used (history)
- [ ] Template favorites/pinning

## Files Modified

- `OwOGPT/frontend/src/components/TemplateSwitcher.tsx` (+8 lines)
- `OwOGPT/frontend/src/components/Chat.tsx` (+15 lines)

## Testing

### Test 1: Template Persistence
1. Select a template
2. Reload page (F5)
3. ✅ Template should still be selected

### Test 2: New Session with Preference
1. Select "Developer Mode"
2. Click "New Session"
3. Send a message
4. ✅ Response should use "Developer Mode" behavior

### Test 3: Deleted Template Handling
1. Select template with ID 5
2. Delete that template via API/UI
3. Reload page
4. ✅ Dropdown shows empty, no errors

### Test 4: Cross-Tab
1. Open app in Tab A, select "Physics"
2. Open app in Tab B
3. Click "New Session" in Tab B
4. ✅ Should use "Physics" template (from localStorage)

---

**Result**: ✅ Template preference is now persistent across reloads and new sessions!



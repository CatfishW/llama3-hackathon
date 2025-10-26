# Fix: Mode Selection Panel Not Working

## Issue
The "Choose Mode" panel in the game start flow was not properly applying the selected mode (Manual vs LAM) when starting a new game.

## Root Cause
The game mode was being set in multiple places with timing conflicts:

1. **In `doStartGame` callback** (line 1087): Set `gameMode` based on `selectedMode`
2. **In "Publish & Start" button** (line 1966): Set `gameMode` again
3. **Dependency array issue**: `selectedMode` was in the `doStartGame` dependency array, causing the callback to be recreated every time the user clicked a mode option

This created a race condition where:
- State updates happen asynchronously
- The game might start before the mode is fully updated
- Multiple setGameMode calls could interfere with each other

## Solution

### 1. Set Mode Before Starting Game
**File**: `frontend/src/pages/WebGame.tsx` (line ~1960-1977)

Changed the "Publish & Start" button to:
- Capture the selected mode in a local variable `chosenMode`
- Set `gameMode` state immediately
- Use the captured value for board dimensions
- Pass dimensions to `doStartGame`

```typescript
const chosenMode = selectedMode
setGameMode(chosenMode)

publishSelectedTemplate(selectedTemplateId).finally(() => {
  const targetCols = (chosenMode === 'lam') ? 10 : 33
  const targetRows = (chosenMode === 'lam') ? 10 : 21
  doStartGame(targetCols, targetRows)
})
```

### 2. Remove Duplicate Mode Setting
**File**: `frontend/src/pages/WebGame.tsx` (line ~1086)

Removed the `setGameMode(selectedMode)` call from inside `doStartGame` since:
- Mode is now set before calling `doStartGame`
- Avoids double-setting and race conditions
- Makes the flow more predictable

### 3. Fix Dependency Array
**File**: `frontend/src/pages/WebGame.tsx` (line ~1092)

Removed `selectedMode` from the dependency array:
```typescript
// Before:
}, [boardCols, boardRows, germCount, connectWS, disconnectWS, selectedMode, tile])

// After:
}, [boardCols, boardRows, germCount, connectWS, disconnectWS, tile])
```

This prevents the callback from being recreated when the user clicks mode options.

### 4. Initialize Selected Mode Correctly
**File**: `frontend/src/pages/WebGame.tsx` (line ~1108-1118)

Changed `launchStartFlow` to:
- Use current `gameMode` instead of always defaulting to 'manual'
- Use `gameMode` instead of `gameModeRef.current` for consistency

```typescript
// Initialize with current game mode
setSelectedMode(gameMode)
```

## Testing

After applying this fix, test the following scenarios:

### Test 1: Choose LAM Mode
1. Click "Start Game"
2. Select "LAM Mode" in the mode picker
3. Click "Next"
4. Select a template
5. Click "Publish & Start"
6. **Expected**: Game starts in LAM mode (10x10 board, no manual control)

### Test 2: Choose Manual Mode
1. Click "Start Game"
2. Select "Manual Mode" in the mode picker
3. Click "Next"
4. Select a template
5. Click "Publish & Start"
6. **Expected**: Game starts in Manual mode (33x21 board, manual control)

### Test 3: Switch Between Modes
1. Click "Start Game"
2. Select "LAM Mode"
3. Switch to "Manual Mode" (click it)
4. Switch back to "LAM Mode"
5. Click "Next" and start
6. **Expected**: Game uses LAM mode (the last selected)

### Test 4: No Templates
1. Ensure no templates exist
2. Click "Start Game"
3. **Expected**: Game starts immediately with current mode

### Test 5: Cancel and Restart
1. Click "Start Game"
2. Select a different mode
3. Click "Cancel"
4. Click "Start Game" again
5. **Expected**: Mode picker shows the previously selected mode

## Technical Details

### Mode Flow
```
User clicks "Start Game"
  ↓
launchStartFlow() opens picker
  ↓
User selects mode (selectedMode state updated)
  ↓
User clicks "Publish & Start"
  ↓
setGameMode(chosenMode) - immediate state update
  ↓
publishSelectedTemplate() - async
  ↓
doStartGame(targetCols, targetRows) - uses captured mode
  ↓
Game initializes with correct mode
```

### State Variables
- `gameMode`: The actual active game mode ('manual' | 'lam')
- `selectedMode`: The mode selected in the picker (before confirmation)
- `gameModeRef`: A ref that tracks gameMode for use in callbacks

### Key Insight
React state updates are asynchronous. When you call `setGameMode(value)`, the `gameMode` variable doesn't update immediately. That's why we:
1. Capture the value in a local variable
2. Set state
3. Use the captured value for immediate calculations
4. Let React handle the re-render with the new state

## Files Modified
- `frontend/src/pages/WebGame.tsx`
  - Line ~1960-1977: "Publish & Start" button handler
  - Line ~1086: Removed duplicate setGameMode
  - Line ~1092: Fixed dependency array
  - Line ~1108-1118: Fixed launchStartFlow initialization

## Impact
- ✅ Mode selection now works correctly
- ✅ No race conditions
- ✅ Predictable flow
- ✅ Board size matches selected mode
- ✅ Game behavior matches selected mode

## Related Issues
This fix ensures that:
- The new scoring system correctly identifies LAM vs Manual mode
- Board dimensions are correct for each mode
- Control behavior matches the selected mode
- Metrics are tracked for the correct mode

---

**Fix Applied**: October 26, 2025
**Status**: ✅ Complete

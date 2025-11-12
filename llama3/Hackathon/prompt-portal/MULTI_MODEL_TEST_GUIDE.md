# ✅ Multi-Model Support - Quick Test Guide

## Backend is Running ✓

The backend is now successfully running on `http://0.0.0.0:8000`

## What's Working

1. ✅ **Beautiful UI Rendered** - Model selection cards are showing
2. ✅ **Backend Server Running** - On port 8000
3. ✅ **Database Migration Complete** - `selected_model` column added
4. ✅ **API Endpoints Registered** - Models API available

## Quick Test Steps

### 1. Test Model Selection API

Open your browser console and run:

```javascript
// Get available models
fetch('http://localhost:8000/api/models/available', {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  }
})
.then(r => r.json())
.then(d => console.log('Available models:', d))

// Get currently selected model
fetch('http://localhost:8000/api/models/selected', {
  headers: {
    'Authorization': 'Bearer ' + localStorage.getItem('token')
  }
})
.then(r => r.json())
.then(d => console.log('Selected model:', d))
```

### 2. Test Model Selection in UI

1. Go to Settings page (you're already there!)
2. Click on any model card (e.g., "MiniMax M2")
3. You should see:
   - ✅ Checkmark appears on clicked card
   - ✅ Gradient background on selected card
   - ✅ Success message: "Successfully switched to MiniMax M2!"
   - ✅ Previous selection loses checkmark

### 3. Test Chat with Selected Model

1. Go to Chat page
2. Send a message
3. The response will come from your selected model

## Expected Behavior

### Before Selection
- Default model: **TangLLM** (first in list)
- Checkmark on TangLLM card

### After Clicking MiniMax M2
- Checkmark moves to MiniMax M2
- API call: `PUT /api/models/select` with `{"model_name": "MiniMax M2"}`
- Database updated: `users.selected_model = "MiniMax M2"`
- Success notification appears

### On Next Chat Request
- Backend reads `user.selected_model` from database
- Loads MiniMax M2 config from `models.json`
- Creates LLM client with OpenRouter API endpoint
- Sends request to MiniMax M2 model

## Troubleshooting

### If Settings Don't Load
- Check backend logs for errors
- Ensure user is logged in
- Try refreshing the page

### If Model Selection Doesn't Save
- Check browser console for errors
- Verify backend is running
- Check database has `selected_model` column:
  ```bash
  cd backend
  sqlite3 app.db "PRAGMA table_info(users);"
  ```

### If Chat Uses Wrong Model
- Check user's `selected_model` in database
- Verify `models.json` has correct API endpoints
- Check backend logs for LLM client creation

## Verification Commands

```bash
# Check if backend is running
curl http://localhost:8000/api/health

# Check models endpoint (needs auth token)
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/api/models/available

# Check database
cd backend
sqlite3 app.db "SELECT id, email, selected_model FROM users;"
```

## Success Indicators

✅ Model cards render beautifully
✅ Clicking a card shows visual feedback
✅ Success message appears
✅ Selection persists after page refresh
✅ Chat uses selected model

## Current Status

- **Backend**: ✅ Running on port 8000
- **Frontend**: ✅ Showing model selection UI
- **Database**: ✅ Migration complete
- **API**: ✅ Endpoints registered
- **UI**: ✅ Beautiful and responsive

**Everything is ready!** Try selecting a different model now! 🚀

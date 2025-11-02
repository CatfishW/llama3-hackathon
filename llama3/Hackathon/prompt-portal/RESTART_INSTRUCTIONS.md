# 🔄 Restart Instructions to Fix Driving Game Leaderboard

## Problem
You're seeing **1356 Maze game scores** in the Driving Game leaderboard section when it should show **0 entries**.

## Root Cause
The backend server is still running **old code** before the separation fix was applied.

---

## ✅ Solution: Restart Backend Server

### Step 1: Stop the Current Backend

**Option A: If running in terminal/PowerShell**
```powershell
# Press Ctrl+C in the terminal where the server is running
```

**Option B: If running as a service**
```powershell
# Find the process
Get-Process | Where-Object {$_.ProcessName -like "*python*"} | Select-Object Id, ProcessName, Path

# Kill the backend process (replace <PID> with actual process ID)
Stop-Process -Id <PID> -Force
```

**Option C: Task Manager (Windows)**
1. Open Task Manager (Ctrl+Shift+Esc)
2. Find "Python" processes
3. Look for the one in `prompt-portal\backend`
4. Right-click → End Task

---

### Step 2: Start Backend with Updated Code

```powershell
cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal\backend
python run_server.py
```

**Or if using uvicorn directly:**
```powershell
cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal\backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Watch for this message:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
```

---

### Step 3: Hard Refresh Frontend

**In your browser:**

**Chrome/Edge:**
- `Ctrl + Shift + R` (Windows)
- `Ctrl + F5` (Windows)

**Firefox:**
- `Ctrl + Shift + R`

**Safari:**
- `Cmd + Option + R`

**Or manually:**
1. Open Developer Tools (F12)
2. Right-click the refresh button
3. Select "Empty Cache and Hard Reload"

---

### Step 4: Verify the Fix

1. **Go to Leaderboard page**
2. **Click "🏁 Driving Game" button**
3. **You should see:**
   ```
   Total entries: 0
   Showing: 0
   ```
4. **Table should say:** "No entries yet"

---

## 🔍 Verification Checklist

- [ ] Backend server restarted
- [ ] Console shows no errors
- [ ] Frontend hard refreshed (Ctrl+Shift+R)
- [ ] Driving Game leaderboard shows 0 entries ✓
- [ ] LAM Mode shows 31 entries ✓
- [ ] Manual Mode shows 979 entries ✓

---

## 📊 Expected Behavior After Restart

| Mode | Expected Count | What You Should See |
|------|----------------|---------------------|
| **🏁 Driving Game** | 0 | "No entries yet" message |
| **LAM Mode** | 31 | 31 maze navigation scores |
| **Manual Mode** | 979 | 979 maze navigation scores |

---

## 🎮 Test the Driving Game Scoring

After restart, you can test the Driving Game scoring:

1. **Go to ChatBot (Chat page)**
2. **Select a prompt template** (or create one for Cap agent)
3. **Enable "Driving Game Testing"** checkbox
4. **Have a conversation until consensus**
5. **Modal shows score with correct message count**
6. **Check Driving Game leaderboard** → Should now show 1 entry!

---

## 🐛 If Still Not Working

### Check 1: Verify Backend is Using New Code
```powershell
# In backend directory, check the file
cd Z:\llama3_20250528\llama3\Hackathon\prompt-portal\backend\app\routers
notepad leaderboard.py

# Line 90-92 should have:
# if mode in ("lam","manual","driving_game"):
#     base_q = base_q.filter(models.Score.mode == mode)
```

### Check 2: Test API Directly
Open browser and go to:
```
http://localhost:8000/api/leaderboard/?mode=driving_game&limit=10
```

**Expected response:**
```json
[]
```
(Empty array since no driving_game scores exist)

### Check 3: Check Backend Logs
Look for these messages in the backend console:
```
INFO:     127.0.0.1:XXXXX - "GET /api/leaderboard/?mode=driving_game&limit=50&skip=0 HTTP/1.1" 200 OK
```

---

## 💡 Quick Summary

**The fix is already in the code!** You just need to:

1. **Stop old backend** (Ctrl+C or Task Manager)
2. **Start new backend** (`python run_server.py`)
3. **Hard refresh frontend** (Ctrl+Shift+R)
4. **Check Driving Game leaderboard** → Should be empty now ✓

---

## ✨ What Was Fixed

| Issue | Solution |
|-------|----------|
| ❌ Modal shows Messages: 0 | ✅ Fixed: Now tracks count correctly |
| ❌ Leaderboard shows Maze scores in Driving Game | ✅ Fixed: Proper filtering by mode |
| ❌ Could mix Maze and Driving metrics | ✅ Fixed: Backend validation enforces separation |

---

**Once backend is restarted, everything will work perfectly!** 🎉


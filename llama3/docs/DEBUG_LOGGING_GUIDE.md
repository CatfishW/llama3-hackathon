# Debug Logging Guide

## Overview

The vLLM deployment now includes comprehensive debug logging that captures:
- ✅ Raw user messages received via MQTT
- ✅ Full conversation history
- ✅ Complete LLM prompts (with system prompt + history)
- ✅ Raw LLM outputs
- ✅ Generation parameters (temperature, top_p, max_tokens)
- ✅ Timing information
- ✅ Error messages

All debug information is saved to: **`debug_info.log`**

---

## What Gets Logged

### For Each User Message:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║ NEW MESSAGE | Session: user-12345678... | Project: general
╠══════════════════════════════════════════════════════════════════════════════╣
USER MESSAGE:
What is the capital of France?
────────────────────────────────────────────────────────────────────────────────
================================================================================
GENERATION REQUEST | Session: user-12345678
Temperature: 0.6, Top-P: 0.9, Max Tokens: 256
────────────────────────────────────────────────────────────────────────────────
FULL PROMPT TO LLM:
<|im_start|>system
You are a helpful AI assistant. Provide clear, concise, and accurate responses.<|im_end|>
<|im_start|>user
What is the capital of France?<|im_end|>
<|im_start|>assistant
────────────────────────────────────────────────────────────────────────────────
LLM RAW OUTPUT:
The capital of France is Paris.
────────────────────────────────────────────────────────────────────────────────
Generation Time: 1.234s
Output Length: 31 chars
================================================================================

ASSISTANT RESPONSE:
The capital of France is Paris.
╚══════════════════════════════════════════════════════════════════════════════╝
```

---

## Viewing Debug Logs

### Method 1: Direct File Access
Simply open `debug_info.log` in any text editor:
```bash
notepad debug_info.log     # Windows
code debug_info.log         # VS Code
```

### Method 2: Use the Debug Log Viewer (Recommended)

I've created a helper script for easy viewing:

#### View last 50 lines:
```bash
python view_debug_log.py view
```

#### View last 100 lines:
```bash
python view_debug_log.py view --lines 100
```

#### Follow log in real-time (like tail -f):
```bash
python view_debug_log.py view --follow
```

#### Filter by session ID:
```bash
python view_debug_log.py view --session user-12345678
```

#### Search for keyword:
```bash
python view_debug_log.py view --search "error"
python view_debug_log.py view --search "temperature"
```

#### Show statistics:
```bash
python view_debug_log.py stats
```

Output:
```
📊 Debug Log Statistics
================================================================================
File: debug_info.log
Size: 2.45 MB (2,567,890 bytes)
Total Lines: 15,234
────────────────────────────────────────────────────────────────────────────────
User Messages: 345
LLM Prompts: 345
LLM Outputs: 345
Errors: 2
Unique Sessions: 12
================================================================================
```

#### Clear the log:
```bash
python view_debug_log.py clear
```

---

## Use Cases

### 1. Debugging Response Quality Issues

**Problem:** LLM giving weird responses

**Solution:** Check what prompt it's actually receiving
```bash
python view_debug_log.py view --search "FULL PROMPT TO LLM"
```

You might discover:
- System prompt not being applied correctly
- Conversation history getting corrupted
- Context being trimmed too aggressively

---

### 2. Tracking User Conversations

**Problem:** Need to see full conversation for a specific user

**Solution:** Filter by session ID
```bash
python view_debug_log.py view --session user-d352264e --lines 1000
```

This shows:
- All messages from that user
- Complete conversation flow
- How context evolved

---

### 3. Performance Analysis

**Problem:** Some responses are slow

**Solution:** Check generation times
```bash
python view_debug_log.py view --search "Generation Time"
```

Look for patterns:
- Which messages take longest?
- Is prompt length the issue?
- Are certain projects slower?

---

### 4. Error Investigation

**Problem:** Users reporting errors

**Solution:** Find all errors
```bash
python view_debug_log.py view --search "ERROR" --lines 200
```

You'll see:
- What input caused the error
- Full error message
- Which session was affected

---

### 5. Real-time Monitoring

**Problem:** Want to watch what's happening live

**Solution:** Follow the log
```bash
python view_debug_log.py view --follow
```

Great for:
- Testing new features
- Watching user interactions
- Debugging live issues

---

## Log Entry Format

### 🔵 User Input Level (INFO)
```
╔══════════════════════════════════════════════════════════════════════════════╗
║ NEW MESSAGE | Session: xxx | Project: xxx
╠══════════════════════════════════════════════════════════════════════════════╣
USER MESSAGE:
<user's actual message>
```

### 🟢 LLM Interaction Level (DEBUG)
```
================================================================================
GENERATION REQUEST | Session: xxx
Temperature: X, Top-P: X, Max Tokens: X
────────────────────────────────────────────────────────────────────────────────
FULL PROMPT TO LLM:
<complete formatted prompt sent to model>
────────────────────────────────────────────────────────────────────────────────
LLM RAW OUTPUT:
<exact text generated by model>
────────────────────────────────────────────────────────────────────────────────
Generation Time: X.XXXs
Output Length: XXX chars
================================================================================
```

### 🔵 Response Level (INFO)
```
ASSISTANT RESPONSE:
<final response sent to user>
╚══════════════════════════════════════════════════════════════════════════════╝
```

### 🔴 Error Level (ERROR)
```
ERROR in session xxx: <error details>
```

---

## Log Rotation

The log file can grow large over time. Here are management tips:

### Manual Cleanup
```bash
# Clear the log
python view_debug_log.py clear

# Or rename to archive
mv debug_info.log debug_info_backup_2025-10-23.log
```

### Automatic Rotation (PowerShell Script)

Create `rotate_debug_log.ps1`:
```powershell
# Rotate log if larger than 100MB
$logFile = "debug_info.log"
if (Test-Path $logFile) {
    $size = (Get-Item $logFile).Length / 1MB
    if ($size -gt 100) {
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        $backup = "debug_info_$timestamp.log"
        Move-Item $logFile $backup
        Write-Host "✅ Rotated log to $backup"
    }
}
```

Run before starting server:
```bash
powershell -File rotate_debug_log.ps1
python vLLMDeploy.py ...
```

---

## Privacy & Security

⚠️ **Important:** The debug log contains:
- Full user messages
- Complete conversation history
- All LLM responses

**Best Practices:**
1. ✅ Keep `debug_info.log` secure
2. ✅ Don't commit to public repositories (add to `.gitignore`)
3. ✅ Rotate/clear logs regularly
4. ✅ Review before sharing

**Add to .gitignore:**
```
debug_info.log
debug_info_*.log
```

---

## Example Analysis Session

### Scenario: User complains about incorrect responses

**Step 1: Find their session**
```bash
# Search for recent user messages
python view_debug_log.py view --lines 200 --search "USER MESSAGE"
```

**Step 2: Get their session ID**
From the output, identify: `Session: user-abc12345`

**Step 3: View full conversation**
```bash
python view_debug_log.py view --session user-abc12345 --lines 1000
```

**Step 4: Check what prompt LLM received**
Look at the "FULL PROMPT TO LLM" section. Check:
- ✅ Is system prompt correct?
- ✅ Is conversation history accurate?
- ✅ Are parameters appropriate?

**Step 5: Compare input vs output**
- What did user ask?
- What did LLM receive?
- What did LLM generate?
- What was sent back to user?

**Step 6: Identify issue**
Common findings:
- Chat template formatting issue
- Context being trimmed
- Wrong system prompt
- Temperature too high/low

---

## Tips & Tricks

### 1. Quick Stats Check
```bash
python view_debug_log.py stats
```
Shows message count, errors, unique sessions

### 2. Monitor Errors Only
```bash
python view_debug_log.py view --follow --search "ERROR"
```

### 3. Check Specific Project
```bash
python view_debug_log.py view --search "Project: driving"
```

### 4. Find Slow Generations
```bash
python view_debug_log.py view --search "Generation Time" | findstr /R "1[0-9]\.[0-9]"
# Find generation times > 10 seconds
```

### 5. Export Session Data
```bash
python view_debug_log.py view --session user-abc123 --lines 10000 > session_abc123.txt
```

---

## Troubleshooting

### Issue: Log file not created
**Cause:** Deployment hasn't received any messages yet

**Solution:** Send a test message with the client

### Issue: Log file too large
**Cause:** Many messages processed

**Solution:** 
```bash
python view_debug_log.py clear
```

### Issue: Can't find specific session
**Cause:** Session ID might be truncated in display

**Solution:** Use first 8 characters:
```bash
python view_debug_log.py view --session user-abc1
```

---

## Summary

✅ **All interactions are logged** to `debug_info.log`
✅ **View with:** `python view_debug_log.py view`
✅ **Follow live:** `python view_debug_log.py view --follow`
✅ **Get stats:** `python view_debug_log.py stats`
✅ **Clear log:** `python view_debug_log.py clear`

**Location:** Same directory as `vLLMDeploy.py`

Now you have complete visibility into every user interaction! 🔍

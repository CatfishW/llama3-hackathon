# Speech-to-Text (STT) Setup Guide

The Voice Chat feature now uses a robust server-side speech-to-text implementation that replaces the unreliable Web Speech API.

## How It Works

1. **Frontend**: Records audio using Web Audio API
2. **Backend**: Receives audio and transcribes using cloud APIs
3. **Fallback**: Automatically falls back to Web Speech API if backend is unavailable

## Setup Instructions

### Option 1: Using OpenAI Whisper API (Recommended)

**Best for**: High accuracy, reliable, supports 99 languages

#### Step 1: Get OpenAI API Key

1. Visit [OpenAI Platform](https://platform.openai.com/)
2. Sign up or log in
3. Go to API keys section
4. Create a new API key
5. Copy the key

#### Step 2: Configure Backend

Set the environment variable before running the server:

**Windows (PowerShell):**
```powershell
$env:OPENAI_API_KEY = "sk-..."
$env:STT_BACKEND = "openai"
python main.py
```

**Windows (Command Prompt):**
```cmd
set OPENAI_API_KEY=sk-...
set STT_BACKEND=openai
python main.py
```

**Linux/Mac:**
```bash
export OPENAI_API_KEY="sk-..."
export STT_BACKEND="openai"
python main.py
```

**Or add to `.env` file in backend directory:**
```
OPENAI_API_KEY=sk-...
STT_BACKEND=openai
```

#### Pricing
- $0.02 per minute of audio
- Very cost-effective for typical usage

---

### Option 2: Using AssemblyAI API

**Best for**: Fast processing, detailed transcription metadata

#### Step 1: Get AssemblyAI API Key

1. Visit [AssemblyAI](https://www.assemblyai.com/)
2. Sign up for free account
3. Get your API token from dashboard
4. Copy the token

#### Step 2: Configure Backend

**Windows (PowerShell):**
```powershell
$env:ASSEMBLYAI_API_KEY = "..."
$env:STT_BACKEND = "assemblyai"
python main.py
```

**Windows (Command Prompt):**
```cmd
set ASSEMBLYAI_API_KEY=...
set STT_BACKEND=assemblyai
python main.py
```

**Linux/Mac:**
```bash
export ASSEMBLYAI_API_KEY="..."
export STT_BACKEND="assemblyai"
python main.py
```

#### Pricing
- Free tier: 100 minutes/month
- Paid: $10.80 per 1000 minutes

---

## Testing STT Setup

### Check Backend Health

```bash
curl http://localhost:8000/api/stt/health
```

Should return:
```json
{
  "status": "healthy",
  "backend": "openai",
  "configured": true
}
```

### List Available Backends

```bash
curl http://localhost:8000/api/stt/backends
```

### Test Transcription

```bash
# Create a test audio file (or use existing .wav/.mp3 file)
curl -X POST http://localhost:8000/api/stt/transcribe \
  -F "file=@test_audio.wav" \
  -F "language=en"
```

---

## Using in Voice Chat

Once configured:

1. Navigate to Voice Chat page
2. Click and hold the "Talk" button
3. Speak your message
4. Release the button

The process:
- ✅ Records your audio
- ✅ Sends to backend for transcription
- ✅ Displays "✨ Transcribing..."
- ✅ Shows final text when ready
- ✅ Sends to LLM and gets response
- ✅ Plays audio response

---

## Troubleshooting

### "OpenAI API key not configured" Error

**Solution**: Make sure you set the `OPENAI_API_KEY` environment variable before starting the server.

Verify with:
```powershell
echo $env:OPENAI_API_KEY
```

### "AssemblyAI API error" or Timeout

**Solution**: 
- Check your internet connection
- Verify API key is correct
- Try OpenAI backend instead
- Check AssemblyAI service status

### Fallback to Web Speech API

If the backend STT doesn't work, the system automatically falls back to Web Speech API. You'll see console logs like:
```
[STT] Transcription error: ...
[STT] Attempting Web Speech API fallback...
```

Check browser console (F12) for more details.

### Empty Audio Blob

**Issue**: "Empty audio blob" message

**Solution**:
- Make sure you're actually speaking into the microphone
- Check microphone permissions
- Try in a different browser
- Clear browser cache

---

## API Endpoints

### POST `/api/stt/transcribe`
Transcribe audio file to text

**Parameters:**
- `file` (FormData): Audio file (WAV, MP3, M4A, FLAC, WebM, etc.)
- `language` (optional): Language code (default: 'en')

**Response:**
```json
{
  "text": "transcribed text here",
  "confidence": 0.95,
  "language": "en",
  "backend": "openai"
}
```

### GET `/api/stt/health`
Check if STT service is configured and healthy

**Response:**
```json
{
  "status": "healthy",
  "backend": "openai",
  "configured": true
}
```

### GET `/api/stt/backends`
List available backends and their configuration status

**Response:**
```json
{
  "backends": {
    "openai": {
      "configured": true,
      "description": "OpenAI Whisper API (cloud-based, very reliable)"
    },
    "assemblyai": {
      "configured": false,
      "description": "AssemblyAI API (cloud-based, fast)"
    }
  },
  "current": "openai",
  "note": "Configure backends via environment variables..."
}
```

---

## Best Practices

1. **Choose OpenAI** for best accuracy and language support
2. **Monitor API usage** in your provider dashboard
3. **Test with real audio** before deployment
4. **Use HTTPS in production** for secure audio transmission
5. **Consider rate limiting** on the backend if publicly exposed
6. **Log transcriptions** for debugging (be mindful of privacy)

---

## Environment Variables Reference

```bash
# STT Backend Selection
STT_BACKEND=openai          # or 'assemblyai'

# OpenAI Configuration
OPENAI_API_KEY=sk-...

# AssemblyAI Configuration
ASSEMBLYAI_API_KEY=...

# Backend Server (if needed)
LLM_SERVER_URL=http://localhost:8000
```

---

## Advanced: Custom Backend Implementation

To add support for another STT provider, edit `/backend/app/routers/stt.py`:

1. Create a new function `transcribe_with_provider()`
2. Add a new condition in the `@router.post("/transcribe")` endpoint
3. Update environment variable checks
4. Test with the health endpoint

Example structure:
```python
async def transcribe_with_custom(audio_data: bytes, language: str) -> dict:
    # Your implementation
    return {
        "text": "transcribed text",
        "confidence": 0.95,
        "language": language,
        "backend": "custom"
    }
```

---

## Support

- **Errors in browser console**: Press F12 and check Console tab
- **Backend logs**: Check terminal output where server is running
- **API status**: Visit `/api/stt/health` endpoint
- **Integration issues**: Review VoiceChat.tsx hook implementation


# Voice Chat Integration Guide
## SST (Whisper.cpp) + TTS (Kokoro) + FastAPI Backend

This guide integrates your SST (Speech-to-Text) and TTS (Text-to-Speech) broker servers with the FastAPI backend for real-time voice chat capabilities.

---

## 📋 Architecture Overview

```
┌─────────────┐          ┌─────────────┐
│   Client    │          │   Client    │
│  (Browser)  │          │ (Mobile)    │
└──────┬──────┘          └──────┬──────┘
       │                        │
       └──────────┬─────────────┘
                  │
        ┌─────────▼─────────┐
        │  FastAPI Backend  │
        │  /api/voice/*     │
        └─────────┬─────────┘
                  │
      ┌───────────┼───────────┐
      │           │           │
      ▼           ▼           ▼
   ┌──────┐   ┌──────┐   ┌──────┐
   │ SST  │   │ TTS  │   │ MQTT │
   │Broker│   │Broker│   │Bridge│
   └──┬───┘   └───┬──┘   └──────┘
      │           │
      ▼           ▼
┌──────────┐ ┌──────────┐
│Whisper.  │ │ Kokoro   │
│cpp Server│ │TTS Server│
└──────────┘ └──────────┘
```

---

## 🚀 Setup Instructions

### 1. Environment Variables Configuration

Add these to your `.env` file:

```env
# SST (Speech-to-Text) Configuration
SST_BROKER_HOST=0.0.0.0
SST_BROKER_PORT=9082
SST_BROKER_URL=http://localhost:9082
SST_REQUEST_TIMEOUT=300.0
SST_BROKER_LOG_LEVEL=INFO

# TTS (Text-to-Speech) Configuration
TTS_BROKER_HOST=0.0.0.0
TTS_BROKER_PORT=8080
TTS_BROKER_URL=http://localhost:8080
TTS_REQUEST_TIMEOUT=30.0
TTS_BROKER_LOG_LEVEL=INFO

# Remote SST Server (if broker is on different machine)
REMOTE_SST_HOST=localhost
REMOTE_SST_PORT=8082
REMOTE_SST_URL=http://localhost:8082

# Remote TTS Server (if broker is on different machine)
REMOTE_TTS_HOST=localhost
REMOTE_TTS_PORT=8081
REMOTE_TTS_URL=http://localhost:8081
```

### 2. Update Backend Configuration

Edit `backend/app/config.py` to include voice settings:

```python
# Voice Chat Configuration
SST_BROKER_URL: str = os.getenv("SST_BROKER_URL", "http://localhost:9082")
SST_REQUEST_TIMEOUT: float = float(os.getenv("SST_REQUEST_TIMEOUT", "300.0"))

TTS_BROKER_URL: str = os.getenv("TTS_BROKER_URL", "http://localhost:8080")
TTS_REQUEST_TIMEOUT: float = float(os.getenv("TTS_REQUEST_TIMEOUT", "30.0"))

# Available TTS Voices
TTS_VOICES: list = ["af_heart", "af", "am", "bf", "bm"]
TTS_DEFAULT_VOICE: str = "af_heart"
TTS_DEFAULT_SPEED: float = 1.0
```

### 3. Register Voice Chat Router

Update `backend/app/main.py`:

```python
from app.routers import voice_chat

app.include_router(voice_chat.router)
```

### 4. Start Services

**Terminal 1 - SST Broker (Whisper.cpp):**
```powershell
cd z:\llama3_20250528\llama3\SST
python publicip_server_whisper_sst.py --port 9082 --remote-host localhost --remote-port 8082
```

**Terminal 2 - TTS Broker (Kokoro):**
```powershell
cd z:\llama3_20250528\llama3\TTS
python publicip_server_kokoro_tts.py --port 8080 --remote-host localhost --remote-port 8081
```

**Terminal 3 - FastAPI Backend:**
```powershell
cd z:\llama3_20250528\llama3\Hackathon\prompt-portal\backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 📡 API Endpoints

### REST API

#### 1. Transcribe Audio (SST)

**Endpoint:** `POST /api/voice/transcribe`

**Request:**
```bash
curl -X POST http://localhost:8000/api/voice/transcribe \
  -F "file=@audio.wav" \
  -F "language=en"
```

**Response:**
```json
{
  "text": "Hello, how are you?",
  "language": "en",
  "confidence": null,
  "duration_seconds": 1.5,
  "model": "whisper.cpp"
}
```

#### 2. Synthesize Speech (TTS)

**Endpoint:** `POST /api/voice/synthesize`

**Request:**
```bash
curl -X POST http://localhost:8000/api/voice/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is a test",
    "voice": "af_heart",
    "lang_code": "a",
    "speed": 1.0
  }'
```

**Response:**
```json
{
  "audio_base64": "UklGRiY...",
  "audio_sample_rate": 24000,
  "audio_duration_seconds": 2.3,
  "voice": "af_heart",
  "speed": 1.0
}
```

#### 3. Stream Audio (Direct MP3/WAV)

**Endpoint:** `POST /api/voice/audio-stream`

**Request:**
```bash
curl -X POST http://localhost:8000/api/voice/audio-stream \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello world",
    "voice": "af_heart"
  }' \
  -o output.wav
```

**Response:** Audio file (WAV format)

#### 4. Get Available Voices

**Endpoint:** `GET /api/voice/voices`

**Response:**
```json
{
  "voices": ["af_heart", "af", "am", "bf", "bm"],
  "default_voice": "af_heart",
  "service": "Kokoro TTS"
}
```

#### 5. Health Check

**Endpoint:** `GET /api/voice/health`

**Response:**
```json
{
  "status": "healthy",
  "sst_service": "http://localhost:9082",
  "tts_service": "http://localhost:8080",
  "sst_healthy": true,
  "tts_healthy": true
}
```

### WebSocket API (Real-time Voice Chat)

**Endpoint:** `WS /api/voice/ws/chat`

#### Connect & Transcribe

```javascript
// Connect
const ws = new WebSocket('ws://localhost:8000/api/voice/ws/chat');

// Send audio for transcription
ws.send(JSON.stringify({
  type: 'transcribe',
  audio_base64: '<base64-encoded-audio>',
  language: 'en'
}));

// Receive transcription
ws.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'transcription') {
    console.log('Transcribed:', data.text);
  }
});
```

#### Send for Synthesis

```javascript
// Synthesize text
ws.send(JSON.stringify({
  type: 'synthesize',
  text: 'Hello, this is a test',
  voice: 'af_heart',
  lang_code: 'a',
  speed: 1.0
}));

// Receive audio
ws.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'audio') {
    console.log('Audio:', data.audio_base64);
    console.log('Duration:', data.duration_seconds);
  }
});
```

#### Keep-Alive Ping

```javascript
// Keep connection alive
setInterval(() => {
  ws.send(JSON.stringify({ type: 'ping' }));
}, 30000);

ws.addEventListener('message', (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'pong') {
    console.log('Connection alive');
  }
});
```

---

## 🔌 Integration with Message Router

Add voice capabilities to existing chat messages:

```python
# In messages.py router
from app.routers.voice_chat import _transcribe_audio, _synthesize_speech

@router.post("/api/messages/voice")
async def send_voice_message(
    file: UploadFile = File(...),
    conversation_id: str = Query(...),
    user_id: str = Query(...),
    language: str = Query("en")
):
    """Send a voice message in a conversation"""
    try:
        # Transcribe voice message
        audio_data = await file.read()
        transcription = await _transcribe_audio(audio_data, language)
        
        # Create text message from transcription
        message = await create_message(
            conversation_id=conversation_id,
            user_id=user_id,
            text=transcription["text"],
            message_type="voice",
            metadata={"transcription": transcription}
        )
        
        # Synthesize response if needed
        if message.get("assistant_response"):
            audio_response = await _synthesize_speech(
                text=message["assistant_response"]["text"]
            )
            message["assistant_audio"] = audio_response["audio_base64"]
        
        return message
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
```

---

## 🎤 Frontend Integration Examples

### React Component Example

```jsx
import React, { useRef, useState } from 'react';

const VoiceChatComponent = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [audioUrl, setAudioUrl] = useState('');
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);

  const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder.current = new MediaRecorder(stream);
    audioChunks.current = [];

    mediaRecorder.current.addEventListener('dataavailable', (event) => {
      audioChunks.current.push(event.data);
    });

    mediaRecorder.current.start();
    setIsRecording(true);
  };

  const stopRecording = async () => {
    mediaRecorder.current.stop();
    setIsRecording(false);

    // Convert audio to base64
    const audioBlob = new Blob(audioChunks.current);
    const reader = new FileReader();

    reader.onload = async (e) => {
      const base64Audio = e.target.result.split(',')[1];

      // Transcribe
      const transcribeResponse = await fetch('/api/voice/transcribe', {
        method: 'POST',
        body: JSON.stringify({
          audio_base64: base64Audio,
          language: 'en'
        })
      });

      const transcribeData = await transcribeResponse.json();
      setTranscript(transcribeData.text);

      // Synthesize response
      const synthesizeResponse = await fetch('/api/voice/audio-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: `You said: ${transcribeData.text}`,
          voice: 'af_heart'
        })
      });

      const audioBlob = await synthesizeResponse.blob();
      setAudioUrl(URL.createObjectURL(audioBlob));
    };

    reader.readAsDataURL(audioBlob);
  };

  return (
    <div>
      <button onClick={startRecording} disabled={isRecording}>
        🎤 Start Recording
      </button>
      <button onClick={stopRecording} disabled={!isRecording}>
        ⏹️ Stop Recording
      </button>

      {transcript && <p>Transcript: {transcript}</p>}

      {audioUrl && (
        <audio controls src={audioUrl}>
          Your browser does not support the audio element.
        </audio>
      )}
    </div>
  );
};

export default VoiceChatComponent;
```

---

## 🐛 Troubleshooting

### SST Broker Connection Issues

**Problem:** `Failed to connect to SST broker`

**Solution:**
1. Check if SST broker is running on port 9082
2. Verify `REMOTE_SST_HOST` and `REMOTE_SST_PORT` are correct
3. Check firewall rules

```powershell
# Test connectivity
curl http://localhost:9082/healthz
```

### TTS Broker Connection Issues

**Problem:** `Failed to connect to TTS broker`

**Solution:**
1. Check if TTS broker is running on port 8080
2. Verify `REMOTE_TTS_HOST` and `REMOTE_TTS_PORT` are correct
3. Check firewall rules

```powershell
# Test connectivity
curl http://localhost:8080/healthz
```

### Audio Playback Issues

**Problem:** Garbled or no audio output

**Solution:**
1. Check audio sample rate (should be 24000 Hz)
2. Verify base64 decoding is correct
3. Test audio with direct file output

```bash
curl -X POST http://localhost:8000/api/voice/synthesize \
  -H "Content-Type: application/json" \
  -d '{"text": "Test"}' \
  | python -m json.tool
```

### Timeout Issues

**Problem:** `Request timed out` errors

**Solution:**
1. Increase `SST_REQUEST_TIMEOUT` for long audio files
2. Check SST server performance
3. Monitor network latency

```env
# Increase timeouts for slower networks
SST_REQUEST_TIMEOUT=600.0  # 10 minutes
TTS_REQUEST_TIMEOUT=60.0   # 1 minute
```

---

## 📊 Performance Optimization

### 1. Audio Compression

Before sending audio to SST broker, compress it:

```python
import librosa
import numpy as np

def compress_audio(audio_bytes, sample_rate=16000, target_rate=16000):
    """Compress audio for faster transmission"""
    y, sr = librosa.load(audio_bytes, sr=target_rate)
    y = librosa.effects.trim(y, top_db=25)[0]
    return librosa.output.write_wav(y, sr=target_rate)
```

### 2. Caching Synthesis Results

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
async def _synthesize_cached(text: str, voice: str, speed: float) -> dict:
    """Cache synthesis results for identical requests"""
    return await _synthesize_speech(text, voice, lang_code="a", speed=speed)
```

### 3. Batch Processing

```python
@router.post("/api/voice/synthesize-batch")
async def synthesize_batch(requests: List[VoiceSynthesisRequest]):
    """Process multiple synthesis requests efficiently"""
    results = []
    for request in requests:
        result = await _synthesize_speech(
            text=request.text,
            voice=request.voice,
            lang_code=request.lang_code,
            speed=request.speed
        )
        results.append(result)
    return results
```

---

## 📝 Logging & Monitoring

### Enable Debug Logging

```env
# Set log levels
SST_BROKER_LOG_LEVEL=DEBUG
TTS_BROKER_LOG_LEVEL=DEBUG
BACKEND_LOG_LEVEL=DEBUG
```

### Monitor Service Health

```python
import asyncio
from datetime import datetime

async def monitor_voice_services():
    """Continuous health monitoring"""
    while True:
        response = await client.get('/api/voice/health')
        health = response.json()
        
        print(f"[{datetime.now()}] Voice Services Health:")
        print(f"  Overall: {health['status']}")
        print(f"  SST: {health['sst_healthy']}")
        print(f"  TTS: {health['tts_healthy']}")
        
        await asyncio.sleep(60)  # Check every minute
```

---

## 🔒 Security Considerations

1. **API Key Protection:**
   - Implement API key authentication for voice endpoints
   - Rate limit voice transcription (expensive operation)

2. **Audio Data Privacy:**
   - Audio files should not be logged
   - Store transcriptions securely
   - Implement data retention policies

3. **Network Security:**
   - Use HTTPS/WSS in production
   - Implement TLS between brokers and backend
   - Restrict access to SST/TTS brokers to internal network only

Example HTTPS wrapper:

```python
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "yourdomain.com"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📚 Related Documentation

- [SST Broker Documentation](../SST/publicip_server_whisper_sst.py)
- [TTS Broker Documentation](../TTS/publicip_server_kokoro_tts.py)
- [Backend Router Documentation](stt.py)
- [Backend Router Documentation](tts.py)

---

## 🤝 Contributing

To add new voice features:

1. Add new request/response models in `voice_chat.py`
2. Implement handler function using `_transcribe_audio()` or `_synthesize_speech()`
3. Create endpoint with proper error handling
4. Add WebSocket support if needed
5. Update this documentation

---

## 📞 Support

For issues or questions:
1. Check logs: `SST_BROKER_LOG_LEVEL=DEBUG` and `TTS_BROKER_LOG_LEVEL=DEBUG`
2. Test connectivity: `curl http://localhost:9082/healthz` and `curl http://localhost:8080/healthz`
3. Review endpoint responses: Use Swagger UI at `http://localhost:8000/docs`

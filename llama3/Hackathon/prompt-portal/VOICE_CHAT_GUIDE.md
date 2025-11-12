# Voice Chat with LLM - Feature Guide

## Overview

The "Talk with LLM" feature enables users to have voice conversations with the LLM. Users can hold down a button to record their speech, which is automatically converted to text and sent to the LLM. The LLM's response is then converted back to speech and played to the user.

## Features

### 🎤 Speech-to-Text (STT)
- **Technology**: Web Speech API (native browser support)
- **Languages**: English (en-US) with easy multilingual extension
- **Confidence Scoring**: Real-time confidence feedback while speaking
- **Interim Results**: Live transcription as you speak
- **Final Results**: Confirmed text after speaking ends
- **Error Handling**: Graceful fallback and error reporting

### 🔊 Text-to-Speech (TTS)
- **Technology**: Kokoro TTS (high-quality neural voices)
- **Available Voices**:
  - `af_heart` (Female - Warm)
  - `af` (Female)
  - `am` (Male)
  - `bf` (Female - British)
  - `bm` (Male - British)
- **Speed Control**: 0.5x to 2.0x playback speed
- **Audio Format**: WAV with configurable sample rates
- **Response Streaming**: Fast synthesis and playback

### 🎨 User Interface
- **Beautiful Design**: Modern gradient-based UI with smooth animations
- **Talk Button**: Large, centered button with visual feedback
- **Recording Indicator**: Animated pulsing effect while recording
- **Waveform Visualization**: Real-time frequency and waveform display
- **Transcription Display**: Live interim and final transcription
- **Chat Bubbles**: User and assistant messages in conversation format
- **Mobile Responsive**: Full support for mobile and tablet devices
- **Dark Theme**: Eye-friendly gradient backgrounds with proper contrast

### ⚙️ Settings
- **Voice Selection**: Choose from 5 different voices
- **Speech Speed**: Adjust playback speed from 0.5x to 2.0x
- **Session Management**: Create and manage voice chat sessions
- **Export**: Copy conversation history to clipboard

## Architecture

### Frontend Components

#### `src/pages/VoiceChat.tsx`
Main page component for the voice chat interface. Handles:
- User interaction (hold-to-talk button)
- Message display and management
- Settings panel for voice and speed configuration
- Integration with hooks and utilities

#### `src/hooks/useVoiceRecorder.ts`
Custom React hook for audio recording and speech recognition:
- Manages microphone access via Web Audio API
- Integrates with Web Speech API for STT
- Provides audio visualization data
- Handles audio context and stream management
- Confidence tracking and transcript management

#### `src/hooks/useTTS.ts`
Custom React hook for text-to-speech:
- Calls Kokoro TTS API
- Manages audio playback
- Handles base64 audio decoding
- Provides playback controls (play, pause, resume, stop)
- Error handling and cleanup

#### `src/components/VoiceVisualizer.tsx`
Canvas-based audio visualization component:
- Renders frequency bars from audio analyser data
- Waveform display option
- Configurable styling and colors
- Real-time animation updates

### Backend Components

#### `backend/app/routers/tts.py`
FastAPI router for TTS service:
- **POST /api/tts/synthesize**: Converts text to speech
- **GET /api/tts/voices**: Lists available voices
- **GET /api/tts/health**: Health check for TTS service
- Proxies requests to Kokoro TTS server
- Handles audio encoding/decoding
- Error handling and timeout management

#### Integration Points
- **Chatbot API**: Uses existing `/api/chatbot/messages` for LLM responses
- **Kokoro TTS Server**: Proxied through backend TTS router
- **Web Speech API**: Browser-native STT integration

## How to Use

### Starting a Voice Chat Session

1. **Navigate**: Click "Voice" in the navbar (🎤 icon)
2. **Customize**: Use the ⚙️ Settings button to select voice and speed
3. **Talk**: Hold the large center button and speak your message
4. **Release**: Release the button to send your transcription to the LLM
5. **Listen**: The response plays automatically with audio feedback

### Session Management

- **Create Session**: Each voice chat session is independent
- **View History**: All messages appear in conversation bubbles
- **Clear Session**: Use the 🗑️ Clear button to start fresh
- **Copy Conversation**: Use 📋 Copy All to export the conversation

### Voice Settings

- **Voice Selection**: Choose from 5 different voice options in settings
- **Speech Speed**: Adjust playback speed while listening (0.5x - 2.0x)
- **Session Title**: Edit the session title for organization

## Configuration

### Environment Variables

Backend configuration via `.env`:

```env
# TTS Server Configuration
TTS_SERVER_URL=http://localhost:8081
TTS_REQUEST_TIMEOUT=30.0

# Chat Configuration
LLM_COMM_MODE=sse
LLM_SERVER_URL=http://localhost:8000
```

### Frontend Configuration

The voice chat automatically uses:
- Default system language for speech recognition
- Kokoro TTS server for audio synthesis
- Existing chatbot API for LLM responses

## Technical Details

### Web Audio API Integration

The `useVoiceRecorder` hook uses:
- **getUserMedia()**: Accesses microphone with echo cancellation
- **AudioContext**: Manages audio processing
- **AnalyserNode**: Provides frequency and waveform data
- **MediaRecorder**: Captures raw audio stream

### Web Speech API Integration

- **SpeechRecognition**: Browser-native speech recognition
- **Continuous mode**: Enables multi-word sentences
- **Interim results**: Shows text before user stops speaking
- **Final results**: Confirms completed utterances

### Audio Processing

STT Pipeline:
```
Microphone → AudioContext → AnalyserNode → SpeechRecognition → Transcription
                                        ↓
                           Frequency/Waveform Visualization
```

TTS Pipeline:
```
Text → Kokoro TTS API → Base64 Audio → Decode → Audio Element → Playback
```

## Browser Compatibility

### Required APIs
- **Web Audio API**: Chrome, Firefox, Safari, Edge
- **Web Speech API**: Chrome, Edge, Safari (iOS 14.5+)
- **MediaDevices.getUserMedia()**: All modern browsers

### Tested On
- Chrome 90+
- Firefox 88+
- Safari 14.5+
- Edge 90+
- Mobile Chrome/Firefox on Android
- Mobile Safari on iOS 14.5+

### Fallback Behavior
- If Web Speech API unavailable: Shows friendly error message
- If Kokoro TTS unavailable: Text response still displays
- If microphone access denied: Clear permission error

## Performance Optimizations

### Frontend
- **Lazy state updates**: Only update visualization at 50ms intervals
- **Audio context reuse**: Single shared audio context per session
- **Efficient canvas rendering**: Direct pixel manipulation for visualization
- **Debounced settings**: Settings changes auto-save after 500ms

### Backend
- **HTTP client pooling**: Reuses async HTTP client
- **Request timeout**: 30-second timeout for TTS requests
- **Async processing**: Non-blocking request forwarding
- **Error caching**: Returns sensible defaults on service unavailability

## Error Handling

### Common Issues

**"Microphone access denied"**
- Check browser permissions for microphone
- Try clearing site data and refreshing
- Works best in HTTPS (with exception for localhost)

**"Web Speech API not supported"**
- Browser doesn't support Web Speech API
- Try Chrome, Edge, or Safari
- Firefox has limited support

**"TTS server unavailable"**
- Check that Kokoro TTS server is running
- Verify TTS_SERVER_URL environment variable
- Text response still available even if TTS fails

**"Confidence very low"**
- Speak more clearly
- Reduce background noise
- Move closer to microphone
- Try different microphone if available

## Future Enhancements

1. **Language Support**
   - Add multilingual STT
   - Multi-language TTS voices
   - Auto-detect language

2. **Advanced Features**
   - Voice command recognition
   - Speaker identification
   - Accent adaptation
   - Custom voice training

3. **Performance**
   - WebRTC for improved audio quality
   - Local speech recognition models
   - Audio compression for faster transmission
   - Streaming TTS synthesis

4. **Accessibility**
   - Voice control for all features
   - Enhanced visual feedback
   - Screen reader support
   - Customizable audio settings

## Troubleshooting

### Microphone Issues
```bash
# Check browser microphone permissions
# Chrome: Settings → Privacy and security → Site settings → Microphone
# Firefox: Preferences → Privacy & Security → Permissions → Microphone
```

### TTS Server Connection
```bash
# Verify Kokoro TTS is running
curl http://localhost:8081/healthz

# Check backend TTS router
curl http://localhost:8000/api/tts/health
```

### Debug Console
- Open browser DevTools (F12)
- Go to Console tab
- Look for messages prefixed with "TTS Error:" or "STT Error:"
- Check Network tab for failed requests

## Integration with Existing Features

The Voice Chat feature integrates seamlessly with:

1. **Chat Studio**: Users can switch between text and voice chat
2. **Chatbot API**: Reuses existing session management
3. **Templates**: Can apply system prompts from templates
4. **LLM Service**: Works with both MQTT and SSE communication modes
5. **User Authentication**: Requires login like other features

## Code Examples

### Using Voice Recorder Hook

```typescript
const { 
  transcript, 
  isRecording, 
  startRecording, 
  stopRecording 
} = useVoiceRecorder({
  language: 'en-US',
  onTranscription: (text) => console.log('Got:', text),
  onError: (err) => console.error(err)
})

// Start recording
await startRecording()

// Stop and get final transcript
const finalText = await stopRecording()
```

### Using TTS Hook

```typescript
const { 
  isPlaying, 
  synthesizeAndPlay, 
  stop 
} = useTTS({
  voice: 'af_heart',
  speed: 1.0,
  onError: (err) => console.error(err)
})

// Speak text
await synthesizeAndPlay('Hello, world!', 'af_heart', 1.0)

// Stop playback
stop()
```

### Calling TTS API Directly

```typescript
import { ttsAPI } from '../api'

const result = await ttsAPI.synthesize({
  text: 'Hello there!',
  voice: 'af',
  lang_code: 'a',
  speed: 1.2
})

// Use result.audio_base64 to play audio
```

## License & Attribution

- **Web Speech API**: Browser native, W3C standard
- **Web Audio API**: Browser native, W3C standard
- **Kokoro TTS**: Integrated via publicip_server_kokoro_tts.py
- **UI Design**: Custom gradient-based theme

## Support & Feedback

For issues or feature requests:
1. Check the browser console for errors
2. Verify microphone and TTS server configuration
3. Test with a different browser
4. Review environment variables and API endpoints

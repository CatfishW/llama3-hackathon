# Voice Chat - Quick Start Guide

## 🚀 Start Using Voice Chat

### 1. Open Voice Chat
- Click the **🎤 Voice** button in the navbar
- Or navigate to `/voice-chat`

### 2. Talk to LLM
1. Hold down the large **💬 Talk** button in the center
2. Speak your message clearly
3. Release the button when done
4. Your speech appears as text
5. LLM response appears below
6. Response plays automatically

### 3. Listen Again
- Click **▶ Play** on any assistant message to replay
- Click **⏸ Stop** to stop playback

## ⚙️ Settings

Click **⚙️ Settings** to customize:

| Setting | Options | Effect |
|---------|---------|--------|
| 🎤 Voice | af_heart, af, am, bf, bm | Changes voice tone/gender |
| 🔊 Speed | 0.5x to 2.0x | Slower or faster speech |

## 📝 Message Management

| Action | Button | Result |
|--------|--------|--------|
| Clear all messages | 🗑️ Clear | Starts fresh |
| Copy conversation | 📋 Copy All | Copies all text to clipboard |
| Go back | ← Back | Returns to previous page |

## 🎯 Session Title

- Click title at top to rename your conversation
- Automatically saves

## 🐛 Troubleshooting

### Speech-to-Text Not Working?

1. **Check permissions**
   - Browser should ask for microphone access
   - Click "Allow" when prompted

2. **Check browser**
   - Works best in Chrome, Edge, Safari
   - Limited support in Firefox

3. **Check microphone**
   - Test in other apps first
   - Ensure not muted
   - Check volume settings

4. **Check server**
   - Backend must run on port 8000
   - Frontend must run on port 5173

### Not Hearing Response?

1. Check volume
2. Make sure TTS server is running (port 8081)
3. Look for "Could not play audio" error message
4. Check browser console (F12) for errors

## 📱 Mobile Usage

- Tap and hold the Talk button
- Works on iPhone, Android
- Responsive design adapts to screen size

## 🎤 Recording Tips

✅ **Do:**
- Speak clearly and naturally
- Use proper microphone
- Keep background noise low
- Speak at normal pace
- Be specific in requests

❌ **Don't:**
- Whisper or mumble
- Speak too fast
- Have loud background noise
- Speak too softly
- Use phone speaker as input

## 🔌 System Requirements

**Browser:**
- Chrome 90+ (Best)
- Edge 90+
- Safari 14.5+
- Firefox (Limited)

**Hardware:**
- Working microphone
- Speaker or headphones
- Stable internet connection

**Server:**
- Backend running on port 8000
- TTS server running on port 8081

## 🚀 Quick Actions

```
Hold → Talk button     Start recording
Release → Talk button  End recording, send text
Click ⚙️              Open/close settings
Click ← Back          Go to previous page
Click 📋 Copy All     Copy all messages
Click 🗑️ Clear       Clear all messages
Click ▶ Play          Replay message
Click ⏸ Stop         Stop playback
```

## 💡 Pro Tips

1. **Faster responses**: Use shorter, clearer messages
2. **Better accuracy**: Speak at natural pace
3. **Better audio**: Use headphones instead of speakers
4. **Batch questions**: Can ask multiple things in one message
5. **Settings**: Adjust speed if audio is hard to understand

## 🔍 Monitor Console (Developers)

Open DevTools with F12:
```
Console tab shows:
[STT] Speech recognition logs
[VoiceChat] Application logs
[TTS Error] Audio issues
```

## 📊 Voice Options

| Voice | Gender | Description | Best For |
|-------|--------|-------------|----------|
| af_heart | Female | Warm, friendly | Conversational |
| af | Female | Standard | General use |
| am | Male | Standard | Varied voice |
| bf | Female | British accent | Professional |
| bm | Male | British accent | Professional |

## ⏱️ Speed Settings

| Speed | Pace | Best For |
|-------|------|----------|
| 0.5x | Very slow | Comprehension |
| 0.75x | Slow | Clarity |
| 1.0x | Normal | Comfortable |
| 1.25x | Fast | Quick review |
| 1.5x | Very fast | Impatient |
| 2.0x | Extreme | Skimming |

## 🎯 Example Conversation

**You**: "What's the capital of France?"
```
[Hold Talk button] → [Speak] → [Release]
↓
Your message: "What's the capital of France?"
↓
Assistant: "The capital of France is Paris."
↓
[Auto-plays in selected voice]
```

## 🔗 Navigation

| Page | Link | Use For |
|------|------|---------|
| Voice Chat | /voice-chat | Talk with LLM |
| Text Chat | /chat | Type with LLM |
| Dashboard | /dashboard | Main hub |
| Settings | /settings | App settings |

## 💬 Message Format

```
👤 You [timestamp]
Blue bubble with your message

🤖 Assistant [timestamp]
Green bubble with AI response
```

## 🎓 Learning Path

1. **Start simple**: Ask basic questions
2. **Experiment**: Try different voices
3. **Adjust speed**: Find comfortable pace
4. **Use settings**: Customize experience
5. **Batch questions**: Ask complex things

## 📞 Need Help?

1. Check console (F12) for errors
2. Refresh page (Ctrl+R)
3. Try different browser
4. Check microphone settings
5. Restart backend server

---

**Happy voice chatting!** 🎤✨

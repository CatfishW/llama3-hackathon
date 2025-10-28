# TAB Completion Feature

This document describes the TAB completion feature implemented for the Prompt Portal, which provides intelligent completion suggestions for all input fields using the local LLM via MQTT.

## Overview

The TAB completion feature consists of three main components:

1. **Completion Service** (`completion_service.py`) - Backend MQTT service that handles completion requests
2. **Completion Client** (`frontend/src/completion/CompletionClient.ts`) - Frontend MQTT client for sending requests
3. **React Components** (`frontend/src/completion/TabCompletionInput.tsx`) - React components with built-in TAB completion

## Features

- **Context-aware completions** based on input field type (message, code, prompt, search, email, etc.)
- **Real-time suggestions** via MQTT
- **Integration with local LLM** using llamacpp_mqtt_deploy.py
- **Multiple completion modes** for different types of content
- **Rate limiting** to prevent abuse
- **Error handling** and fallback mechanisms

## Architecture

```
Frontend Input Field
        ↓
TabCompletionInput Component
        ↓
CompletionClient (MQTT)
        ↓
MQTT Broker
        ↓
completion_service.py
        ↓
llamacpp_mqtt_deploy.py (Local LLM)
```

## Installation

### Backend Dependencies

The completion service requires the same dependencies as `llamacpp_mqtt_deploy.py`:

```bash
pip install openai paho-mqtt fire
```

### Frontend Dependencies

The frontend requires the MQTT client:

```bash
npm install mqtt @types/mqtt
```

## Usage

### Starting the Completion Service

1. **Start the llama.cpp server** (if not already running):
```bash
llama-server -m qwen3-30b-a3b-instruct-2507-Q4_K_M.gguft --host 0.0.0.0 --port 8080 -c 28192 -ngl 35 -t 8 --parallel 8
```

2. **Start the completion service** (integrated into llamacpp_mqtt_deploy.py):
```bash
python llamacpp_mqtt_deploy.py --projects completion_service --server_url http://localhost:8080 --mqtt_username TangClinic --mqtt_password Tang123
```

3. **Or start multiple projects including completion**:
```bash
python llamacpp_mqtt_deploy.py --projects "maze,prompt_portal,completion_service" --server_url http://localhost:8080 --mqtt_username TangClinic --mqtt_password Tang123
```

### Using TAB Completion in Frontend

The TAB completion is automatically available in all input fields that use the `TabCompletionInput` or `TabCompletionTextarea` components:

```tsx
import { TabCompletionInput, TabCompletionTextarea } from '../completion/TabCompletionInput'

// For single-line inputs
<TabCompletionInput
  value={inputValue}
  onChange={(e) => setInputValue(e.target.value)}
  completionType="message"
  placeholder="Type your message..."
/>

// For multi-line inputs
<TabCompletionTextarea
  value={inputValue}
  onChange={(e) => setInputValue(e.target.value)}
  completionType="prompt"
  placeholder="Enter your prompt template..."
/>
```

### Completion Types

The system supports different completion types:

- **`general`** - General text completion
- **`code`** - Code completion with syntax awareness
- **`prompt`** - Prompt template completion
- **`message`** - Conversational message completion
- **`search`** - Search query completion
- **`email`** - Email text completion
- **`description`** - Descriptive text completion

## Configuration

### Completion Service Configuration

The completion service is configured via the main llamacpp_mqtt_deploy.py arguments:

```bash
python llamacpp_mqtt_deploy.py \
  --projects completion_service \
  --server_url http://localhost:8080 \
  --temperature 0.3 \
  --max_tokens 50 \
  --num_workers 8 \
  --mqtt_broker 47.89.252.2 \
  --mqtt_username TangClinic \
  --mqtt_password Tang123
```

### Frontend Configuration

The completion client can be configured in the `CompletionProvider`:

```tsx
<CompletionProvider
  broker="47.89.252.2"
  port={1883}
  username="TangClinic"
  password="Tang123"
>
  <App />
</CompletionProvider>
```

## Testing

### Manual Testing

1. **Start the completion service**:
```bash
python llamacpp_mqtt_deploy.py --projects completion_service --server_url http://localhost:8080 --mqtt_username TangClinic --mqtt_password Tang123
```

2. **Run the test script**:
```bash
python test_completion.py
```

3. **Test in the frontend**:
   - Open the Prompt Portal
   - Navigate to any page with input fields (Chat, Messages, Friends)
   - Type some text and press TAB to see completions

### Automated Testing

The test script (`test_completion.py`) performs comprehensive testing:

- Tests all completion types
- Verifies MQTT communication
- Checks response quality
- Measures response times

## Integration Points

### Current Integration

The TAB completion is currently integrated into:

1. **ChatStudio** - Message input with `completionType="message"`
2. **Messages** - Message input with `completionType="message"`
3. **Friends** - Search input with `completionType="search"`

### Adding to New Components

To add TAB completion to new input fields:

1. **Import the component**:
```tsx
import { TabCompletionInput } from '../completion/TabCompletionInput'
```

2. **Replace the input element**:
```tsx
// Instead of:
<input value={value} onChange={onChange} />

// Use:
<TabCompletionInput
  value={value}
  onChange={onChange}
  completionType="appropriate_type"
/>
```

3. **Choose appropriate completion type** based on the input field's purpose.

## Performance Considerations

### Rate Limiting

- **Per-client rate limiting**: 30 requests per minute per client
- **Server-side queue**: Maximum 500 pending requests
- **Timeout handling**: 5-second timeout for completion requests

### Optimization

- **Caching**: Completion responses are not cached (by design for freshness)
- **Debouncing**: Frontend debounces input to avoid excessive requests
- **Connection pooling**: Single MQTT connection per client

## Troubleshooting

### Common Issues

1. **"Completion client not connected"**
   - Check if MQTT broker is running
   - Verify MQTT credentials
   - Check network connectivity

2. **"Completion request timeout"**
   - Check if completion service is running
   - Verify llama.cpp server is running
   - Check server logs for errors

3. **Poor completion quality**
   - Adjust temperature parameter (lower = more focused)
   - Increase max_tokens for longer completions
   - Check if the LLM model is appropriate for the task

### Debugging

1. **Enable debug logging** in the completion service:
```bash
python completion_service.py --verbose
```

2. **Check browser console** for frontend errors

3. **Monitor MQTT traffic** using MQTT tools like MQTT Explorer

## Security Considerations

- **MQTT authentication** is required
- **Rate limiting** prevents abuse
- **Input validation** on both client and server
- **No sensitive data** is logged in completion requests

## Future Enhancements

- **Context awareness** - Use conversation history for better completions
- **User preferences** - Allow users to customize completion behavior
- **Offline mode** - Cache common completions for offline use
- **Multi-language support** - Support for different languages
- **Custom completion models** - Allow users to train custom completion models

## API Reference

### Completion Service API

**MQTT Topics:**
- `completion/request/{client_id}/{request_id}` - Send completion request
- `completion/response/{client_id}/{request_id}` - Receive completion response

**Request Format:**
```json
{
  "text": "Text to complete",
  "completion_type": "general|code|prompt|message|search|email|description",
  "temperature": 0.3,
  "top_p": 0.9,
  "max_tokens": 50
}
```

**Response Format:**
```json
{
  "request_id": "unique_request_id",
  "completion": "Completed text",
  "error": null,
  "timestamp": 1234567890.123
}
```

### Frontend API

**CompletionClient:**
```typescript
const client = new CompletionClient(options)
await client.connect()
const completion = await client.getCompletion({
  text: "Hello",
  completionType: "message"
})
```

**React Hooks:**
```typescript
const { getCompletion, loading, error } = useCompletion({
  completionType: "message",
  temperature: 0.3
})
```

## Contributing

When contributing to the TAB completion feature:

1. **Follow the existing code style**
2. **Add tests** for new functionality
3. **Update documentation** for API changes
4. **Consider performance impact** of changes
5. **Test with different completion types**

## License

This feature is part of the Prompt Portal project and follows the same license terms.

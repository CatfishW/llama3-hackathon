# OwOGPT Image Upload / Vision Support

This guide covers the new optional image upload capability added to the chat system.

## Summary
You can now send a chat message with one or more images. Images are encoded client-side as Data URLs (base64) and included in the JSON payload field `images`. The backend passes these along to the configured LLM provider (OpenAI, Ollama, or MQTT pipeline). OpenAI multi-modal models will receive both text and image parts; Ollama vision-capable models will get raw base64 in the `images` array; MQTT passes the list transparently for downstream consumers.

## API Changes
`POST /api/chat/messages`

Request body (JSON):
```
{
  "session_id": 123,
  "content": "Describe this image.", // optional when images present
  "images": ["data:image/png;base64,iVBORw0KGgo...", "data:image/jpeg;base64,/9j/4AAQ..."]
}
```
Rules:
- Either `content` (non-empty) or at least one image must be provided.
- Max 4 images per message.
- Max ~4MB base64 length per image, ~10MB total.
- When only images are sent, stored message content becomes `(image-only message)`.

Response (unchanged shape):
```
{
  "session": { ... },
  "user_message": { "metadata": {"image_count": 2}, ... },
  "assistant_message": { ... },
  "raw_response": { ... }
}
```

## Provider Handling
- OpenAI: Builds a multi-part `content` array combining text (`{"type":"text"}`) and each image as `{"type":"image_url"}` with a Data URL.
- Ollama: Adds an `images` array of raw base64 (Data URL prefix stripped) to the user message object.
- MQTT: Adds `images` array to published payload; downstream consumer must decide how to interpret.

## Frontend Usage
The `Chat` component now includes:
- Multiple image file picker (accepts images only).
- Preview thumbnails before sending.
- Images converted to Data URLs with `FileReader` and dispatched via `sendMessage(sessionId, content, images)`.

Edge cases handled:
- Sending images without text.
- Validation of type and length (approximate) server-side.

## Migration Notes
Existing clients can continue to send text-only messages; `content` is now optional server-side. If you have older code relying on `content` being required, adjust validation.

## Disabling Feature
If you need to temporarily disable image support:
1. Remove `images` field from `ChatMessageSendRequest` in `schemas.py`.
2. Remove image validations block in `routers/chat.py`.
3. Adjust frontend to hide file input.

## Future Improvements
- Persist images to disk or object storage instead of sending base64 (reduces payload size, enables reuse).
- Add server-side MIME sniffing for stricter validation.
- Implement streaming partial vision reasoning steps via SSE.
- Add automated tests for multi-modal messages.

## Quick Test
1. Start backend & frontend.
2. Open UI, select 1-2 small PNG/JPEG files.
3. Add prompt like: `What is in these pictures?`
4. Send. Confirm assistant responds referencing image contents (model must be vision-capable).

If the model replies `(no response)`, verify the configured model supports vision (e.g., OpenAI `gpt-4o` variants or an Ollama vision model like `llava`).

---
Last updated: 2025-11-09

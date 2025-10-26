# MQTT Polling Migration - Fix WebSocket Connection Issues

## Problem
The maze game (WebGame) and TestMQTT pages were unable to connect to the WebSocket endpoint at `wss://lammp.agaii.org/api/mqtt/ws/hints/session-xxx`, while the chatbot worked fine using MQTT directly.

## Solution
Migrated the maze game and test pages from WebSocket to **HTTP polling** with MQTT backend, matching the architecture that works for the chatbot.

## Changes Made

### 1. Backend Changes

#### `backend/app/mqtt.py`
- **Added timestamp to hints**: Modified `_handle_hint_message()` to add `data["timestamp"] = time.time()` to each hint
- This allows the frontend to detect new hints when polling

#### `backend/app/routers/mqtt_bridge.py`
- **Enhanced `/api/mqtt/last_hint` endpoint**: Now returns:
  ```json
  {
    "session_id": "session-xxx",
    "last_hint": {...},
    "has_hint": true,
    "timestamp": 1234567890.123
  }
  ```
- **Added new `/api/mqtt/request_hint` endpoint**: POST endpoint to request hints (publishes state to MQTT)
  - Accepts `session_id`, `template_id`, and `state` payload
  - Publishes to MQTT for LAM to process
  - Returns immediately (client polls for response)

### 2. Frontend Changes

#### `frontend/src/pages/WebGame.tsx`
- **Removed WebSocket connection code**
- **Added HTTP polling mechanism**:
  - Polls `/api/mqtt/last_hint?session_id=xxx` every 500ms
  - Tracks last seen hint timestamp to avoid reprocessing
  - Uses `pollingIntervalRef` to manage polling interval
  - All hint processing logic remains the same
- **Simplified connect/disconnect**: Now just toggles `connected` state (no actual WebSocket)

#### `frontend/src/pages/TestMQTT.tsx`
- **Same migration as WebGame**
- Removed WebSocket connection, auto-reconnect logic
- Added HTTP polling at 500ms intervals
- Updated UI to show "Using HTTP polling (500ms interval)" instead of reconnect settings

### 3. Deploy Script Changes (Optional)

#### `Hackathon/prompt-portal/deploy.sh`
- **Fixed Nginx WebSocket routing**: Changed regex patterns to exact prefix matches
  - `location ~ ^/api/mqtt/ws/` → `location /api/mqtt/ws/`
  - `location ~ ^/ws/` → `location /ws/`
- This fix is now optional since we're using HTTP polling, but improves WebSocket reliability if needed in future

## Architecture Comparison

### Before (WebSocket - Failed)
```
Frontend → WSS Connection → Nginx → Backend WebSocket → MQTT Subscriber
                ❌ Failed here (routing/upgrade issues)
```

### After (HTTP Polling - Works)
```
Frontend → HTTP Polling (500ms) → Nginx → Backend HTTP → MQTT (in memory)
                ✅ Works like chatbot
```

## Benefits

1. **Reliability**: No WebSocket connection issues with Nginx/SSL
2. **Consistency**: Same pattern as working chatbot
3. **Simplicity**: No complex WebSocket upgrade headers or routing
4. **Firewall-friendly**: Plain HTTP/HTTPS works everywhere
5. **Debugging**: Easy to test with curl/Postman

## Testing

To test the changes:

1. **Start the backend** (if not running):
   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 3000
   ```

2. **Rebuild and start frontend**:
   ```bash
   cd frontend
   npm run build
   npm run preview -- --host 0.0.0.0 --port 3001
   ```

3. **Test the maze game**:
   - Navigate to the Web Game page
   - Click "Connect" - should show connected status
   - Verify hints are received from MQTT

4. **Test MQTT page**:
   - Navigate to Test MQTT page
   - Connect and publish state
   - Verify hints appear in the message list

## Performance

- **Polling interval**: 500ms (2 polls/second)
- **Overhead**: Minimal - only polls when connected
- **Latency**: ~250ms average (half of polling interval)
- **Network usage**: ~2 requests/second (negligible for localhost/LAN)

## Rollback

If needed to rollback to WebSocket (after fixing Nginx routing):

1. Revert WebGame.tsx and TestMQTT.tsx to use WebSocket
2. Keep the backend changes (timestamps are still useful)
3. Ensure Nginx WebSocket routing is properly configured

## Notes

- The WebSocket endpoint `/api/mqtt/ws/hints/{session_id}` still exists but is not used
- MQTT backend continues to work as before
- Chatbot continues to use its direct MQTT request/response pattern
- This change makes all MQTT-based features consistent in architecture

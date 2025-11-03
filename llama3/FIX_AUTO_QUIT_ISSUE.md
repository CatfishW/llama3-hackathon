# Fix for Auto-Quit Issue

## Problem Identified

The script was automatically quitting after running for too long or processing too many requests due to **uncontrolled debug log file growth**.

### Root Cause

The `debug_info.log` file was configured to append indefinitely without any size limits or rotation. This caused:

1. **Disk Space Exhaustion**: The log file could grow to gigabytes in size
2. **I/O Performance Degradation**: Writing to huge log files causes slowdowns
3. **System Resource Exhaustion**: Eventually leading to crashes or automatic termination
4. **Excessive Logging**: Every request logged full conversation history, user inputs, and LLM outputs

## Solution Implemented

### 1. Log Rotation Added

Changed from simple `FileHandler` to `RotatingFileHandler`:

```python
# Before (UNLIMITED growth):
debug_handler = logging.FileHandler('debug_info.log', mode='a', encoding='utf-8')

# After (50MB limit with 3 backups = ~150MB total):
debug_handler = logging.handlers.RotatingFileHandler(
    'debug_info.log', 
    mode='a', 
    encoding='utf-8',
    maxBytes=50*1024*1024,  # 50 MB per file
    backupCount=3            # Keep 3 backup files
)
```

**Behavior**: When `debug_info.log` reaches 50MB, it's renamed to `debug_info.log.1`, and a new `debug_info.log` is created. Old backups are automatically deleted when exceeding 3 files.

### 2. Debug Logging Now Optional (Default: DISABLED)

Added a new parameter `--enable_debug_logging` (default: `False`):

```python
def main(
    ...
    enable_debug_logging: bool = False,  # NEW parameter
):
```

**Benefits**:
- Debug logging is OFF by default (prevents log file growth)
- Can be enabled only when troubleshooting: `--enable_debug_logging True`
- Significant performance improvement when disabled
- No disk space issues in production

### 3. User-Friendly Warnings

The script now clearly indicates debug logging status:

```
# When disabled (default):
Debug logging is DISABLED (enable with --enable_debug_logging True)
ℹ️  Debug logging disabled (enable with --enable_debug_logging True)

# When enabled:
Debug logging is ENABLED (writes to debug_info.log with rotation)
⚠️  Debug logging creates large files - only use for troubleshooting!
📝 Debug logging enabled: debug_info.log (with rotation: 50MB max, 3 backups)
```

## Usage Examples

### Production Use (Recommended)

```bash
# Debug logging OFF by default (no log file growth issues)
python llamacpp_mqtt_deploy.py --projects maze --server_url http://localhost:8080
```

### Troubleshooting Mode

```bash
# Enable debug logging temporarily for debugging
python llamacpp_mqtt_deploy.py --projects maze --enable_debug_logging True
```

### With Full Configuration

```bash
python llamacpp_mqtt_deploy.py \
    --projects "maze driving" \
    --server_url http://localhost:8080 \
    --mqtt_username TangClinic \
    --mqtt_password Tang123 \
    --enable_debug_logging False  # Explicitly disable
```

## Impact

### Before Fix
- ❌ Log file grows indefinitely (could reach 10+ GB)
- ❌ Disk I/O bottlenecks after processing thousands of requests
- ❌ Script crashes due to disk space exhaustion
- ❌ No way to disable debug logging

### After Fix
- ✅ Log file limited to ~150MB total (50MB × 3 backups)
- ✅ Debug logging disabled by default (no log growth)
- ✅ Can run indefinitely without crashes
- ✅ Optional debug logging for troubleshooting only
- ✅ Better performance without debug overhead

## Files Changed

- `llamacpp_mqtt_deploy.py`: 
  - Added `import logging.handlers`
  - Changed `FileHandler` to `RotatingFileHandler`
  - Added `enable_debug_logging` parameter
  - Added debug logging control logic
  - Updated docstring and help text

## Verification

To verify the fix is working:

1. Run the script normally (debug logging disabled):
   ```bash
   python llamacpp_mqtt_deploy.py --projects maze
   ```
   - You should see: `Debug logging is DISABLED`
   - No `debug_info.log` file will be created or grow

2. Enable debug logging temporarily:
   ```bash
   python llamacpp_mqtt_deploy.py --projects maze --enable_debug_logging True
   ```
   - You should see: `Debug logging is ENABLED`
   - `debug_info.log` will be created but limited to 50MB
   - When it reaches 50MB, it rotates to `debug_info.log.1`

## Recommendation

**For production use**: Always run with debug logging DISABLED (default behavior).

**For troubleshooting**: Enable debug logging temporarily, then disable it once the issue is resolved.

## Additional Notes

The script has no other automatic quit mechanisms. It's designed to run indefinitely via:
- `mqtt_client.loop_forever()` - maintains persistent MQTT connection
- Daemon threads for cleanup and statistics reporting
- Proper error handling without exits

The only way the script stops is:
1. User interrupts with Ctrl+C
2. Fatal unrecoverable errors (e.g., MQTT broker unavailable at startup)
3. System-level issues (out of memory, killed by OS, etc.)

With this fix, issue #3 (disk space exhaustion) is resolved.

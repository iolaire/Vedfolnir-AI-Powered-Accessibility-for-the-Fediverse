# WebSocket Troubleshooting Guide

## Overview
This guide helps troubleshoot WebSocket connection issues in Vedfolnir admin pages.

## Common Issues and Solutions

### 1. "WebSocket is closed due to suspension"

**Cause**: Browser suspends WebSocket connections due to inactivity or resource management.

**Solutions**:
- The WebSocket client now automatically falls back to polling mode
- Connection will retry with improved error handling
- Status indicator shows current connection state

### 2. Authentication Required Errors

**Cause**: WebSocket connections require user authentication.

**Solutions**:
- Ensure you're logged in before accessing admin pages
- WebSocket will auto-connect after page load and authentication check
- Manual reconnection available via status indicator

### 3. CORS Errors

**Cause**: Cross-origin request issues.

**Solutions**:
- Server is configured with `cors_allowed_origins="*"`
- Ensure you're accessing the correct domain/port
- Check browser console for specific CORS error messages

### 4. Rate Limiting

**Cause**: Too many connection attempts in short time.

**Solutions**:
- Wait for rate limit to reset (typically 1 minute)
- Avoid rapid reconnection attempts
- Status indicator will show rate limit status

## Debugging Tools

### Browser Console Commands

```javascript
// Check WebSocket environment
WebSocketDebug.runDiagnostics()

// Test connection manually
WebSocketDebug.testConnection()

// Check current status
WebSocketDebug.showStatus()

// Test Socket.IO endpoint
WebSocketDebug.testEndpoint()

// Force reconnection
window.VedfolnirWS.connect()

// Check connection status
window.VedfolnirWS.isConnected()
```

### Enable Debug Mode

Add `?debug=1` to admin URLs to enable debug logging:
```
http://127.0.0.1:5000/admin?debug=1
```

Or set localStorage flag:
```javascript
localStorage.setItem('websocket_debug', 'true')
```

### Test Script

Run the WebSocket connection test:
```bash
python tests/admin/test_websocket_connection.py
```

## Status Indicators

The WebSocket status indicator in the admin navbar shows:

- **🟢 Connected**: WebSocket working normally
- **🟡 Connecting**: Attempting to establish connection
- **🟡 Reconnecting**: Attempting to reconnect after disconnection
- **🟡 Suspended**: Connection suspended, using polling fallback
- **🟡 Rate Limited**: Too many connection attempts, waiting
- **🔵 Auth Required**: Authentication needed for connection
- **🔴 Error**: Connection error occurred
- **🔴 Failed**: Connection failed after maximum attempts
- **🔴 CORS Error**: Cross-origin request blocked

## Manual Connection

If auto-connection fails, use the retry button in the status indicator or run:

```javascript
window.VedfolnirWS.connect()
```

## Server-Side Checks

### Verify Socket.IO is Running

Check that the Flask app is started with Socket.IO:
```bash
# Should see Socket.IO initialization messages
python web_app.py
```

### Check Authentication

WebSocket connections require authenticated users:
- Ensure user is logged in
- Check session is valid
- Verify admin permissions for admin features

### Verify Dependencies

Ensure Flask-SocketIO is installed:
```bash
pip install flask-socketio>=5.3.0
```

## Configuration

### Environment Variables

```bash
# WebSocket Configuration
SOCKETIO_ASYNC_MODE=threading
SOCKETIO_CORS_ALLOWED_ORIGINS=*
SOCKETIO_MAX_CONNECTIONS=1000

# Session Configuration (affects WebSocket auth)
REDIS_SESSION_TIMEOUT=7200
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SECURE=true
```

### Transport Configuration

The client is configured to:
1. Try WebSocket first
2. Fall back to polling if WebSocket fails
3. Use polling-only if suspension detected
4. Retry with exponential backoff

## Real-time Features

When WebSocket is connected, admin pages support:

- **System Metrics**: Real-time system performance updates
- **Job Updates**: Live job status and progress
- **Admin Alerts**: Instant system notifications
- **Progress Tracking**: Real-time task progress updates

## Fallback Behavior

If WebSocket fails completely:
- Admin pages still function normally
- Real-time updates disabled
- Manual refresh required for latest data
- All core functionality remains available

## Getting Help

If issues persist:

1. Run full diagnostics: `WebSocketDebug.runDiagnostics()`
2. Check browser console for errors
3. Verify server logs for WebSocket errors
4. Test with the connection test script
5. Try different browsers/devices
6. Check network/firewall settings

## Recent Improvements

- **Enhanced Error Handling**: Better detection of suspension and CORS issues
- **Automatic Fallback**: Polling mode when WebSocket unavailable
- **Status Indicators**: Clear visual feedback on connection state
- **Debug Tools**: Comprehensive debugging utilities
- **Retry Logic**: Intelligent reconnection with exponential backoff
- **Authentication Checks**: Proper handling of auth requirements
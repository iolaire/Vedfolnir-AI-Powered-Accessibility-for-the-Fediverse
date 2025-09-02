# WebSocket CORS Troubleshooting Guide

## Overview

This guide helps diagnose and resolve common WebSocket CORS and connection issues in the Vedfolnir application. It covers error identification, root cause analysis, and step-by-step resolution procedures.

## Common CORS Issues

### 1. CORS Origin Not Allowed

**Symptoms:**
- Browser console error: "Access to XMLHttpRequest blocked by CORS policy"
- WebSocket connection fails immediately
- Network tab shows failed preflight requests

**Error Messages:**
```
CORS error: Origin 'http://localhost:3000' not allowed
WebSocket connection failed: CORS policy violation
```

**Diagnosis:**
```bash
# Check current CORS configuration
python -c "
from websocket_config_manager import WebSocketConfigManager
from config import Config
config = Config()
ws_config = WebSocketConfigManager(config)
print('Allowed origins:', ws_config.get_cors_origins())
"
```

**Resolution:**
1. **Check FLASK_HOST and FLASK_PORT**:
   ```bash
   # Verify environment variables match your actual server
   echo "FLASK_HOST: $FLASK_HOST"
   echo "FLASK_PORT: $FLASK_PORT"
   ```

2. **Update environment configuration**:
   ```bash
   # For development on localhost:3000
   FLASK_HOST=localhost
   FLASK_PORT=3000
   
   # Or explicitly set CORS origins
   SOCKETIO_CORS_ORIGINS=http://localhost:3000,https://localhost:3000
   ```

3. **Restart the application**:
   ```bash
   # Stop current process
   pkill -f "python web_app.py"
   
   # Start with new configuration
   python web_app.py & sleep 10
   ```

### 2. Localhost vs 127.0.0.1 Mismatch

**Symptoms:**
- Connection works with localhost but not 127.0.0.1 (or vice versa)
- Intermittent connection failures

**Error Messages:**
```
CORS error: Origin 'http://127.0.0.1:5000' not in allowed origins
```

**Resolution:**
1. **Use consistent addressing**:
   ```bash
   # Set FLASK_HOST to match your client
   FLASK_HOST=localhost  # If client uses localhost
   # OR
   FLASK_HOST=127.0.0.1  # If client uses 127.0.0.1
   ```

2. **The system automatically includes both variants for localhost**:
   ```python
   # Automatic inclusion when FLASK_HOST is localhost or 127.0.0.1
   # Both http://localhost:5000 and http://127.0.0.1:5000 will be allowed
   ```

### 3. HTTPS/HTTP Protocol Mismatch

**Symptoms:**
- Connection fails when switching between HTTP and HTTPS
- Mixed content warnings in browser

**Error Messages:**
```
Mixed Content: The page at 'https://example.com' was loaded over HTTPS, 
but attempted to connect to the insecure WebSocket endpoint 'ws://example.com'
```

**Resolution:**
1. **Ensure protocol consistency**:
   ```bash
   # For HTTPS sites, use WSS
   FLASK_HOST=example.com
   FLASK_PORT=443
   
   # Client should connect to wss://example.com
   ```

2. **Update client connection**:
   ```javascript
   // Use secure WebSocket for HTTPS sites
   const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
   const socket = io(`${protocol}//${window.location.host}`);
   ```

### 4. Preflight Request Failures

**Symptoms:**
- OPTIONS requests failing
- CORS preflight errors in network tab

**Error Messages:**
```
Preflight request failed: Method OPTIONS not allowed
Access-Control-Allow-Methods missing required method
```

**Resolution:**
1. **Check CORS methods configuration**:
   ```bash
   SOCKETIO_CORS_METHODS=GET,POST,OPTIONS
   ```

2. **Verify preflight handlers are registered**:
   ```python
   # This is handled automatically by the CORS manager
   # Check logs for preflight handler registration
   ```

## Connection Issues

### 1. WebSocket Connection Timeout

**Symptoms:**
- Connection attempts timeout
- Long delays before connection failure

**Error Messages:**
```
WebSocket connection timeout after 60 seconds
Connection failed: timeout
```

**Diagnosis:**
```bash
# Test WebSocket connectivity
python scripts/test_websocket_connection.py --host localhost --port 5000
```

**Resolution:**
1. **Adjust timeout settings**:
   ```bash
   SOCKETIO_CONNECT_TIMEOUT=30
   SOCKETIO_PING_TIMEOUT=20
   SOCKETIO_PING_INTERVAL=10
   ```

2. **Check network connectivity**:
   ```bash
   # Test basic connectivity
   curl -I http://localhost:5000
   
   # Test WebSocket upgrade
   curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
        -H "Sec-WebSocket-Version: 13" -H "Sec-WebSocket-Key: test" \
        http://localhost:5000/socket.io/
   ```

### 2. Transport Fallback Issues

**Symptoms:**
- WebSocket fails but polling doesn't activate
- Connection stuck in connecting state

**Error Messages:**
```
WebSocket transport failed, attempting fallback
Polling transport not available
```

**Resolution:**
1. **Enable transport fallback**:
   ```bash
   SOCKETIO_TRANSPORTS=websocket,polling
   ```

2. **Configure client fallback**:
   ```javascript
   const socket = io({
       transports: ['websocket', 'polling'],
       upgrade: true,
       rememberUpgrade: true
   });
   ```

### 3. Authentication Failures

**Symptoms:**
- Connection established but authentication fails
- User context not available in WebSocket handlers

**Error Messages:**
```
WebSocket authentication failed: Invalid session
User not authenticated for WebSocket connection
```

**Diagnosis:**
```bash
# Check session configuration
python -c "
from flask import Flask
app = Flask(__name__)
with app.app_context():
    from flask import session
    print('Session interface:', app.session_interface.__class__.__name__)
"
```

**Resolution:**
1. **Verify session configuration**:
   ```bash
   SESSION_COOKIE_NAME=session
   SESSION_COOKIE_HTTPONLY=true
   SESSION_COOKIE_SECURE=false  # Set to false for HTTP development
   SESSION_COOKIE_SAMESITE=Lax
   ```

2. **Check authentication flow**:
   ```python
   # Ensure user is logged in before WebSocket connection
   # Check browser cookies for session cookie
   ```

### 4. Rate Limiting Blocks

**Symptoms:**
- Connection rejected immediately
- Multiple connection attempts fail

**Error Messages:**
```
Connection rejected: Rate limit exceeded
Too many connection attempts from IP
```

**Resolution:**
1. **Adjust rate limiting**:
   ```bash
   SOCKETIO_RATE_LIMITING=false  # Disable for development
   SOCKETIO_RATE_LIMIT_CONNECTIONS=20  # Increase limit
   ```

2. **Clear rate limit cache**:
   ```bash
   # Restart application to clear rate limits
   pkill -f "python web_app.py"
   python web_app.py & sleep 10
   ```

## Browser-Specific Issues

### Chrome/Chromium

**Issue**: Strict CORS enforcement
**Solution**:
```bash
# For development only - disable web security
google-chrome --disable-web-security --user-data-dir=/tmp/chrome_dev
```

### Firefox

**Issue**: WebSocket connection blocked by tracking protection
**Solution**:
1. Disable tracking protection for localhost
2. Add localhost to exceptions in about:config

### Safari

**Issue**: Strict cookie handling
**Solution**:
```bash
# Ensure proper cookie configuration
SESSION_COOKIE_SAMESITE=None  # For cross-origin requests
SESSION_COOKIE_SECURE=true    # Required with SameSite=None
```

## Network Environment Issues

### Corporate Firewalls

**Symptoms:**
- WebSocket connections blocked
- Only HTTP polling works

**Resolution:**
1. **Use polling-only transport**:
   ```bash
   SOCKETIO_TRANSPORTS=polling
   ```

2. **Configure proxy settings**:
   ```javascript
   const socket = io({
       transports: ['polling'],
       forceNew: true,
       timeout: 60000
   });
   ```

### Reverse Proxy Issues

**Symptoms:**
- Connection works directly but fails through proxy
- WebSocket upgrade failures

**Resolution for Nginx**:
```nginx
location /socket.io/ {
    proxy_pass http://backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

**Resolution for Apache**:
```apache
ProxyPass /socket.io/ ws://localhost:5000/socket.io/
ProxyPassReverse /socket.io/ ws://localhost:5000/socket.io/
```

## Debugging Tools and Commands

### 1. WebSocket Connection Test

```bash
# Test basic WebSocket connectivity
python scripts/debug_websocket_connection.py
```

### 2. CORS Configuration Check

```bash
# Verify CORS configuration
python -c "
from websocket_cors_manager import CORSManager
from websocket_config_manager import WebSocketConfigManager
from config import Config

config = Config()
ws_config = WebSocketConfigManager(config)
cors_manager = CORSManager(ws_config)

print('Allowed origins:')
for origin in cors_manager.get_allowed_origins():
    print(f'  - {origin}')
"
```

### 3. Real-time Connection Monitoring

```bash
# Monitor WebSocket connections in real-time
python scripts/monitor_websocket_connections.py
```

### 4. Browser Developer Tools

**Chrome DevTools:**
1. Open DevTools (F12)
2. Go to Network tab
3. Filter by "WS" for WebSocket connections
4. Check connection status and messages

**Console Commands:**
```javascript
// Test WebSocket connection manually
const testSocket = io();
testSocket.on('connect', () => console.log('Connected'));
testSocket.on('disconnect', () => console.log('Disconnected'));
testSocket.on('connect_error', (error) => console.error('Connection error:', error));
```

## Error Log Analysis

### Common Log Patterns

**CORS Errors:**
```
ERROR: CORS origin validation failed for: http://localhost:3000
WARNING: Preflight request missing required headers
```

**Connection Errors:**
```
ERROR: WebSocket connection timeout for user: 123
WARNING: Transport fallback activated for session: abc123
```

**Authentication Errors:**
```
ERROR: WebSocket authentication failed: No valid session
WARNING: User context not available for WebSocket connection
```

### Log File Locations

```bash
# Main application logs
tail -f logs/webapp.log

# WebSocket-specific logs
tail -f logs/websocket_errors.log

# CORS-specific logs
tail -f logs/websocket_cors_errors.log
```

## Performance Troubleshooting

### High Connection Latency

**Diagnosis:**
```bash
# Check connection performance
python scripts/test_websocket_performance.py
```

**Resolution:**
1. **Optimize timeout settings**:
   ```bash
   SOCKETIO_PING_INTERVAL=15
   SOCKETIO_PING_TIMEOUT=30
   ```

2. **Use WebSocket-only transport**:
   ```bash
   SOCKETIO_TRANSPORTS=websocket
   ```

### Memory Usage Issues

**Diagnosis:**
```bash
# Monitor memory usage
python scripts/monitor_websocket_memory.py
```

**Resolution:**
1. **Limit connections per user**:
   ```bash
   SOCKETIO_MAX_CONNECTIONS_PER_USER=3
   ```

2. **Enable connection cleanup**:
   ```bash
   SOCKETIO_CONNECTION_CLEANUP_INTERVAL=300  # 5 minutes
   ```

## Emergency Procedures

### Complete WebSocket Reset

```bash
# 1. Stop the application
pkill -f "python web_app.py"

# 2. Clear any cached data
rm -rf __pycache__/websocket*
rm -f logs/websocket*.log

# 3. Reset configuration to defaults
cp config/websocket.env.default .env

# 4. Restart application
python web_app.py & sleep 10

# 5. Test basic connectivity
python scripts/test_websocket_basic.py
```

### Fallback to Polling Only

```bash
# Emergency fallback configuration
SOCKETIO_TRANSPORTS=polling
SOCKETIO_CORS_CREDENTIALS=false
SOCKETIO_RATE_LIMITING=false
```

## Getting Help

### Diagnostic Information Collection

Before seeking help, collect this information:

```bash
# System information
python --version
pip list | grep -E "(flask|socketio|eventlet|gevent)"

# Configuration dump
python scripts/dump_websocket_config.py

# Recent error logs
tail -50 logs/websocket_errors.log

# Connection test results
python scripts/test_websocket_comprehensive.py
```

### Support Resources

- **Documentation**: `docs/websocket-cors-configuration.md`
- **API Reference**: `docs/websocket-api-reference.md`
- **Migration Guide**: `docs/websocket-migration-guide.md`
- **GitHub Issues**: Report bugs and request features
- **Community Forum**: Get help from other users

## Prevention Best Practices

### Development
- Always test WebSocket connections in multiple browsers
- Use consistent localhost addressing (localhost vs 127.0.0.1)
- Enable debug logging during development
- Test both WebSocket and polling transports

### Staging
- Mirror production network configuration
- Test with realistic connection loads
- Validate CORS configuration with actual domains
- Test authentication flows thoroughly

### Production
- Monitor WebSocket connection health
- Set up alerting for connection failures
- Regularly review and update CORS origins
- Implement proper error logging and monitoring

### Security
- Regularly audit CORS configuration
- Monitor for unusual connection patterns
- Keep WebSocket libraries updated
- Implement proper rate limiting
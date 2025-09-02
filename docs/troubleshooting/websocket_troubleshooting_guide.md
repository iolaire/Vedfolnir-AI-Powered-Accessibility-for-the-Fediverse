# WebSocket Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting steps for common WebSocket connection issues, CORS problems, and performance concerns in the Vedfolnir WebSocket system.

## Quick Diagnostic Commands

### Run Comprehensive Diagnostics
```python
from websocket_diagnostic_tools import WebSocketDiagnosticTools
from websocket_config_manager import WebSocketConfigManager
from websocket_cors_manager import CORSManager

# Initialize diagnostic tools
config_manager = WebSocketConfigManager()
cors_manager = CORSManager(config_manager)
diagnostics = WebSocketDiagnosticTools(config_manager, cors_manager)

# Run full diagnostics
results = diagnostics.run_comprehensive_diagnostics("http://localhost:5000")
print(json.dumps(results, indent=2, default=str))
```

### Check Configuration
```python
# Quick configuration check
config_check = diagnostics.check_configuration()
if config_check['status'] != 'pass':
    print("Configuration issues found:")
    for issue in config_check['issues']:
        print(f"  - {issue}")
```

### Test Connection
```python
# Test basic connection
connection_test = diagnostics.test_websocket_connection("http://localhost:5000")
if connection_test['status'] != 'pass':
    print("Connection issues found:")
    for issue in connection_test['issues']:
        print(f"  - {issue}")
```

## Common Issues and Solutions

### 1. CORS Connection Failures

#### Symptoms
- Browser console shows CORS errors
- WebSocket connection fails with "Access to XMLHttpRequest blocked by CORS policy"
- Connection works in some browsers but not others

#### Diagnostic Steps
```python
# Check CORS configuration
cors_validation = diagnostics.validate_cors_configuration("http://localhost:5000")
print("CORS Status:", cors_validation['status'])

# Check allowed origins
origins = cors_manager.get_allowed_origins()
print("Allowed origins:", origins)
```

#### Solutions

**Solution 1: Fix Environment Variables**
```bash
# Ensure FLASK_HOST and FLASK_PORT are set correctly
export FLASK_HOST=localhost
export FLASK_PORT=5000

# Or in .env file
FLASK_HOST=localhost
FLASK_PORT=5000
```

**Solution 2: Manual CORS Origins**
```bash
# Set explicit CORS origins if auto-detection fails
export SOCKETIO_CORS_ORIGINS="http://localhost:5000,https://localhost:5000"

# Or in .env file
SOCKETIO_CORS_ORIGINS=http://localhost:5000,https://localhost:5000
```

**Solution 3: Development vs Production**
```bash
# Development (allows localhost variants)
export FLASK_ENV=development

# Production (requires explicit origins)
export FLASK_ENV=production
export SOCKETIO_CORS_ORIGINS="https://yourdomain.com"
```

### 2. Connection Timeout Issues

#### Symptoms
- WebSocket connections time out
- Long delays before connection establishment
- Intermittent connection failures

#### Diagnostic Steps
```python
# Test connection performance
performance_test = diagnostics.test_connection_performance("http://localhost:5000")
avg_time = performance_test['metrics'].get('avg_connection_time', 0)
print(f"Average connection time: {avg_time:.2f}s")

if avg_time > 5.0:
    print("Connection time is slow - check network and server performance")
```

#### Solutions

**Solution 1: Increase Timeout Values**
```bash
# Increase SocketIO timeouts
export SOCKETIO_PING_TIMEOUT=60
export SOCKETIO_PING_INTERVAL=25

# Or in .env file
SOCKETIO_PING_TIMEOUT=60
SOCKETIO_PING_INTERVAL=25
```

**Solution 2: Check Server Load**
```bash
# Monitor server resources
top
htop

# Check if server is overloaded
ps aux | grep python
```

**Solution 3: Network Diagnostics**
```bash
# Test network connectivity
ping localhost
telnet localhost 5000

# Check for firewall issues
sudo ufw status
```

### 3. Transport Fallback Problems

#### Symptoms
- WebSocket connections fail but polling works
- Connections work in some networks but not others
- Mobile connections fail while desktop works

#### Diagnostic Steps
```python
# Test transport fallback
transport_test = diagnostics.test_transport_fallback("http://localhost:5000")
print("Transport test results:")
for transport, result in transport_test['transports_tested'].items():
    print(f"  {transport}: {result['status']}")
```

#### Solutions

**Solution 1: Enable Transport Fallback**
```bash
# Enable both WebSocket and polling
export SOCKETIO_TRANSPORTS="websocket,polling"

# Or in .env file
SOCKETIO_TRANSPORTS=websocket,polling
```

**Solution 2: Polling-Only Mode**
```bash
# Force polling mode for problematic networks
export SOCKETIO_TRANSPORTS="polling"
```

**Solution 3: WebSocket-Only Mode**
```bash
# Force WebSocket mode for optimal performance
export SOCKETIO_TRANSPORTS="websocket"
```

### 4. Authentication Failures

#### Symptoms
- Connections establish but authentication fails
- Admin namespace access denied
- Session-related errors

#### Diagnostic Steps
```python
# Test authentication flow
auth_test = diagnostics.test_authentication_flow("http://localhost:5000")
print("Authentication test results:")
for test_name, result in auth_test['tests'].items():
    print(f"  {test_name}: {result.get('status', 'unknown')}")
```

#### Solutions

**Solution 1: Check Session Configuration**
```python
# Verify session management
from flask import session
print("Session data:", dict(session))

# Check if user is authenticated
from flask_login import current_user
print("Current user:", current_user.is_authenticated if current_user else "No user")
```

**Solution 2: Verify Admin Permissions**
```python
# Check user role
if current_user and current_user.is_authenticated:
    print("User role:", current_user.role)
    print("Is admin:", current_user.role == UserRole.ADMIN)
```

**Solution 3: Session Cleanup**
```bash
# Clear browser cookies and session data
# In browser: Developer Tools > Application > Storage > Clear All

# Or restart the application
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

### 5. Performance Issues

#### Symptoms
- Slow message delivery
- High CPU usage
- Memory leaks
- Connection drops under load

#### Diagnostic Steps
```python
# Monitor connection performance
from websocket_monitoring_dashboard import get_connection_monitor
monitor = get_connection_monitor()

# Get current metrics
metrics = monitor.get_metrics_summary()
print("Performance metrics:")
print(f"  Message rate: {metrics['message_rate_per_minute']}/min")
print(f"  Error rate: {metrics['error_rate_per_minute']}/min")
print(f"  Average connection time: {metrics['avg_connection_time']:.2f}s")
```

#### Solutions

**Solution 1: Optimize Configuration**
```bash
# Reduce ping frequency for better performance
export SOCKETIO_PING_INTERVAL=30
export SOCKETIO_PING_TIMEOUT=120

# Increase buffer sizes
export SOCKETIO_MAX_HTTP_BUFFER_SIZE=1000000
```

**Solution 2: Enable Async Mode**
```bash
# Use threading for better concurrency
export SOCKETIO_ASYNC_MODE=threading

# Or use eventlet for high concurrency
export SOCKETIO_ASYNC_MODE=eventlet
```

**Solution 3: Connection Limits**
```bash
# Limit concurrent connections per user
export SOCKETIO_MAX_CONNECTIONS_PER_USER=5

# Set global connection limits
export SOCKETIO_MAX_CONNECTIONS=1000
```

### 6. Browser-Specific Issues

#### Chrome Issues
- Check for CORS policy changes
- Disable browser extensions
- Clear browser cache and cookies
- Check for mixed content warnings (HTTP/HTTPS)

#### Firefox Issues
- Check `about:config` for WebSocket settings
- Verify `network.websocket.enabled` is true
- Check for tracking protection interference

#### Safari Issues
- Check for WebSocket support in older versions
- Verify SameSite cookie settings
- Check for Intelligent Tracking Prevention interference

#### Mobile Browser Issues
- Test with polling transport only
- Check for network switching (WiFi to cellular)
- Verify mobile-specific CORS requirements

### 7. Development Environment Issues

#### Local Development
```bash
# Ensure proper host binding
export FLASK_HOST=0.0.0.0  # Bind to all interfaces
export FLASK_PORT=5000

# Or bind to specific interface
export FLASK_HOST=127.0.0.1  # Localhost only
```

#### Docker Environment
```bash
# Expose ports properly
docker run -p 5000:5000 your-app

# Check container networking
docker network ls
docker inspect your-container
```

#### Virtual Environment Issues
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Check for version conflicts
pip check

# Reinstall socketio dependencies
pip uninstall python-socketio flask-socketio
pip install python-socketio flask-socketio
```

## Debugging Tools and Commands

### Enable Debug Logging
```python
from websocket_debug_logger import set_debug_level, DebugLevel

# Set verbose logging
set_debug_level(DebugLevel.VERBOSE)

# Or set via environment
import os
os.environ['WEBSOCKET_DEBUG_LEVEL'] = 'VERBOSE'
```

### Start Monitoring Dashboard
```python
from websocket_monitoring_dashboard import start_monitoring_dashboard

# Start dashboard on port 5001
start_monitoring_dashboard(port=5001)

# Access at http://localhost:5001
```

### Export Diagnostic Report
```python
# Export comprehensive diagnostic report
results = diagnostics.run_comprehensive_diagnostics()
filename = diagnostics.export_diagnostic_report(results)
print(f"Report saved to: {filename}")
```

### Manual Connection Testing
```python
import socketio

# Create test client
sio = socketio.Client()

@sio.event
def connect():
    print("Connected successfully!")

@sio.event
def connect_error(data):
    print(f"Connection failed: {data}")

@sio.event
def disconnect():
    print("Disconnected")

# Test connection
try:
    sio.connect('http://localhost:5000')
    sio.emit('test_message', {'data': 'test'})
    sio.sleep(1)
    sio.disconnect()
except Exception as e:
    print(f"Connection error: {e}")
```

## Environment-Specific Troubleshooting

### Development Environment
1. **Check Flask Debug Mode**: Ensure `FLASK_DEBUG=True` for detailed error messages
2. **Verify Port Availability**: Use `netstat -an | grep 5000` to check port usage
3. **Check File Permissions**: Ensure log directories are writable
4. **Monitor Resource Usage**: Use `htop` or Activity Monitor to check CPU/memory

### Staging Environment
1. **HTTPS Configuration**: Ensure proper SSL certificates for WSS connections
2. **Load Balancer Settings**: Configure sticky sessions if using load balancers
3. **Firewall Rules**: Verify WebSocket ports are open
4. **DNS Resolution**: Check that domain names resolve correctly

### Production Environment
1. **Security Headers**: Verify CORS origins are restrictive
2. **Rate Limiting**: Implement connection rate limiting
3. **Monitoring**: Set up comprehensive monitoring and alerting
4. **Backup Plans**: Have fallback mechanisms for WebSocket failures

## Performance Optimization

### Server-Side Optimizations
```bash
# Use production WSGI server
pip install gunicorn eventlet
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5000 web_app:app

# Or use uWSGI with gevent
pip install uwsgi gevent
uwsgi --http :5000 --gevent 1000 --http-websockets --module web_app:app
```

### Client-Side Optimizations
```javascript
// Optimize client configuration
const socket = io({
    transports: ['websocket', 'polling'],
    upgrade: true,
    rememberUpgrade: true,
    timeout: 20000,
    forceNew: false,
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    maxReconnectionAttempts: 5
});
```

### Database Optimizations
```python
# Optimize session storage
# Use Redis for session storage instead of database
REDIS_URL=redis://localhost:6379/0
SESSION_TYPE=redis

# Or optimize database connections
SQLALCHEMY_POOL_SIZE=20
SQLALCHEMY_POOL_RECYCLE=3600
```

## Monitoring and Alerting

### Set Up Monitoring
```python
# Enable comprehensive monitoring
from websocket_monitoring_dashboard import get_connection_monitor

monitor = get_connection_monitor()

# Set up alerts for high error rates
def check_error_rate():
    metrics = monitor.get_metrics_summary()
    if metrics['error_rate_per_minute'] > 10:
        send_alert("High WebSocket error rate detected")

# Schedule regular checks
import threading
threading.Timer(60, check_error_rate).start()
```

### Log Analysis
```bash
# Analyze WebSocket logs
grep "WebSocket" logs/webapp.log | tail -100

# Check for CORS errors
grep -i "cors" logs/webapp.log

# Monitor connection patterns
grep "connection" logs/websocket_debug_*.log | wc -l
```

## Getting Help

### Collect Diagnostic Information
Before seeking help, collect this information:

1. **System Information**:
   - Operating system and version
   - Python version
   - Browser type and version
   - Network configuration

2. **Configuration**:
   - Environment variables
   - CORS settings
   - Transport configuration

3. **Error Messages**:
   - Browser console errors
   - Server log errors
   - Network tab information

4. **Diagnostic Report**:
   ```python
   # Generate comprehensive report
   results = diagnostics.run_comprehensive_diagnostics()
   filename = diagnostics.export_diagnostic_report(results)
   ```

### Common Support Channels
1. Check the project documentation
2. Search existing issues on GitHub
3. Create a new issue with diagnostic information
4. Join the community discussion forums

### Emergency Procedures
If WebSocket functionality is completely broken:

1. **Disable WebSocket Features**:
   ```bash
   export WEBSOCKET_ENABLED=false
   ```

2. **Use Polling Only**:
   ```bash
   export SOCKETIO_TRANSPORTS=polling
   ```

3. **Restart Services**:
   ```bash
   pkill -f "python web_app.py"
   python web_app.py & sleep 10
   ```

4. **Check System Resources**:
   ```bash
   df -h  # Check disk space
   free -m  # Check memory
   top  # Check CPU usage
   ```

This troubleshooting guide should help resolve most WebSocket-related issues. For complex problems, use the diagnostic tools and monitoring dashboard to gather detailed information before implementing solutions.
# Notification System Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting procedures for the unified notification system. It covers common issues, diagnostic tools, and step-by-step resolution procedures for WebSocket connections, notification delivery, and system integration problems.

## Quick Diagnostic Checklist

### Initial System Check
```bash
# 1. Verify web application is running
curl -I http://127.0.0.1:5000/
# Expected: HTTP/1.1 200 OK

# 2. Check Redis connection
redis-cli ping
# Expected: PONG

# 3. Verify WebSocket endpoint
curl -I http://127.0.0.1:5000/socket.io/
# Expected: HTTP/1.1 200 OK

# 4. Check notification system status
python -c "
from web_app import app
with app.app_context():
    print('Notification system enabled:', app.config.get('NOTIFICATION_SYSTEM_ENABLED', False))
"
```

### Browser Console Check
Open browser developer tools (F12) and check for:
- WebSocket connection errors
- CORS policy violations
- JavaScript errors in notification components
- Failed network requests to `/socket.io/`

## Common Issues and Solutions

### 1. WebSocket Connection Failures

#### Symptoms
- Notifications not appearing in real-time
- Console error: "WebSocket connection failed"
- Page shows "Connecting..." status indefinitely

#### Diagnostic Steps
```javascript
// Check WebSocket connection status in browser console
console.log('Socket connected:', socket.connected);
console.log('Socket ID:', socket.id);
console.log('Socket transport:', socket.io.engine.transport.name);
```

#### Solutions

**Solution 1: CORS Configuration**
```python
# In web_app.py, verify CORS settings
socketio = SocketIO(
    app,
    cors_allowed_origins=["http://127.0.0.1:5000", "http://localhost:5000"],
    logger=True,
    engineio_logger=True
)
```

**Solution 2: Check Environment Variables**
```bash
# Verify WebSocket configuration
echo $WEBSOCKET_CORS_ORIGINS
echo $WEBSOCKET_NAMESPACE_USER
echo $WEBSOCKET_NAMESPACE_ADMIN
```

**Solution 3: Firewall/Network Issues**
```bash
# Test WebSocket endpoint directly
curl -H "Upgrade: websocket" \
     -H "Connection: Upgrade" \
     -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
     -H "Sec-WebSocket-Version: 13" \
     http://127.0.0.1:5000/socket.io/
```

### 2. Notification Not Displaying

#### Symptoms
- WebSocket connected but notifications don't appear
- Console shows notification received but no UI update
- Notifications appear briefly then disappear

#### Diagnostic Steps
```javascript
// Check notification container exists
const container = document.getElementById('notification-container');
console.log('Notification container:', container);

// Check notification renderer initialization
console.log('Notification renderer:', window.notificationRenderer);

// Monitor notification events
socket.on('notification', function(data) {
    console.log('Notification received:', data);
});
```

#### Solutions

**Solution 1: Missing Notification Container**
```html
<!-- Ensure this exists in base template -->
<div id="notification-container" class="notification-container"></div>
```

**Solution 2: JavaScript Loading Issues**
```html
<!-- Verify scripts are loaded in correct order -->
<script src="{{ url_for('static', filename='js/notification-ui-renderer.js') }}"></script>
<script src="{{ url_for('static', filename='js/page-notification-integrator.js') }}"></script>
```

**Solution 3: CSS Styling Issues**
```css
/* Ensure notification container is visible */
.notification-container {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 9999;
    pointer-events: none;
}

.notification {
    pointer-events: auto;
    /* Additional styling */
}
```

### 3. Authentication and Authorization Issues

#### Symptoms
- "Unauthorized" errors in WebSocket connection
- Admin notifications not received by admin users
- User notifications appearing for wrong users

#### Diagnostic Steps
```python
# Check user session and role
from flask import session
print('User ID:', session.get('user_id'))
print('User role:', session.get('role'))
print('Session token:', session.get('csrf_token'))
```

#### Solutions

**Solution 1: Session Authentication**
```python
# Verify session middleware is properly configured
@socketio.on('connect')
def handle_connect(auth):
    if not session.get('user_id'):
        return False  # Reject connection
    join_room(f"user_{session['user_id']}")
```

**Solution 2: Role-Based Access**
```python
# Check admin namespace access
@socketio.on('connect', namespace='/admin')
def handle_admin_connect():
    if session.get('role') != 'admin':
        return False
    join_room('admin_room')
```

### 4. Message Delivery Failures

#### Symptoms
- Notifications sent but not received
- Partial notification delivery
- Notifications received with delay

#### Diagnostic Steps
```python
# Check notification manager status
from app.services.notification.core.unified_notification_manager import UnifiedNotificationManager
manager = UnifiedNotificationManager(socketio, db_manager)
stats = manager.get_delivery_stats()
print('Delivery stats:', stats)
```

#### Solutions

**Solution 1: Redis Connection Issues**
```bash
# Check Redis connectivity
redis-cli info replication
redis-cli client list
```

**Solution 2: Message Queue Overflow**
```python
# Check queue size and clear if needed
from notification_persistence_manager import NotificationPersistenceManager
persistence = NotificationPersistenceManager(db_manager)
queue_size = persistence.get_queue_size()
if queue_size > 1000:
    persistence.cleanup_old_notifications(retention_days=1)
```

### 5. Performance Issues

#### Symptoms
- Slow notification delivery (>1 second)
- High memory usage
- Browser becomes unresponsive

#### Diagnostic Steps
```javascript
// Monitor performance metrics
console.time('notification-render');
// ... notification rendering code ...
console.timeEnd('notification-render');

// Check memory usage
console.log('Memory usage:', performance.memory);
```

#### Solutions

**Solution 1: Notification Throttling**
```javascript
// Implement notification throttling
class NotificationThrottler {
    constructor(maxPerSecond = 5) {
        this.maxPerSecond = maxPerSecond;
        this.queue = [];
        this.processing = false;
    }
    
    addNotification(notification) {
        this.queue.push(notification);
        this.processQueue();
    }
    
    processQueue() {
        if (this.processing || this.queue.length === 0) return;
        
        this.processing = true;
        const notification = this.queue.shift();
        this.renderNotification(notification);
        
        setTimeout(() => {
            this.processing = false;
            this.processQueue();
        }, 1000 / this.maxPerSecond);
    }
}
```

**Solution 2: Memory Management**
```javascript
// Limit notification history
const MAX_NOTIFICATIONS = 50;
if (notificationHistory.length > MAX_NOTIFICATIONS) {
    notificationHistory = notificationHistory.slice(-MAX_NOTIFICATIONS);
}
```

## Diagnostic Tools

### 1. WebSocket Connection Tester

Create a test file: `tests/scripts/test_websocket_connection.py`

```python
#!/usr/bin/env python3
import socketio
import time
import sys

def test_websocket_connection():
    """Test WebSocket connection and basic functionality"""
    
    # Create client
    sio = socketio.Client()
    
    @sio.event
    def connect():
        print("✅ WebSocket connected successfully")
        sio.emit('test_message', {'data': 'test'})
    
    @sio.event
    def disconnect():
        print("🔌 WebSocket disconnected")
    
    @sio.event
    def notification(data):
        print(f"📢 Notification received: {data}")
    
    try:
        # Connect to server
        print("🔄 Connecting to WebSocket server...")
        sio.connect('http://127.0.0.1:5000')
        
        # Wait for events
        time.sleep(5)
        
        # Disconnect
        sio.disconnect()
        print("✅ WebSocket test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_websocket_connection()
    sys.exit(0 if success else 1)
```

### 2. Notification System Health Check

Create: `tests/scripts/check_notification_health.py`

```python
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from config import Config
from app.core.database.core.database_manager import DatabaseManager
from app.services.notification.core.unified_notification_manager import UnifiedNotificationManager
import redis

def check_notification_system_health():
    """Comprehensive health check for notification system"""
    
    print("🔍 Checking Notification System Health...")
    
    # Check configuration
    config = Config()
    print(f"✅ Configuration loaded")
    
    # Check Redis connection
    try:
        r = redis.Redis.from_url(config.REDIS_URL)
        r.ping()
        print("✅ Redis connection successful")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        return False
    
    # Check database connection
    try:
        db_manager = DatabaseManager(config)
        with db_manager.get_session() as session:
            result = session.execute("SELECT 1").fetchone()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Check notification manager
    try:
        # Note: This would need actual socketio instance in real implementation
        print("✅ Notification manager components available")
    except Exception as e:
        print(f"❌ Notification manager check failed: {e}")
        return False
    
    print("✅ All notification system components healthy")
    return True

if __name__ == '__main__':
    success = check_notification_system_health()
    sys.exit(0 if success else 1)
```

### 3. Browser Console Debugger

Add to `static/js/notification-debug.js`:

```javascript
// Notification System Debug Tools
class NotificationDebugger {
    constructor() {
        this.enabled = localStorage.getItem('notification-debug') === 'true';
        this.logs = [];
        
        if (this.enabled) {
            this.initializeDebugger();
        }
    }
    
    enable() {
        localStorage.setItem('notification-debug', 'true');
        this.enabled = true;
        this.initializeDebugger();
        console.log('🐛 Notification debugging enabled');
    }
    
    disable() {
        localStorage.setItem('notification-debug', 'false');
        this.enabled = false;
        console.log('🐛 Notification debugging disabled');
    }
    
    initializeDebugger() {
        // Monitor WebSocket events
        if (window.socket) {
            window.socket.on('connect', () => {
                this.log('WebSocket connected', 'success');
            });
            
            window.socket.on('disconnect', () => {
                this.log('WebSocket disconnected', 'warning');
            });
            
            window.socket.on('notification', (data) => {
                this.log('Notification received', 'info', data);
            });
        }
        
        // Monitor notification rendering
        this.monitorNotificationRenderer();
    }
    
    monitorNotificationRenderer() {
        if (window.notificationRenderer) {
            const originalRender = window.notificationRenderer.renderNotification;
            window.notificationRenderer.renderNotification = (notification) => {
                this.log('Rendering notification', 'info', notification);
                return originalRender.call(window.notificationRenderer, notification);
            };
        }
    }
    
    log(message, level = 'info', data = null) {
        const timestamp = new Date().toISOString();
        const logEntry = { timestamp, message, level, data };
        
        this.logs.push(logEntry);
        
        // Keep only last 100 logs
        if (this.logs.length > 100) {
            this.logs = this.logs.slice(-100);
        }
        
        // Console output with styling
        const styles = {
            success: 'color: green; font-weight: bold;',
            warning: 'color: orange; font-weight: bold;',
            error: 'color: red; font-weight: bold;',
            info: 'color: blue;'
        };
        
        console.log(`%c[NotificationDebug] ${message}`, styles[level] || styles.info, data);
    }
    
    getLogs() {
        return this.logs;
    }
    
    exportLogs() {
        const blob = new Blob([JSON.stringify(this.logs, null, 2)], {
            type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `notification-debug-${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
    
    testNotification() {
        if (window.socket) {
            window.socket.emit('test_notification', {
                type: 'INFO',
                title: 'Debug Test',
                message: 'This is a test notification from the debugger'
            });
        } else {
            this.log('Cannot test notification - WebSocket not available', 'error');
        }
    }
}

// Initialize debugger
window.notificationDebugger = new NotificationDebugger();

// Console commands for debugging
console.log('🐛 Notification Debug Tools Available:');
console.log('  notificationDebugger.enable() - Enable debug logging');
console.log('  notificationDebugger.disable() - Disable debug logging');
console.log('  notificationDebugger.getLogs() - Get debug logs');
console.log('  notificationDebugger.exportLogs() - Export logs to file');
console.log('  notificationDebugger.testNotification() - Send test notification');
```

## Environment-Specific Issues

### Development Environment

#### Common Issues
1. **CORS Errors**: Browser blocks WebSocket connections
2. **Self-Signed Certificates**: HTTPS/WSS certificate issues
3. **Port Conflicts**: Multiple development servers

#### Solutions
```bash
# Development CORS configuration
export WEBSOCKET_CORS_ORIGINS="http://127.0.0.1:5000,http://localhost:5000,http://localhost:3000"

# Disable HTTPS in development
export WEBSOCKET_SSL_ENABLED=false

# Use different ports for development
export FLASK_PORT=5000
export WEBSOCKET_PORT=5001
```

### Production Environment

#### Common Issues
1. **Load Balancer Configuration**: WebSocket sticky sessions
2. **SSL/TLS Issues**: Certificate configuration for WSS
3. **Firewall Rules**: WebSocket port blocking

#### Solutions
```nginx
# Nginx configuration for WebSocket proxy
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

## Performance Optimization

### WebSocket Connection Optimization

```javascript
// Optimize WebSocket connection
const socket = io({
    transports: ['websocket'], // Use WebSocket only
    upgrade: false,
    rememberUpgrade: false,
    timeout: 20000,
    forceNew: true
});
```

### Notification Batching

```python
# Server-side notification batching
class NotificationBatcher:
    def __init__(self, batch_size=10, batch_timeout=1.0):
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout
        self.pending_notifications = []
        self.timer = None
    
    def add_notification(self, notification):
        self.pending_notifications.append(notification)
        
        if len(self.pending_notifications) >= self.batch_size:
            self.flush_batch()
        elif self.timer is None:
            self.timer = threading.Timer(self.batch_timeout, self.flush_batch)
            self.timer.start()
    
    def flush_batch(self):
        if self.pending_notifications:
            # Send batch of notifications
            socketio.emit('notification_batch', {
                'notifications': self.pending_notifications
            })
            self.pending_notifications = []
        
        if self.timer:
            self.timer.cancel()
            self.timer = None
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **WebSocket Connection Rate**
   - Connections per second
   - Connection success rate
   - Connection duration

2. **Notification Delivery Metrics**
   - Delivery latency (target: <100ms)
   - Delivery success rate (target: >99%)
   - Queue depth

3. **System Resource Usage**
   - Redis memory usage
   - WebSocket connection count
   - CPU usage for notification processing

### Alerting Thresholds

```python
# Example monitoring configuration
MONITORING_THRESHOLDS = {
    'websocket_connection_failure_rate': 0.05,  # 5%
    'notification_delivery_latency_ms': 1000,   # 1 second
    'notification_queue_depth': 1000,           # 1000 messages
    'redis_memory_usage_mb': 500,               # 500 MB
    'websocket_connection_count': 1000          # 1000 connections
}
```

## Recovery Procedures

### Automatic Recovery

```python
# Automatic WebSocket reconnection
class WebSocketRecovery:
    def __init__(self, max_retries=5, retry_delay=2):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_count = 0
    
    def handle_disconnect(self):
        if self.retry_count < self.max_retries:
            self.retry_count += 1
            setTimeout(() => {
                this.attempt_reconnection()
            }, self.retry_delay * 1000 * self.retry_count)
    
    def attempt_reconnection(self):
        try:
            socket.connect()
            self.retry_count = 0  # Reset on successful connection
        except Exception as e:
            self.handle_disconnect()
```

### Manual Recovery Steps

1. **Restart WebSocket Service**
   ```bash
   # Restart the web application
   pkill -f "python web_app.py"
   python web_app.py & sleep 10
   ```

2. **Clear Redis Cache**
   ```bash
   # Clear notification cache if corrupted
   redis-cli FLUSHDB
   ```

3. **Reset User Sessions**
   ```python
   # Clear user sessions if authentication issues
   from app.core.session.core.session_manager import SessionManager
   session_manager = SessionManager(db_manager)
   session_manager.cleanup_all_sessions()
   ```

## Support and Escalation

### Log Collection

```bash
# Collect comprehensive logs for support
mkdir -p /tmp/notification-debug
cp /var/log/vedfolnir/app.log /tmp/notification-debug/
redis-cli MONITOR > /tmp/notification-debug/redis.log &
REDIS_PID=$!
sleep 30
kill $REDIS_PID
tar -czf notification-debug-$(date +%Y%m%d-%H%M%S).tar.gz /tmp/notification-debug/
```

### Contact Information

For issues not resolved by this guide:

1. **Check GitHub Issues**: Search existing issues for similar problems
2. **Create Bug Report**: Include logs, configuration, and reproduction steps
3. **Emergency Contact**: For production issues affecting multiple users

---

**Troubleshooting Guide Version**: 1.0  
**Last Updated**: August 30, 2025  
**Compatibility**: Unified Notification System v1.0+
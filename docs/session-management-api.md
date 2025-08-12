# Session Management API Documentation

This document provides comprehensive developer documentation for the Vedfolnir session management system, including API usage, code examples, and integration patterns.

## Overview

The session management system provides robust, secure, and synchronized session handling across multiple browser tabs and platform contexts. It consists of several key components:

- **Database Session Manager**: Manages persistent session records
- **Flask Session Manager**: Handles Flask session integration
- **Cross-Tab Synchronization**: JavaScript-based session sync across tabs
- **Platform Context Management**: Maintains active platform state
- **Security Features**: Session validation, CSRF protection, and audit logging

## Core Components

### SessionManager Class

The main session management class that handles database-backed sessions.

```python
from session_manager import SessionManager
from database import DatabaseManager
from config import Config

# Initialize session manager
config = Config()
db_manager = DatabaseManager(config)
session_manager = SessionManager(db_manager)
```

#### Key Methods

##### create_user_session(user_id, platform_connection_id)

Creates a new user session with platform context.

```python
# Create session for user with default platform
session_id = session_manager.create_user_session(
    user_id=123,
    platform_connection_id=456
)
```

**Parameters:**
- `user_id` (int): ID of the user
- `platform_connection_id` (int, optional): Platform connection ID

**Returns:** Session ID string

##### get_session_context(session_id)

Retrieves session context including user and platform information.

```python
# Get session context
context = session_manager.get_session_context(session_id)
if context:
    user_id = context['user_id']
    platform_id = context['platform_connection_id']
    platform_name = context['platform_name']
```

**Returns:** Dictionary with session context or None

##### update_platform_context(session_id, platform_connection_id)

Updates the active platform for a session.

```python
# Switch platform context
success = session_manager.update_platform_context(
    session_id="abc123",
    platform_connection_id=789
)
```

**Returns:** Boolean indicating success

### Flask Session Integration

The Flask session manager provides seamless integration with Flask's session system.

```python
from flask_session_manager import FlaskSessionManager

# Initialize Flask session manager
flask_session_manager = FlaskSessionManager(db_manager)

# Create session context
success = flask_session_manager.create_user_session(user_id, platform_id)

# Update platform context
success = flask_session_manager.update_platform_context(platform_id)

# Clear session
flask_session_manager.clear_session()
```

### Platform Context Utilities

Helper functions for accessing current platform context.

```python
from session_manager import get_current_platform_context, get_current_platform

# Get current platform context
context = get_current_platform_context()
if context:
    platform_info = context.get('platform_info')
    user_id = context.get('user_id')

# Get current platform object
platform = get_current_platform()
if platform:
    platform_type = platform.platform_type
    instance_url = platform.instance_url
```

## API Endpoints

### Session State API

#### GET /api/session_state

Returns current session state for cross-tab synchronization.

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "user": {
    "id": 123,
    "username": "user@example.com",
    "email": "user@example.com"
  },
  "platform": {
    "id": 456,
    "name": "My Pixelfed",
    "type": "pixelfed",
    "instance_url": "https://pixelfed.social",
    "is_default": true
  },
  "session": {
    "session_id": "abc123",
    "created_at": "2025-01-11T10:00:00Z",
    "last_activity": "2025-01-11T10:30:00Z"
  },
  "session_type": "integrated",
  "timestamp": "2025-01-11T10:30:00Z"
}
```

**Usage Example:**
```javascript
fetch('/api/session_state', {
    method: 'GET',
    headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest'
    },
    credentials: 'same-origin'
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        console.log('Current platform:', data.platform.name);
        console.log('Session type:', data.session_type);
    }
});
```

### Session Validation API

#### POST /api/session/validate

Validates current session integrity.

**Authentication:** Required

**Response:**
```json
{
  "success": true,
  "valid": true,
  "database_session_valid": true,
  "flask_session_valid": true,
  "timestamp": "2025-01-11T10:30:00Z"
}
```

### Session Cleanup API

#### POST /api/session/cleanup

Cleans up expired sessions for the current user.

**Authentication:** Required
**CSRF Protection:** Required

**Response:**
```json
{
  "success": true,
  "cleaned_sessions": 3,
  "message": "Cleaned up 3 expired sessions"
}
```

### Platform Switching API

#### POST /api/switch_platform/<platform_id>

Switches to a different platform with session synchronization.

**Authentication:** Required
**CSRF Protection:** Required

**Response:**
```json
{
  "success": true,
  "message": "Successfully switched to My Mastodon (Mastodon)",
  "platform": {
    "id": 789,
    "name": "My Mastodon",
    "platform_type": "mastodon",
    "instance_url": "https://mastodon.social",
    "username": "myuser"
  }
}
```

## JavaScript Session Sync

The client-side session synchronization system handles cross-tab communication and real-time updates.

### SessionSync Class

```javascript
// Initialize session sync
const sessionSync = new SessionSync();
sessionSync.init();

// Listen for session state changes
window.addEventListener('sessionStateChanged', function(event) {
    const sessionState = event.detail;
    console.log('Session state updated:', sessionState);
    
    // Update UI based on new session state
    updatePlatformUI(sessionState.platform);
});

// Listen for platform switches
window.addEventListener('platformSwitched', function(event) {
    const switchEvent = event.detail;
    console.log('Platform switched to:', switchEvent.platformName);
});

// Listen for session expiration
window.addEventListener('sessionExpired', function(event) {
    console.log('Session expired, redirecting to login');
    // Handle session expiration
});
```

### Manual Session Sync

```javascript
// Manually trigger session sync
if (window.sessionSync) {
    window.sessionSync.syncSessionState();
}

// Validate session
if (window.sessionSync) {
    window.sessionSync.validateSession();
}

// Broadcast platform switch to other tabs
if (window.sessionSync) {
    window.sessionSync.notifyPlatformSwitch(platformId, platformName);
}
```

## Integration Patterns

### Flask Route Integration

```python
from flask import Flask, request, jsonify
from flask_login import login_required, current_user
from session_manager import get_current_platform_context
from session_aware_decorators import with_db_session, require_platform_context

@app.route('/my_route')
@login_required
@require_platform_context
@with_db_session
def my_route():
    """Example route with session management integration"""
    
    # Get current platform context
    context = get_current_platform_context()
    if not context:
        return jsonify({'error': 'No platform context'}), 400
    
    platform_id = context['platform_connection_id']
    platform_name = context['platform_name']
    
    # Use platform-specific logic
    return jsonify({
        'platform_id': platform_id,
        'platform_name': platform_name,
        'user_id': current_user.id
    })
```

### Database Session Scope

```python
from request_scoped_session_manager import RequestScopedSessionManager

# Initialize request-scoped session manager
request_session_manager = RequestScopedSessionManager(db_manager)

# Use session scope for database operations
def my_database_operation():
    with request_session_manager.session_scope() as db_session:
        # Perform database operations
        user = db_session.query(User).get(user_id)
        
        # Session is automatically committed and closed
        return user
```

### Custom Session-Aware Components

```python
from session_aware_decorators import with_session_error_handling

class MyService:
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    @with_session_error_handling
    def process_with_platform_context(self, user_id):
        """Process data with current platform context"""
        
        # Get current platform context
        context = get_current_platform_context()
        if not context:
            raise ValueError("No platform context available")
        
        platform_id = context['platform_connection_id']
        
        # Use request-scoped session for database operations
        with self.db_manager.get_session() as db_session:
            # Process data for specific platform
            data = db_session.query(MyModel).filter_by(
                user_id=user_id,
                platform_connection_id=platform_id
            ).all()
            
            return data
```

## Configuration

### Session Configuration

```python
from session_config import get_session_config, SessionConfig

# Get current session configuration
config = get_session_config()

# Access configuration values
session_lifetime = config.timeout.session_lifetime
cleanup_interval = config.cleanup.cleanup_interval
enable_cross_tab_sync = config.features.enable_cross_tab_sync

# Custom configuration
custom_config = SessionConfig(
    timeout=SessionTimeoutConfig(
        session_lifetime=timedelta(hours=24),
        idle_timeout=timedelta(hours=12)
    ),
    features=SessionFeatureConfig(
        enable_cross_tab_sync=True,
        enable_background_cleanup=True
    )
)
```

### Environment Variables

```bash
# Session timeouts
SESSION_LIFETIME_SECONDS=172800  # 48 hours
SESSION_IDLE_TIMEOUT_SECONDS=86400  # 24 hours

# Cross-tab synchronization
SESSION_SYNC_CHECK_INTERVAL_SECONDS=2
SESSION_HEARTBEAT_INTERVAL_SECONDS=30

# Security features
SESSION_ENABLE_FINGERPRINTING=true
SESSION_ENABLE_AUDIT_LOGGING=true
SESSION_MAX_CONCURRENT_PER_USER=5

# Cleanup settings
SESSION_CLEANUP_INTERVAL_SECONDS=1800  # 30 minutes
SESSION_CLEANUP_BATCH_SIZE=100
```

## Security Considerations

### CSRF Protection

All session-modifying operations require CSRF tokens:

```javascript
// Get CSRF token
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

// Include CSRF token in requests
fetch('/api/switch_platform/123', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCSRFToken()
    },
    credentials: 'same-origin'
});
```

### Session Validation

```python
from session_manager import SessionManager

def validate_user_session(session_id, user_id):
    """Validate session belongs to user and is not expired"""
    
    session_manager = SessionManager(db_manager)
    
    # Validate session
    is_valid = session_manager.validate_session(session_id, user_id)
    
    if not is_valid:
        # Handle invalid session
        raise SecurityError("Invalid or expired session")
    
    return True
```

### Secure Session Data

```python
# Create secure session data (non-sensitive only)
secure_data = session_manager.create_secure_session_data(
    user_id=123,
    platform_id=456,
    request_info={
        'user_agent': request.headers.get('User-Agent'),
        'ip_address': request.remote_addr
    }
)

# Sanitize for client-side use
client_data = session_manager.sanitize_session_data_for_client(secure_data)
```

## Error Handling

### Session Errors

```python
from session_manager import SessionError, SessionDatabaseError

try:
    session_id = session_manager.create_user_session(user_id, platform_id)
except SessionDatabaseError as e:
    # Handle database-specific errors
    logger.error(f"Database error creating session: {e}")
    return jsonify({'error': 'Database error'}), 500
except SessionError as e:
    # Handle general session errors
    logger.error(f"Session error: {e}")
    return jsonify({'error': 'Session error'}), 400
```

### JavaScript Error Handling

```javascript
class SessionErrorHandler {
    static handleSessionError(error, context) {
        console.error('Session error:', error, context);
        
        if (error.message.includes('expired')) {
            // Handle session expiration
            this.handleSessionExpired();
        } else if (error.message.includes('network')) {
            // Handle network errors
            this.handleNetworkError();
        } else {
            // Handle general errors
            this.showErrorNotification(error.message);
        }
    }
    
    static handleSessionExpired() {
        // Clear local session data
        localStorage.removeItem('vedfolnir_session_state');
        
        // Redirect to login
        window.location.href = '/login';
    }
    
    static handleNetworkError() {
        // Show offline notification
        this.showErrorNotification('Network error. Please check your connection.', 'warning');
    }
    
    static showErrorNotification(message, type = 'error') {
        // Show user-friendly notification
        if (window.errorHandler) {
            window.errorHandler.showNotification(message, type);
        }
    }
}

// Use error handler in session sync
window.addEventListener('error', function(event) {
    if (event.error && event.error.context === 'session') {
        SessionErrorHandler.handleSessionError(event.error, event.error.context);
    }
});
```

## Performance Optimization

### Connection Pool Management

```python
# Get connection pool status
pool_status = session_manager.get_connection_pool_status()
print(f"Pool utilization: {pool_status['checked_out']}/{pool_status['pool_size']}")

# Optimize connection pool
session_manager.optimize_connection_pool()
```

### Batch Session Operations

```python
# Clean up multiple expired sessions efficiently
cleaned_count = session_manager.batch_cleanup_sessions(batch_size=100)
print(f"Cleaned up {cleaned_count} expired sessions")

# Enforce session timeout with batching
timeout_count = session_manager.enforce_session_timeout()
print(f"Expired {timeout_count} idle sessions")
```

### Client-Side Performance

```javascript
// Debounced session sync to prevent excessive API calls
const debouncedSync = debounce(() => {
    if (window.sessionSync) {
        window.sessionSync.syncSessionState();
    }
}, 1000);

// Use debounced sync for frequent events
window.addEventListener('focus', debouncedSync);
window.addEventListener('visibilitychange', debouncedSync);

// Performance metrics
const metrics = window.sessionSync.getPerformanceMetrics();
console.log('Session sync performance:', {
    syncCount: metrics.syncCount,
    errorRate: metrics.errorRate,
    avgSyncTime: metrics.avgSyncTime
});
```

## Monitoring and Debugging

### Session Monitoring

```python
from session_monitoring import get_session_monitor

# Get session monitor
monitor = get_session_monitor(db_manager)

# Get current metrics
metrics = monitor.get_current_metrics()
print(f"Active sessions: {metrics['session_metrics']['active_sessions']}")

# Get performance summary
summary = monitor.get_performance_summary()
print(summary)
```

### Debug Information

```python
# Get session security info
security_info = session_manager.get_session_security_info(session_id)
if security_info:
    print(f"Session age: {security_info['session_age_seconds']} seconds")
    print(f"Last activity: {security_info['last_activity_seconds']} seconds ago")
    print(f"Is suspicious: {security_info['is_suspicious']}")
```

### Client-Side Debugging

```javascript
// Enable debug mode
window.sessionSync.debugMode = true;

// Get session sync status
const status = {
    isInitialized: window.sessionSync.isInitialized,
    isOnline: window.sessionSync.isOnline,
    tabId: window.sessionSync.getTabId(),
    lastSyncTime: window.sessionSync.lastSyncTime,
    performanceMetrics: window.sessionSync.getPerformanceMetrics()
};

console.log('Session sync status:', status);

// Monitor storage events
window.addEventListener('storage', function(event) {
    if (event.key && event.key.startsWith('vedfolnir_')) {
        console.log('Storage event:', event.key, event.newValue);
    }
});
```

## Testing

### Unit Testing

```python
import unittest
from unittest.mock import Mock, patch
from session_manager import SessionManager

class TestSessionManager(unittest.TestCase):
    def setUp(self):
        self.mock_db_manager = Mock()
        self.session_manager = SessionManager(self.mock_db_manager)
    
    def test_create_user_session(self):
        """Test session creation"""
        # Mock database operations
        self.mock_db_manager.get_session.return_value.__enter__.return_value = Mock()
        
        # Test session creation
        session_id = self.session_manager.create_user_session(123, 456)
        
        # Verify session ID is returned
        self.assertIsNotNone(session_id)
        self.assertIsInstance(session_id, str)
    
    def test_validate_session(self):
        """Test session validation"""
        # Mock session context
        mock_context = {
            'user_id': 123,
            'session_id': 'test-session',
            'platform_connection_id': 456
        }
        
        with patch.object(self.session_manager, 'get_session_context', return_value=mock_context):
            # Test valid session
            is_valid = self.session_manager.validate_session('test-session', 123)
            self.assertTrue(is_valid)
            
            # Test invalid user ID
            is_valid = self.session_manager.validate_session('test-session', 999)
            self.assertFalse(is_valid)
```

### Integration Testing

```python
import asyncio
from flask import Flask
from session_manager import SessionManager
from flask_session_manager import FlaskSessionManager

class TestSessionIntegration(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()
        
        # Initialize session managers
        self.session_manager = SessionManager(db_manager)
        self.flask_session_manager = FlaskSessionManager(db_manager)
    
    def test_cross_tab_synchronization(self):
        """Test session synchronization across tabs"""
        with self.app.test_request_context():
            # Create session in first tab
            session_id = self.session_manager.create_user_session(123, 456)
            
            # Simulate platform switch in second tab
            success = self.session_manager.update_platform_context(session_id, 789)
            self.assertTrue(success)
            
            # Verify context is updated in first tab
            context = self.session_manager.get_session_context(session_id)
            self.assertEqual(context['platform_connection_id'], 789)
```

### Frontend Testing

```javascript
// Jest test for SessionSync class
describe('SessionSync', () => {
    let sessionSync;
    
    beforeEach(() => {
        sessionSync = new SessionSync();
        
        // Mock localStorage
        global.localStorage = {
            getItem: jest.fn(),
            setItem: jest.fn(),
            removeItem: jest.fn()
        };
        
        // Mock fetch
        global.fetch = jest.fn();
    });
    
    test('should initialize correctly', () => {
        expect(sessionSync.tabId).toBeDefined();
        expect(sessionSync.isInitialized).toBe(false);
    });
    
    test('should sync session state', async () => {
        // Mock successful API response
        global.fetch.mockResolvedValueOnce({
            ok: true,
            json: () => Promise.resolve({
                success: true,
                user: { id: 123 },
                platform: { id: 456, name: 'Test Platform' }
            })
        });
        
        await sessionSync.syncSessionState();
        
        expect(global.fetch).toHaveBeenCalledWith('/api/session_state', expect.any(Object));
        expect(global.localStorage.setItem).toHaveBeenCalled();
    });
    
    test('should handle session expiration', () => {
        const mockRedirect = jest.fn();
        Object.defineProperty(window, 'location', {
            value: { href: mockRedirect }
        });
        
        sessionSync.handleSessionExpired();
        
        expect(global.localStorage.removeItem).toHaveBeenCalled();
        expect(mockRedirect).toHaveBeenCalledWith('/login');
    });
});
```

This comprehensive API documentation provides developers with all the information needed to integrate with and extend the session management system. The examples cover common use cases and best practices for secure, performant session handling.
# Unified Session Management API Documentation

This document provides comprehensive developer documentation for the consolidated Vedfolnir session management system, which uses database sessions as the single source of truth.

## Overview

The unified session management system eliminates the complexity of dual session systems by using database sessions exclusively. This approach provides:

- **Single Source of Truth**: All session data stored in database
- **Consistent API**: Unified interface for all session operations
- **Enhanced Security**: Centralized session validation and audit trails
- **Cross-Tab Synchronization**: Real-time session state sharing
- **Scalability**: Database-backed sessions support multiple application instances

## Core Components

### UnifiedSessionManager

The main session management class that handles all database session operations.

```python
from unified_session_manager import UnifiedSessionManager
from app.core.database.core.database_manager import DatabaseManager

# Initialize unified session manager
db_manager = DatabaseManager()
session_manager = UnifiedSessionManager(db_manager)
```

#### Key Methods

##### create_session(user_id, platform_connection_id=None)

Creates a new database session with optional platform context.

```python
# Create session for user with specific platform
session_id = session_manager.create_session(
    user_id=123,
    platform_connection_id=456
)

# Create session with user's default platform
session_id = session_manager.create_session(user_id=123)
```

**Parameters:**
- `user_id` (int): ID of the user
- `platform_connection_id` (int, optional): Platform connection ID

**Returns:** Session ID string

**Raises:**
- `SessionValidationError`: If user or platform is invalid
- `SessionDatabaseError`: If database operation fails

##### get_session_context(session_id)

Retrieves complete session context from database.

```python
# Get session context
context = session_manager.get_session_context(session_id)
if context:
    user_id = context['user_id']
    platform_id = context['platform_connection_id']
    user_info = context['user_info']
    platform_info = context['platform_info']
```

**Returns:** Dictionary with session context or None if session not found/expired

**Context Structure:**
```python
{
    'session_id': 'uuid-string',
    'user_id': 123,
    'user_info': {
        'username': 'user@example.com',
        'email': 'user@example.com',
        'is_active': True
    },
    'platform_connection_id': 456,
    'platform_info': {
        'name': 'My Platform',
        'platform_type': 'pixelfed',
        'instance_url': 'https://pixelfed.social',
        'is_default': True
    },
    'created_at': '2025-01-11T10:00:00Z',
    'last_activity': '2025-01-11T10:30:00Z',
    'expires_at': '2025-01-13T10:00:00Z'
}
```

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

##### validate_session(session_id)

Validates that session exists and is not expired.

```python
# Validate session
is_valid = session_manager.validate_session(session_id)
if not is_valid:
    # Handle invalid/expired session
    redirect_to_login()
```

**Returns:** Boolean indicating validity

##### destroy_session(session_id)

Removes session from database.

```python
# Destroy session (logout)
success = session_manager.destroy_session(session_id)
```

**Returns:** Boolean indicating success

### SessionCookieManager

Manages secure cookies containing only session IDs.

```python
from session_cookie_manager import SessionCookieManager, create_session_cookie_manager

# Create from Flask app config
cookie_manager = create_session_cookie_manager(app.config)

# Or create manually
cookie_manager = SessionCookieManager(
    cookie_name='session_id',
    max_age=86400,  # 24 hours
    secure=True
)
```

#### Key Methods

##### set_session_cookie(response, session_id)

Sets secure session cookie with session ID.

```python
from flask import make_response

response = make_response(jsonify({'success': True}))
cookie_manager.set_session_cookie(response, session_id)
```

##### get_session_id_from_cookie()

Extracts session ID from request cookie.

```python
# Get session ID from current request
session_id = cookie_manager.get_session_id_from_cookie()
if session_id:
    # Load session context
    context = session_manager.get_session_context(session_id)
```

##### clear_session_cookie(response)

Clears session cookie (logout).

```python
response = make_response(redirect('/login'))
cookie_manager.clear_session_cookie(response)
```

### DatabaseSessionMiddleware

Middleware that loads session context before each request.

```python
from database_session_middleware import DatabaseSessionMiddleware

# Initialize middleware
middleware = DatabaseSessionMiddleware(app, session_manager, cookie_manager)
```

The middleware automatically:
- Loads session context from cookies and database
- Makes session data available via Flask `g` object
- Updates session activity timestamps
- Handles session expiration and cleanup

## Session Context Access Functions

These functions replace Flask session access throughout the application.

### get_current_session_context()

```python
from database_session_middleware import get_current_session_context

# Get complete session context
context = get_current_session_context()
if context:
    user_id = context['user_id']
    platform_id = context['platform_connection_id']
```

### get_current_user_id()

```python
from database_session_middleware import get_current_user_id

# Get current user ID
user_id = get_current_user_id()
if user_id:
    # User is authenticated
    process_authenticated_request()
```

### get_current_platform_id()

```python
from database_session_middleware import get_current_platform_id

# Get current platform ID
platform_id = get_current_platform_id()
if platform_id:
    # Platform context available
    load_platform_specific_data()
```

### update_session_platform(platform_id)

```python
from database_session_middleware import update_session_platform

# Switch platform context
success = update_session_platform(new_platform_id)
if success:
    # Platform switched successfully
    reload_platform_data()
```

### is_session_authenticated()

```python
from database_session_middleware import is_session_authenticated

# Check authentication status
if is_session_authenticated():
    # User is logged in
    show_authenticated_content()
else:
    # Redirect to login
    return redirect('/login')
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
    "name": "My Platform",
    "type": "pixelfed",
    "instance_url": "https://pixelfed.social",
    "is_default": true
  },
  "session": {
    "session_id": "abc123",
    "created_at": "2025-01-11T10:00:00Z",
    "last_activity": "2025-01-11T10:30:00Z",
    "expires_at": "2025-01-13T10:00:00Z"
  },
  "timestamp": "2025-01-11T10:30:00Z"
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
  "message": "Successfully switched to My Platform (Pixelfed)",
  "platform": {
    "id": 456,
    "name": "My Platform",
    "platform_type": "pixelfed",
    "instance_url": "https://pixelfed.social",
    "username": "myuser"
  }
}
```

## Integration Patterns

### Flask Route Integration

```python
from flask import Flask, jsonify
from database_session_middleware import get_current_session_context, is_session_authenticated

@app.route('/api/user_data')
def get_user_data():
    """Get user data with session context"""
    
    # Check authentication
    if not is_session_authenticated():
        return jsonify({'error': 'Authentication required'}), 401
    
    # Get session context
    context = get_current_session_context()
    
    return jsonify({
        'user_id': context['user_id'],
        'platform': context.get('platform_info'),
        'session_info': {
            'created_at': context['created_at'],
            'last_activity': context['last_activity']
        }
    })
```

### Login Route Implementation

```python
from flask import request, jsonify, make_response
from unified_session_manager import UnifiedSessionManager
from session_cookie_manager import SessionCookieManager

@app.route('/login', methods=['POST'])
def login():
    """Login with unified session management"""
    
    # Validate credentials
    user = authenticate_user(request.json['username'], request.json['password'])
    if not user:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    # Create database session
    session_id = session_manager.create_session(user.id)
    
    # Set secure cookie
    response = make_response(jsonify({'success': True}))
    cookie_manager.set_session_cookie(response, session_id)
    
    return response
```

### Logout Route Implementation

```python
@app.route('/logout', methods=['POST'])
def logout():
    """Logout with session cleanup"""
    
    session_id = get_current_session_id()
    if session_id:
        # Destroy database session
        session_manager.destroy_session(session_id)
    
    # Clear cookie
    response = make_response(jsonify({'success': True}))
    cookie_manager.clear_session_cookie(response)
    
    return response
```

### Session-Aware Decorators

```python
from functools import wraps
from flask import jsonify
from database_session_middleware import is_session_authenticated, get_current_platform_id

def require_authentication(f):
    """Decorator requiring valid session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_session_authenticated():
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_platform_context(f):
    """Decorator requiring platform context"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not get_current_platform_id():
            return jsonify({'error': 'Platform context required'}), 400
        return f(*args, **kwargs)
    return decorated_function

# Usage
@app.route('/api/platform_data')
@require_authentication
@require_platform_context
def get_platform_data():
    """Route requiring authentication and platform context"""
    platform_id = get_current_platform_id()
    return jsonify({'platform_id': platform_id})
```

## JavaScript Integration

### Session Synchronization

The client-side session sync works with the unified session system:

```javascript
// Session sync automatically works with database sessions
if (window.sessionSync) {
    // Get current session state
    window.sessionSync.syncSessionState();
    
    // Listen for session changes
    window.addEventListener('sessionStateChanged', function(event) {
        const sessionState = event.detail;
        updateUI(sessionState);
    });
}
```

### Platform Switching

```javascript
async function switchPlatform(platformId) {
    try {
        const response = await fetch(`/api/switch_platform/${platformId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            credentials: 'same-origin'
        });
        
        const result = await response.json();
        
        if (result.success) {
            // Notify other tabs
            if (window.sessionSync) {
                window.sessionSync.notifyPlatformSwitch(
                    platformId,
                    result.platform.name
                );
            }
            return true;
        }
    } catch (error) {
        console.error('Platform switch error:', error);
    }
    
    return false;
}
```

## Configuration

### Environment Variables

```bash
# Session configuration
SESSION_LIFETIME_SECONDS=172800  # 48 hours
SESSION_IDLE_TIMEOUT_SECONDS=86400  # 24 hours
SESSION_CLEANUP_INTERVAL_SECONDS=1800  # 30 minutes

# Cookie configuration
SESSION_COOKIE_NAME=session_id
SESSION_COOKIE_SECURE=true
PERMANENT_SESSION_LIFETIME=86400  # 24 hours

# Security features
SESSION_ENABLE_FINGERPRINTING=true
SESSION_ENABLE_AUDIT_LOGGING=true
SESSION_MAX_CONCURRENT_PER_USER=5
```

### Session Configuration

```python
from session_config import get_session_config

# Get current configuration
config = get_session_config()

# Access configuration values
session_lifetime = config.timeout.session_lifetime
cleanup_interval = config.cleanup.cleanup_interval
enable_cross_tab_sync = config.features.enable_cross_tab_sync
```

## Error Handling

### Session Exceptions

```python
from unified_session_manager import (
    SessionValidationError,
    SessionExpiredError,
    SessionNotFoundError,
    SessionDatabaseError
)

try:
    session_id = session_manager.create_session(user_id, platform_id)
except SessionValidationError as e:
    # Handle validation errors (invalid user/platform)
    return jsonify({'error': 'Invalid user or platform'}), 400
except SessionDatabaseError as e:
    # Handle database errors
    return jsonify({'error': 'Database error'}), 500
```

### Middleware Error Handling

The middleware automatically handles session errors:

```python
from flask import g
from database_session_middleware import get_current_session_context

@app.route('/protected')
def protected_route():
    # Check for session errors
    if hasattr(g, 'session_error'):
        # Session validation failed
        return redirect('/login')
    
    # Normal session handling
    context = get_current_session_context()
    if not context:
        return redirect('/login')
    
    return render_template('protected.html')
```

## Security Features

### Session Fingerprinting

Sessions include security fingerprints for validation:

```python
# Fingerprinting is automatic when security manager is available
session_id = session_manager.create_session(user_id, platform_id)

# Validation includes fingerprint checking
is_valid = session_manager.validate_session(session_id)
```

### Audit Logging

All session operations are logged for security auditing:

```python
# Audit events are created automatically:
# - session_created
# - session_destroyed
# - platform_switch
# - session_expired
```

### CSRF Protection

All session-modifying operations require CSRF tokens:

```javascript
// Include CSRF token in requests
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

fetch('/api/switch_platform/123', {
    method: 'POST',
    headers: {
        'X-CSRFToken': csrfToken
    }
});
```

## Performance Optimization

### Session Cleanup

Automatic cleanup of expired sessions:

```python
# Cleanup runs automatically based on configuration
cleaned_count = session_manager.cleanup_expired_sessions()
```

### Connection Pool Management

Database connections are managed efficiently:

```python
# Connection pooling is handled automatically
# Sessions are properly closed and committed
```

### Caching

Session context can be cached for performance:

```python
# Caching is available through session configuration
# Context is cached per request to avoid repeated database queries
```

## Migration from Flask Sessions

### Code Changes Required

1. **Replace Flask session access:**
```python
# Old Flask session usage
from flask import session
user_id = session.get('user_id')
platform_id = session.get('platform_connection_id')

# New unified session usage
from database_session_middleware import get_current_user_id, get_current_platform_id
user_id = get_current_user_id()
platform_id = get_current_platform_id()
```

2. **Update login routes:**
```python
# Old Flask session login
session['user_id'] = user.id
session['platform_connection_id'] = platform.id

# New unified session login
session_id = session_manager.create_session(user.id, platform.id)
cookie_manager.set_session_cookie(response, session_id)
```

3. **Update logout routes:**
```python
# Old Flask session logout
session.clear()

# New unified session logout
session_id = get_current_session_id()
session_manager.destroy_session(session_id)
cookie_manager.clear_session_cookie(response)
```

### Testing Migration

Verify migration with comprehensive tests:

```python
def test_unified_session_creation():
    """Test session creation with unified manager"""
    session_id = session_manager.create_session(user_id, platform_id)
    assert session_id is not None
    
    context = session_manager.get_session_context(session_id)
    assert context['user_id'] == user_id
    assert context['platform_connection_id'] == platform_id

def test_session_context_access():
    """Test session context access functions"""
    # Create session
    session_id = session_manager.create_session(user_id, platform_id)
    
    # Simulate middleware loading context
    with app.test_request_context():
        g.session_context = session_manager.get_session_context(session_id)
        
        # Test access functions
        assert get_current_user_id() == user_id
        assert get_current_platform_id() == platform_id
        assert is_session_authenticated() == True
```

## Troubleshooting

### Common Issues

1. **Session not found:**
   - Check cookie configuration
   - Verify session hasn't expired
   - Check database connectivity

2. **Platform context missing:**
   - Ensure user has active platforms
   - Check platform ownership
   - Verify platform is not deactivated

3. **Cross-tab sync not working:**
   - Check JavaScript console for errors
   - Verify localStorage is available
   - Test session state API endpoint

### Debug Tools

```python
# Debug session state
context = session_manager.get_session_context(session_id)
print(f"Session context: {context}")

# Check session validity
is_valid = session_manager.validate_session(session_id)
print(f"Session valid: {is_valid}")

# Clean up expired sessions
count = session_manager.cleanup_expired_sessions()
print(f"Cleaned up {count} expired sessions")
```

This unified session management system provides a robust, secure, and scalable foundation for session handling in the Vedfolnir application.
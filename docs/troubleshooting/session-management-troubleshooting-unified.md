# Unified Session Management Troubleshooting Guide

This guide provides comprehensive troubleshooting information for the consolidated database-only session management system in Vedfolnir.

## Table of Contents

1. [Common Issues](#common-issues)
2. [Session Context Problems](#session-context-problems)
3. [Database Session Issues](#database-session-issues)
4. [Cookie Management Problems](#cookie-management-problems)
5. [Cross-Tab Synchronization Issues](#cross-tab-synchronization-issues)
6. [Platform Context Issues](#platform-context-issues)
7. [Performance Problems](#performance-problems)
8. [Security Issues](#security-issues)
9. [Debugging Tools](#debugging-tools)
10. [Recovery Procedures](#recovery-procedures)

## Common Issues

### Issue: "No session context available" Error

**Symptoms:**
- Users see "No session context available" error messages
- Session appears to exist but context is not loaded
- Middleware not providing session data

**Possible Causes:**
1. Database session middleware not initialized
2. Session cookie not being sent/received
3. Database connectivity issues
4. Session expired but cookie still present

**Troubleshooting Steps:**

1. **Check Middleware Initialization:**
```python
# Verify middleware is properly initialized
from database_session_middleware import DatabaseSessionMiddleware

# Check if middleware is registered
print(f"App before_request functions: {app.before_request_funcs}")
print(f"App after_request functions: {app.after_request_funcs}")
```

2. **Check Session Context in Request:**
```python
from flask import g
from database_session_middleware import get_current_session_context

@app.route('/debug/session')
def debug_session():
    """Debug session context"""
    context = get_current_session_context()
    session_id = getattr(g, 'session_id', None)
    session_error = getattr(g, 'session_error', None)
    
    return jsonify({
        'context': context,
        'session_id': session_id,
        'session_error': str(session_error) if session_error else None,
        'g_attributes': [attr for attr in dir(g) if not attr.startswith('_')]
    })
```

3. **Verify Cookie Presence:**
```python
from flask import request

# Check if session cookie is present
session_cookie = request.cookies.get('session_id')
print(f"Session cookie: {session_cookie}")

# Check all cookies
print(f"All cookies: {dict(request.cookies)}")
```

**Solutions:**

1. **Reinitialize Middleware:**
```python
# Ensure middleware is properly initialized
middleware = DatabaseSessionMiddleware(app, session_manager, cookie_manager)
```

2. **Check Database Session:**
```python
# Manually check database session
if session_cookie:
    context = session_manager.get_session_context(session_cookie)
    print(f"Database context: {context}")
```

### Issue: Session Expires Immediately

**Symptoms:**
- Users are logged out immediately after login
- Session context is None right after creation
- Session validation fails for newly created sessions

**Possible Causes:**
1. Session timeout configuration too short
2. System clock issues
3. Database timezone problems
4. Session creation failing silently

**Troubleshooting Steps:**

1. **Check Session Configuration:**
```python
from session_config import get_session_config

config = get_session_config()
print(f"Session lifetime: {config.timeout.session_lifetime}")
print(f"Idle timeout: {config.timeout.idle_timeout}")
```

2. **Test Session Creation:**
```python
# Test session creation step by step
try:
    session_id = session_manager.create_session(user_id, platform_id)
    print(f"Created session: {session_id}")
    
    # Immediately check context
    context = session_manager.get_session_context(session_id)
    print(f"Context: {context}")
    
    # Check validation
    is_valid = session_manager.validate_session(session_id)
    print(f"Valid: {is_valid}")
    
except Exception as e:
    print(f"Session creation error: {e}")
```

3. **Check Database Session Record:**
```python
from models import UserSession

with db_manager.get_session() as db_session:
    user_session = db_session.query(UserSession).filter_by(
        session_id=session_id
    ).first()
    
    if user_session:
        print(f"DB Session created: {user_session.created_at}")
        print(f"DB Session expires: {user_session.expires_at}")
        print(f"DB Session active: {user_session.is_active}")
        print(f"Is expired: {user_session.is_expired()}")
```

**Solutions:**

1. **Adjust Session Timeouts:**
```bash
# In .env file
SESSION_LIFETIME_SECONDS=172800  # 48 hours
SESSION_IDLE_TIMEOUT_SECONDS=86400  # 24 hours
```

2. **Fix Timezone Issues:**
```python
# Ensure consistent timezone usage
from datetime import datetime, timezone

# Always use UTC for session timestamps
now = datetime.now(timezone.utc)
```

### Issue: Cross-Tab Synchronization Not Working

**Symptoms:**
- Platform switches in one tab don't reflect in other tabs
- Session state inconsistent across browser tabs
- JavaScript errors in console

**Possible Causes:**
1. Session state API not returning correct data
2. localStorage not working properly
3. JavaScript SessionSync not initialized
4. API endpoints returning old Flask session data

**Troubleshooting Steps:**

1. **Test Session State API:**
```bash
# Test API endpoint directly
curl -X GET http://localhost:5000/api/session_state \
  -H "Cookie: session_id=your-session-id" \
  -H "Content-Type: application/json"
```

2. **Check JavaScript Console:**
```javascript
// Check SessionSync availability
console.log('SessionSync available:', typeof window.SessionSync);
console.log('SessionSync instance:', window.sessionSync);

// Test manual sync
if (window.sessionSync) {
    window.sessionSync.syncSessionState();
}
```

3. **Test localStorage:**
```javascript
// Check localStorage functionality
try {
    localStorage.setItem('test', 'value');
    console.log('localStorage test:', localStorage.getItem('test'));
    localStorage.removeItem('test');
} catch (error) {
    console.error('localStorage error:', error);
}
```

**Solutions:**

1. **Update Session State API:**
```python
@app.route('/api/session_state')
def session_state():
    """Return unified session state"""
    from database_session_middleware import get_current_session_context
    
    context = get_current_session_context()
    if not context:
        return jsonify({'success': False, 'error': 'No session'}), 401
    
    return jsonify({
        'success': True,
        'user': context.get('user_info'),
        'platform': context.get('platform_info'),
        'session': {
            'session_id': context['session_id'],
            'created_at': context['created_at'],
            'last_activity': context['last_activity']
        },
        'timestamp': datetime.now(timezone.utc).isoformat()
    })
```

## Session Context Problems

### Debugging Session Context Loading

**Check Context Loading Process:**
```python
from database_session_middleware import DatabaseSessionMiddleware

class DebugDatabaseSessionMiddleware(DatabaseSessionMiddleware):
    """Debug version of middleware"""
    
    def before_request(self):
        print(f"Before request: {request.path}")
        
        # Call parent method
        super().before_request()
        
        # Debug output
        print(f"Session ID: {getattr(g, 'session_id', None)}")
        print(f"Session context: {getattr(g, 'session_context', None)}")
        print(f"Session error: {getattr(g, 'session_error', None)}")
```

### Context Access Function Issues

**Test Context Access Functions:**
```python
from database_session_middleware import (
    get_current_session_context,
    get_current_user_id,
    get_current_platform_id,
    is_session_authenticated
)

def debug_context_access():
    """Debug context access functions"""
    print(f"Session context: {get_current_session_context()}")
    print(f"User ID: {get_current_user_id()}")
    print(f"Platform ID: {get_current_platform_id()}")
    print(f"Authenticated: {is_session_authenticated()}")
```

## Database Session Issues

### Connection Pool Problems

**Check Connection Pool Status:**
```python
def debug_connection_pool():
    """Debug database connection pool"""
    try:
        with session_manager.get_db_session() as db_session:
            from sqlalchemy import text
            result = db_session.execute(text("SELECT 1")).fetchone()
            print(f"Database connection test: {result[0] == 1}")
            
        # Check pool status if available
        if hasattr(db_manager, 'engine'):
            pool = db_manager.engine.pool
            print(f"Pool size: {pool.size()}")
            print(f"Checked out: {pool.checkedout()}")
            print(f"Overflow: {pool.overflow()}")
            
    except Exception as e:
        print(f"Database connection error: {e}")
```

### Session Table Issues

**Verify Session Table Structure:**
```python
from models import UserSession
from sqlalchemy import inspect

def debug_session_table():
    """Debug session table structure"""
    inspector = inspect(db_manager.engine)
    
    # Check if table exists
    tables = inspector.get_table_names()
    print(f"Tables: {tables}")
    
    if 'user_sessions' in tables:
        columns = inspector.get_columns('user_sessions')
        print(f"Session table columns: {[col['name'] for col in columns]}")
        
        # Check session count
        with db_manager.get_session() as db_session:
            count = db_session.query(UserSession).count()
            print(f"Total sessions: {count}")
            
            # Check active sessions
            active_count = db_session.query(UserSession).filter_by(is_active=True).count()
            print(f"Active sessions: {active_count}")
```

## Cookie Management Problems

### Cookie Not Being Set

**Debug Cookie Setting:**
```python
from flask import make_response

@app.route('/debug/cookie')
def debug_cookie():
    """Debug cookie setting"""
    session_id = "test-session-id"
    
    response = make_response(jsonify({'message': 'Cookie test'}))
    
    # Set cookie manually
    cookie_manager.set_session_cookie(response, session_id)
    
    # Check response headers
    print(f"Response headers: {dict(response.headers)}")
    
    return response
```

### Cookie Security Issues

**Validate Cookie Configuration:**
```python
def debug_cookie_security():
    """Debug cookie security settings"""
    print(f"Cookie name: {cookie_manager.cookie_name}")
    print(f"Max age: {cookie_manager.max_age}")
    print(f"Secure: {cookie_manager.secure}")
    
    # Validate security
    is_valid = cookie_manager.validate_cookie_security()
    print(f"Cookie security valid: {is_valid}")
```

### Cookie Not Being Sent

**Check Cookie Domain/Path Issues:**
```python
from flask import request

@app.route('/debug/request-cookies')
def debug_request_cookies():
    """Debug cookies in request"""
    return jsonify({
        'cookies': dict(request.cookies),
        'headers': dict(request.headers),
        'host': request.host,
        'path': request.path
    })
```

## Cross-Tab Synchronization Issues

### JavaScript SessionSync Problems

**Debug SessionSync Initialization:**
```javascript
// Add to your JavaScript
window.debugSessionSync = {
    checkInit: function() {
        console.log('SessionSync type:', typeof window.SessionSync);
        console.log('SessionSync instance:', window.sessionSync);
        
        if (window.sessionSync) {
            console.log('Initialized:', window.sessionSync.isInitialized);
            console.log('Online:', window.sessionSync.isOnline);
            console.log('Tab ID:', window.sessionSync.getTabId());
        }
    },
    
    testSync: function() {
        if (window.sessionSync) {
            window.sessionSync.syncSessionState();
        } else {
            console.error('SessionSync not available');
        }
    },
    
    testStorage: function() {
        // Test localStorage
        const testKey = 'vedfolnir_test';
        const testValue = JSON.stringify({test: true, timestamp: Date.now()});
        
        try {
            localStorage.setItem(testKey, testValue);
            const retrieved = localStorage.getItem(testKey);
            console.log('Storage test success:', retrieved === testValue);
            localStorage.removeItem(testKey);
        } catch (error) {
            console.error('Storage test failed:', error);
        }
    }
};

// Run debug checks
window.debugSessionSync.checkInit();
```

### Storage Event Issues

**Monitor Storage Events:**
```javascript
// Add storage event monitoring
window.addEventListener('storage', function(event) {
    if (event.key && event.key.startsWith('vedfolnir_')) {
        console.log('Storage event:', {
            key: event.key,
            oldValue: event.oldValue ? JSON.parse(event.oldValue) : null,
            newValue: event.newValue ? JSON.parse(event.newValue) : null,
            url: event.url
        });
    }
});

console.log('Storage event monitoring enabled');
```

## Platform Context Issues

### Platform Not Found Errors

**Debug Platform Ownership:**
```python
def debug_platform_access(user_id, platform_id):
    """Debug platform access issues"""
    from models import PlatformConnection
    
    with db_manager.get_session() as db_session:
        # Check if platform exists
        platform = db_session.query(PlatformConnection).filter_by(id=platform_id).first()
        if not platform:
            print(f"Platform {platform_id} does not exist")
            return
        
        print(f"Platform exists: {platform.name}")
        print(f"Platform owner: {platform.user_id}")
        print(f"Platform active: {platform.is_active}")
        print(f"Requested by user: {user_id}")
        
        # Check user's platforms
        user_platforms = db_session.query(PlatformConnection).filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        
        print(f"User has {len(user_platforms)} active platforms:")
        for p in user_platforms:
            print(f"  - {p.name} (ID: {p.id}, Default: {p.is_default})")
```

### Default Platform Issues

**Fix Default Platform:**
```python
def fix_default_platform(user_id):
    """Ensure user has a default platform"""
    from models import PlatformConnection
    
    with db_manager.get_session() as db_session:
        # Check for existing default
        default_platform = db_session.query(PlatformConnection).filter_by(
            user_id=user_id,
            is_default=True,
            is_active=True
        ).first()
        
        if default_platform:
            print(f"User has default platform: {default_platform.name}")
            return default_platform.id
        
        # Set first active platform as default
        first_platform = db_session.query(PlatformConnection).filter_by(
            user_id=user_id,
            is_active=True
        ).first()
        
        if first_platform:
            first_platform.is_default = True
            db_session.commit()
            print(f"Set {first_platform.name} as default platform")
            return first_platform.id
        
        print(f"User {user_id} has no active platforms")
        return None
```

## Performance Problems

### Slow Session Operations

**Profile Session Operations:**
```python
import time
from functools import wraps

def profile_session_operation(operation_name):
    """Decorator to profile session operations"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                print(f"{operation_name} completed in {duration:.3f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                print(f"{operation_name} failed in {duration:.3f}s: {e}")
                raise
        return wrapper
    return decorator

# Profile session manager methods
session_manager.create_session = profile_session_operation("create_session")(session_manager.create_session)
session_manager.get_session_context = profile_session_operation("get_session_context")(session_manager.get_session_context)
```

### Database Query Optimization

**Analyze Session Queries:**
```python
def analyze_session_queries():
    """Analyze session-related database queries"""
    from sqlalchemy import event
    from sqlalchemy.engine import Engine
    
    query_count = 0
    query_times = []
    
    @event.listens_for(Engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        context._query_start_time = time.time()
        nonlocal query_count
        query_count += 1
        print(f"Query {query_count}: {statement[:100]}...")
    
    @event.listens_for(Engine, "after_cursor_execute")
    def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        total = time.time() - context._query_start_time
        query_times.append(total)
        print(f"Query completed in {total:.3f}s")
    
    # Test session operations
    session_id = session_manager.create_session(user_id, platform_id)
    context = session_manager.get_session_context(session_id)
    
    print(f"Total queries: {query_count}")
    print(f"Average query time: {sum(query_times)/len(query_times):.3f}s")
```

## Security Issues

### Session Fingerprinting Problems

**Debug Session Fingerprinting:**
```python
def debug_session_fingerprinting():
    """Debug session fingerprinting"""
    try:
        # Test fingerprint creation
        fingerprint = session_manager._create_session_fingerprint()
        print(f"Session fingerprint: {fingerprint}")
        
        if not fingerprint:
            print("Warning: Session fingerprinting not working")
            
            # Check security manager
            if session_manager.security_manager:
                print("Security manager available")
            elif session_manager.security_hardening:
                print("Security hardening available")
            else:
                print("No security components available")
                
    except Exception as e:
        print(f"Fingerprinting error: {e}")
```

### Audit Logging Issues

**Check Audit Logging:**
```python
def debug_audit_logging():
    """Debug security audit logging"""
    try:
        # Test audit event creation
        session_manager._create_security_audit_event(
            event_type='test_event',
            user_id=123,
            session_id='test-session',
            details={'test': True}
        )
        print("Audit logging working")
        
    except Exception as e:
        print(f"Audit logging error: {e}")
```

## Debugging Tools

### Session Debug Console

```python
def session_debug_console():
    """Interactive session debugging console"""
    
    while True:
        command = input("Session Debug> ").strip().lower()
        
        if command == 'help':
            print("Available commands:")
            print("  create <user_id> [platform_id] - Create session")
            print("  get <session_id> - Get session context")
            print("  validate <session_id> - Validate session")
            print("  destroy <session_id> - Destroy session")
            print("  cleanup - Clean up expired sessions")
            print("  list [user_id] - List sessions")
            print("  platform <user_id> - List user platforms")
            print("  cookie - Test cookie operations")
            print("  quit - Exit debug console")
        
        elif command.startswith('create '):
            parts = command.split()
            user_id = int(parts[1])
            platform_id = int(parts[2]) if len(parts) > 2 else None
            
            try:
                session_id = session_manager.create_session(user_id, platform_id)
                print(f"Created session: {session_id}")
            except Exception as e:
                print(f"Error creating session: {e}")
        
        elif command.startswith('get '):
            session_id = command.split(' ', 1)[1]
            context = session_manager.get_session_context(session_id)
            print(f"Session context: {context}")
        
        elif command.startswith('validate '):
            session_id = command.split(' ', 1)[1]
            is_valid = session_manager.validate_session(session_id)
            print(f"Session valid: {is_valid}")
        
        elif command.startswith('destroy '):
            session_id = command.split(' ', 1)[1]
            success = session_manager.destroy_session(session_id)
            print(f"Session destroyed: {success}")
        
        elif command == 'cleanup':
            count = session_manager.cleanup_expired_sessions()
            print(f"Cleaned up {count} expired sessions")
        
        elif command.startswith('list'):
            parts = command.split()
            user_id = int(parts[1]) if len(parts) > 1 else None
            
            with db_manager.get_session() as db_session:
                query = db_session.query(UserSession)
                if user_id:
                    query = query.filter_by(user_id=user_id)
                
                sessions = query.all()
                print(f"Found {len(sessions)} sessions:")
                for s in sessions:
                    print(f"  {s.session_id} - User {s.user_id} - Active: {s.is_active}")
        
        elif command.startswith('platform '):
            user_id = int(command.split(' ', 1)[1])
            debug_platform_access(user_id, None)
        
        elif command == 'cookie':
            print(f"Cookie manager: {cookie_manager.cookie_name}")
            print(f"Cookie security valid: {cookie_manager.validate_cookie_security()}")
        
        elif command in ['quit', 'exit']:
            break
        
        else:
            print("Unknown command. Type 'help' for available commands.")

# Run debug console
if __name__ == '__main__':
    session_debug_console()
```

### JavaScript Debug Tools

```javascript
// Comprehensive session debugging tools
window.sessionDebugTools = {
    // Test all session functions
    runAllTests: async function() {
        console.log('=== Session Debug Tests ===');
        
        // Test 1: Check SessionSync
        this.testSessionSync();
        
        // Test 2: Check localStorage
        this.testLocalStorage();
        
        // Test 3: Test API endpoints
        await this.testAPIEndpoints();
        
        // Test 4: Test cookie operations
        this.testCookies();
        
        console.log('=== Tests Complete ===');
    },
    
    testSessionSync: function() {
        console.log('Testing SessionSync...');
        
        if (typeof window.SessionSync === 'undefined') {
            console.error('❌ SessionSync class not available');
            return;
        }
        
        if (!window.sessionSync) {
            console.error('❌ SessionSync instance not created');
            return;
        }
        
        console.log('✅ SessionSync available');
        console.log('Initialized:', window.sessionSync.isInitialized);
        console.log('Online:', window.sessionSync.isOnline);
        console.log('Tab ID:', window.sessionSync.getTabId());
    },
    
    testLocalStorage: function() {
        console.log('Testing localStorage...');
        
        const testKey = 'vedfolnir_debug_test';
        const testValue = JSON.stringify({test: true, timestamp: Date.now()});
        
        try {
            localStorage.setItem(testKey, testValue);
            const retrieved = localStorage.getItem(testKey);
            
            if (retrieved === testValue) {
                console.log('✅ localStorage working');
            } else {
                console.error('❌ localStorage data mismatch');
            }
            
            localStorage.removeItem(testKey);
        } catch (error) {
            console.error('❌ localStorage error:', error);
        }
    },
    
    testAPIEndpoints: async function() {
        console.log('Testing API endpoints...');
        
        try {
            // Test session state endpoint
            const response = await fetch('/api/session_state', {
                credentials: 'same-origin'
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('✅ Session state API working');
                console.log('Session data:', data);
            } else {
                console.error('❌ Session state API failed:', response.status);
            }
        } catch (error) {
            console.error('❌ API test error:', error);
        }
    },
    
    testCookies: function() {
        console.log('Testing cookies...');
        
        const cookies = document.cookie.split(';').reduce((acc, cookie) => {
            const [name, value] = cookie.trim().split('=');
            acc[name] = value;
            return acc;
        }, {});
        
        console.log('Available cookies:', Object.keys(cookies));
        
        if (cookies.session_id) {
            console.log('✅ Session cookie found');
            console.log('Session ID:', cookies.session_id.substring(0, 8) + '...');
        } else {
            console.log('❌ No session cookie found');
        }
    },
    
    // Monitor session events
    monitorEvents: function() {
        console.log('Starting session event monitoring...');
        
        // Monitor storage events
        window.addEventListener('storage', (event) => {
            if (event.key && event.key.startsWith('vedfolnir_')) {
                console.log('📡 Storage event:', {
                    key: event.key,
                    oldValue: event.oldValue,
                    newValue: event.newValue
                });
            }
        });
        
        // Monitor custom session events
        ['sessionStateChanged', 'platformSwitched', 'sessionExpired'].forEach(eventType => {
            window.addEventListener(eventType, (event) => {
                console.log(`📡 ${eventType}:`, event.detail);
            });
        });
        
        console.log('Event monitoring enabled');
    }
};

// Auto-run basic tests
console.log('Session debug tools loaded. Use window.sessionDebugTools for debugging.');
```

## Recovery Procedures

### Complete Session System Reset

```python
def complete_session_system_reset():
    """Complete reset of unified session system"""
    
    print("Starting complete session system reset...")
    
    try:
        # 1. Clean up all database sessions
        with db_manager.get_session() as db_session:
            from models import UserSession
            session_count = db_session.query(UserSession).count()
            print(f"Found {session_count} sessions to clean up")
            
            # Delete all sessions
            db_session.query(UserSession).delete()
            db_session.commit()
            print("✅ All database sessions cleared")
        
        # 2. Reset session configuration
        from session_config import reload_session_config
        reload_session_config()
        print("✅ Session configuration reloaded")
        
        # 3. Test session manager
        test_session_id = session_manager.create_session(1, 1)  # Use existing user/platform
        if test_session_id:
            session_manager.destroy_session(test_session_id)
            print("✅ Session manager working")
        
        # 4. Test cookie manager
        if cookie_manager.validate_cookie_security():
            print("✅ Cookie manager working")
        
        print("Complete session system reset finished successfully")
        return True
        
    except Exception as e:
        print(f"❌ Session system reset failed: {e}")
        return False
```

### Emergency Session Recovery

```python
def emergency_session_recovery(user_id):
    """Emergency recovery for specific user"""
    
    print(f"Starting emergency session recovery for user {user_id}...")
    
    try:
        # 1. Clean up user's existing sessions
        count = session_manager.cleanup_user_sessions(user_id)
        print(f"Cleaned up {count} existing sessions")
        
        # 2. Ensure user has a default platform
        platform_id = fix_default_platform(user_id)
        if not platform_id:
            print("❌ User has no active platforms")
            return None
        
        # 3. Create new session
        session_id = session_manager.create_session(user_id, platform_id)
        print(f"Created new session: {session_id}")
        
        # 4. Validate new session
        context = session_manager.get_session_context(session_id)
        if context:
            print("✅ Emergency recovery successful")
            return session_id
        else:
            print("❌ Emergency recovery failed - context not available")
            return None
            
    except Exception as e:
        print(f"❌ Emergency recovery failed: {e}")
        return None
```

### Database Session Table Recovery

```python
def recover_session_table():
    """Recover session table if corrupted"""
    
    print("Starting session table recovery...")
    
    try:
        # Check table structure
        from sqlalchemy import inspect
        inspector = inspect(db_manager.engine)
        
        if 'user_sessions' not in inspector.get_table_names():
            print("Session table missing - recreating...")
            
            # Recreate table
            from models import UserSession
            UserSession.__table__.create(db_manager.engine)
            print("✅ Session table recreated")
        
        # Verify table structure
        columns = inspector.get_columns('user_sessions')
        expected_columns = [
            'id', 'user_id', 'session_id', 'active_platform_id',
            'created_at', 'updated_at', 'last_activity', 'expires_at',
            'is_active', 'session_fingerprint', 'user_agent', 'ip_address'
        ]
        
        actual_columns = [col['name'] for col in columns]
        missing_columns = set(expected_columns) - set(actual_columns)
        
        if missing_columns:
            print(f"❌ Missing columns: {missing_columns}")
            print("Manual database migration may be required")
            return False
        
        print("✅ Session table structure valid")
        return True
        
    except Exception as e:
        print(f"❌ Session table recovery failed: {e}")
        return False
```

This comprehensive troubleshooting guide provides solutions for all common issues with the unified session management system and includes tools for debugging and recovery.
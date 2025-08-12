# Session Management Troubleshooting Guide

This guide provides comprehensive troubleshooting information for common session management issues in the Vedfolnir application.

## Table of Contents

1. [Common Issues](#common-issues)
2. [Session Expiration Problems](#session-expiration-problems)
3. [Cross-Tab Synchronization Issues](#cross-tab-synchronization-issues)
4. [Platform Switching Problems](#platform-switching-problems)
5. [Database Session Issues](#database-session-issues)
6. [Performance Problems](#performance-problems)
7. [Security-Related Issues](#security-related-issues)
8. [Debugging Tools](#debugging-tools)
9. [Configuration Issues](#configuration-issues)
10. [Recovery Procedures](#recovery-procedures)

## Common Issues

### Issue: "No platform context available" Error

**Symptoms:**
- Users see "No platform context available" error messages
- Platform-dependent features are not accessible
- Session appears valid but platform context is missing

**Possible Causes:**
1. Session was created without platform context
2. Platform connection was deactivated or deleted
3. Database session corruption
4. Cross-tab synchronization failure

**Troubleshooting Steps:**

1. **Check Session Context:**
```python
from session_manager import get_current_platform_context

# In a Flask route or shell
context = get_current_platform_context()
print(f"Context: {context}")

if not context:
    print("No platform context found")
elif not context.get('platform_connection_id'):
    print("Platform connection ID missing from context")
```

2. **Verify Platform Connection:**
```python
from models import PlatformConnection
from database import DatabaseManager

db_manager = DatabaseManager()
with db_manager.get_session() as db_session:
    platforms = db_session.query(PlatformConnection).filter_by(
        user_id=user_id,
        is_active=True
    ).all()
    
    print(f"Active platforms for user {user_id}: {len(platforms)}")
    for platform in platforms:
        print(f"- {platform.name} (ID: {platform.id}, Default: {platform.is_default})")
```

3. **Check Flask Session:**
```python
from flask import session

print(f"Flask session keys: {list(session.keys())}")
print(f"Session ID: {session.get('_id')}")
print(f"Platform ID: {session.get('platform_connection_id')}")
print(f"User ID: {session.get('user_id')}")
```

**Solutions:**

1. **Recreate Session with Platform Context:**
```python
from session_manager import SessionManager

session_manager = SessionManager(db_manager)

# Get user's default platform
with db_manager.get_session() as db_session:
    default_platform = db_session.query(PlatformConnection).filter_by(
        user_id=user_id,
        is_default=True,
        is_active=True
    ).first()
    
    if default_platform:
        # Create new session with platform context
        new_session_id = session_manager.create_user_session(
            user_id, default_platform.id
        )
        
        # Update Flask session
        session['_id'] = new_session_id
        session['platform_connection_id'] = default_platform.id
```

2. **Set Default Platform:**
```python
from database import DatabaseManager

db_manager = DatabaseManager()
success = db_manager.set_default_platform(user_id, platform_id)
if success:
    print("Default platform set successfully")
```

### Issue: Session Expires Too Quickly

**Symptoms:**
- Users are logged out frequently
- "Session expired" messages appear often
- Session lifetime seems shorter than configured

**Possible Causes:**
1. Incorrect session timeout configuration
2. System clock issues
3. Database timezone problems
4. Aggressive session cleanup

**Troubleshooting Steps:**

1. **Check Session Configuration:**
```python
from session_config import get_session_config

config = get_session_config()
print(f"Session lifetime: {config.timeout.session_lifetime}")
print(f"Idle timeout: {config.timeout.idle_timeout}")
print(f"Absolute timeout: {config.timeout.absolute_timeout}")
```

2. **Check Session Age:**
```python
from session_manager import SessionManager

session_manager = SessionManager(db_manager)
security_info = session_manager.get_session_security_info(session_id)

if security_info:
    print(f"Session age: {security_info['session_age_seconds']} seconds")
    print(f"Last activity: {security_info['last_activity_seconds']} seconds ago")
    print(f"Is expired: {security_info['is_expired']}")
```

3. **Verify System Time:**
```python
from datetime import datetime, timezone

print(f"System time (UTC): {datetime.now(timezone.utc)}")
print(f"System time (local): {datetime.now()}")

# Check database time
with db_manager.get_session() as db_session:
    from sqlalchemy import text
    result = db_session.execute(text("SELECT datetime('now')")).fetchone()
    print(f"Database time: {result[0]}")
```

**Solutions:**

1. **Adjust Session Timeouts:**
```bash
# In .env file
SESSION_LIFETIME_SECONDS=172800  # 48 hours
SESSION_IDLE_TIMEOUT_SECONDS=86400  # 24 hours
SESSION_ABSOLUTE_TIMEOUT_SECONDS=604800  # 7 days
```

2. **Fix Timezone Issues:**
```python
# Ensure all datetime objects use UTC
from datetime import datetime, timezone

# When creating/updating sessions
now = datetime.now(timezone.utc)
```

### Issue: Cross-Tab Synchronization Not Working

**Symptoms:**
- Platform switches in one tab don't reflect in other tabs
- Session state inconsistent across tabs
- Users need to refresh pages to see updates

**Possible Causes:**
1. JavaScript errors preventing SessionSync initialization
2. localStorage not working (private browsing, storage full)
3. Network issues preventing API calls
4. CSRF token problems

**Troubleshooting Steps:**

1. **Check JavaScript Console:**
```javascript
// Open browser console and check for errors
console.log('SessionSync available:', typeof window.SessionSync);
console.log('SessionSync instance:', window.sessionSync);

if (window.sessionSync) {
    console.log('SessionSync initialized:', window.sessionSync.isInitialized);
    console.log('SessionSync online:', window.sessionSync.isOnline);
    console.log('Tab ID:', window.sessionSync.getTabId());
}
```

2. **Test localStorage:**
```javascript
// Test localStorage functionality
try {
    localStorage.setItem('test', 'value');
    console.log('localStorage test:', localStorage.getItem('test'));
    localStorage.removeItem('test');
    console.log('localStorage working');
} catch (error) {
    console.error('localStorage error:', error);
}
```

3. **Check Session Sync Status:**
```javascript
if (window.sessionSync) {
    const metrics = window.sessionSync.getPerformanceMetrics();
    console.log('Sync metrics:', metrics);
    
    // Manually trigger sync
    window.sessionSync.syncSessionState();
}
```

4. **Monitor Storage Events:**
```javascript
window.addEventListener('storage', function(event) {
    console.log('Storage event:', {
        key: event.key,
        oldValue: event.oldValue,
        newValue: event.newValue,
        url: event.url
    });
});
```

**Solutions:**

1. **Reinitialize SessionSync:**
```javascript
// Destroy and recreate SessionSync
if (window.sessionSync) {
    window.sessionSync.destroy();
}

window.sessionSync = new SessionSync();
window.sessionSync.init();
```

2. **Clear Storage and Restart:**
```javascript
// Clear session-related storage
Object.keys(localStorage).forEach(key => {
    if (key.startsWith('vedfolnir_')) {
        localStorage.removeItem(key);
    }
});

// Reload page
window.location.reload();
```

## Session Expiration Problems

### Debugging Session Expiration

**Check Session Expiration Logic:**
```python
from session_manager import SessionManager
from models import UserSession
from datetime import datetime, timezone

session_manager = SessionManager(db_manager)

# Get session object
with db_manager.get_session() as db_session:
    user_session = db_session.query(UserSession).filter_by(
        session_id=session_id
    ).first()
    
    if user_session:
        print(f"Session created: {user_session.created_at}")
        print(f"Session updated: {user_session.updated_at}")
        
        # Check expiration manually
        is_expired = session_manager._is_session_expired(user_session)
        print(f"Is expired: {is_expired}")
        
        # Check specific timeouts
        now = datetime.now(timezone.utc)
        if user_session.updated_at:
            idle_time = now - user_session.updated_at.replace(tzinfo=timezone.utc)
            print(f"Idle time: {idle_time}")
            print(f"Idle timeout: {session_manager.config.timeout.idle_timeout}")
            print(f"Idle expired: {idle_time > session_manager.config.timeout.idle_timeout}")
        
        if user_session.created_at:
            absolute_time = now - user_session.created_at.replace(tzinfo=timezone.utc)
            print(f"Absolute time: {absolute_time}")
            print(f"Absolute timeout: {session_manager.config.timeout.absolute_timeout}")
            print(f"Absolute expired: {absolute_time > session_manager.config.timeout.absolute_timeout}")
```

### Preventing Premature Expiration

**Update Session Activity:**
```python
from flask import session
from datetime import datetime, timezone

# Update session activity timestamp
session['last_activity'] = datetime.now(timezone.utc).isoformat()

# Update database session
with db_manager.get_session() as db_session:
    user_session = db_session.query(UserSession).filter_by(
        session_id=session.get('_id')
    ).first()
    
    if user_session:
        user_session.updated_at = datetime.now(timezone.utc)
        db_session.commit()
```

## Cross-Tab Synchronization Issues

### Debugging Cross-Tab Communication

**Test Storage Events:**
```javascript
// In one tab, trigger a storage event
localStorage.setItem('test_sync', JSON.stringify({
    type: 'test',
    timestamp: Date.now(),
    tabId: 'tab1'
}));

// In another tab, listen for the event
window.addEventListener('storage', function(event) {
    if (event.key === 'test_sync') {
        console.log('Received test sync:', JSON.parse(event.newValue));
    }
});
```

**Manual Session Sync Test:**
```javascript
// Test session sync API directly
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
    console.log('Session state:', data);
    
    // Manually update localStorage
    localStorage.setItem('vedfolnir_session_state', JSON.stringify({
        ...data,
        timestamp: Date.now(),
        tabId: 'manual-test'
    }));
})
.catch(error => {
    console.error('Session sync error:', error);
});
```

### Fixing Sync Issues

**Reset Session Sync:**
```javascript
function resetSessionSync() {
    // Clear all session-related storage
    Object.keys(localStorage).forEach(key => {
        if (key.startsWith('vedfolnir_')) {
            localStorage.removeItem(key);
        }
    });
    
    // Reinitialize session sync
    if (window.sessionSync) {
        window.sessionSync.destroy();
        window.sessionSync = new SessionSync();
        window.sessionSync.init();
    }
    
    console.log('Session sync reset complete');
}
```

## Platform Switching Problems

### Debugging Platform Switch Failures

**Check Platform Ownership:**
```python
from models import PlatformConnection

def debug_platform_switch(user_id, platform_id):
    with db_manager.get_session() as db_session:
        platform = db_session.query(PlatformConnection).filter_by(
            id=platform_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if not platform:
            print(f"Platform {platform_id} not found or not accessible to user {user_id}")
            
            # Check if platform exists but belongs to different user
            other_platform = db_session.query(PlatformConnection).filter_by(
                id=platform_id
            ).first()
            
            if other_platform:
                print(f"Platform exists but belongs to user {other_platform.user_id}")
            else:
                print(f"Platform {platform_id} does not exist")
        else:
            print(f"Platform {platform_id} is valid for user {user_id}")
            print(f"Platform name: {platform.name}")
            print(f"Platform type: {platform.platform_type}")
            print(f"Is active: {platform.is_active}")
```

**Test Platform Switch API:**
```javascript
async function testPlatformSwitch(platformId) {
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
        console.log('Platform switch result:', result);
        
        if (!result.success) {
            console.error('Platform switch failed:', result.error);
        }
        
        return result;
    } catch (error) {
        console.error('Platform switch error:', error);
        return { success: false, error: error.message };
    }
}

function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}
```

### Fixing Platform Switch Issues

**Force Platform Context Update:**
```python
from flask import session
from session_manager import SessionManager

def force_platform_context_update(user_id, platform_id):
    """Force update platform context in all session systems"""
    
    session_manager = SessionManager(db_manager)
    
    # Update database session
    flask_session_id = session.get('_id')
    if flask_session_id:
        success = session_manager.update_platform_context(flask_session_id, platform_id)
        print(f"Database session update: {success}")
    
    # Update Flask session
    session['platform_connection_id'] = platform_id
    session['last_activity'] = datetime.now(timezone.utc).isoformat()
    
    # Set as default platform
    db_success = db_manager.set_default_platform(user_id, platform_id)
    print(f"Default platform update: {db_success}")
    
    return success and db_success
```

## Database Session Issues

### Debugging Database Connection Problems

**Check Connection Pool Status:**
```python
from session_manager import SessionManager

session_manager = SessionManager(db_manager)
pool_status = session_manager.get_connection_pool_status()

print("Connection Pool Status:")
print(f"Pool size: {pool_status['pool_size']}")
print(f"Checked out: {pool_status['checked_out']}")
print(f"Available: {pool_status['available_connections']}")
print(f"Overflow: {pool_status['overflow']}")

if pool_status['checked_out'] >= pool_status['pool_size']:
    print("WARNING: Connection pool exhausted!")
```

**Test Database Connectivity:**
```python
def test_database_connection():
    try:
        with db_manager.get_session() as db_session:
            from sqlalchemy import text
            result = db_session.execute(text("SELECT 1")).fetchone()
            print(f"Database connection test: {result[0] == 1}")
            return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False
```

### Fixing Database Issues

**Optimize Connection Pool:**
```python
from session_manager import SessionManager

session_manager = SessionManager(db_manager)

# Optimize connection pool
success = session_manager.optimize_connection_pool()
print(f"Connection pool optimization: {success}")

# Check status after optimization
pool_status = session_manager.get_connection_pool_status()
print(f"Pool status after optimization: {pool_status}")
```

**Clean Up Stale Sessions:**
```python
def cleanup_stale_sessions():
    """Clean up stale database sessions"""
    
    session_manager = SessionManager(db_manager)
    
    # Clean up expired sessions
    expired_count = session_manager.cleanup_expired_sessions()
    print(f"Cleaned up {expired_count} expired sessions")
    
    # Enforce session timeout
    timeout_count = session_manager.enforce_session_timeout()
    print(f"Expired {timeout_count} idle sessions")
    
    return expired_count + timeout_count
```

## Performance Problems

### Identifying Performance Issues

**Monitor Session Performance:**
```python
from session_performance_monitor import get_performance_monitor

monitor = get_performance_monitor()
if monitor:
    metrics = monitor.get_current_metrics()
    print("Session Performance Metrics:")
    print(f"Active sessions: {metrics['session_metrics']['active_sessions']}")
    print(f"Session creation rate: {metrics['session_metrics']['creation_rate']}")
    print(f"Session error rate: {metrics['session_metrics']['error_rate']}")
    
    summary = monitor.get_performance_summary()
    print(f"Performance summary: {summary}")
```

**Check Session Query Performance:**
```python
import time
from session_manager import SessionManager

def benchmark_session_operations():
    session_manager = SessionManager(db_manager)
    
    # Benchmark session creation
    start_time = time.time()
    session_id = session_manager.create_user_session(user_id, platform_id)
    creation_time = time.time() - start_time
    print(f"Session creation time: {creation_time:.3f}s")
    
    # Benchmark session context retrieval
    start_time = time.time()
    context = session_manager.get_session_context(session_id)
    retrieval_time = time.time() - start_time
    print(f"Session retrieval time: {retrieval_time:.3f}s")
    
    # Benchmark session validation
    start_time = time.time()
    is_valid = session_manager.validate_session(session_id, user_id)
    validation_time = time.time() - start_time
    print(f"Session validation time: {validation_time:.3f}s")
```

### Optimizing Performance

**Enable Session Caching:**
```python
from session_manager import CachedSessionManager

# Use cached session manager for better performance
cached_session_manager = CachedSessionManager(db_manager)

# This will hit the database
context1 = cached_session_manager.get_session_context(session_id)

# This will hit the cache
context2 = cached_session_manager.get_session_context(session_id)
```

**Batch Session Operations:**
```python
from session_manager import BatchSessionOperations

batch_ops = BatchSessionOperations(session_manager)

# Validate multiple sessions at once
session_pairs = [
    ("session1", 123),
    ("session2", 124),
    ("session3", 125)
]

results = batch_ops.batch_validate_sessions(session_pairs)
print(f"Batch validation results: {results}")
```

## Security-Related Issues

### Debugging CSRF Token Problems

**Check CSRF Token Availability:**
```javascript
function checkCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    if (token) {
        console.log('CSRF token found:', token.getAttribute('content').substring(0, 10) + '...');
        return true;
    } else {
        console.error('CSRF token not found in page');
        return false;
    }
}

// Test CSRF token in API request
async function testCSRFRequest() {
    const token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    
    try {
        const response = await fetch('/api/test_csrf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': token
            },
            credentials: 'same-origin',
            body: JSON.stringify({ test: 'data' })
        });
        
        console.log('CSRF test response:', response.status);
        return response.ok;
    } catch (error) {
        console.error('CSRF test error:', error);
        return false;
    }
}
```

**Refresh CSRF Token:**
```javascript
async function refreshCSRFToken() {
    try {
        const response = await fetch('/api/csrf-token', {
            credentials: 'same-origin'
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Update meta tag
            let csrfMeta = document.querySelector('meta[name="csrf-token"]');
            if (!csrfMeta) {
                csrfMeta = document.createElement('meta');
                csrfMeta.name = 'csrf-token';
                document.head.appendChild(csrfMeta);
            }
            csrfMeta.content = data.csrf_token;
            
            console.log('CSRF token refreshed');
            return true;
        }
    } catch (error) {
        console.error('Error refreshing CSRF token:', error);
    }
    
    return false;
}
```

### Fixing Security Issues

**Validate Session Security:**
```python
from session_manager import SessionManager

def validate_session_security(session_id, user_id):
    session_manager = SessionManager(db_manager)
    
    # Get security information
    security_info = session_manager.get_session_security_info(session_id)
    
    if security_info:
        print(f"Session security info:")
        print(f"- Is expired: {security_info['is_expired']}")
        print(f"- Is suspicious: {security_info['is_suspicious']}")
        print(f"- Session age: {security_info['session_age_seconds']}s")
        print(f"- Last activity: {security_info['last_activity_seconds']}s ago")
        
        if security_info['is_suspicious']:
            print("WARNING: Suspicious session activity detected!")
            
            # Invalidate suspicious session
            session_manager.invalidate_session(session_id, "suspicious_activity")
            return False
    
    return True
```

## Debugging Tools

### Session Debug Console

```python
def session_debug_console():
    """Interactive session debugging console"""
    
    session_manager = SessionManager(db_manager)
    
    while True:
        command = input("Session Debug> ").strip().lower()
        
        if command == 'help':
            print("Available commands:")
            print("  list - List all active sessions")
            print("  get <session_id> - Get session context")
            print("  validate <session_id> <user_id> - Validate session")
            print("  cleanup - Clean up expired sessions")
            print("  stats - Show session statistics")
            print("  pool - Show connection pool status")
            print("  quit - Exit debug console")
        
        elif command == 'list':
            with db_manager.get_session() as db_session:
                sessions = db_session.query(UserSession).all()
                print(f"Active sessions: {len(sessions)}")
                for session_obj in sessions[:10]:  # Show first 10
                    print(f"  {session_obj.session_id} - User {session_obj.user_id}")
        
        elif command.startswith('get '):
            session_id = command.split(' ', 1)[1]
            context = session_manager.get_session_context(session_id)
            print(f"Session context: {context}")
        
        elif command.startswith('validate '):
            parts = command.split(' ')
            if len(parts) == 3:
                session_id, user_id = parts[1], int(parts[2])
                is_valid = session_manager.validate_session(session_id, user_id)
                print(f"Session valid: {is_valid}")
        
        elif command == 'cleanup':
            count = session_manager.cleanup_expired_sessions()
            print(f"Cleaned up {count} expired sessions")
        
        elif command == 'stats':
            # Show session statistics
            with db_manager.get_session() as db_session:
                total_sessions = db_session.query(UserSession).count()
                print(f"Total sessions: {total_sessions}")
        
        elif command == 'pool':
            pool_status = session_manager.get_connection_pool_status()
            print(f"Connection pool status: {pool_status}")
        
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
// Session debugging utilities
window.sessionDebug = {
    // Get current session state
    getState: async function() {
        try {
            const response = await fetch('/api/session_state', {
                credentials: 'same-origin'
            });
            const data = await response.json();
            console.log('Current session state:', data);
            return data;
        } catch (error) {
            console.error('Error getting session state:', error);
            return null;
        }
    },
    
    // Test session sync
    testSync: function() {
        if (window.sessionSync) {
            console.log('Testing session sync...');
            window.sessionSync.syncSessionState();
            
            const metrics = window.sessionSync.getPerformanceMetrics();
            console.log('Sync metrics:', metrics);
        } else {
            console.error('SessionSync not available');
        }
    },
    
    // Monitor storage events
    monitorStorage: function() {
        window.addEventListener('storage', function(event) {
            if (event.key && event.key.startsWith('vedfolnir_')) {
                console.log('Storage event:', {
                    key: event.key,
                    oldValue: event.oldValue ? JSON.parse(event.oldValue) : null,
                    newValue: event.newValue ? JSON.parse(event.newValue) : null
                });
            }
        });
        console.log('Storage monitoring enabled');
    },
    
    // Clear all session data
    clearAll: function() {
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith('vedfolnir_')) {
                localStorage.removeItem(key);
            }
        });
        console.log('All session data cleared');
    },
    
    // Test platform switch
    testPlatformSwitch: async function(platformId) {
        if (window.customSessionHandler) {
            const result = await window.customSessionHandler.switchPlatform(platformId);
            console.log('Platform switch result:', result);
            return result;
        } else {
            console.error('Custom session handler not available');
            return false;
        }
    }
};

// Enable debug mode
console.log('Session debug tools loaded. Use window.sessionDebug for debugging.');
```

## Configuration Issues

### Common Configuration Problems

**Check Environment Variables:**
```bash
# Verify session configuration
echo "Session lifetime: $SESSION_LIFETIME_SECONDS"
echo "Idle timeout: $SESSION_IDLE_TIMEOUT_SECONDS"
echo "Cleanup interval: $SESSION_CLEANUP_INTERVAL_SECONDS"
echo "Cross-tab sync: $SESSION_FEATURE_CROSS_TAB_SYNC"
```

**Validate Configuration:**
```python
from session_config import get_session_config

def validate_session_config():
    config = get_session_config()
    
    # Validate configuration
    issues = config.validate_configuration()
    
    if issues:
        print("Configuration issues found:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    else:
        print("Configuration is valid")
        return True

# Show current configuration
def show_session_config():
    config = get_session_config()
    
    print("Session Configuration:")
    print(f"Environment: {config.environment}")
    print(f"Debug mode: {config.debug_mode}")
    print(f"Session lifetime: {config.timeout.session_lifetime}")
    print(f"Idle timeout: {config.timeout.idle_timeout}")
    print(f"Cross-tab sync: {config.features.enable_cross_tab_sync}")
    print(f"Background cleanup: {config.features.enable_background_cleanup}")
```

### Fixing Configuration Issues

**Reset to Default Configuration:**
```python
from session_config import SessionConfig

def reset_to_defaults():
    # Create default configuration
    default_config = SessionConfig.create_default()
    
    # Apply to environment
    default_config.apply_to_environment()
    
    print("Configuration reset to defaults")
```

## Recovery Procedures

### Complete Session System Reset

```python
def complete_session_reset(user_id=None):
    """Complete reset of session system"""
    
    print("Starting complete session system reset...")
    
    # 1. Clean up database sessions
    session_manager = SessionManager(db_manager)
    
    if user_id:
        # Clean up specific user's sessions
        count = session_manager.cleanup_all_user_sessions(user_id)
        print(f"Cleaned up {count} sessions for user {user_id}")
    else:
        # Clean up all expired sessions
        count = session_manager.cleanup_expired_sessions()
        print(f"Cleaned up {count} expired sessions")
    
    # 2. Optimize connection pool
    session_manager.optimize_connection_pool()
    print("Connection pool optimized")
    
    # 3. Clear session cache if using cached manager
    try:
        from session_manager import session_cache
        session_cache.clear()
        print("Session cache cleared")
    except ImportError:
        pass
    
    # 4. Reset session configuration
    from session_config import reload_session_config
    reload_session_config()
    print("Session configuration reloaded")
    
    print("Complete session system reset finished")
```

### Emergency Session Recovery

```python
def emergency_session_recovery():
    """Emergency recovery for broken session system"""
    
    print("Starting emergency session recovery...")
    
    try:
        # 1. Test database connectivity
        with db_manager.get_session() as db_session:
            from sqlalchemy import text
            db_session.execute(text("SELECT 1"))
        print("✓ Database connectivity OK")
        
        # 2. Check session table integrity
        with db_manager.get_session() as db_session:
            count = db_session.query(UserSession).count()
        print(f"✓ Session table accessible ({count} sessions)")
        
        # 3. Validate session manager
        session_manager = SessionManager(db_manager)
        pool_status = session_manager.get_connection_pool_status()
        print(f"✓ Session manager OK (pool: {pool_status['available_connections']} available)")
        
        # 4. Test session operations
        test_user_id = 1  # Use existing user ID
        test_platform_id = 1  # Use existing platform ID
        
        # Create test session
        test_session_id = session_manager.create_user_session(test_user_id, test_platform_id)
        print(f"✓ Session creation OK ({test_session_id})")
        
        # Get session context
        context = session_manager.get_session_context(test_session_id)
        if context:
            print("✓ Session context retrieval OK")
        else:
            print("✗ Session context retrieval failed")
        
        # Clean up test session
        session_manager._cleanup_session(test_session_id)
        print("✓ Session cleanup OK")
        
        print("Emergency recovery completed successfully")
        return True
        
    except Exception as e:
        print(f"✗ Emergency recovery failed: {e}")
        print("Manual intervention required")
        return False
```

### Session Data Recovery

```python
def recover_session_data(user_id):
    """Recover session data for a specific user"""
    
    print(f"Recovering session data for user {user_id}...")
    
    with db_manager.get_session() as db_session:
        # Get user's platforms
        platforms = db_session.query(PlatformConnection).filter_by(
            user_id=user_id,
            is_active=True
        ).all()
        
        if not platforms:
            print("No active platforms found for user")
            return False
        
        # Get default platform or first available
        default_platform = None
        for platform in platforms:
            if platform.is_default:
                default_platform = platform
                break
        
        if not default_platform:
            default_platform = platforms[0]
            # Set as default
            default_platform.is_default = True
            db_session.commit()
        
        print(f"Default platform: {default_platform.name}")
        
        # Create new session
        session_manager = SessionManager(db_manager)
        session_id = session_manager.create_user_session(user_id, default_platform.id)
        
        print(f"New session created: {session_id}")
        
        # Verify session
        context = session_manager.get_session_context(session_id)
        if context:
            print("Session recovery successful")
            return session_id
        else:
            print("Session recovery failed")
            return None
```

This comprehensive troubleshooting guide provides solutions for the most common session management issues and includes debugging tools and recovery procedures to help maintain a healthy session management system.
# session_manager

Session Management for Platform-Aware Database System

This module provides session management utilities that track user's active platform context
and handle platform switching, session cleanup, and security validation.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_manager.py`

## Classes

### SessionDatabaseError

```python
class SessionDatabaseError(Exception)
```

Raised when database session operations fail

### SessionError

```python
class SessionError(Exception)
```

General session management error

### SessionManager

```python
class SessionManager
```

Manages platform-aware user sessions

**Properties:**
- `monitor`
- `security_hardening`

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager, config: Optional[SessionConfig])
```

**Type:** Instance method

#### get_db_session

```python
def get_db_session(self)
```

Context manager for database sessions with comprehensive error handling and cleanup

Yields:
    SQLAlchemy session object
    
Raises:
    SessionDatabaseError: For database-specific errors
    SessionError: For general session errors

**Decorators:**
- `@contextmanager`

**Type:** Instance method

#### create_user_session

```python
def create_user_session(self, user_id: int, platform_connection_id: Optional[int]) -> str
```

Create a new user session with optional platform context

Args:
    user_id: ID of the user
    platform_connection_id: Optional platform connection ID to set as active
    
Returns:
    Session ID string
    
Raises:
    ValueError: If user or platform connection is invalid

**Type:** Instance method

#### get_session_context

```python
def get_session_context(self, session_id: str) -> Optional[Dict[str, Any]]
```

Get session context including user and platform information

Args:
    session_id: Session ID to look up
    
Returns:
    Dictionary with session context or None if session not found

**Type:** Instance method

#### update_platform_context

```python
def update_platform_context(self, session_id: str, platform_connection_id: int) -> bool
```

Update the active platform for a session with proper validation

Args:
    session_id: Session ID to update
    platform_connection_id: New platform connection ID
    
Returns:
    True if successful, False otherwise

**Type:** Instance method

#### cleanup_expired_sessions

```python
def cleanup_expired_sessions(self) -> int
```

Clean up expired sessions using configurable batch processing

Returns:
    Number of sessions cleaned up

**Type:** Instance method

#### cleanup_user_sessions

```python
def cleanup_user_sessions(self, user_id: int, keep_current: Optional[str]) -> int
```

Clean up expired sessions for a user with concurrent session limits

Args:
    user_id: User ID to clean up sessions for
    keep_current: Session ID to keep (optional)
    
Returns:
    Number of sessions cleaned up

**Type:** Instance method

#### get_user_active_sessions

```python
def get_user_active_sessions(self, user_id: int) -> list
```

Get all active (non-expired) sessions for a user

Args:
    user_id: User ID to get sessions for
    
Returns:
    List of active session dictionaries

**Type:** Instance method

#### cleanup_all_user_sessions

```python
def cleanup_all_user_sessions(self, user_id: int) -> int
```

Clean up ALL sessions for a user (for logout from all devices)

Args:
    user_id: User ID to clean up sessions for
    
Returns:
    Number of sessions cleaned up

**Type:** Instance method

#### validate_session

```python
def validate_session(self, session_id: str, user_id: int) -> bool
```

Validate that a session belongs to the specified user and is not expired

Args:
    session_id: Session ID to validate
    user_id: Expected user ID
    
Returns:
    True if session is valid, False otherwise

**Type:** Instance method

#### _validate_session_security

```python
def _validate_session_security(self, session_id: str, user_id: int) -> bool
```

Perform additional security validation on session

Args:
    session_id: Session ID to validate
    user_id: User ID to validate
    
Returns:
    True if security validation passes, False otherwise

**Type:** Instance method

#### _detect_suspicious_activity

```python
def _detect_suspicious_activity(self, user_session: UserSession) -> bool
```

Detect suspicious session activity patterns

Args:
    user_session: UserSession object to analyze
    
Returns:
    True if suspicious activity detected, False otherwise

**Type:** Instance method

#### invalidate_session

```python
def invalidate_session(self, session_id: str, reason: str) -> bool
```

Invalidate a session for security reasons

Args:
    session_id: Session ID to invalidate
    reason: Reason for invalidation
    
Returns:
    True if successful, False otherwise

**Type:** Instance method

#### get_session_security_info

```python
def get_session_security_info(self, session_id: str) -> Optional[Dict[str, Any]]
```

Get security information about a session

Args:
    session_id: Session ID to analyze
    
Returns:
    Dictionary with security information or None

**Type:** Instance method

#### validate_csrf_token

```python
def validate_csrf_token(self, token: str, session_id: str) -> bool
```

Validate CSRF token for session operations

Args:
    token: CSRF token to validate
    session_id: Session ID associated with the token
    
Returns:
    True if token is valid, False otherwise

**Type:** Instance method

#### create_secure_session_data

```python
def create_secure_session_data(self, user_id: int, platform_id: Optional[int], request_info: Optional[Dict[str, Any]]) -> Dict[str, Any]
```

Create secure session data with minimal sensitive information

Args:
    user_id: User ID
    platform_id: Optional platform ID
    request_info: Optional request information (IP, user agent, etc.)
    
Returns:
    Dictionary with secure session data

**Type:** Instance method

#### sanitize_session_data_for_client

```python
def sanitize_session_data_for_client(self, session_data: Dict[str, Any]) -> Dict[str, Any]
```

Sanitize session data for client-side use (remove sensitive information)

Args:
    session_data: Full session data
    
Returns:
    Sanitized session data safe for client-side use

**Type:** Instance method

#### enforce_session_timeout

```python
def enforce_session_timeout(self, max_idle_time: Optional[timedelta]) -> int
```

Enforce session timeout by cleaning up idle sessions using configuration

Args:
    max_idle_time: Maximum idle time before session expires (uses config if None)
    
Returns:
    Number of sessions cleaned up

**Type:** Instance method

#### batch_cleanup_sessions

```python
def batch_cleanup_sessions(self, batch_size: Optional[int]) -> int
```

Perform batch cleanup of expired sessions using configuration settings

Args:
    batch_size: Number of sessions to process in each batch (uses config default if None)
    
Returns:
    Total number of sessions cleaned up

**Type:** Instance method

#### get_session_cache_key

```python
def get_session_cache_key(self, session_id: str) -> str
```

Generate cache key for session data

Args:
    session_id: Session ID
    
Returns:
    Cache key string

**Type:** Instance method

#### optimize_session_queries

```python
def optimize_session_queries(self) -> Dict[str, Any]
```

Optimize session-related database queries

Returns:
    Dictionary with optimization results

**Type:** Instance method

#### _log_session_operation

```python
def _log_session_operation(self, operation: str, session_id: str, user_id: int, success: bool, details: Optional[Dict[str, Any]])
```

Log session operation for monitoring

**Type:** Instance method

#### _cleanup_session

```python
def _cleanup_session(self, session_id: str) -> bool
```

Clean up a specific session

Args:
    session_id: Session ID to clean up
    
Returns:
    True if successful, False otherwise

**Type:** Instance method

#### _is_session_expired

```python
def _is_session_expired(self, user_session: UserSession) -> bool
```

Check if a session is expired using configuration timeouts

Args:
    user_session: UserSession object to check
    
Returns:
    True if expired, False otherwise

**Type:** Instance method

#### _log_session_metrics

```python
def _log_session_metrics(self, db_session)
```

Log session metrics for monitoring and performance analysis

Args:
    db_session: Database session to analyze

**Type:** Instance method

#### get_connection_pool_status

```python
def get_connection_pool_status(self) -> Dict[str, Any]
```

Get current connection pool status for monitoring

Returns:
    Dictionary with pool status information

**Type:** Instance method

#### optimize_connection_pool

```python
def optimize_connection_pool(self) -> bool
```

Perform connection pool optimization and cleanup

Returns:
    True if optimization successful, False otherwise

**Type:** Instance method

### PlatformContextMiddleware

```python
class PlatformContextMiddleware
```

Flask middleware for managing platform context in requests

**Methods:**

#### __init__

```python
def __init__(self, app, session_manager: SessionManager)
```

**Type:** Instance method

#### init_app

```python
def init_app(self, app)
```

Initialize the middleware with Flask app

**Type:** Instance method

#### before_request

```python
def before_request(self)
```

Set up platform context before each request with proper error handling

**Type:** Instance method

#### after_request

```python
def after_request(self, response)
```

Clean up after request

**Type:** Instance method

## Functions

### get_current_platform_context

```python
def get_current_platform_context() -> Optional[Dict[str, Any]]
```

Get the current platform context from Flask's g object with fallback

Returns:
    Platform context dictionary or None

### get_current_platform

```python
def get_current_platform() -> Optional[PlatformConnection]
```

Get the current platform connection from context using fresh database query

Returns:
    PlatformConnection object or None

### get_current_user_from_context

```python
def get_current_user_from_context() -> Optional[User]
```

Get the current user from platform context using fresh database query

Returns:
    User object or None

### switch_platform_context

```python
def switch_platform_context(platform_connection_id: int) -> bool
```

Switch the current session's platform context

Args:
    platform_connection_id: ID of platform to switch to
    
Returns:
    True if successful, False otherwise


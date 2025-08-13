# database_context_middleware

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/database_context_middleware.py`

## Classes

### DatabaseContextMiddleware

```python
class DatabaseContextMiddleware
```

Middleware to ensure proper database session lifecycle management for Flask requests.

This middleware handles:
- Initializing request-scoped database sessions
- Proper session cleanup and rollback on errors
- Injecting session-aware objects into template context
- Preventing DetachedInstanceError throughout the request lifecycle

**Methods:**

#### __init__

```python
def __init__(self, app: Flask, session_manager: RequestScopedSessionManager)
```

Initialize the database context middleware.

Args:
    app: Flask application instance
    session_manager: RequestScopedSessionManager for handling database sessions

**Type:** Instance method

#### setup_handlers

```python
def setup_handlers(self)
```

Setup Flask request handlers for database session management

**Type:** Instance method

#### _create_safe_template_context

```python
def _create_safe_template_context(self) -> Dict[str, Any]
```

Create safe template context with error handling for database objects.

Returns:
    Dictionary containing safe template context variables

**Type:** Instance method

#### _get_safe_user_dict

```python
def _get_safe_user_dict(self, user) -> Optional[Dict[str, Any]]
```

Safely extract user information into a dictionary.

Args:
    user: Current user object
    
Returns:
    Dictionary with safe user information or None if error

**Type:** Instance method

#### _get_safe_user_platforms

```python
def _get_safe_user_platforms(self, user) -> Dict[str, Any]
```

Safely get user platforms with error handling and recovery.

Args:
    user: Current user object
    
Returns:
    Dictionary containing platform information

**Type:** Instance method

#### _load_platforms_from_database

```python
def _load_platforms_from_database(self, user_id: int) -> Dict[str, Any]
```

Load user platforms directly from database as recovery mechanism.

Args:
    user_id: User ID to load platforms for
    
Returns:
    Dictionary containing platform information

**Type:** Instance method

#### _platform_to_dict

```python
def _platform_to_dict(self, platform: PlatformConnection) -> Dict[str, Any]
```

Convert PlatformConnection to safe dictionary representation.

Args:
    platform: PlatformConnection object
    
Returns:
    Dictionary representation of platform

**Type:** Instance method

#### _get_session_context_info

```python
def _get_session_context_info(self) -> Optional[Dict[str, Any]]
```

Get session context information for debugging.

Returns:
    Dictionary with session context information or None

**Type:** Instance method

#### handle_detached_instance_error

```python
def handle_detached_instance_error(self, error: DetachedInstanceError, context: str)
```

Handle DetachedInstanceError by logging and attempting recovery.

Args:
    error: The DetachedInstanceError that occurred
    context: Context where the error occurred for logging

**Type:** Instance method

#### get_middleware_status

```python
def get_middleware_status(self) -> Dict[str, Any]
```

Get status information about the middleware for monitoring.

Returns:
    Dictionary containing middleware status information

**Type:** Instance method


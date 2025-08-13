# flask_session_manager

Flask-based Session Management System

This module provides Flask-native session management that replaces the database-based
session system. It uses Flask's built-in session handling with secure cookies.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/flask_session_manager.py`

## Classes

### FlaskSessionManager

```python
class FlaskSessionManager
```

Flask-based session manager using secure cookies

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager)
```

**Type:** Instance method

#### create_user_session

```python
def create_user_session(self, user_id: int, platform_connection_id: Optional[int]) -> bool
```

Create a new user session using Flask's session

Args:
    user_id: ID of the user
    platform_connection_id: Optional platform connection ID
    
Returns:
    True if successful, False otherwise

**Type:** Instance method

#### get_session_context

```python
def get_session_context(self) -> Optional[Dict[str, Any]]
```

Get current session context from Flask session

Returns:
    Dictionary with session context or None if not authenticated

**Type:** Instance method

#### update_platform_context

```python
def update_platform_context(self, platform_connection_id: int) -> bool
```

Update the active platform for current session

Args:
    platform_connection_id: New platform connection ID
    
Returns:
    True if successful, False otherwise

**Type:** Instance method

#### validate_session

```python
def validate_session(self, user_id: int) -> bool
```

Validate that current session belongs to the specified user

Args:
    user_id: Expected user ID
    
Returns:
    True if session is valid, False otherwise

**Type:** Instance method

#### clear_session

```python
def clear_session(self)
```

Clear the current session

**Type:** Instance method

#### is_authenticated

```python
def is_authenticated(self) -> bool
```

Check if current session is authenticated

**Type:** Instance method

#### get_current_user_id

```python
def get_current_user_id(self) -> Optional[int]
```

Get current user ID from session

**Type:** Instance method

#### get_current_platform_id

```python
def get_current_platform_id(self) -> Optional[int]
```

Get current platform connection ID from session

**Type:** Instance method

### FlaskPlatformContextMiddleware

```python
class FlaskPlatformContextMiddleware
```

Flask middleware for managing platform context in requests

**Methods:**

#### __init__

```python
def __init__(self, app, flask_session_manager: FlaskSessionManager)
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

Set up platform context before each request

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

Get the current platform context from Flask's g object

Returns:
    Platform context dictionary or None

### get_current_platform

```python
def get_current_platform() -> Optional[PlatformConnection]
```

Get the current platform connection from context

Returns:
    PlatformConnection object or None

### get_current_user_from_context

```python
def get_current_user_from_context() -> Optional[User]
```

Get the current user from platform context

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


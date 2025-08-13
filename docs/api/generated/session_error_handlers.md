# session_error_handlers

Session Error Handlers

Comprehensive error handling for database session issues, specifically targeting
DetachedInstanceError and related SQLAlchemy session problems throughout the application.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_error_handlers.py`

## Classes

### SessionErrorHandler

```python
class SessionErrorHandler
```

Comprehensive handler for database session errors and recovery

**Methods:**

#### __init__

```python
def __init__(self, session_manager, detached_instance_handler)
```

Initialize session error handler

Args:
    session_manager: RequestScopedSessionManager instance
    detached_instance_handler: DetachedInstanceHandler instance

**Type:** Instance method

#### handle_detached_instance_error

```python
def handle_detached_instance_error(self, error: DetachedInstanceError, endpoint: str) -> Any
```

Handle DetachedInstanceError with context-aware recovery

Args:
    error: The DetachedInstanceError that occurred
    endpoint: The endpoint where the error occurred
    
Returns:
    Flask response with appropriate redirect and user message

**Type:** Instance method

#### handle_sqlalchemy_error

```python
def handle_sqlalchemy_error(self, error: SQLAlchemyError, endpoint: str) -> Any
```

Handle general SQLAlchemy errors with graceful degradation

Args:
    error: The SQLAlchemy error that occurred
    endpoint: The endpoint where the error occurred
    
Returns:
    Flask response with appropriate error handling

**Type:** Instance method

#### handle_session_timeout

```python
def handle_session_timeout(self, endpoint: str) -> Any
```

Handle session timeout scenarios

Args:
    endpoint: The endpoint where the timeout occurred
    
Returns:
    Flask response with appropriate timeout handling

**Type:** Instance method

#### _force_logout_with_message

```python
def _force_logout_with_message(self, message: str) -> Any
```

Force user logout with a specific message

Args:
    message: Message to display to user
    
Returns:
    Redirect to login page

**Type:** Instance method

#### _log_session_error

```python
def _log_session_error(self, error_context: Dict[str, Any])
```

Log session error with comprehensive context

Args:
    error_context: Dictionary containing error details

**Type:** Instance method

#### _increment_error_count

```python
def _increment_error_count(self, error_type: str, endpoint: str)
```

Increment error count for monitoring

Args:
    error_type: Type of error (detached_instance, sqlalchemy, etc.)
    endpoint: Endpoint where error occurred

**Type:** Instance method

#### get_error_statistics

```python
def get_error_statistics(self) -> Dict[str, int]
```

Get error statistics for monitoring

Returns:
    Dictionary of error counts by type and endpoint

**Type:** Instance method

## Functions

### with_session_error_handling

```python
def with_session_error_handling(f: Callable) -> Callable
```

Decorator to add comprehensive session error handling to view functions

Args:
    f: View function to wrap
    
Returns:
    Wrapped function with error handling

### register_session_error_handlers

```python
def register_session_error_handlers(app, session_manager, detached_instance_handler)
```

Register comprehensive session error handlers with Flask app

Args:
    app: Flask application instance
    session_manager: RequestScopedSessionManager instance
    detached_instance_handler: DetachedInstanceHandler instance

### get_session_error_handler

```python
def get_session_error_handler()
```

Get the current application's SessionErrorHandler

Returns:
    SessionErrorHandler instance
    
Raises:
    RuntimeError: If no handler is configured


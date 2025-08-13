# detached_instance_handler

DetachedInstanceError Recovery Handler

This module provides comprehensive handling and recovery mechanisms for SQLAlchemy
DetachedInstanceError exceptions, ensuring database objects remain accessible
throughout the Flask request lifecycle.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/detached_instance_handler.py`

## Classes

### DetachedInstanceHandler

```python
class DetachedInstanceHandler
```

Handler for DetachedInstanceError recovery with session manager integration

**Methods:**

#### __init__

```python
def __init__(self, session_manager)
```

Initialize handler with session manager

Args:
    session_manager: RequestScopedSessionManager instance

**Type:** Instance method

#### handle_detached_instance

```python
def handle_detached_instance(self, obj: Any, session: Optional[Session]) -> Any
```

Recover detached objects using merge or reload

Args:
    obj: The detached SQLAlchemy object
    session: Optional session to use, defaults to request session
    
Returns:
    Recovered object attached to session
    
Raises:
    InvalidRequestError: If recovery fails

**Type:** Instance method

#### safe_access

```python
def safe_access(self, obj: Any, attr_name: str, default: Any) -> Any
```

Safely access object attributes with automatic recovery

Args:
    obj: The SQLAlchemy object
    attr_name: Name of the attribute to access
    default: Default value if access fails
    
Returns:
    Attribute value or default

**Type:** Instance method

#### safe_relationship_access

```python
def safe_relationship_access(self, obj: Any, relationship_name: str, default: Optional[list]) -> Any
```

Safely access object relationships with automatic recovery

Args:
    obj: The SQLAlchemy object
    relationship_name: Name of the relationship to access
    default: Default value if access fails (defaults to empty list)
    
Returns:
    Relationship value or default

**Type:** Instance method

#### ensure_attached

```python
def ensure_attached(self, obj: Any, session: Optional[Session]) -> Any
```

Ensure object is attached to session, recovering if necessary

Args:
    obj: The SQLAlchemy object
    session: Optional session to use, defaults to request session
    
Returns:
    Object attached to session

**Type:** Instance method

#### _record_recovery_metrics

```python
def _record_recovery_metrics(self, object_type: str, duration: float, success: bool)
```

Record recovery performance metrics

**Type:** Instance method

## Functions

### create_global_detached_instance_handler

```python
def create_global_detached_instance_handler(app, session_manager)
```

Create global error handler for DetachedInstanceError exceptions

Args:
    app: Flask application instance
    session_manager: RequestScopedSessionManager instance

### get_detached_instance_handler

```python
def get_detached_instance_handler()
```

Get the current application's DetachedInstanceHandler

Returns:
    DetachedInstanceHandler instance
    
Raises:
    RuntimeError: If no handler is configured


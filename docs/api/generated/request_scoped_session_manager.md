# request_scoped_session_manager

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/request_scoped_session_manager.py`

## Classes

### RequestScopedSessionManager

```python
class RequestScopedSessionManager
```

Manages database sessions scoped to Flask requests to prevent DetachedInstanceError

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager)
```

Initialize the request-scoped session manager.

Args:
    db_manager: The database manager instance

**Type:** Instance method

#### get_request_session

```python
def get_request_session(self)
```

Get or create a database session for the current request.

Returns:
    SQLAlchemy session object scoped to the current request
    
Raises:
    RuntimeError: If called outside of Flask request context

**Type:** Instance method

#### close_request_session

```python
def close_request_session(self)
```

Close the database session at the end of the request.

This method should be called in Flask's teardown_request handler
to ensure proper cleanup of database resources.

**Type:** Instance method

#### session_scope

```python
def session_scope(self)
```

Context manager for database operations with automatic commit/rollback.

This provides a transactional scope around a series of operations.
The session will be committed if no exceptions occur, otherwise
it will be rolled back.

Yields:
    SQLAlchemy session object
    
Example:
    with session_manager.session_scope() as session:
        user = session.query(User).get(user_id)
        user.name = "New Name"
        # Automatic commit happens here if no exception

**Decorators:**
- `@contextmanager`

**Type:** Instance method

#### ensure_session_attachment

```python
def ensure_session_attachment(self, obj)
```

Ensure that a database object is attached to the current request session.

This method helps prevent DetachedInstanceError by reattaching objects
to the current session if they become detached.

Args:
    obj: SQLAlchemy model instance to ensure attachment
    
Returns:
    The object attached to the current session

**Type:** Instance method

#### is_session_active

```python
def is_session_active(self) -> bool
```

Check if there is an active session for the current request.

Returns:
    True if there is an active session, False otherwise

**Type:** Instance method

#### get_session_info

```python
def get_session_info(self) -> dict
```

Get information about the current session for debugging purposes.

Returns:
    Dictionary containing session information

**Type:** Instance method

#### _record_session_creation

```python
def _record_session_creation(self, duration: float)
```

Record session creation metrics

**Type:** Instance method

#### _record_session_closure

```python
def _record_session_closure(self, duration: float)
```

Record session closure metrics

**Type:** Instance method

#### _record_session_commit

```python
def _record_session_commit(self)
```

Record session commit metrics

**Type:** Instance method

#### _record_session_rollback

```python
def _record_session_rollback(self)
```

Record session rollback metrics

**Type:** Instance method

#### _record_session_reattachment

```python
def _record_session_reattachment(self, object_type: str, duration: float)
```

Record session reattachment metrics

**Type:** Instance method

#### _record_session_error

```python
def _record_session_error(self, error_type: str, error_message: str)
```

Record session error metrics

**Type:** Instance method


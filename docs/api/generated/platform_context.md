# platform_context

Platform Context Manager

This module provides the PlatformContextManager class for handling platform-specific
operations and context switching in the Vedfolnir platform-aware system.

The context manager tracks the current user and their active platform connection,
provides platform filtering for database queries, and handles platform-specific
configuration generation.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/platform_context.py`

## Classes

### PlatformContext

```python
class PlatformContext
```

Represents the current platform context for a user

**Decorators:**
- `@dataclass`

**Properties:**
- `is_valid`
- `platform_info`

**Methods:**

#### __post_init__

```python
def __post_init__(self)
```

Validate context after initialization

**Type:** Instance method

### PlatformContextError

```python
class PlatformContextError(Exception)
```

Raised when there are issues with platform context operations

### PlatformContextManager

```python
class PlatformContextManager
```

Manages platform context for users and provides platform-aware operations.

This class handles:
- Setting and tracking user and platform context
- Platform filtering for database queries
- Data injection with platform information
- ActivityPub configuration generation
- Thread-safe context management

**Properties:**
- `current_context`

**Methods:**

#### __init__

```python
def __init__(self, session: Session)
```

Initialize the platform context manager.

Args:
    session: SQLAlchemy database session

**Type:** Instance method

#### set_context

```python
def set_context(self, user_id: int, platform_connection_id: Optional[int], session_id: Optional[str]) -> PlatformContext
```

Set the platform context for the current thread.

Args:
    user_id: ID of the user
    platform_connection_id: ID of the platform connection (optional)
    session_id: Session ID for tracking (optional)
    
Returns:
    The created platform context
    
Raises:
    PlatformContextError: If context cannot be set

**Type:** Instance method

#### clear_context

```python
def clear_context(self) -> None
```

Clear the platform context for the current thread

**Type:** Instance method

#### require_context

```python
def require_context(self) -> PlatformContext
```

Get the current context, raising an error if not set.

Returns:
    The current platform context
    
Raises:
    PlatformContextError: If no context is set

**Type:** Instance method

#### context_scope

```python
def context_scope(self, user_id: int, platform_connection_id: Optional[int], session_id: Optional[str])
```

Context manager for temporary platform context.

Args:
    user_id: ID of the user
    platform_connection_id: ID of the platform connection (optional)
    session_id: Session ID for tracking (optional)
    
Yields:
    The platform context

**Decorators:**
- `@contextmanager`

**Type:** Instance method

#### get_platform_filter_criteria

```python
def get_platform_filter_criteria(self, model_class) -> List
```

Get SQLAlchemy filter criteria for platform-aware queries.

Args:
    model_class: The SQLAlchemy model class to filter
    
Returns:
    List of SQLAlchemy filter criteria
    
Raises:
    PlatformContextError: If no context is set

**Type:** Instance method

#### apply_platform_filter

```python
def apply_platform_filter(self, query, model_class)
```

Apply platform filtering to a SQLAlchemy query.

Args:
    query: SQLAlchemy query object
    model_class: The model class being queried
    
Returns:
    Filtered query object

**Type:** Instance method

#### inject_platform_data

```python
def inject_platform_data(self, data: Dict[str, Any], model_class) -> Dict[str, Any]
```

Inject platform identification data into a dictionary.

Args:
    data: Dictionary to inject platform data into
    model_class: Optional model class to determine which fields to inject
    
Returns:
    Dictionary with platform data injected
    
Raises:
    PlatformContextError: If no context is set

**Type:** Instance method

#### create_activitypub_config

```python
def create_activitypub_config(self) -> ActivityPubConfig
```

Create an ActivityPub configuration from the current platform context.

Returns:
    ActivityPub configuration object
    
Raises:
    PlatformContextError: If no context is set or config cannot be created

**Type:** Instance method

#### switch_platform

```python
def switch_platform(self, platform_connection_id: int) -> PlatformContext
```

Switch to a different platform connection for the current user.

Args:
    platform_connection_id: ID of the platform connection to switch to
    
Returns:
    Updated platform context
    
Raises:
    PlatformContextError: If switch fails or platform not accessible

**Type:** Instance method

#### get_user_platforms

```python
def get_user_platforms(self, user_id: Optional[int]) -> List[PlatformConnection]
```

Get all active platform connections for a user.

Args:
    user_id: User ID (uses current context user if not provided)
    
Returns:
    List of active platform connections

**Type:** Instance method

#### set_default_platform

```python
def set_default_platform(self, platform_connection_id: int, user_id: Optional[int]) -> None
```

Set a platform connection as the default for a user.

Args:
    platform_connection_id: ID of the platform connection to set as default
    user_id: User ID (uses current context user if not provided)
    
Raises:
    PlatformContextError: If operation fails

**Type:** Instance method

#### test_platform_connection

```python
def test_platform_connection(self, platform_connection_id: Optional[int]) -> Tuple[bool, str]
```

Test a platform connection.

Args:
    platform_connection_id: ID of platform to test (uses current context if not provided)
    
Returns:
    Tuple of (success, message)

**Type:** Instance method

#### get_context_info

```python
def get_context_info(self) -> Dict[str, Any]
```

Get information about the current context.

Returns:
    Dictionary with context information

**Type:** Instance method

#### validate_context

```python
def validate_context(self) -> List[str]
```

Validate the current context and return any issues.

Returns:
    List of validation error messages (empty if valid)

**Type:** Instance method


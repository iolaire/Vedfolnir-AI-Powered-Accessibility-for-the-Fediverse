# safe_template_context

Safe Template Context Processor

This module provides safe template context processing with error handling
for DetachedInstanceError and other database session issues. It ensures
templates never receive detached database objects.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/safe_template_context.py`

## Functions

### safe_template_context

```python
def safe_template_context() -> Dict[str, Any]
```

Provide safe template context with error handling for database objects.

This function ensures that templates receive safe, serialized data instead
of potentially detached database objects. It handles DetachedInstanceError
gracefully and provides fallback mechanisms.

Requirements: 5.1, 5.2, 5.3, 5.4, 7.1, 7.2

Returns:
    Dictionary containing safe template context variables

### _get_safe_user_data

```python
def _get_safe_user_data(user, handler) -> Optional[Dict[str, Any]]
```

Safely extract user data for template context.

Args:
    user: Current user object
    handler: DetachedInstanceHandler instance
    
Returns:
    Dictionary with safe user data or None

### _get_safe_platforms_data

```python
def _get_safe_platforms_data(user, handler, session_manager) -> Dict[str, Any]
```

Safely extract platform data for template context.

Args:
    user: Current user object
    handler: DetachedInstanceHandler instance
    session_manager: RequestScopedSessionManager instance
    
Returns:
    Dictionary with platform data

### _platform_to_safe_dict

```python
def _platform_to_safe_dict(platform, handler) -> Optional[Dict[str, Any]]
```

Convert platform object to safe dictionary.

Args:
    platform: PlatformConnection object
    handler: DetachedInstanceHandler instance
    
Returns:
    Safe dictionary representation or None

### _query_platforms_fallback

```python
def _query_platforms_fallback(user, handler, session_manager) -> List
```

Fallback method to query platforms directly from database.

Args:
    user: Current user object
    handler: DetachedInstanceHandler instance
    session_manager: RequestScopedSessionManager instance
    
Returns:
    List of platform objects

### _handle_detached_error_fallback

```python
def _handle_detached_error_fallback(context: Dict[str, Any], session_manager) -> None
```

Handle DetachedInstanceError by providing minimal fallback data.

Args:
    context: Template context dictionary to update
    session_manager: RequestScopedSessionManager instance

### create_safe_template_context_processor

```python
def create_safe_template_context_processor(app)
```

Register the safe template context processor with Flask app.

Args:
    app: Flask application instance

### get_safe_user_context

```python
def get_safe_user_context(user_id: Optional[int]) -> Dict[str, Any]
```

Get safe user context for a specific user (utility function).

Args:
    user_id: Optional user ID, defaults to current_user
    
Returns:
    Safe user context dictionary


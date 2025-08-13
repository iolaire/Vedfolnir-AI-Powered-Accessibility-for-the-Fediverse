# platform_context_utils

Platform Context Utilities

Provides utilities to ensure platform context is consistently available throughout the application.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/platform_context_utils.py`

## Functions

### ensure_platform_context

```python
def ensure_platform_context(db_manager, session_manager) -> Tuple[Optional[Dict[str, Any]], bool]
```

Ensure platform context is available, creating it if necessary.

Args:
    db_manager: Database manager instance
    session_manager: Session manager instance
    
Returns:
    Tuple of (platform_context, was_created)
    - platform_context: Dictionary with platform context or None
    - was_created: Boolean indicating if context was newly created

### get_platform_context_with_fallback

```python
def get_platform_context_with_fallback(db_manager, session_manager) -> Optional[Dict[str, Any]]
```

Get platform context with automatic fallback and creation if needed.

Args:
    db_manager: Database manager instance
    session_manager: Session manager instance
    
Returns:
    Platform context dictionary or None

### validate_platform_context

```python
def validate_platform_context(context: Optional[Dict[str, Any]], db_manager) -> bool
```

Validate that a platform context is still valid.

Args:
    context: Platform context dictionary
    db_manager: Database manager instance
    
Returns:
    True if context is valid, False otherwise

### refresh_platform_context

```python
def refresh_platform_context(db_manager, session_manager) -> Optional[Dict[str, Any]]
```

Force refresh of platform context from database.

Args:
    db_manager: Database manager instance
    session_manager: Session manager instance
    
Returns:
    Refreshed platform context or None

### get_current_platform_dict

```python
def get_current_platform_dict(context: Optional[Dict[str, Any]], db_manager) -> Optional[Dict[str, Any]]
```

Get current platform as a dictionary from context.

Args:
    context: Platform context dictionary
    db_manager: Database manager instance
    
Returns:
    Platform dictionary or None


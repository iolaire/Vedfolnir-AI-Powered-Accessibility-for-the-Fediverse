# session_aware_decorators

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_aware_decorators.py`

## Functions

### with_db_session

```python
def with_db_session(f)
```

Decorator to ensure view functions have proper database session and current_user attachment.

This decorator:
- Ensures a request-scoped database session exists
- Reattaches current_user object if it becomes detached
- Handles DetachedInstanceError gracefully

Requirements: 1.1, 1.2, 6.1, 6.2

### require_platform_context

```python
def require_platform_context(f)
```

Decorator to ensure platform context is available for platform-dependent views.

This decorator:
- Ensures user is authenticated
- Verifies user has at least one active platform
- Ensures current platform context is available
- Handles missing platform context gracefully

Requirements: 3.1, 3.2

### handle_detached_instance_error

```python
def handle_detached_instance_error(f)
```

Decorator to handle DetachedInstanceError specifically.

This decorator provides a fallback mechanism for views that might encounter
DetachedInstanceError and need graceful recovery.

Requirements: 6.1, 6.2

### ensure_user_session_attachment

```python
def ensure_user_session_attachment(f)
```

Lightweight decorator to ensure current_user session attachment without full platform checks.

This decorator is useful for views that need current_user but don't require platform context.

Requirements: 1.1, 1.2


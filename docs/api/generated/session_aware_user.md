# session_aware_user

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_aware_user.py`

## Classes

### SessionAwareUser

```python
class SessionAwareUser(UserMixin)
```

A session-aware wrapper for User objects that prevents DetachedInstanceError
by maintaining proper session attachment throughout the request lifecycle.

**Properties:**
- `platforms`
- `is_authenticated`
- `is_anonymous`
- `is_active`

**Methods:**

#### __init__

```python
def __init__(self, user: User, session_manager: RequestScopedSessionManager)
```

Initialize SessionAwareUser with a User object and session manager.

Args:
    user: The User model instance to wrap
    session_manager: RequestScopedSessionManager instance for session management

**Type:** Instance method

#### _get_attached_user

```python
def _get_attached_user(self) -> Optional[User]
```

Get the user object attached to the current request session.

Returns:
    User object attached to current session, or None if not available

**Type:** Instance method

#### _invalidate_cache

```python
def _invalidate_cache(self)
```

Invalidate the platforms cache

**Type:** Instance method

#### get_active_platform

```python
def get_active_platform(self) -> Optional[PlatformConnection]
```

Get the user's active/default platform with proper session context.

Returns:
    Active PlatformConnection object or None if not found

**Type:** Instance method

#### get_platform_by_id

```python
def get_platform_by_id(self, platform_id: int) -> Optional[PlatformConnection]
```

Get a specific platform by ID with session attachment.

Args:
    platform_id: ID of the platform to retrieve
    
Returns:
    PlatformConnection object or None if not found

**Type:** Instance method

#### get_platform_by_type

```python
def get_platform_by_type(self, platform_type: str) -> Optional[PlatformConnection]
```

Get platform by type with session attachment.

Args:
    platform_type: Type of platform to find
    
Returns:
    PlatformConnection object or None if not found

**Type:** Instance method

#### refresh_platforms

```python
def refresh_platforms(self)
```

Force refresh of platforms cache

**Type:** Instance method

#### __getattr__

```python
def __getattr__(self, name: str) -> Any
```

Proxy attribute access to the underlying User object with session safety.

Args:
    name: Attribute name to access
    
Returns:
    Attribute value from underlying User object

**Type:** Instance method

#### __setattr__

```python
def __setattr__(self, name: str, value: Any)
```

Proxy attribute setting to the underlying User object with session safety.

Args:
    name: Attribute name to set
    value: Value to set

**Type:** Instance method

#### get_id

```python
def get_id(self) -> str
```

Get user ID as string for Flask-Login

**Type:** Instance method

#### __repr__

```python
def __repr__(self) -> str
```

String representation of SessionAwareUser

**Type:** Instance method


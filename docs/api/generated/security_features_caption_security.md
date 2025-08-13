# security.features.caption_security

Security controls for caption generation functionality

Implements authorization, validation, and security checks specific to caption generation.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/features/caption_security.py`

## Classes

### CaptionSecurityManager

```python
class CaptionSecurityManager
```

Security manager for caption generation operations

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager)
```

**Type:** Instance method

#### generate_secure_task_id

```python
def generate_secure_task_id(self) -> str
```

Generate cryptographically secure task ID

**Type:** Instance method

#### validate_task_id

```python
def validate_task_id(self, task_id: str) -> bool
```

Validate task ID format

**Type:** Instance method

#### check_user_platform_access

```python
def check_user_platform_access(self, user_id: int, platform_connection_id: int) -> bool
```

Check if user has access to platform connection

**Type:** Instance method

#### check_task_ownership

```python
def check_task_ownership(self, task_id: str, user_id: int) -> bool
```

Check if user owns the task

**Type:** Instance method

#### check_generation_rate_limit

```python
def check_generation_rate_limit(self, user_id: int, limit: int, window_minutes: int) -> bool
```

Check if user is within generation rate limits

**Type:** Instance method

#### validate_generation_settings

```python
def validate_generation_settings(self, settings: Dict[str, Any]) -> tuple[bool, list]
```

Validate caption generation settings

**Type:** Instance method

#### sanitize_task_input

```python
def sanitize_task_input(self, data: Dict[str, Any]) -> Dict[str, Any]
```

Sanitize task input data

**Type:** Instance method

## Functions

### caption_generation_auth_required

```python
def caption_generation_auth_required(f)
```

Decorator to require authentication and platform access for caption generation

### validate_task_access

```python
def validate_task_access(f)
```

Decorator to validate task access for task-specific endpoints

### caption_generation_rate_limit

```python
def caption_generation_rate_limit(limit: int, window_minutes: int)
```

Decorator to rate limit caption generation requests

### validate_caption_settings_input

```python
def validate_caption_settings_input(f)
```

Decorator to validate caption settings input

### log_caption_security_event

```python
def log_caption_security_event(event_type: str, details: Dict[str, Any])
```

Log security events for caption generation


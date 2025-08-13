# error_recovery_manager

Error Recovery Manager for Caption Generation

Implements comprehensive error handling and recovery strategies for caption generation operations.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/error_recovery_manager.py`

## Classes

### ErrorCategory

```python
class ErrorCategory(Enum)
```

Categories of errors for different handling strategies

**Class Variables:**
- `AUTHENTICATION`
- `PLATFORM`
- `RESOURCE`
- `VALIDATION`
- `NETWORK`
- `SYSTEM`
- `UNKNOWN`

### RecoveryStrategy

```python
class RecoveryStrategy(Enum)
```

Recovery strategies for different error types

**Class Variables:**
- `RETRY`
- `FAIL_FAST`
- `FALLBACK`
- `NOTIFY_ADMIN`
- `IGNORE`

### ErrorInfo

```python
class ErrorInfo
```

Information about an error occurrence

**Decorators:**
- `@dataclass`

### RecoveryConfig

```python
class RecoveryConfig
```

Configuration for error recovery

**Decorators:**
- `@dataclass`

### ErrorRecoveryManager

```python
class ErrorRecoveryManager
```

Manages error handling and recovery for caption generation operations

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### _initialize_error_patterns

```python
def _initialize_error_patterns(self) -> Dict[str, ErrorCategory]
```

Initialize error pattern matching for categorization

**Type:** Instance method

#### _initialize_recovery_configs

```python
def _initialize_recovery_configs(self) -> Dict[ErrorCategory, RecoveryConfig]
```

Initialize recovery configurations for each error category

**Type:** Instance method

#### categorize_error

```python
def categorize_error(self, error: Exception, context: Dict[str, Any]) -> ErrorCategory
```

Categorize an error based on its message and context

**Type:** Instance method

#### create_error_info

```python
def create_error_info(self, error: Exception, context: Dict[str, Any]) -> ErrorInfo
```

Create ErrorInfo object from exception

**Type:** Instance method

#### _is_recoverable

```python
def _is_recoverable(self, category: ErrorCategory, error: Exception) -> bool
```

Determine if an error is recoverable

**Type:** Instance method

#### handle_error

```python
async def handle_error(self, error: Exception, operation: Callable, context: Dict[str, Any], *args, **kwargs) -> Any
```

Handle an error with appropriate recovery strategy

**Type:** Instance method

#### _fail_fast

```python
async def _fail_fast(self, error_info: ErrorInfo) -> None
```

Fail fast strategy - immediately raise the error

**Type:** Instance method

#### _retry_with_backoff

```python
async def _retry_with_backoff(self, error_info: ErrorInfo, operation: Callable, config: RecoveryConfig, *args, **kwargs) -> Any
```

Retry operation with exponential backoff

**Type:** Instance method

#### _notify_admin_and_fail

```python
async def _notify_admin_and_fail(self, error_info: ErrorInfo) -> None
```

Notify admin and fail the operation

**Type:** Instance method

#### _fallback_strategy

```python
async def _fallback_strategy(self, error_info: ErrorInfo, operation: Callable, *args, **kwargs) -> Any
```

Implement fallback strategy (placeholder for future implementation)

**Type:** Instance method

#### _get_user_friendly_message

```python
def _get_user_friendly_message(self, error_info: ErrorInfo) -> str
```

Generate user-friendly error message

**Type:** Instance method

#### get_error_statistics

```python
def get_error_statistics(self) -> Dict[str, Any]
```

Get error statistics for monitoring

**Type:** Instance method

#### get_admin_notifications

```python
def get_admin_notifications(self, unread_only: bool) -> List[Dict[str, Any]]
```

Get admin notifications

**Type:** Instance method

#### mark_notification_read

```python
def mark_notification_read(self, notification_index: int) -> bool
```

Mark an admin notification as read

**Type:** Instance method

#### clear_old_errors

```python
def clear_old_errors(self, hours: int) -> int
```

Clear error history older than specified hours

**Type:** Instance method

## Functions

### handle_caption_error

```python
def handle_caption_error(context: Dict[str, Any])
```

Decorator for handling caption generation errors


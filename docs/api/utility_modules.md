# Utility Modules API Documentation

This document provides comprehensive API documentation for Vedfolnir's utility and service modules, including function signatures, parameters, return types, and usage examples.

## Table of Contents

- [Utilities (utils.py)](#utilities)
- [Platform Context (platform_context.py)](#platform-context)
- [Progress Tracker (progress_tracker.py)](#progress-tracker)
- [Rate Limiter (rate_limiter.py)](#rate-limiter)

---

## Utilities

### Class: RetryConfig

Configuration class for retry behavior with comprehensive options.

#### Constructor

```python
def __init__(self, 
             max_attempts: int = 3, 
             base_delay: float = 1.0,
             max_delay: float = 30.0,
             backoff_factor: float = 2.0,
             retry_exceptions: Optional[List[Type[Exception]]] = None,
             retry_status_codes: Optional[List[int]] = None,
             jitter: bool = True,
             jitter_factor: float = 0.1,
             retry_on_timeout: bool = True,
             retry_on_connection_error: bool = True,
             retry_on_server_error: bool = True,
             retry_on_rate_limit: bool = True,
             retry_on_specific_errors: Optional[List[str]] = None)
```

**Parameters:**
- `max_attempts` (int): Maximum number of retry attempts. Defaults to 3.
- `base_delay` (float): Initial delay between retries in seconds. Defaults to 1.0.
- `max_delay` (float): Maximum delay between retries in seconds. Defaults to 30.0.
- `backoff_factor` (float): Multiplier for delay after each retry. Defaults to 2.0.
- `retry_exceptions` (List[Type[Exception]], optional): List of exception types to retry on.
- `retry_status_codes` (List[int], optional): List of HTTP status codes to retry on.
- `jitter` (bool): Whether to add random jitter to delay times. Defaults to True.
- `jitter_factor` (float): Factor to determine jitter amount (0.1 = ±10%). Defaults to 0.1.
- `retry_on_timeout` (bool): Whether to retry on timeout exceptions. Defaults to True.
- `retry_on_connection_error` (bool): Whether to retry on connection errors. Defaults to True.
- `retry_on_server_error` (bool): Whether to retry on server errors (5xx). Defaults to True.
- `retry_on_rate_limit` (bool): Whether to retry on rate limit errors (429). Defaults to True.
- `retry_on_specific_errors` (List[str], optional): List of error message substrings to retry on.

### Decorators

#### async_retry

```python
def async_retry(config: RetryConfig = None, 
                max_attempts: int = None,
                base_delay: float = None,
                max_delay: float = None,
                backoff_factor: float = None,
                jitter: bool = None,
                retry_exceptions: List[Type[Exception]] = None,
                retry_status_codes: List[int] = None) -> Callable
```

Decorator for adding retry logic to async functions.

**Parameters:**
- `config` (RetryConfig, optional): Retry configuration object
- `max_attempts` (int, optional): Override max attempts
- `base_delay` (float, optional): Override base delay
- `max_delay` (float, optional): Override max delay
- `backoff_factor` (float, optional): Override backoff factor
- `jitter` (bool, optional): Override jitter setting
- `retry_exceptions` (List[Type[Exception]], optional): Override retry exceptions
- `retry_status_codes` (List[int], optional): Override retry status codes

**Returns:**
- `Callable`: Decorated function with retry logic

**Example:**
```python
from utils import async_retry, RetryConfig

# Using decorator with default config
@async_retry(max_attempts=5, base_delay=2.0)
async def fetch_data(url: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.json()

# Using decorator with custom config
retry_config = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    backoff_factor=2.0,
    retry_on_timeout=True
)

@async_retry(config=retry_config)
async def api_call():
    # API call implementation
    pass
```

### Statistics Functions

#### get_retry_stats_summary

```python
def get_retry_stats_summary() -> Dict[str, Any]
```

Get summary of retry statistics across all operations.

**Returns:**
- `Dict[str, Any]`: Summary statistics including total attempts, successes, failures

#### get_retry_stats_detailed

```python
def get_retry_stats_detailed() -> Dict[str, Any]
```

Get detailed retry statistics with per-operation breakdown.

**Returns:**
- `Dict[str, Any]`: Detailed statistics with operation-specific metrics

---

## Platform Context

### Class: PlatformContext

Data class representing the current platform context for a user.

#### Constructor

```python
@dataclass
class PlatformContext:
    user_id: int
    user: Optional[User] = None
    platform_connection_id: Optional[int] = None
    platform_connection: Optional[PlatformConnection] = None
    session_id: Optional[str] = None
```

**Attributes:**
- `user_id` (int): User identifier (required)
- `user` (User, optional): User object
- `platform_connection_id` (int, optional): Platform connection ID
- `platform_connection` (PlatformConnection, optional): Platform connection object
- `session_id` (str, optional): Session identifier

#### Properties

##### is_valid

```python
@property
def is_valid(self) -> bool
```

Check if the context is valid and complete.

**Returns:**
- `bool`: True if context is valid, False otherwise

##### platform_info

```python
@property
def platform_info(self) -> Dict[str, Any]
```

Get platform information as a dictionary.

**Returns:**
- `Dict[str, Any]`: Platform information including type, URL, username, etc.

### Class: PlatformContextManager

Manages platform context for users and provides platform-aware operations.

#### Constructor

```python
def __init__(self, session: Session)
```

**Parameters:**
- `session` (Session): SQLAlchemy database session

#### Core Methods

##### set_context

```python
def set_context(self, user_id: int, platform_connection_id: int = None) -> PlatformContext
```

Set the current platform context for a user.

**Parameters:**
- `user_id` (int): User identifier
- `platform_connection_id` (int, optional): Platform connection ID

**Returns:**
- `PlatformContext`: The established context

**Raises:**
- `PlatformContextError`: If context cannot be established

##### get_context

```python
def get_context(self) -> Optional[PlatformContext]
```

Get the current platform context.

**Returns:**
- `PlatformContext`: Current context or None if not set

##### clear_context

```python
def clear_context(self) -> None
```

Clear the current platform context.

##### filter_posts_by_platform

```python
def filter_posts_by_platform(self, query, user_id: int = None) -> Any
```

Filter posts query by current platform context.

**Parameters:**
- `query`: SQLAlchemy query object
- `user_id` (int, optional): User ID to filter by

**Returns:**
- `Any`: Filtered query object

#### Usage Example

```python
from platform_context import PlatformContextManager, PlatformContext
from database import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)

with db_manager.get_session() as session:
    context_manager = PlatformContextManager(session)
    
    # Set context for user
    context = context_manager.set_context(
        user_id=123,
        platform_connection_id=456
    )
    
    if context.is_valid:
        print(f"Context set for platform: {context.platform_info['platform_type']}")
        
        # Use context for filtering
        posts_query = session.query(Post)
        filtered_query = context_manager.filter_posts_by_platform(posts_query)
        posts = filtered_query.all()
        
    # Clear context when done
    context_manager.clear_context()
```

---

## Progress Tracker

### Class: ProgressStatus

Data class for progress status information.

#### Constructor

```python
@dataclass
class ProgressStatus:
    task_id: str
    user_id: int
    current_step: str
    progress_percent: int
    details: Dict[str, Any]
    started_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

**Attributes:**
- `task_id` (str): Task identifier
- `user_id` (int): User identifier
- `current_step` (str): Description of current step
- `progress_percent` (int): Progress percentage (0-100)
- `details` (Dict[str, Any]): Additional progress details
- `started_at` (datetime, optional): Task start time
- `updated_at` (datetime, optional): Last update time

#### Methods

##### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

Convert to dictionary for JSON serialization.

**Returns:**
- `Dict[str, Any]`: Dictionary representation with ISO datetime strings

### Class: ProgressTracker

Tracks progress of caption generation tasks with real-time updates.

#### Constructor

```python
def __init__(self, db_manager: DatabaseManager)
```

**Parameters:**
- `db_manager` (DatabaseManager): Database manager instance

#### Core Methods

##### create_progress_session

```python
def create_progress_session(self, task_id: str, user_id: int) -> str
```

Create a progress tracking session for a task.

**Parameters:**
- `task_id` (str): The task ID to track
- `user_id` (int): The user ID for authorization

**Returns:**
- `str`: Session ID (same as task_id for simplicity)

**Raises:**
- `ValueError`: If task not found or user not authorized

##### update_progress

```python
def update_progress(self, 
                   task_id: str, 
                   current_step: str, 
                   progress_percent: int,
                   details: Dict[str, Any] = None) -> bool
```

Update progress for a task.

**Parameters:**
- `task_id` (str): The task ID to update
- `current_step` (str): Description of current processing step
- `progress_percent` (int): Progress percentage (0-100)
- `details` (Dict[str, Any], optional): Additional progress details

**Returns:**
- `bool`: True if update successful, False otherwise

##### get_progress

```python
def get_progress(self, task_id: str, user_id: int) -> Optional[ProgressStatus]
```

Get current progress for a task.

**Parameters:**
- `task_id` (str): The task ID to query
- `user_id` (int): The user ID for authorization

**Returns:**
- `ProgressStatus`: Current progress status or None if not found

##### register_callback

```python
def register_callback(self, task_id: str, callback: Callable[[ProgressStatus], None]) -> None
```

Register a callback for progress updates.

**Parameters:**
- `task_id` (str): The task ID to monitor
- `callback` (Callable): Function to call on progress updates

#### Usage Example

```python
from progress_tracker import ProgressTracker, ProgressStatus
from database import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)
tracker = ProgressTracker(db_manager)

# Create progress session
session_id = tracker.create_progress_session('task_123', user_id=456)

# Update progress
tracker.update_progress(
    task_id='task_123',
    current_step='Processing images',
    progress_percent=25,
    details={'images_processed': 5, 'total_images': 20}
)

# Get current progress
progress = tracker.get_progress('task_123', user_id=456)
if progress:
    print(f"Progress: {progress.progress_percent}% - {progress.current_step}")

# Register callback for real-time updates
def on_progress_update(status: ProgressStatus):
    print(f"Task {status.task_id}: {status.progress_percent}%")

tracker.register_callback('task_123', on_progress_update)
```

---

## Rate Limiter

### Class: RateLimitConfig

Configuration class for rate limiting behavior with support for per-endpoint and per-platform limits.

#### Constructor

```python
@dataclass
class RateLimitConfig:
    requests_per_minute: int = 60
    requests_per_hour: int = 1000
    requests_per_day: int = 10000
    max_burst: int = 10
    endpoint_limits: Dict[str, Dict[str, int]] = field(default_factory=dict)
    platform_limits: Dict[str, Dict[str, int]] = field(default_factory=dict)
    platform_endpoint_limits: Dict[str, Dict[str, Dict[str, int]]] = field(default_factory=dict)
```

**Attributes:**
- `requests_per_minute` (int): Global requests per minute limit. Defaults to 60.
- `requests_per_hour` (int): Global requests per hour limit. Defaults to 1000.
- `requests_per_day` (int): Global requests per day limit. Defaults to 10000.
- `max_burst` (int): Maximum burst size for token bucket. Defaults to 10.
- `endpoint_limits` (Dict): Per-endpoint rate limits overriding global limits.
- `platform_limits` (Dict): Per-platform rate limits.
- `platform_endpoint_limits` (Dict): Per-platform per-endpoint rate limits.

#### Class Methods

##### from_env

```python
@classmethod
def from_env(cls, env_prefix: str = "RATE_LIMIT") -> RateLimitConfig
```

Create a RateLimitConfig from environment variables.

**Parameters:**
- `env_prefix` (str): Prefix for environment variables. Defaults to "RATE_LIMIT".

**Returns:**
- `RateLimitConfig`: Configuration instance loaded from environment

**Environment Variables:**
- `RATE_LIMIT_REQUESTS_PER_MINUTE`: Global minute limit
- `RATE_LIMIT_REQUESTS_PER_HOUR`: Global hour limit
- `RATE_LIMIT_REQUESTS_PER_DAY`: Global day limit
- `RATE_LIMIT_MAX_BURST`: Maximum burst size
- `RATE_LIMIT_ENDPOINT_<endpoint>_<timeframe>`: Endpoint-specific limits
- `RATE_LIMIT_<platform>_<timeframe>`: Platform-specific limits

### Class: RateLimiter

Token bucket-based rate limiter with support for multiple time windows.

#### Constructor

```python
def __init__(self, config: RateLimitConfig)
```

**Parameters:**
- `config` (RateLimitConfig): Rate limiting configuration

#### Core Methods

##### is_allowed

```python
def is_allowed(self, key: str, endpoint: str = None, platform: str = None) -> Tuple[bool, Dict[str, Any]]
```

Check if a request is allowed under current rate limits.

**Parameters:**
- `key` (str): Unique identifier for the rate limit bucket (e.g., user ID, IP address)
- `endpoint` (str, optional): API endpoint being accessed
- `platform` (str, optional): Platform being accessed

**Returns:**
- `Tuple[bool, Dict[str, Any]]`: (allowed, rate_limit_info)

##### wait_time

```python
def wait_time(self, key: str, endpoint: str = None, platform: str = None) -> float
```

Get the time to wait before the next request is allowed.

**Parameters:**
- `key` (str): Unique identifier for the rate limit bucket
- `endpoint` (str, optional): API endpoint being accessed
- `platform` (str, optional): Platform being accessed

**Returns:**
- `float`: Wait time in seconds

##### reset_limits

```python
def reset_limits(self, key: str) -> None
```

Reset rate limits for a specific key.

**Parameters:**
- `key` (str): Unique identifier for the rate limit bucket

### Decorators

#### rate_limited

```python
def rate_limited(config: RateLimitConfig = None,
                key_func: Callable = None,
                endpoint: str = None,
                platform: str = None) -> Callable
```

Decorator for applying rate limiting to functions.

**Parameters:**
- `config` (RateLimitConfig, optional): Rate limiting configuration
- `key_func` (Callable, optional): Function to generate rate limit key
- `endpoint` (str, optional): API endpoint identifier
- `platform` (str, optional): Platform identifier

**Returns:**
- `Callable`: Decorated function with rate limiting

### Utility Functions

#### get_rate_limiter

```python
def get_rate_limiter(config: RateLimitConfig = None) -> RateLimiter
```

Get a singleton rate limiter instance.

**Parameters:**
- `config` (RateLimitConfig, optional): Configuration for new instance

**Returns:**
- `RateLimiter`: Rate limiter instance

#### extract_endpoint_from_url

```python
def extract_endpoint_from_url(url: str) -> str
```

Extract endpoint identifier from URL for rate limiting.

**Parameters:**
- `url` (str): URL to extract endpoint from

**Returns:**
- `str`: Endpoint identifier

#### Usage Example

```python
from rate_limiter import RateLimitConfig, get_rate_limiter, rate_limited
import asyncio

# Create configuration
config = RateLimitConfig(
    requests_per_minute=30,
    requests_per_hour=500,
    endpoint_limits={
        'media': {'minute': 10, 'hour': 100},
        'posts': {'minute': 20, 'hour': 200}
    },
    platform_limits={
        'mastodon': {'minute': 300, 'hour': 5000},
        'pixelfed': {'minute': 60, 'hour': 1000}
    }
)

# Get rate limiter
limiter = get_rate_limiter(config)

# Check if request is allowed
allowed, info = limiter.is_allowed(
    key='user_123',
    endpoint='media',
    platform='mastodon'
)

if allowed:
    print("Request allowed")
else:
    wait_time = limiter.wait_time('user_123', 'media', 'mastodon')
    print(f"Rate limited. Wait {wait_time} seconds")

# Using decorator
@rate_limited(
    config=config,
    key_func=lambda user_id: f"user_{user_id}",
    endpoint='posts',
    platform='pixelfed'
)
async def create_post(user_id: int, content: str):
    # Post creation logic
    pass

# Environment-based configuration
env_config = RateLimitConfig.from_env()
```

---

## Error Handling

All utility modules implement comprehensive error handling:

### Common Exceptions

- `PlatformContextError`: Platform context operation failures
- `RateLimitExceeded`: Rate limit violations
- `RetryExhausted`: Maximum retry attempts exceeded

### Logging

All modules use structured logging with sanitized output for security:

```python
from security.core.security_utils import sanitize_for_log

logger.info(f"Operation completed for user {sanitize_for_log(user_id)}")
```

---

## Thread Safety

All utility modules are designed to be thread-safe:

- **Platform Context**: Uses thread-local storage for context isolation
- **Progress Tracker**: Uses threading locks for concurrent access
- **Rate Limiter**: Thread-safe token bucket implementation
- **Retry Logic**: Safe for concurrent use across multiple tasks

---

This documentation provides a comprehensive reference for Vedfolnir's utility modules. For implementation details and advanced usage patterns, refer to the source code and additional documentation in the `docs/` directory.
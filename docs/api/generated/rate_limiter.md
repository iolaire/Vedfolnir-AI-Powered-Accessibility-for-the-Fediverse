# rate_limiter

Rate limiting implementation for API calls.

This module provides rate limiting functionality for API calls to prevent
hitting rate limits on external services. It implements token bucket algorithm
for rate limiting with support for different rate limits per endpoint.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/rate_limiter.py`

## Classes

### RateLimitConfig

```python
class RateLimitConfig
```

Configuration for rate limiting behavior

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls, env_prefix: str)
```

Create a RateLimitConfig from environment variables

Args:
    env_prefix: Prefix for environment variables
    
Returns:
    RateLimitConfig instance

**Decorators:**
- `@classmethod`

**Type:** Class method

### TokenBucket

```python
class TokenBucket
```

Token bucket implementation for rate limiting.

The token bucket algorithm works by having a bucket that fills with tokens at a
constant rate. When a request is made, a token is removed from the bucket.
If the bucket is empty, the request is either delayed or rejected.

**Methods:**

#### __init__

```python
def __init__(self, rate: float, capacity: int)
```

Initialize a token bucket

Args:
    rate: Rate at which tokens are added to the bucket (tokens per second)
    capacity: Maximum number of tokens the bucket can hold

**Type:** Instance method

#### _refill

```python
def _refill(self) -> None
```

Refill the bucket based on elapsed time

**Type:** Instance method

#### consume

```python
def consume(self, tokens: int) -> Tuple[bool, float]
```

Try to consume tokens from the bucket

Args:
    tokens: Number of tokens to consume
    
Returns:
    Tuple of (success, wait_time):
        - success: True if tokens were consumed, False otherwise
        - wait_time: Time to wait in seconds before tokens would be available

**Type:** Instance method

#### async_consume

```python
async def async_consume(self, tokens: int) -> bool
```

Asynchronously consume tokens, waiting if necessary

Args:
    tokens: Number of tokens to consume
    
Returns:
    True if tokens were consumed, False if it would take too long to wait

**Type:** Instance method

### RateLimiter

```python
class RateLimiter
```

Rate limiter for API calls using token bucket algorithm.

This class manages multiple token buckets for different time windows
(minute, hour, day), different endpoints, and different platforms.

**Methods:**

#### __init__

```python
def __init__(self, config: RateLimitConfig)
```

Initialize rate limiter with configuration

Args:
    config: Rate limit configuration

**Type:** Instance method

#### _get_endpoint_buckets

```python
def _get_endpoint_buckets(self, endpoint: Optional[str]) -> Dict[str, TokenBucket]
```

Get token buckets for a specific endpoint

Args:
    endpoint: Endpoint name or None for global buckets
    
Returns:
    Dictionary of token buckets for the endpoint

**Type:** Instance method

#### _get_platform_buckets

```python
def _get_platform_buckets(self, platform: Optional[str]) -> Dict[str, TokenBucket]
```

Get token buckets for a specific platform

Args:
    platform: Platform name or None for global buckets
    
Returns:
    Dictionary of token buckets for the platform

**Type:** Instance method

#### _get_platform_endpoint_buckets

```python
def _get_platform_endpoint_buckets(self, platform: Optional[str], endpoint: Optional[str]) -> Dict[str, TokenBucket]
```

Get token buckets for a specific platform-endpoint combination

Args:
    platform: Platform name
    endpoint: Endpoint name
    
Returns:
    Dictionary of token buckets for the platform-endpoint combination

**Type:** Instance method

#### _update_stats

```python
def _update_stats(self, endpoint: Optional[str], throttled: bool, wait_time: float, platform: Optional[str]) -> None
```

Update usage statistics

Args:
    endpoint: Endpoint name or None
    throttled: Whether the request was throttled
    wait_time: Time waited for rate limit
    platform: Platform name or None

**Type:** Instance method

#### check_rate_limit

```python
def check_rate_limit(self, endpoint: Optional[str], platform: Optional[str]) -> Tuple[bool, float]
```

Check if a request would exceed rate limits

Args:
    endpoint: Optional endpoint name for endpoint-specific limits
    platform: Optional platform name for platform-specific limits
    
Returns:
    Tuple of (allowed, wait_time):
        - allowed: True if request is allowed, False if it would exceed rate limits
        - wait_time: Time to wait in seconds before request would be allowed

**Type:** Instance method

#### wait_if_needed

```python
async def wait_if_needed(self, endpoint: Optional[str], platform: Optional[str]) -> float
```

Wait if necessary to comply with rate limits

Args:
    endpoint: Optional endpoint name for endpoint-specific limits
    platform: Optional platform name for platform-specific limits
    
Returns:
    Time waited in seconds (0.0 if no wait was needed)

**Type:** Instance method

#### get_stats

```python
def get_stats(self) -> Dict[str, Any]
```

Get rate limiting statistics

Returns:
    Dictionary with rate limiting statistics

**Type:** Instance method

#### reset_stats

```python
def reset_stats(self) -> None
```

Reset usage statistics

**Type:** Instance method

#### update_from_response_headers

```python
def update_from_response_headers(self, headers: Dict[str, str], platform: Optional[str]) -> None
```

Update rate limiter state based on response headers from the platform

Args:
    headers: HTTP response headers
    platform: Platform name (pixelfed, mastodon, etc.)

**Type:** Instance method

#### _update_from_mastodon_headers

```python
def _update_from_mastodon_headers(self, headers: Dict[str, str]) -> None
```

Update rate limiter from Mastodon-style headers

**Type:** Instance method

#### _update_from_pixelfed_headers

```python
def _update_from_pixelfed_headers(self, headers: Dict[str, str]) -> None
```

Update rate limiter from Pixelfed-style headers

**Type:** Instance method

#### _update_from_standard_headers

```python
def _update_from_standard_headers(self, headers: Dict[str, str]) -> None
```

Update rate limiter from standard X-RateLimit-* headers

**Type:** Instance method

## Functions

### get_rate_limiter

```python
def get_rate_limiter(config: Optional[RateLimitConfig]) -> RateLimiter
```

Get or create the global rate limiter instance

Args:
    config: Optional rate limit configuration
    
Returns:
    RateLimiter instance

### extract_endpoint_from_url

```python
def extract_endpoint_from_url(url: str) -> Optional[str]
```

Extract endpoint name from URL for rate limiting purposes

Args:
    url: URL to extract endpoint from
    
Returns:
    Endpoint name or None if not recognized

### rate_limited

```python
def rate_limited(func: Optional[Callable], endpoint: Optional[str], platform: Optional[str])
```

Decorator for rate-limiting async functions

Args:
    func: Function to decorate
    endpoint: Optional endpoint name for endpoint-specific limits
    platform: Optional platform name for platform-specific limits
    
Returns:
    Decorated function


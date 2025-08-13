# activitypub_client

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/activitypub_client.py`

## Classes

### ActivityPubClient

```python
class ActivityPubClient
```

Platform-agnostic client for interacting with ActivityPub servers via API.

This client uses platform adapters to handle platform-specific implementations
while providing a consistent interface for all ActivityPub platforms.

The client can be initialized either with a traditional config object or with
a PlatformConnection object for platform-aware operations.

**Methods:**

#### __init__

```python
def __init__(self, config, platform_connection)
```

Initialize the ActivityPub client.

Args:
    config: ActivityPubConfig object or PlatformConnection object
    platform_connection: Optional PlatformConnection for platform-aware operations

**Type:** Instance method

#### _ensure_session

```python
async def _ensure_session(self)
```

Ensure HTTP session is initialized

**Type:** Instance method

#### close

```python
def close(self)
```

Synchronous cleanup method to prevent resource leaks

**Type:** Instance method

#### _load_keys

```python
def _load_keys(self)
```

Load RSA keys for HTTP signatures if available

**Type:** Instance method

#### _apply_platform_rate_limits

```python
def _apply_platform_rate_limits(self, base_config)
```

Apply platform-specific rate limits to the base configuration

**Type:** Instance method

#### _create_error_context

```python
def _create_error_context(self, error, method: str, url: str, endpoint: str) -> dict
```

Create error context for platform-aware error handling

**Type:** Instance method

#### _handle_platform_error

```python
def _handle_platform_error(self, error: httpx.HTTPStatusError, context: dict)
```

Handle platform-specific HTTP errors

**Type:** Instance method

#### _handle_mastodon_error

```python
def _handle_mastodon_error(self, error: httpx.HTTPStatusError, context: dict)
```

Handle Mastodon-specific errors

**Type:** Instance method

#### _handle_pixelfed_error

```python
def _handle_pixelfed_error(self, error: httpx.HTTPStatusError, context: dict)
```

Handle Pixelfed-specific errors

**Type:** Instance method

#### _handle_generic_error

```python
def _handle_generic_error(self, error: httpx.HTTPStatusError, context: dict)
```

Handle generic ActivityPub platform errors

**Type:** Instance method

#### _log_platform_error

```python
def _log_platform_error(self, error: Exception, context: dict)
```

Log platform-specific non-HTTP errors

**Type:** Instance method

#### __aenter__

```python
async def __aenter__(self)
```

**Type:** Instance method

#### __aexit__

```python
async def __aexit__(self, exc_type, exc_val, exc_tb)
```

**Type:** Instance method

#### _get_with_retry

```python
async def _get_with_retry(self, url: str, headers: dict, params: dict) -> httpx.Response
```

Make a GET request with retry logic and rate limiting

**Type:** Instance method

#### _put_with_retry

```python
async def _put_with_retry(self, url: str, headers: dict, json: dict) -> httpx.Response
```

Make a PUT request with retry logic and rate limiting

**Type:** Instance method

#### _post_with_retry

```python
async def _post_with_retry(self, url: str, headers: dict, json: dict) -> httpx.Response
```

Make a POST request with retry logic and rate limiting

**Type:** Instance method

#### _delete_with_retry

```python
async def _delete_with_retry(self, url: str, headers: dict) -> httpx.Response
```

Make a DELETE request with retry logic and rate limiting

**Type:** Instance method

#### get_user_posts

```python
async def get_user_posts(self, user_id: str, limit: int) -> List[Dict[str, Any]]
```

Retrieve user's posts from ActivityPub platform using API.

Args:
    user_id: The user ID to fetch posts for
    limit: Maximum number of posts to fetch
    
Returns:
    List of posts in ActivityPub format
    
Raises:
    PlatformAdapterError: If the platform adapter fails

**Type:** Instance method

#### get_post_by_id

```python
async def get_post_by_id(self, post_id: str) -> Optional[Dict[str, Any]]
```

Retrieve a specific post by ID.

Args:
    post_id: The ID of the post to retrieve
    
Returns:
    Post data in ActivityPub format, or None if not found
    
Raises:
    PlatformAdapterError: If the platform adapter fails

**Type:** Instance method

#### update_post

```python
async def update_post(self, post_id: str, updated_post: Dict[str, Any]) -> bool
```

Update a post with new content (primarily for alt text).

Args:
    post_id: The ID of the post to update
    updated_post: The updated post data
    
Returns:
    True if successful, False otherwise
    
Raises:
    PlatformAdapterError: If the platform adapter fails

**Type:** Instance method

#### update_media_caption

```python
async def update_media_caption(self, image_post_id: str, caption: str) -> bool
```

Update a specific media attachment's caption/description.

Args:
    image_post_id: The ID of the media attachment to update
    caption: The new caption text
    
Returns:
    True if successful, False otherwise
    
Raises:
    PlatformAdapterError: If the platform adapter fails

**Type:** Instance method

#### extract_images_from_post

```python
def extract_images_from_post(self, post: Dict[str, Any]) -> List[Dict[str, Any]]
```

Extract image attachments from a post.

Args:
    post: The post data in ActivityPub format
    
Returns:
    List of image attachment dictionaries
    
Raises:
    PlatformAdapterError: If the platform adapter fails

**Type:** Instance method

#### get_platform_name

```python
def get_platform_name(self) -> str
```

Get the name of the current platform.

Returns:
    String with the platform name (e.g., 'pixelfed', 'mastodon')

**Type:** Instance method

#### get_platform_info

```python
def get_platform_info(self) -> Dict[str, Any]
```

Get information about the current platform adapter.

Returns:
    Dictionary with platform information

**Type:** Instance method

#### authenticate

```python
async def authenticate(self) -> bool
```

Authenticate with the platform if required.

Returns:
    True if authentication successful or not required, False otherwise

**Type:** Instance method

#### test_connection

```python
async def test_connection(self) -> tuple[bool, str]
```

Test the connection to the platform.

Returns:
    Tuple of (success, message)

**Type:** Instance method

#### validate_platform_connection

```python
async def validate_platform_connection(self) -> dict
```

Validate the platform connection and return detailed status.

Returns:
    Dictionary with validation results

**Type:** Instance method

#### health_check

```python
async def health_check(self) -> dict
```

Perform a comprehensive health check of the platform connection.

Returns:
    Dictionary with health check results

**Type:** Instance method

#### get_retry_stats

```python
def get_retry_stats(self) -> str
```

Get statistics about API call retries

**Type:** Instance method

#### get_detailed_retry_stats

```python
def get_detailed_retry_stats(self) -> dict
```

Get detailed statistics about API call retries in JSON format

**Type:** Instance method

#### get_platform_specific_retry_info

```python
def get_platform_specific_retry_info(self) -> dict
```

Get platform-specific retry information and statistics

**Type:** Instance method

#### get_rate_limit_stats

```python
def get_rate_limit_stats(self) -> dict
```

Get statistics about API rate limiting

**Type:** Instance method

#### reset_rate_limit_stats

```python
def reset_rate_limit_stats(self) -> None
```

Reset rate limiting statistics

**Type:** Instance method

#### get_api_usage_report

```python
def get_api_usage_report(self) -> dict
```

Get a comprehensive report of API usage including both retry and rate limit statistics

Returns:
    Dictionary with API usage statistics

**Type:** Instance method


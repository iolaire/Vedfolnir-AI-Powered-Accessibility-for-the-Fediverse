# activitypub_platforms

Platform-specific adapters for different ActivityPub implementations.
This module provides adapters for different ActivityPub platforms like Pixelfed, Mastodon, etc.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/activitypub_platforms.py`

## Classes

### PlatformAdapterError

```python
class PlatformAdapterError(Exception)
```

Base exception for platform adapter errors

### UnsupportedPlatformError

```python
class UnsupportedPlatformError(PlatformAdapterError)
```

Raised when an unsupported platform is requested

### PlatformDetectionError

```python
class PlatformDetectionError(PlatformAdapterError)
```

Raised when platform detection fails

### ActivityPubPlatform

```python
class ActivityPubPlatform(abc.ABC)
```

Base abstract class for ActivityPub platform adapters.

This class defines the common interface that all platform adapters must implement.
Each platform adapter provides platform-specific implementations for interacting
with different ActivityPub servers (Pixelfed, Mastodon, Pleroma, etc.).

**Properties:**
- `platform_name`

**Methods:**

#### __init__

```python
def __init__(self, config)
```

Initialize the platform adapter with configuration.

Args:
    config: Configuration object containing platform-specific settings

**Type:** Instance method

#### _validate_config

```python
def _validate_config(self)
```

Validate the configuration for this platform adapter.
Subclasses can override this to add platform-specific validation.

**Type:** Instance method

#### get_user_posts

```python
async def get_user_posts(self, client, user_id: str, limit: int) -> List[Dict[str, Any]]
```

Retrieve user's posts from the platform.

Args:
    client: The ActivityPubClient instance
    user_id: The user ID to fetch posts for
    limit: Maximum number of posts to fetch
    
Returns:
    List of posts in ActivityPub format
    
Raises:
    PlatformAdapterError: If the operation fails

**Decorators:**
- `@abc.abstractmethod`

**Type:** Instance method

#### update_media_caption

```python
async def update_media_caption(self, client, image_post_id: str, caption: str) -> bool
```

Update a media attachment's caption/description.

Args:
    client: The ActivityPubClient instance
    image_post_id: The ID of the media attachment to update
    caption: The new caption text
    
Returns:
    True if successful, False otherwise
    
Raises:
    PlatformAdapterError: If the operation fails

**Decorators:**
- `@abc.abstractmethod`

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

**Decorators:**
- `@abc.abstractmethod`

**Type:** Instance method

#### get_post_by_id

```python
async def get_post_by_id(self, client, post_id: str) -> Optional[Dict[str, Any]]
```

Retrieve a specific post by ID.

Args:
    client: The ActivityPubClient instance
    post_id: The ID of the post to retrieve
    
Returns:
    Post data in ActivityPub format, or None if not found
    
Raises:
    PlatformAdapterError: If the operation fails

**Decorators:**
- `@abc.abstractmethod`

**Type:** Instance method

#### update_post

```python
async def update_post(self, client, post_id: str, updated_post: Dict[str, Any]) -> bool
```

Update a post with new content.

Args:
    client: The ActivityPubClient instance
    post_id: The ID of the post to update
    updated_post: The updated post data
    
Returns:
    True if successful, False otherwise
    
Raises:
    PlatformAdapterError: If the operation fails

**Decorators:**
- `@abc.abstractmethod`

**Type:** Instance method

#### detect_platform

```python
def detect_platform(cls, instance_url: str) -> bool
```

Detect if an instance URL belongs to this platform.

Args:
    instance_url: The URL of the instance to check
    
Returns:
    True if this platform can handle the instance, False otherwise

**Decorators:**
- `@classmethod`
- `@abc.abstractmethod`

**Type:** Class method

#### get_rate_limit_info

```python
def get_rate_limit_info(self, response_headers: Dict[str, str]) -> Dict[str, Any]
```

Extract rate limit information from response headers.
Default implementation returns empty dict. Subclasses should override
to provide platform-specific rate limit parsing.

Args:
    response_headers: HTTP response headers
    
Returns:
    Dictionary containing rate limit information

**Type:** Instance method

#### cleanup

```python
async def cleanup(self)
```

Cleanup resources used by this adapter.
Subclasses can override this to perform platform-specific cleanup.

**Type:** Instance method

#### __str__

```python
def __str__(self) -> str
```

String representation of the adapter

**Type:** Instance method

#### __repr__

```python
def __repr__(self) -> str
```

Detailed string representation of the adapter

**Type:** Instance method

### PixelfedPlatform

```python
class PixelfedPlatform(ActivityPubPlatform)
```

Adapter for Pixelfed platform

**Methods:**

#### _validate_config

```python
def _validate_config(self)
```

Validate Pixelfed-specific configuration

**Type:** Instance method

#### detect_platform

```python
def detect_platform(cls, instance_url: str) -> bool
```

Detect if an instance URL is a Pixelfed instance.

Args:
    instance_url: The URL of the instance to check
    
Returns:
    True if this appears to be a Pixelfed instance, False otherwise

**Decorators:**
- `@classmethod`

**Type:** Class method

#### get_user_posts

```python
async def get_user_posts(self, client, user_id: str, limit: int) -> List[Dict[str, Any]]
```

Retrieve user's posts from Pixelfed using API with pagination support

Args:
    client: The ActivityPubClient instance
    user_id: The user ID to fetch posts for
    limit: Maximum number of posts to fetch
    
Returns:
    List of posts in ActivityPub format

**Type:** Instance method

#### update_media_caption

```python
async def update_media_caption(self, client, image_post_id: str, caption: str) -> bool
```

Update a specific media attachment's caption/description using the Pixelfed API

**Type:** Instance method

#### extract_images_from_post

```python
def extract_images_from_post(self, post: Dict[str, Any]) -> List[Dict[str, Any]]
```

Extract image attachments from a Pixelfed post

**Type:** Instance method

#### get_post_by_id

```python
async def get_post_by_id(self, client, post_id: str) -> Optional[Dict[str, Any]]
```

Retrieve a specific post by ID

**Type:** Instance method

#### update_post

```python
async def update_post(self, client, post_id: str, updated_post: Dict[str, Any]) -> bool
```

Update a Pixelfed post with new content (primarily for alt text)

**Type:** Instance method

#### get_rate_limit_info

```python
def get_rate_limit_info(self, response_headers: Dict[str, str]) -> Dict[str, Any]
```

Extract rate limit information from Pixelfed response headers.

Args:
    response_headers: HTTP response headers
    
Returns:
    Dictionary containing rate limit information

**Type:** Instance method

### MastodonPlatform

```python
class MastodonPlatform(ActivityPubPlatform)
```

Adapter for Mastodon platform

**Methods:**

#### __init__

```python
def __init__(self, config)
```

Initialize Mastodon platform adapter

**Type:** Instance method

#### _validate_config

```python
def _validate_config(self)
```

Validate Mastodon-specific configuration

**Type:** Instance method

#### authenticate

```python
async def authenticate(self, client) -> bool
```

Authenticate with the Mastodon instance using OAuth2 client credentials.

Args:
    client: The ActivityPubClient instance
    
Returns:
    True if authentication successful, False otherwise

**Type:** Instance method

#### _validate_token

```python
async def _validate_token(self, client) -> bool
```

Validate the current access token by making a test API call.

Args:
    client: The ActivityPubClient instance
    
Returns:
    True if token is valid, False otherwise

**Type:** Instance method

#### _get_auth_headers

```python
def _get_auth_headers(self) -> Dict[str, str]
```

Get authentication headers for API requests.

Returns:
    Dictionary of authentication headers
    
Raises:
    PlatformAdapterError: If not authenticated

**Type:** Instance method

#### _refresh_token_if_needed

```python
async def _refresh_token_if_needed(self, client) -> bool
```

Refresh the access token if needed (placeholder for future implementation).

Note: Mastodon access tokens typically don't expire, but this method
provides a hook for future token refresh functionality.

Args:
    client: The ActivityPubClient instance
    
Returns:
    True if token is still valid or was refreshed, False otherwise

**Type:** Instance method

#### detect_platform

```python
def detect_platform(cls, instance_url: str) -> bool
```

Detect if an instance URL is a Mastodon instance.

Args:
    instance_url: The URL of the instance to check
    
Returns:
    True if this appears to be a Mastodon instance, False otherwise

**Decorators:**
- `@classmethod`

**Type:** Class method

#### get_user_posts

```python
async def get_user_posts(self, client, user_id: str, limit: int) -> List[Dict[str, Any]]
```

Retrieve user's posts from Mastodon using API with pagination support.

Args:
    client: The ActivityPubClient instance
    user_id: The user ID or username to fetch posts for
    limit: Maximum number of posts to fetch
    
Returns:
    List of posts in ActivityPub format
    
Raises:
    PlatformAdapterError: If the operation fails

**Type:** Instance method

#### _resolve_user_to_account_id

```python
async def _resolve_user_to_account_id(self, client, user_id: str, headers: Dict[str, str]) -> Optional[str]
```

Resolve a user ID or username to a Mastodon account ID.

Args:
    client: The ActivityPubClient instance
    user_id: The user ID or username to resolve
    headers: Authentication headers
    
Returns:
    The account ID if found, None otherwise

**Type:** Instance method

#### _convert_mastodon_statuses_to_activitypub

```python
def _convert_mastodon_statuses_to_activitypub(self, statuses: List[Dict[str, Any]], user_id: str) -> List[Dict[str, Any]]
```

Convert Mastodon statuses to ActivityPub format.

Args:
    statuses: List of Mastodon status objects
    user_id: The user ID for attribution
    
Returns:
    List of posts in ActivityPub format

**Type:** Instance method

#### update_media_caption

```python
async def update_media_caption(self, client, image_post_id: str, caption: str) -> bool
```

Update a media attachment's caption using Mastodon's status edit API

**Type:** Instance method

#### update_status_media_caption

```python
async def update_status_media_caption(self, client, status_id: str, media_id: str, caption: str) -> bool
```

Update a media attachment's caption using Mastodon's status edit API

**Type:** Instance method

#### extract_images_from_post

```python
def extract_images_from_post(self, post: Dict[str, Any]) -> List[Dict[str, Any]]
```

Extract image attachments from a Mastodon post.

This method parses Mastodon media attachment JSON format, identifies images
without alt text descriptions, and extracts image URLs and metadata.

Args:
    post: Mastodon post in ActivityPub format
    
Returns:
    List of image dictionaries for images without alt text

**Type:** Instance method

#### _is_meaningful_alt_text

```python
def _is_meaningful_alt_text(self, alt_text: str) -> bool
```

Determine if alt text is meaningful (not just whitespace or emojis).

Args:
    alt_text: The alt text to check
    
Returns:
    True if the alt text is meaningful, False otherwise

**Type:** Instance method

#### get_post_by_id

```python
async def get_post_by_id(self, client, post_id: str) -> Optional[Dict[str, Any]]
```

Retrieve a specific post by ID

**Type:** Instance method

#### update_post

```python
async def update_post(self, client, post_id: str, updated_post: Dict[str, Any]) -> bool
```

Update a Mastodon post using the status edit API

**Type:** Instance method

#### get_rate_limit_info

```python
def get_rate_limit_info(self, response_headers: Dict[str, str]) -> Dict[str, Any]
```

Extract rate limit information from Mastodon response headers.

Args:
    response_headers: HTTP response headers
    
Returns:
    Dictionary containing rate limit information

**Type:** Instance method

#### get_rate_limit_info

```python
def get_rate_limit_info(self, response_headers: Dict[str, str]) -> Dict[str, Any]
```

Extract rate limit information from Mastodon response headers.

Args:
    response_headers: HTTP response headers
    
Returns:
    Dictionary containing rate limit information

**Type:** Instance method

### PleromaPlatform

```python
class PleromaPlatform(ActivityPubPlatform)
```

Adapter for Pleroma platform

**Methods:**

#### detect_platform

```python
def detect_platform(cls, instance_url: str) -> bool
```

Detect if an instance URL is a Pleroma instance

**Decorators:**
- `@classmethod`

**Type:** Class method

#### get_user_posts

```python
async def get_user_posts(self, client, user_id: str, limit: int) -> List[Dict[str, Any]]
```

Retrieve user's posts from Pleroma using API

**Type:** Instance method

#### update_media_caption

```python
async def update_media_caption(self, client, image_post_id: str, caption: str) -> bool
```

Update a specific media attachment's caption/description using the Pleroma API

**Type:** Instance method

#### extract_images_from_post

```python
def extract_images_from_post(self, post: Dict[str, Any]) -> List[Dict[str, Any]]
```

Extract image attachments from a Pleroma post

**Type:** Instance method

#### get_post_by_id

```python
async def get_post_by_id(self, client, post_id: str) -> Optional[Dict[str, Any]]
```

Retrieve a specific post by ID

**Type:** Instance method

#### update_post

```python
async def update_post(self, client, post_id: str, updated_post: Dict[str, Any]) -> bool
```

Update a Pleroma post with new content (primarily for alt text)

**Type:** Instance method

### PlatformAdapterFactory

```python
class PlatformAdapterFactory
```

Factory class for creating platform adapters

**Class Variables:**
- `_adapters`

**Methods:**

#### create_adapter

```python
def create_adapter(cls, config) -> ActivityPubPlatform
```

Create the appropriate platform adapter based on configuration or automatic detection.

Args:
    config: Configuration object or PlatformConnection containing platform settings
    
Returns:
    Platform adapter instance
    
Raises:
    UnsupportedPlatformError: If the platform type is not supported
    PlatformDetectionError: If platform detection fails
    PlatformAdapterError: If adapter creation fails

**Decorators:**
- `@classmethod`

**Type:** Class method

#### get_supported_platforms

```python
def get_supported_platforms(cls) -> List[str]
```

Get list of supported platform types.

Returns:
    List of supported platform names

**Decorators:**
- `@classmethod`

**Type:** Class method

#### create_adapter_from_platform_connection

```python
def create_adapter_from_platform_connection(cls, platform_connection) -> ActivityPubPlatform
```

Create a platform adapter from a PlatformConnection object.

Args:
    platform_connection: PlatformConnection model instance
    
Returns:
    Platform adapter instance
    
Raises:
    UnsupportedPlatformError: If the platform type is not supported
    PlatformAdapterError: If adapter creation fails

**Decorators:**
- `@classmethod`

**Type:** Class method

#### validate_platform_connection

```python
def validate_platform_connection(cls, platform_connection) -> dict
```

Validate a platform connection by creating and testing an adapter.

Args:
    platform_connection: PlatformConnection model instance
    
Returns:
    Dictionary with validation results

**Decorators:**
- `@classmethod`

**Type:** Class method

#### register_adapter

```python
def register_adapter(cls, platform_name: str, adapter_class: type)
```

Register a new platform adapter.

Args:
    platform_name: Name of the platform
    adapter_class: Platform adapter class
    
Raises:
    ValueError: If the adapter class doesn't inherit from ActivityPubPlatform

**Decorators:**
- `@classmethod`

**Type:** Class method

## Functions

### get_platform_adapter

```python
def get_platform_adapter(config) -> ActivityPubPlatform
```

Factory function to get the appropriate platform adapter based on configuration
or automatic detection.

This function is maintained for backward compatibility.
New code should use PlatformAdapterFactory.create_adapter() instead.

Args:
    config: Configuration object containing platform settings
    
Returns:
    Platform adapter instance

### detect_platform_type

```python
async def detect_platform_type(instance_url: str) -> str
```

Detect the platform type from an instance URL by checking nodeinfo endpoint

Returns:
    String with platform type: 'pixelfed', 'mastodon', 'pleroma', or 'unknown'


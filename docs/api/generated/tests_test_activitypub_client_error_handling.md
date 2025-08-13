# tests.test_activitypub_client_error_handling

Tests for ActivityPub client error handling and retry logic.

This module tests error propagation, retry mechanisms, and platform-specific
error handling scenarios for both Pixelfed and Mastodon platforms.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_activitypub_client_error_handling.py`

## Classes

### MockConfig

```python
class MockConfig
```

Mock configuration for testing

**Decorators:**
- `@dataclass`

**Methods:**

#### __post_init__

```python
def __post_init__(self)
```

**Type:** Instance method

### TestActivityPubClientErrorHandling

```python
class TestActivityPubClientErrorHandling(unittest.TestCase)
```

Test error handling in ActivityPub client

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### mock_pixelfed_client

```python
def mock_pixelfed_client(self)
```

Create a mock client with Pixelfed adapter

**Type:** Instance method

#### mock_mastodon_client

```python
def mock_mastodon_client(self)
```

Create a mock client with Mastodon adapter

**Type:** Instance method

#### test_get_user_posts_http_error

```python
async def test_get_user_posts_http_error(self)
```

Test get_user_posts with HTTP error

**Type:** Instance method

#### test_get_user_posts_timeout_error

```python
async def test_get_user_posts_timeout_error(self)
```

Test get_user_posts with timeout error

**Type:** Instance method

#### test_get_user_posts_connection_error

```python
async def test_get_user_posts_connection_error(self)
```

Test get_user_posts with connection error

**Type:** Instance method

#### test_update_media_caption_platform_error_propagation

```python
async def test_update_media_caption_platform_error_propagation(self)
```

Test that platform adapter errors are properly propagated

**Type:** Instance method

#### test_update_media_caption_authentication_error

```python
async def test_update_media_caption_authentication_error(self)
```

Test update_media_caption with authentication error

**Type:** Instance method

#### test_get_post_by_id_rate_limit_error

```python
async def test_get_post_by_id_rate_limit_error(self)
```

Test get_post_by_id with rate limit error

**Type:** Instance method

#### test_update_post_server_error

```python
async def test_update_post_server_error(self)
```

Test update_post with server error

**Type:** Instance method

#### test_extract_images_from_post_json_decode_error

```python
def test_extract_images_from_post_json_decode_error(self, mock_pixelfed_client)
```

Test extract_images_from_post with JSON decode error

**Type:** Instance method

#### test_extract_images_from_post_key_error

```python
def test_extract_images_from_post_key_error(self, mock_mastodon_client)
```

Test extract_images_from_post with key error

**Type:** Instance method

### TestActivityPubClientRetryLogic

```python
class TestActivityPubClientRetryLogic(unittest.TestCase)
```

Test retry logic for different platforms

**Methods:**

#### mock_client_with_retry

```python
def mock_client_with_retry(self)
```

Create a mock client with retry configuration

**Type:** Instance method

#### test_retry_on_temporary_failure

```python
async def test_retry_on_temporary_failure(self)
```

Test retry logic on temporary failures

**Type:** Instance method

#### test_retry_exhaustion

```python
async def test_retry_exhaustion(self)
```

Test behavior when retry attempts are exhausted

**Type:** Instance method

#### test_no_retry_on_client_error

```python
async def test_no_retry_on_client_error(self)
```

Test that client errors (4xx) are not retried

**Type:** Instance method

#### test_retry_on_server_error

```python
async def test_retry_on_server_error(self)
```

Test that server errors (5xx) are retried

**Type:** Instance method

### TestActivityPubClientPlatformSpecificErrors

```python
class TestActivityPubClientPlatformSpecificErrors(unittest.TestCase)
```

Test platform-specific error scenarios

**Methods:**

#### test_pixelfed_specific_error_handling

```python
async def test_pixelfed_specific_error_handling(self)
```

Test Pixelfed-specific error handling

**Type:** Instance method

#### test_mastodon_authentication_error_handling

```python
async def test_mastodon_authentication_error_handling(self)
```

Test Mastodon authentication error handling

**Type:** Instance method

#### test_mastodon_oauth_token_expired

```python
async def test_mastodon_oauth_token_expired(self)
```

Test handling of expired OAuth tokens in Mastodon

**Type:** Instance method

#### test_pixelfed_media_not_found_error

```python
async def test_pixelfed_media_not_found_error(self)
```

Test handling of media not found errors in Pixelfed

**Type:** Instance method

### TestActivityPubClientConcurrentErrors

```python
class TestActivityPubClientConcurrentErrors(unittest.TestCase)
```

Test error handling in concurrent scenarios

**Methods:**

#### test_concurrent_requests_with_mixed_results

```python
async def test_concurrent_requests_with_mixed_results(self)
```

Test concurrent requests where some succeed and some fail

**Type:** Instance method

#### _expect_error

```python
async def _expect_error(self, client, media_id, caption)
```

Helper method to expect an error

**Type:** Instance method


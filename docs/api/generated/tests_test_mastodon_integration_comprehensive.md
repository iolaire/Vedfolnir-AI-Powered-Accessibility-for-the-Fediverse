# tests.test_mastodon_integration_comprehensive

Comprehensive integration tests for Mastodon support.

This module tests the complete workflow with Mastodon configuration,
mocks Mastodon API endpoints, and tests error handling for Mastodon-specific scenarios.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_mastodon_integration_comprehensive.py`

## Classes

### MockMastodonConfig

```python
class MockMastodonConfig
```

Mock Mastodon configuration for testing

**Decorators:**
- `@dataclass`

### TestMastodonAPIEndpointMocking

```python
class TestMastodonAPIEndpointMocking(unittest.TestCase)
```

Test mocking of Mastodon API endpoints

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_mock_mastodon_verify_credentials_endpoint

```python
async def test_mock_mastodon_verify_credentials_endpoint(self)
```

Test mocking of Mastodon verify_credentials endpoint

**Type:** Instance method

#### test_mock_mastodon_account_lookup_endpoint

```python
async def test_mock_mastodon_account_lookup_endpoint(self)
```

Test mocking of Mastodon account lookup endpoint

**Type:** Instance method

#### test_mock_mastodon_statuses_endpoint

```python
async def test_mock_mastodon_statuses_endpoint(self)
```

Test mocking of Mastodon statuses endpoint

**Type:** Instance method

#### test_mock_mastodon_media_update_endpoint

```python
async def test_mock_mastodon_media_update_endpoint(self)
```

Test mocking of Mastodon media update endpoint

**Type:** Instance method

### TestMastodonWorkflowIntegration

```python
class TestMastodonWorkflowIntegration(unittest.TestCase)
```

Test complete workflow with Mastodon configuration

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_mastodon_platform_adapter_creation

```python
def test_mastodon_platform_adapter_creation(self)
```

Test that PlatformAdapterFactory creates Mastodon adapter correctly

**Type:** Instance method

#### test_mastodon_activitypub_client_integration

```python
async def test_mastodon_activitypub_client_integration(self)
```

Test ActivityPubClient integration with Mastodon platform

**Type:** Instance method

#### test_mastodon_end_to_end_workflow_mock

```python
async def test_mastodon_end_to_end_workflow_mock(self)
```

Test end-to-end workflow with mocked Mastodon responses

**Type:** Instance method

### TestMastodonErrorHandling

```python
class TestMastodonErrorHandling(unittest.TestCase)
```

Test error handling for Mastodon-specific scenarios

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_mastodon_authentication_401_error

```python
async def test_mastodon_authentication_401_error(self)
```

Test handling of 401 Unauthorized error during authentication

**Type:** Instance method

#### test_mastodon_authentication_403_error

```python
async def test_mastodon_authentication_403_error(self)
```

Test handling of 403 Forbidden error during authentication

**Type:** Instance method

#### test_mastodon_authentication_network_error

```python
async def test_mastodon_authentication_network_error(self)
```

Test handling of network errors during authentication

**Type:** Instance method

#### test_mastodon_authentication_timeout_error

```python
async def test_mastodon_authentication_timeout_error(self)
```

Test handling of timeout errors during authentication

**Type:** Instance method

#### test_mastodon_get_user_posts_user_not_found

```python
async def test_mastodon_get_user_posts_user_not_found(self)
```

Test handling of user not found error when getting posts

**Type:** Instance method

#### test_mastodon_get_user_posts_api_error

```python
async def test_mastodon_get_user_posts_api_error(self)
```

Test handling of API errors when getting user posts

**Type:** Instance method

#### test_mastodon_update_media_caption_authentication_failure

```python
async def test_mastodon_update_media_caption_authentication_failure(self)
```

Test handling of authentication failure during media update

**Type:** Instance method

#### test_mastodon_update_media_caption_404_error

```python
async def test_mastodon_update_media_caption_404_error(self)
```

Test handling of 404 error when updating non-existent media

**Type:** Instance method

#### test_mastodon_update_media_caption_rate_limit_error

```python
async def test_mastodon_update_media_caption_rate_limit_error(self)
```

Test handling of rate limit error during media update

**Type:** Instance method

#### test_mastodon_extract_images_malformed_post

```python
def test_mastodon_extract_images_malformed_post(self)
```

Test handling of malformed post data when extracting images

**Type:** Instance method

#### test_mastodon_extract_images_non_image_media

```python
def test_mastodon_extract_images_non_image_media(self)
```

Test handling of non-image media when extracting images

**Type:** Instance method

#### test_mastodon_pagination_error_handling

```python
async def test_mastodon_pagination_error_handling(self)
```

Test error handling during pagination of user posts

**Type:** Instance method

### TestMastodonAPIEndpointMockingSync

```python
class TestMastodonAPIEndpointMockingSync(TestMastodonAPIEndpointMocking)
```

Synchronous wrapper for async Mastodon API endpoint tests

**Methods:**

#### test_mock_mastodon_verify_credentials_endpoint_sync

```python
def test_mock_mastodon_verify_credentials_endpoint_sync(self)
```

**Type:** Instance method

#### test_mock_mastodon_account_lookup_endpoint_sync

```python
def test_mock_mastodon_account_lookup_endpoint_sync(self)
```

**Type:** Instance method

#### test_mock_mastodon_statuses_endpoint_sync

```python
def test_mock_mastodon_statuses_endpoint_sync(self)
```

**Type:** Instance method

#### test_mock_mastodon_media_update_endpoint_sync

```python
def test_mock_mastodon_media_update_endpoint_sync(self)
```

**Type:** Instance method

### TestMastodonWorkflowIntegrationSync

```python
class TestMastodonWorkflowIntegrationSync(TestMastodonWorkflowIntegration)
```

Synchronous wrapper for async Mastodon workflow tests

**Methods:**

#### test_mastodon_activitypub_client_integration_sync

```python
def test_mastodon_activitypub_client_integration_sync(self)
```

**Type:** Instance method

#### test_mastodon_end_to_end_workflow_mock_sync

```python
def test_mastodon_end_to_end_workflow_mock_sync(self)
```

**Type:** Instance method

### TestMastodonErrorHandlingSync

```python
class TestMastodonErrorHandlingSync(TestMastodonErrorHandling)
```

Synchronous wrapper for async Mastodon error handling tests

**Methods:**

#### test_mastodon_authentication_401_error_sync

```python
def test_mastodon_authentication_401_error_sync(self)
```

**Type:** Instance method

#### test_mastodon_authentication_403_error_sync

```python
def test_mastodon_authentication_403_error_sync(self)
```

**Type:** Instance method

#### test_mastodon_authentication_network_error_sync

```python
def test_mastodon_authentication_network_error_sync(self)
```

**Type:** Instance method

#### test_mastodon_authentication_timeout_error_sync

```python
def test_mastodon_authentication_timeout_error_sync(self)
```

**Type:** Instance method

#### test_mastodon_get_user_posts_user_not_found_sync

```python
def test_mastodon_get_user_posts_user_not_found_sync(self)
```

**Type:** Instance method

#### test_mastodon_get_user_posts_api_error_sync

```python
def test_mastodon_get_user_posts_api_error_sync(self)
```

**Type:** Instance method

#### test_mastodon_update_media_caption_authentication_failure_sync

```python
def test_mastodon_update_media_caption_authentication_failure_sync(self)
```

**Type:** Instance method

#### test_mastodon_update_media_caption_404_error_sync

```python
def test_mastodon_update_media_caption_404_error_sync(self)
```

**Type:** Instance method

#### test_mastodon_update_media_caption_rate_limit_error_sync

```python
def test_mastodon_update_media_caption_rate_limit_error_sync(self)
```

**Type:** Instance method

#### test_mastodon_pagination_error_handling_sync

```python
def test_mastodon_pagination_error_handling_sync(self)
```

**Type:** Instance method

## Functions

### run_async_test

```python
def run_async_test(coro)
```

Helper function to run async tests


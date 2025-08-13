# tests.test_platform_adapters_comprehensive

Comprehensive unit tests for platform adapters.

This module tests the PixelfedPlatform and MastodonPlatform adapters to ensure
they maintain existing functionality and handle platform-specific API calls correctly.
Also tests platform detection and adapter factory functionality.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_platform_adapters_comprehensive.py`

## Classes

### MockConfig

```python
class MockConfig
```

Mock configuration for testing

**Decorators:**
- `@dataclass`

### TestPixelfedPlatformAdapter

```python
class TestPixelfedPlatformAdapter(unittest.TestCase)
```

Test PixelfedPlatform adapter maintains existing functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_pixelfed_platform_initialization

```python
def test_pixelfed_platform_initialization(self)
```

Test PixelfedPlatform initializes correctly

**Type:** Instance method

#### test_pixelfed_config_validation_success

```python
def test_pixelfed_config_validation_success(self)
```

Test successful Pixelfed configuration validation

**Type:** Instance method

#### test_pixelfed_config_validation_missing_instance_url

```python
def test_pixelfed_config_validation_missing_instance_url(self)
```

Test Pixelfed configuration validation with missing instance URL

**Type:** Instance method

#### test_pixelfed_config_validation_missing_access_token

```python
def test_pixelfed_config_validation_missing_access_token(self)
```

Test Pixelfed configuration validation with missing access token

**Type:** Instance method

#### test_pixelfed_get_user_posts_success

```python
async def test_pixelfed_get_user_posts_success(self)
```

Test successful retrieval of Pixelfed user posts

**Type:** Instance method

#### test_pixelfed_get_user_posts_pagination

```python
async def test_pixelfed_get_user_posts_pagination(self)
```

Test Pixelfed user posts retrieval with pagination

**Type:** Instance method

#### test_pixelfed_update_media_caption_success

```python
async def test_pixelfed_update_media_caption_success(self)
```

Test successful Pixelfed media caption update

**Type:** Instance method

#### test_pixelfed_update_media_caption_failure

```python
async def test_pixelfed_update_media_caption_failure(self)
```

Test Pixelfed media caption update failure

**Type:** Instance method

#### test_pixelfed_extract_images_from_post

```python
def test_pixelfed_extract_images_from_post(self)
```

Test extracting images from Pixelfed post

**Type:** Instance method

#### test_pixelfed_extract_images_no_media

```python
def test_pixelfed_extract_images_no_media(self)
```

Test extracting images from post with no media

**Type:** Instance method

#### test_pixelfed_get_rate_limit_info

```python
def test_pixelfed_get_rate_limit_info(self)
```

Test extracting rate limit info from Pixelfed response headers

**Type:** Instance method

#### test_pixelfed_get_rate_limit_info_missing_headers

```python
def test_pixelfed_get_rate_limit_info_missing_headers(self)
```

Test rate limit info extraction with missing headers

**Type:** Instance method

### TestMastodonPlatformAdapter

```python
class TestMastodonPlatformAdapter(unittest.TestCase)
```

Test MastodonPlatform adapter handles Mastodon API correctly

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_mastodon_platform_initialization

```python
def test_mastodon_platform_initialization(self)
```

Test MastodonPlatform initializes correctly

**Type:** Instance method

#### test_mastodon_config_validation_success

```python
def test_mastodon_config_validation_success(self)
```

Test successful Mastodon configuration validation

**Type:** Instance method

#### test_mastodon_config_validation_missing_client_key

```python
def test_mastodon_config_validation_missing_client_key(self)
```

Test Mastodon configuration validation with missing client key

**Type:** Instance method

#### test_mastodon_config_validation_missing_client_secret

```python
def test_mastodon_config_validation_missing_client_secret(self)
```

Test Mastodon configuration validation with missing client secret

**Type:** Instance method

#### test_mastodon_authenticate_success

```python
async def test_mastodon_authenticate_success(self)
```

Test successful Mastodon authentication

**Type:** Instance method

#### test_mastodon_authenticate_invalid_token

```python
async def test_mastodon_authenticate_invalid_token(self)
```

Test Mastodon authentication with invalid token

**Type:** Instance method

#### test_mastodon_get_user_posts_success

```python
async def test_mastodon_get_user_posts_success(self)
```

Test successful retrieval of Mastodon user posts

**Type:** Instance method

#### test_mastodon_update_media_caption_success

```python
async def test_mastodon_update_media_caption_success(self)
```

Test successful Mastodon media caption update

**Type:** Instance method

#### test_mastodon_extract_images_from_post

```python
def test_mastodon_extract_images_from_post(self)
```

Test extracting images from Mastodon post

**Type:** Instance method

### TestPlatformDetectionAndFactory

```python
class TestPlatformDetectionAndFactory(unittest.TestCase)
```

Test platform detection and adapter factory

**Methods:**

#### test_pixelfed_platform_detection_known_instances

```python
def test_pixelfed_platform_detection_known_instances(self)
```

Test Pixelfed platform detection with known instances

**Type:** Instance method

#### test_pixelfed_platform_detection_pixelfed_in_domain

```python
def test_pixelfed_platform_detection_pixelfed_in_domain(self)
```

Test Pixelfed platform detection with 'pixelfed' in domain

**Type:** Instance method

#### test_pixelfed_platform_detection_false_cases

```python
def test_pixelfed_platform_detection_false_cases(self)
```

Test Pixelfed platform detection returns False for non-Pixelfed instances

**Type:** Instance method

#### test_mastodon_platform_detection_known_instances

```python
def test_mastodon_platform_detection_known_instances(self)
```

Test Mastodon platform detection with known instances

**Type:** Instance method

#### test_mastodon_platform_detection_mastodon_in_domain

```python
def test_mastodon_platform_detection_mastodon_in_domain(self)
```

Test Mastodon platform detection with 'mastodon' or 'mstdn' in domain

**Type:** Instance method

#### test_mastodon_platform_detection_false_cases

```python
def test_mastodon_platform_detection_false_cases(self)
```

Test Mastodon platform detection returns False for non-Mastodon instances

**Type:** Instance method

#### test_platform_adapter_factory_create_pixelfed

```python
def test_platform_adapter_factory_create_pixelfed(self)
```

Test PlatformAdapterFactory creates Pixelfed adapter correctly

**Type:** Instance method

#### test_platform_adapter_factory_create_mastodon

```python
def test_platform_adapter_factory_create_mastodon(self)
```

Test PlatformAdapterFactory creates Mastodon adapter correctly

**Type:** Instance method

#### test_platform_adapter_factory_unsupported_platform

```python
def test_platform_adapter_factory_unsupported_platform(self)
```

Test PlatformAdapterFactory raises error for unsupported platform

**Type:** Instance method

#### test_platform_adapter_factory_auto_detection_pixelfed

```python
def test_platform_adapter_factory_auto_detection_pixelfed(self)
```

Test PlatformAdapterFactory auto-detects Pixelfed platform

**Type:** Instance method

#### test_platform_adapter_factory_auto_detection_mastodon

```python
def test_platform_adapter_factory_auto_detection_mastodon(self)
```

Test PlatformAdapterFactory auto-detects Mastodon platform

**Type:** Instance method

#### test_platform_adapter_factory_detection_failure

```python
def test_platform_adapter_factory_detection_failure(self)
```

Test PlatformAdapterFactory defaults to Pixelfed when detection fails

**Type:** Instance method

### TestPixelfedPlatformAdapterSync

```python
class TestPixelfedPlatformAdapterSync(TestPixelfedPlatformAdapter)
```

Synchronous wrapper for async Pixelfed tests

**Methods:**

#### test_pixelfed_get_user_posts_success_sync

```python
def test_pixelfed_get_user_posts_success_sync(self)
```

**Type:** Instance method

#### test_pixelfed_get_user_posts_pagination_sync

```python
def test_pixelfed_get_user_posts_pagination_sync(self)
```

**Type:** Instance method

#### test_pixelfed_update_media_caption_success_sync

```python
def test_pixelfed_update_media_caption_success_sync(self)
```

**Type:** Instance method

#### test_pixelfed_update_media_caption_failure_sync

```python
def test_pixelfed_update_media_caption_failure_sync(self)
```

**Type:** Instance method

### TestMastodonPlatformAdapterSync

```python
class TestMastodonPlatformAdapterSync(TestMastodonPlatformAdapter)
```

Synchronous wrapper for async Mastodon tests

**Methods:**

#### test_mastodon_authenticate_success_sync

```python
def test_mastodon_authenticate_success_sync(self)
```

**Type:** Instance method

#### test_mastodon_authenticate_invalid_token_sync

```python
def test_mastodon_authenticate_invalid_token_sync(self)
```

**Type:** Instance method

#### test_mastodon_get_user_posts_success_sync

```python
def test_mastodon_get_user_posts_success_sync(self)
```

**Type:** Instance method

#### test_mastodon_update_media_caption_success_sync

```python
def test_mastodon_update_media_caption_success_sync(self)
```

**Type:** Instance method

## Functions

### run_async_test

```python
def run_async_test(coro)
```

Helper function to run async tests


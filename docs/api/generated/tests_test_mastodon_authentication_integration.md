# tests.test_mastodon_authentication_integration

Integration tests for Mastodon authentication with ActivityPubClient.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_mastodon_authentication_integration.py`

## Classes

### TestMastodonAuthenticationIntegration

```python
class TestMastodonAuthenticationIntegration(unittest.TestCase)
```

Integration tests for Mastodon authentication

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_mastodon_platform_authentication_integration

```python
async def test_mastodon_platform_authentication_integration(self, mock_get_adapter)
```

Test that MastodonPlatform authentication integrates properly with ActivityPubClient

**Decorators:**
- `@patch('activitypub_platforms.get_platform_adapter')`

**Type:** Instance method

#### test_mastodon_get_user_posts_with_authentication

```python
async def test_mastodon_get_user_posts_with_authentication(self, mock_get_adapter)
```

Test that get_user_posts properly authenticates before making requests

**Decorators:**
- `@patch('activitypub_platforms.get_platform_adapter')`

**Type:** Instance method

#### test_mastodon_update_media_caption_with_authentication

```python
async def test_mastodon_update_media_caption_with_authentication(self, mock_get_adapter)
```

Test that update_media_caption properly authenticates before making requests

**Decorators:**
- `@patch('activitypub_platforms.get_platform_adapter')`

**Type:** Instance method

### TestMastodonAuthenticationIntegrationSync

```python
class TestMastodonAuthenticationIntegrationSync(TestMastodonAuthenticationIntegration)
```

Synchronous wrapper for async integration tests

**Methods:**

#### test_mastodon_platform_authentication_integration_sync

```python
def test_mastodon_platform_authentication_integration_sync(self)
```

**Type:** Instance method

#### test_mastodon_get_user_posts_with_authentication_sync

```python
def test_mastodon_get_user_posts_with_authentication_sync(self)
```

**Type:** Instance method

#### test_mastodon_update_media_caption_with_authentication_sync

```python
def test_mastodon_update_media_caption_with_authentication_sync(self)
```

**Type:** Instance method

## Functions

### run_async_test

```python
def run_async_test(coro)
```

Helper function to run async tests


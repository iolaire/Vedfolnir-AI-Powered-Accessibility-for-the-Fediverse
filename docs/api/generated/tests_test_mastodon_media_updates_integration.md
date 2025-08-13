# tests.test_mastodon_media_updates_integration

Integration tests for Mastodon media updates with mock server responses.
Tests the complete workflow with realistic Mastodon API responses.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_mastodon_media_updates_integration.py`

## Classes

### TestMastodonMediaUpdatesIntegration

```python
class TestMastodonMediaUpdatesIntegration(unittest.TestCase)
```

Integration tests for Mastodon media updates with mock server responses

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### _create_mock_mastodon_media_response

```python
def _create_mock_mastodon_media_response(self, media_id: str, description: str, media_type: str) -> dict
```

Create a realistic Mastodon media response

**Type:** Instance method

#### _create_mock_verify_credentials_response

```python
def _create_mock_verify_credentials_response(self) -> dict
```

Create a realistic Mastodon verify_credentials response

**Type:** Instance method

#### test_complete_media_update_workflow

```python
async def test_complete_media_update_workflow(self)
```

Test complete media update workflow with realistic responses

**Type:** Instance method

#### test_media_update_with_rate_limiting

```python
async def test_media_update_with_rate_limiting(self)
```

Test media update with rate limiting headers

**Type:** Instance method

#### test_media_update_with_mastodon_error_responses

```python
async def test_media_update_with_mastodon_error_responses(self)
```

Test media update with various Mastodon error responses

**Type:** Instance method

#### test_media_update_with_long_description

```python
async def test_media_update_with_long_description(self)
```

Test media update with very long description (testing Mastodon limits)

**Type:** Instance method

#### test_media_update_with_special_content_types

```python
async def test_media_update_with_special_content_types(self)
```

Test media update with different content types and special characters

**Type:** Instance method

#### test_media_update_authentication_flow

```python
async def test_media_update_authentication_flow(self)
```

Test the complete authentication flow during media updates

**Type:** Instance method

#### test_media_update_with_network_issues

```python
async def test_media_update_with_network_issues(self)
```

Test media update handling of various network issues

**Type:** Instance method

### TestMastodonMediaUpdatesIntegrationSync

```python
class TestMastodonMediaUpdatesIntegrationSync(TestMastodonMediaUpdatesIntegration)
```

Synchronous wrapper for async integration tests

**Methods:**

#### test_complete_media_update_workflow_sync

```python
def test_complete_media_update_workflow_sync(self)
```

**Type:** Instance method

#### test_media_update_with_rate_limiting_sync

```python
def test_media_update_with_rate_limiting_sync(self)
```

**Type:** Instance method

#### test_media_update_with_mastodon_error_responses_sync

```python
def test_media_update_with_mastodon_error_responses_sync(self)
```

**Type:** Instance method

#### test_media_update_with_long_description_sync

```python
def test_media_update_with_long_description_sync(self)
```

**Type:** Instance method

#### test_media_update_with_special_content_types_sync

```python
def test_media_update_with_special_content_types_sync(self)
```

**Type:** Instance method

#### test_media_update_authentication_flow_sync

```python
def test_media_update_authentication_flow_sync(self)
```

**Type:** Instance method

#### test_media_update_with_network_issues_sync

```python
def test_media_update_with_network_issues_sync(self)
```

**Type:** Instance method

## Functions

### run_async_test

```python
def run_async_test(coro)
```

Helper function to run async tests


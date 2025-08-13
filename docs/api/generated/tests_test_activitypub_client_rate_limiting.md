# tests.test_activitypub_client_rate_limiting

Integration tests for ActivityPub client with multi-platform rate limiting.

This module tests the integration between the ActivityPub client and the
enhanced rate limiting system for both Pixelfed and Mastodon platforms.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_activitypub_client_rate_limiting.py`

## Classes

### TestActivityPubClientRateLimiting

```python
class TestActivityPubClientRateLimiting(unittest.TestCase)
```

Test ActivityPub client integration with multi-platform rate limiting

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_pixelfed_client_rate_limiting_initialization

```python
def test_pixelfed_client_rate_limiting_initialization(self)
```

Test that Pixelfed client initializes rate limiting correctly

**Type:** Instance method

#### test_mastodon_client_rate_limiting_initialization

```python
def test_mastodon_client_rate_limiting_initialization(self)
```

Test that Mastodon client initializes rate limiting correctly

**Type:** Instance method

#### test_rate_limited_decorator_with_platform_info

```python
def test_rate_limited_decorator_with_platform_info(self)
```

Test that rate_limited decorator receives platform information

**Type:** Instance method

#### test_rate_limit_stats_tracking_by_platform

```python
def test_rate_limit_stats_tracking_by_platform(self)
```

Test that rate limit statistics are tracked by platform

**Type:** Instance method

#### test_response_header_processing

```python
def test_response_header_processing(self)
```

Test that response headers are processed for rate limit info

**Type:** Instance method

#### test_platform_specific_endpoint_rate_limiting

```python
def test_platform_specific_endpoint_rate_limiting(self)
```

Test platform-specific endpoint rate limiting

**Type:** Instance method

#### test_api_usage_report_includes_platform_stats

```python
def test_api_usage_report_includes_platform_stats(self)
```

Test that API usage report includes platform-specific statistics

**Type:** Instance method

#### test_backward_compatibility_without_platform_info

```python
def test_backward_compatibility_without_platform_info(self)
```

Test that rate limiting still works without platform information

**Type:** Instance method


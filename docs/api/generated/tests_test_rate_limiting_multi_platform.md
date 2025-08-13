# tests.test_rate_limiting_multi_platform

Tests for multi-platform rate limiting functionality.

This module tests the enhanced rate limiting system that supports
platform-specific rate limits for both Pixelfed and Mastodon.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_rate_limiting_multi_platform.py`

## Classes

### TestRateLimitConfig

```python
class TestRateLimitConfig(unittest.TestCase)
```

Test RateLimitConfig with multi-platform support

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_default_configuration

```python
def test_default_configuration(self)
```

Test default rate limit configuration

**Type:** Instance method

#### test_global_rate_limit_configuration

```python
def test_global_rate_limit_configuration(self)
```

Test global rate limit configuration from environment

**Type:** Instance method

#### test_endpoint_specific_configuration

```python
def test_endpoint_specific_configuration(self)
```

Test endpoint-specific rate limit configuration

**Type:** Instance method

#### test_platform_specific_configuration

```python
def test_platform_specific_configuration(self)
```

Test platform-specific rate limit configuration

**Type:** Instance method

#### test_platform_endpoint_specific_configuration

```python
def test_platform_endpoint_specific_configuration(self)
```

Test platform-endpoint-specific rate limit configuration

**Type:** Instance method

#### test_invalid_configuration_values

```python
def test_invalid_configuration_values(self)
```

Test handling of invalid configuration values

**Type:** Instance method

### TestRateLimiter

```python
class TestRateLimiter(unittest.TestCase)
```

Test RateLimiter with multi-platform support

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_initialization

```python
def test_initialization(self)
```

Test rate limiter initialization with multi-platform config

**Type:** Instance method

#### test_check_rate_limit_global

```python
def test_check_rate_limit_global(self)
```

Test global rate limit checking

**Type:** Instance method

#### test_check_rate_limit_endpoint_specific

```python
def test_check_rate_limit_endpoint_specific(self)
```

Test endpoint-specific rate limit checking

**Type:** Instance method

#### test_check_rate_limit_platform_specific

```python
def test_check_rate_limit_platform_specific(self)
```

Test platform-specific rate limit checking

**Type:** Instance method

#### test_check_rate_limit_platform_endpoint_specific

```python
def test_check_rate_limit_platform_endpoint_specific(self)
```

Test platform-endpoint-specific rate limit checking

**Type:** Instance method

#### test_rate_limit_enforcement

```python
def test_rate_limit_enforcement(self)
```

Test rate limit enforcement after exceeding max_burst

**Type:** Instance method

#### test_wait_if_needed

```python
def test_wait_if_needed(self)
```

Test wait_if_needed method

**Type:** Instance method

#### test_statistics_tracking

```python
def test_statistics_tracking(self)
```

Test statistics tracking for multi-platform usage

**Type:** Instance method

#### test_reset_stats

```python
def test_reset_stats(self)
```

Test statistics reset

**Type:** Instance method

#### test_update_from_response_headers_mastodon

```python
def test_update_from_response_headers_mastodon(self)
```

Test updating rate limiter from Mastodon response headers

**Type:** Instance method

#### test_update_from_response_headers_pixelfed

```python
def test_update_from_response_headers_pixelfed(self)
```

Test updating rate limiter from Pixelfed response headers

**Type:** Instance method

#### test_update_from_response_headers_low_remaining

```python
def test_update_from_response_headers_low_remaining(self)
```

Test warning when rate limit remaining is low

**Type:** Instance method

### TestExtractEndpointFromUrl

```python
class TestExtractEndpointFromUrl(unittest.TestCase)
```

Test endpoint extraction from URLs for both platforms

**Methods:**

#### test_pixelfed_endpoints

```python
def test_pixelfed_endpoints(self)
```

Test endpoint extraction from Pixelfed URLs

**Type:** Instance method

#### test_mastodon_endpoints

```python
def test_mastodon_endpoints(self)
```

Test endpoint extraction from Mastodon URLs

**Type:** Instance method

#### test_activitypub_endpoints

```python
def test_activitypub_endpoints(self)
```

Test endpoint extraction from ActivityPub URLs

**Type:** Instance method

#### test_oauth_endpoints

```python
def test_oauth_endpoints(self)
```

Test endpoint extraction from OAuth URLs

**Type:** Instance method

#### test_invalid_urls

```python
def test_invalid_urls(self)
```

Test endpoint extraction from invalid URLs

**Type:** Instance method

### TestRateLimitedDecorator

```python
class TestRateLimitedDecorator(unittest.TestCase)
```

Test the rate_limited decorator with multi-platform support

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test environment

**Type:** Instance method

#### test_decorator_basic_usage

```python
def test_decorator_basic_usage(self)
```

Test basic usage of rate_limited decorator

**Type:** Instance method

#### test_decorator_with_endpoint

```python
def test_decorator_with_endpoint(self)
```

Test rate_limited decorator with endpoint parameter

**Type:** Instance method

#### test_decorator_with_platform

```python
def test_decorator_with_platform(self)
```

Test rate_limited decorator with platform parameter

**Type:** Instance method

#### test_decorator_with_endpoint_and_platform

```python
def test_decorator_with_endpoint_and_platform(self)
```

Test rate_limited decorator with both endpoint and platform

**Type:** Instance method

#### test_decorator_extracts_endpoint_from_url

```python
def test_decorator_extracts_endpoint_from_url(self)
```

Test that decorator extracts endpoint from URL parameter

**Type:** Instance method

#### test_decorator_extracts_platform_from_kwargs

```python
def test_decorator_extracts_platform_from_kwargs(self)
```

Test that decorator extracts platform from kwargs

**Type:** Instance method

#### test_decorator_updates_from_response_headers

```python
def test_decorator_updates_from_response_headers(self)
```

Test that decorator updates rate limiter from response headers

**Type:** Instance method

### TestIntegrationScenarios

```python
class TestIntegrationScenarios(unittest.TestCase)
```

Test integration scenarios with simulated rate limit scenarios

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_mastodon_rate_limiting_scenario

```python
def test_mastodon_rate_limiting_scenario(self)
```

Test a realistic Mastodon rate limiting scenario

**Type:** Instance method

#### test_pixelfed_rate_limiting_scenario

```python
def test_pixelfed_rate_limiting_scenario(self)
```

Test a realistic Pixelfed rate limiting scenario

**Type:** Instance method

#### test_mixed_platform_scenario

```python
def test_mixed_platform_scenario(self)
```

Test scenario with both Mastodon and Pixelfed rate limits

**Type:** Instance method

#### test_concurrent_requests_with_rate_limiting

```python
def test_concurrent_requests_with_rate_limiting(self)
```

Test concurrent requests with rate limiting

**Type:** Instance method

#### test_rate_limit_reset_and_window_handling

```python
def test_rate_limit_reset_and_window_handling(self)
```

Test rate limit reset and window handling

**Type:** Instance method


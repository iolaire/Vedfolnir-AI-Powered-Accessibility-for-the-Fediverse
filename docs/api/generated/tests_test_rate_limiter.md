# tests.test_rate_limiter

Tests for the rate limiter implementation.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_rate_limiter.py`

## Classes

### TestRateLimiter

```python
class TestRateLimiter(unittest.TestCase)
```

Test cases for rate limiter functionality

**Methods:**

#### test_token_bucket

```python
def test_token_bucket(self)
```

Test token bucket algorithm

**Type:** Instance method

#### test_rate_limit_config

```python
def test_rate_limit_config(self)
```

Test rate limit configuration

**Type:** Instance method

#### test_extract_endpoint_from_url

```python
def test_extract_endpoint_from_url(self)
```

Test extracting endpoint from URL

**Type:** Instance method

#### test_rate_limiter_check

```python
def test_rate_limiter_check(self)
```

Test rate limiter check functionality

**Type:** Instance method

#### test_rate_limiter_stats

```python
def test_rate_limiter_stats(self)
```

Test rate limiter statistics

**Type:** Instance method

### TestAsyncRateLimiter

```python
class TestAsyncRateLimiter(unittest.IsolatedAsyncioTestCase)
```

Test cases for async rate limiter functionality

**Methods:**

#### test_async_token_bucket

```python
async def test_async_token_bucket(self)
```

Test async token bucket consumption

**Type:** Instance method

#### test_rate_limiter_wait

```python
async def test_rate_limiter_wait(self)
```

Test rate limiter wait functionality

**Type:** Instance method

#### test_global_rate_limiter

```python
async def test_global_rate_limiter(self)
```

Test global rate limiter instance

**Type:** Instance method


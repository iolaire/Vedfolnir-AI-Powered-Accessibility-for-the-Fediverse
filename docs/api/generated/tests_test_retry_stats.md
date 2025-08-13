# tests.test_retry_stats

Test script to demonstrate retry statistics tracking functionality.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_retry_stats.py`

## Classes

### TestRetryStats

```python
class TestRetryStats(unittest.TestCase)
```

Test cases for retry statistics functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Reset statistics before each test

**Type:** Instance method

#### test_sync_retry_with_exceptions

```python
def test_sync_retry_with_exceptions(self)
```

Test synchronous retry with exceptions

**Type:** Instance method

#### test_http_status_retry

```python
def test_http_status_retry(self)
```

Test retry with HTTP status codes

**Type:** Instance method

#### test_retry_exhaustion

```python
def test_retry_exhaustion(self)
```

Test retry exhaustion (all attempts fail)

**Type:** Instance method

#### async_test_async_retry

```python
async def async_test_async_retry(self)
```

Helper for testing async retry

**Type:** Instance method

#### test_async_retry

```python
def test_async_retry(self)
```

Test asynchronous retry with exceptions

**Type:** Instance method

## Functions

### test_sync_retry

```python
def test_sync_retry(fail_count)
```

Test function that fails a specified number of times before succeeding

**Decorators:**
- `@retry(retry_config=test_retry_config)`

### test_async_retry

```python
async def test_async_retry(fail_count)
```

Test async function that fails a specified number of times before succeeding

**Decorators:**
- `@async_retry(retry_config=test_retry_config)`

### test_http_status_retry

```python
def test_http_status_retry()
```

Test function that returns HTTP responses with retry-triggering status codes

**Decorators:**
- `@retry(retry_config=test_retry_config)`

### run_async_tests

```python
async def run_async_tests()
```

Run async retry tests

### run_sync_tests

```python
def run_sync_tests()
```

Run synchronous retry tests

### run_failure_test

```python
def run_failure_test()
```

Run a test that exhausts all retry attempts


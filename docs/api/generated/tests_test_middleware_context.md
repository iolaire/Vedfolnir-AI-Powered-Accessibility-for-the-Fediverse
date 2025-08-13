# tests.test_middleware_context

Tests for middleware platform context application

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_middleware_context.py`

## Classes

### TestMiddlewareContext

```python
class TestMiddlewareContext(unittest.TestCase)
```

Test middleware applies context to all requests

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

#### _create_test_data

```python
def _create_test_data(self)
```

Create test user and platform data

**Type:** Instance method

#### test_middleware_initialization

```python
def test_middleware_initialization(self)
```

Test that middleware is properly initialized

**Type:** Instance method

#### test_middleware_sets_platform_context_with_valid_session

```python
def test_middleware_sets_platform_context_with_valid_session(self)
```

Test that middleware sets platform context when valid session exists

**Type:** Instance method

#### test_middleware_handles_missing_session

```python
def test_middleware_handles_missing_session(self)
```

Test that middleware handles requests without session gracefully

**Type:** Instance method

#### test_middleware_handles_invalid_session

```python
def test_middleware_handles_invalid_session(self)
```

Test that middleware handles invalid session IDs gracefully

**Type:** Instance method

#### test_middleware_updates_session_activity

```python
def test_middleware_updates_session_activity(self)
```

Test that middleware updates session activity on each request

**Type:** Instance method

#### test_middleware_skips_static_files

```python
def test_middleware_skips_static_files(self)
```

Test that middleware skips processing for static files

**Type:** Instance method

#### test_middleware_skips_health_checks

```python
def test_middleware_skips_health_checks(self)
```

Test that middleware skips processing for health check endpoints

**Type:** Instance method

#### test_get_current_platform_context_function

```python
def test_get_current_platform_context_function(self)
```

Test the get_current_platform_context utility function

**Type:** Instance method

#### test_get_current_platform_function

```python
def test_get_current_platform_function(self)
```

Test the get_current_platform utility function

**Type:** Instance method

#### test_middleware_context_isolation_between_requests

```python
def test_middleware_context_isolation_between_requests(self)
```

Test that middleware properly isolates context between different requests

**Type:** Instance method

#### test_middleware_error_handling

```python
def test_middleware_error_handling(self)
```

Test that middleware handles errors gracefully

**Type:** Instance method


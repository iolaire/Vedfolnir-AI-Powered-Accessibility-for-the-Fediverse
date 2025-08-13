# tests.test_middleware_simple

Simple tests for middleware platform context application

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_middleware_simple.py`

## Classes

### TestMiddlewareSimple

```python
class TestMiddlewareSimple(unittest.TestCase)
```

Test middleware applies context to all requests - simplified version

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

#### test_middleware_class_initialization

```python
def test_middleware_class_initialization(self)
```

Test that PlatformContextMiddleware can be initialized

**Type:** Instance method

#### test_get_current_platform_context_utility

```python
def test_get_current_platform_context_utility(self)
```

Test the get_current_platform_context utility function

**Type:** Instance method

#### test_get_current_platform_utility

```python
def test_get_current_platform_utility(self)
```

Test the get_current_platform utility function

**Type:** Instance method

#### test_middleware_before_request_method

```python
def test_middleware_before_request_method(self)
```

Test the middleware before_request method directly

**Type:** Instance method

#### test_middleware_after_request_method

```python
def test_middleware_after_request_method(self)
```

Test the middleware after_request method directly

**Type:** Instance method

#### test_middleware_handles_session_manager_errors

```python
def test_middleware_handles_session_manager_errors(self)
```

Test that middleware handles session manager errors gracefully

**Type:** Instance method

#### test_middleware_skips_static_and_health_endpoints

```python
def test_middleware_skips_static_and_health_endpoints(self)
```

Test that middleware skips processing for certain endpoints

**Type:** Instance method

#### test_middleware_sets_session_manager_in_g

```python
def test_middleware_sets_session_manager_in_g(self)
```

Test that middleware sets session manager in g

**Type:** Instance method

#### test_middleware_integration_with_existing_routes

```python
def test_middleware_integration_with_existing_routes(self)
```

Test that middleware works with existing routes

**Type:** Instance method

#### test_session_context_functions_work_correctly

```python
def test_session_context_functions_work_correctly(self)
```

Test that session context utility functions work as expected

**Type:** Instance method


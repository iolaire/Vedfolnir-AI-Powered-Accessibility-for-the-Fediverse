# tests.test_detached_instance_fix_simple_flask

Simple Flask Context Tests for DetachedInstanceError Fix

Focused tests that demonstrate the DetachedInstanceError fix works correctly
with Flask application context using standardized mock user helpers.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_detached_instance_fix_simple_flask.py`

## Classes

### SimpleFlaskDetachedInstanceFixTest

```python
class SimpleFlaskDetachedInstanceFixTest(unittest.TestCase)
```

Simple Flask context tests for DetachedInstanceError fix

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

#### test_request_scoped_session_with_flask_context

```python
def test_request_scoped_session_with_flask_context(self)
```

Test RequestScopedSessionManager works with Flask context

**Type:** Instance method

#### test_session_aware_user_with_flask_context

```python
def test_session_aware_user_with_flask_context(self)
```

Test SessionAwareUser works with Flask context

**Type:** Instance method

#### test_database_context_middleware_with_flask_context

```python
def test_database_context_middleware_with_flask_context(self)
```

Test DatabaseContextMiddleware works with Flask context

**Type:** Instance method

#### test_detached_instance_handler_with_flask_context

```python
def test_detached_instance_handler_with_flask_context(self)
```

Test DetachedInstanceHandler works with Flask context

**Type:** Instance method

#### test_session_error_handler_with_flask_context

```python
def test_session_error_handler_with_flask_context(self)
```

Test SessionErrorHandler works with Flask context

**Type:** Instance method

#### test_session_error_logging_with_flask_context

```python
def test_session_error_logging_with_flask_context(self)
```

Test session error logging works with Flask context

**Type:** Instance method

#### test_mock_user_helper_with_flask_context

```python
def test_mock_user_helper_with_flask_context(self)
```

Test mock user helper works correctly with Flask context

**Type:** Instance method

#### test_complete_workflow_with_flask_context

```python
def test_complete_workflow_with_flask_context(self)
```

Test complete workflow with Flask context

**Type:** Instance method

#### test_multiple_users_isolation_with_flask_context

```python
def test_multiple_users_isolation_with_flask_context(self)
```

Test multiple users are properly isolated with Flask context

**Type:** Instance method

### SimpleFlaskPerformanceTest

```python
class SimpleFlaskPerformanceTest(unittest.TestCase)
```

Simple performance tests with Flask context

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up performance test environment

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up performance test environment

**Type:** Instance method

#### test_session_performance_with_flask_context

```python
def test_session_performance_with_flask_context(self)
```

Test session performance with Flask context

**Type:** Instance method


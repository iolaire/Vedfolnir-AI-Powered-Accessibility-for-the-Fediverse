# tests.test_detached_instance_fix_flask_integration

Flask Integration Tests for DetachedInstanceError Fix

Comprehensive tests for the DetachedInstanceError fix implementation that require
Flask application context. Uses standardized mock user helpers for consistent
test data and proper cleanup.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_detached_instance_fix_flask_integration.py`

## Classes

### FlaskDetachedInstanceFixTest

```python
class FlaskDetachedInstanceFixTest(unittest.TestCase)
```

Test DetachedInstanceError fix with Flask application context

**Methods:**

#### setUpClass

```python
def setUpClass(cls)
```

Set up test environment

**Decorators:**
- `@classmethod`

**Type:** Class method

#### tearDownClass

```python
def tearDownClass(cls)
```

Clean up test environment

**Decorators:**
- `@classmethod`

**Type:** Class method

#### setUp

```python
def setUp(self)
```

Set up individual test

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up individual test

**Type:** Instance method

#### test_request_scoped_session_manager_with_flask_context

```python
def test_request_scoped_session_manager_with_flask_context(self)
```

Test RequestScopedSessionManager with proper Flask context

**Type:** Instance method

#### test_session_aware_user_with_flask_context

```python
def test_session_aware_user_with_flask_context(self)
```

Test SessionAwareUser with Flask application context

**Type:** Instance method

#### test_database_context_middleware_lifecycle

```python
def test_database_context_middleware_lifecycle(self)
```

Test DatabaseContextMiddleware request lifecycle

**Type:** Instance method

#### test_session_error_handler_with_flask_context

```python
def test_session_error_handler_with_flask_context(self)
```

Test SessionErrorHandler with Flask context

**Type:** Instance method

#### test_detached_instance_handler_recovery_with_flask_context

```python
def test_detached_instance_handler_recovery_with_flask_context(self)
```

Test DetachedInstanceHandler recovery with Flask context

**Type:** Instance method

#### test_session_error_logging_with_flask_context

```python
def test_session_error_logging_with_flask_context(self)
```

Test session error logging with Flask context

**Type:** Instance method

#### test_session_error_handling_decorator_with_flask_context

```python
def test_session_error_handling_decorator_with_flask_context(self)
```

Test @with_session_error_handling decorator with Flask context

**Type:** Instance method

#### test_user_login_workflow_with_session_management

```python
def test_user_login_workflow_with_session_management(self)
```

Test complete user login workflow with session management

**Type:** Instance method

#### test_platform_switching_workflow_with_session_management

```python
def test_platform_switching_workflow_with_session_management(self)
```

Test platform switching workflow with session management

**Type:** Instance method

#### test_dashboard_access_workflow_with_session_management

```python
def test_dashboard_access_workflow_with_session_management(self)
```

Test dashboard access workflow with session management

**Type:** Instance method

#### test_template_context_with_session_management

```python
def test_template_context_with_session_management(self)
```

Test template context with session management

**Type:** Instance method

#### test_concurrent_request_handling

```python
def test_concurrent_request_handling(self)
```

Test concurrent request handling with session management

**Type:** Instance method

### FlaskDetachedInstanceFixAdvancedTest

```python
class FlaskDetachedInstanceFixAdvancedTest(unittest.TestCase)
```

Advanced Flask integration tests for DetachedInstanceError fix

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up advanced test environment

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up advanced test environment

**Type:** Instance method

#### test_multiple_users_session_isolation

```python
def test_multiple_users_session_isolation(self)
```

Test session isolation with multiple users

**Type:** Instance method

#### test_custom_platform_configurations

```python
def test_custom_platform_configurations(self)
```

Test custom platform configurations with session management

**Type:** Instance method

#### test_error_recovery_scenarios

```python
def test_error_recovery_scenarios(self)
```

Test various error recovery scenarios

**Type:** Instance method

#### test_session_performance_under_load

```python
def test_session_performance_under_load(self)
```

Test session performance under load

**Type:** Instance method


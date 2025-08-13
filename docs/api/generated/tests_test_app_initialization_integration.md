# tests.test_app_initialization_integration

Integration Tests for Web Application Initialization

This module tests the integration of the app initialization with the existing web application.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_app_initialization_integration.py`

## Classes

### MockConfig

```python
class MockConfig
```

Mock configuration for testing

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

### TestAppInitializationIntegration

```python
class TestAppInitializationIntegration(unittest.TestCase)
```

Integration test cases for app initialization

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_create_session_managed_app_integration

```python
def test_create_session_managed_app_integration(self, mock_template_processor, mock_error_handler, mock_login_manager, mock_middleware, mock_session_manager, mock_db_manager)
```

Test creating a session-managed app with all components

**Decorators:**
- `@patch('app_initialization.DatabaseManager')`
- `@patch('app_initialization.RequestScopedSessionManager')`
- `@patch('app_initialization.DatabaseContextMiddleware')`
- `@patch('app_initialization.LoginManager')`
- `@patch('app_initialization.create_global_detached_instance_handler')`
- `@patch('app_initialization.create_safe_template_context_processor')`

**Type:** Instance method

#### test_validate_session_management_integration

```python
def test_validate_session_management_integration(self, mock_template_processor, mock_error_handler, mock_login_manager, mock_middleware, mock_session_manager, mock_db_manager)
```

Test validation of session management setup

**Decorators:**
- `@patch('app_initialization.DatabaseManager')`
- `@patch('app_initialization.RequestScopedSessionManager')`
- `@patch('app_initialization.DatabaseContextMiddleware')`
- `@patch('app_initialization.LoginManager')`
- `@patch('app_initialization.create_global_detached_instance_handler')`
- `@patch('app_initialization.create_safe_template_context_processor')`

**Type:** Instance method

#### test_get_session_management_info_integration

```python
def test_get_session_management_info_integration(self, mock_template_processor, mock_error_handler, mock_login_manager, mock_middleware, mock_session_manager, mock_db_manager)
```

Test getting session management info

**Decorators:**
- `@patch('app_initialization.DatabaseManager')`
- `@patch('app_initialization.RequestScopedSessionManager')`
- `@patch('app_initialization.DatabaseContextMiddleware')`
- `@patch('app_initialization.LoginManager')`
- `@patch('app_initialization.create_global_detached_instance_handler')`
- `@patch('app_initialization.create_safe_template_context_processor')`

**Type:** Instance method

#### test_config_compatibility

```python
def test_config_compatibility(self)
```

Test that the mock config is compatible with the app initialization

**Type:** Instance method

### TestAppInitializationErrorHandling

```python
class TestAppInitializationErrorHandling(unittest.TestCase)
```

Test error handling in app initialization

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_database_manager_initialization_error

```python
def test_database_manager_initialization_error(self, mock_db_manager)
```

Test handling of database manager initialization error

**Decorators:**
- `@patch('app_initialization.DatabaseManager')`

**Type:** Instance method

#### test_session_manager_initialization_error

```python
def test_session_manager_initialization_error(self, mock_session_manager, mock_db_manager)
```

Test handling of session manager initialization error

**Decorators:**
- `@patch('app_initialization.DatabaseManager')`
- `@patch('app_initialization.RequestScopedSessionManager')`

**Type:** Instance method

#### test_middleware_initialization_error

```python
def test_middleware_initialization_error(self, mock_middleware, mock_session_manager, mock_db_manager)
```

Test handling of middleware initialization error

**Decorators:**
- `@patch('app_initialization.DatabaseManager')`
- `@patch('app_initialization.RequestScopedSessionManager')`
- `@patch('app_initialization.DatabaseContextMiddleware')`

**Type:** Instance method


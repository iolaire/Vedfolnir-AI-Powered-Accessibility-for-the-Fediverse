# tests.test_app_initialization

Tests for Web Application Initialization with Session Management

This module tests the app initialization functionality including
session management integration and component setup.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_app_initialization.py`

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

### MockUser

```python
class MockUser
```

Mock user for testing

**Methods:**

#### __init__

```python
def __init__(self, user_id, username, is_active)
```

**Type:** Instance method

### TestSessionManagedFlaskApp

```python
class TestSessionManagedFlaskApp(unittest.TestCase)
```

Test cases for SessionManagedFlaskApp

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_initialization

```python
def test_initialization(self)
```

Test SessionManagedFlaskApp initialization

**Type:** Instance method

#### test_create_app_success

```python
def test_create_app_success(self, mock_template_processor, mock_error_handler, mock_login_manager, mock_middleware, mock_session_manager, mock_db_manager)
```

Test successful app creation

**Decorators:**
- `@patch('app_initialization.DatabaseManager')`
- `@patch('app_initialization.RequestScopedSessionManager')`
- `@patch('app_initialization.DatabaseContextMiddleware')`
- `@patch('app_initialization.LoginManager')`
- `@patch('app_initialization.create_global_detached_instance_handler')`
- `@patch('app_initialization.create_safe_template_context_processor')`

**Type:** Instance method

#### test_create_app_db_manager_error

```python
def test_create_app_db_manager_error(self, mock_db_manager)
```

Test app creation with database manager error

**Decorators:**
- `@patch('app_initialization.DatabaseManager')`

**Type:** Instance method

#### test_get_initialization_status_before_creation

```python
def test_get_initialization_status_before_creation(self)
```

Test initialization status before app creation

**Type:** Instance method

#### test_get_initialization_status_after_creation

```python
def test_get_initialization_status_after_creation(self, mock_template_processor, mock_error_handler, mock_login_manager, mock_middleware, mock_session_manager, mock_db_manager)
```

Test initialization status after app creation

**Decorators:**
- `@patch('app_initialization.DatabaseManager')`
- `@patch('app_initialization.RequestScopedSessionManager')`
- `@patch('app_initialization.DatabaseContextMiddleware')`
- `@patch('app_initialization.LoginManager')`
- `@patch('app_initialization.create_global_detached_instance_handler')`
- `@patch('app_initialization.create_safe_template_context_processor')`

**Type:** Instance method

### TestUserLoader

```python
class TestUserLoader(unittest.TestCase)
```

Test cases for Flask-Login user loader

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_user_loader_success

```python
def test_user_loader_success(self, mock_joinedload, mock_session_aware_user, mock_user)
```

Test successful user loading

**Decorators:**
- `@patch('app_initialization.User')`
- `@patch('app_initialization.SessionAwareUser')`
- `@patch('sqlalchemy.orm.joinedload')`

**Type:** Instance method

#### test_user_loader_invalid_id

```python
def test_user_loader_invalid_id(self)
```

Test user loader with invalid user ID

**Type:** Instance method

#### test_user_loader_user_not_found

```python
def test_user_loader_user_not_found(self)
```

Test user loader when user is not found

**Type:** Instance method

#### test_user_loader_database_error

```python
def test_user_loader_database_error(self)
```

Test user loader with database error

**Type:** Instance method

### TestFactoryFunction

```python
class TestFactoryFunction(unittest.TestCase)
```

Test cases for factory function

**Methods:**

#### test_create_session_managed_app

```python
def test_create_session_managed_app(self, mock_app_factory_class)
```

Test create_session_managed_app factory function

**Decorators:**
- `@patch('app_initialization.SessionManagedFlaskApp')`

**Type:** Instance method

### TestValidation

```python
class TestValidation(unittest.TestCase)
```

Test cases for validation functions

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_validate_session_management_setup_success

```python
def test_validate_session_management_setup_success(self)
```

Test successful validation

**Type:** Instance method

#### test_validate_session_management_setup_missing_components

```python
def test_validate_session_management_setup_missing_components(self)
```

Test validation with missing components

**Type:** Instance method

#### test_validate_session_management_setup_no_login_manager

```python
def test_validate_session_management_setup_no_login_manager(self)
```

Test validation without Flask-Login

**Type:** Instance method

#### test_validate_session_management_setup_no_user_loader

```python
def test_validate_session_management_setup_no_user_loader(self)
```

Test validation without user loader

**Type:** Instance method

#### test_get_session_management_info_active

```python
def test_get_session_management_info_active(self)
```

Test getting session management info when active

**Type:** Instance method

#### test_get_session_management_info_inactive

```python
def test_get_session_management_info_inactive(self)
```

Test getting session management info when inactive

**Type:** Instance method

#### test_get_session_management_info_error

```python
def test_get_session_management_info_error(self)
```

Test getting session management info with error

**Type:** Instance method


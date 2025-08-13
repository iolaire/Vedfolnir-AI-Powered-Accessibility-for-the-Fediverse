# tests.test_login_session_management

Tests for login route with proper session management to prevent DetachedInstanceError.

This test suite validates Task 11 requirements:
- Login POST handler uses request-scoped session manager
- User authentication and session creation maintain database context
- Proper error handling for database session issues during login
- Redirect logic maintains session context after successful login

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_login_session_management.py`

## Classes

### TestLoginSessionManagement

```python
class TestLoginSessionManagement(unittest.TestCase)
```

Test login route with proper session management

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment with Flask app and database

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test environment

**Type:** Instance method

#### _create_test_users

```python
def _create_test_users(self)
```

Create test users for login testing

**Type:** Instance method

#### _setup_login_route

```python
def _setup_login_route(self)
```

Set up the login route with proper imports and dependencies

**Type:** Instance method

#### test_successful_login_with_platforms

```python
def test_successful_login_with_platforms(self)
```

Test successful login for user with platforms

**Type:** Instance method

#### test_successful_login_no_platforms

```python
def test_successful_login_no_platforms(self)
```

Test successful login for user without platforms redirects to setup

**Type:** Instance method

#### test_login_invalid_credentials

```python
def test_login_invalid_credentials(self)
```

Test login with invalid credentials

**Type:** Instance method

#### test_login_inactive_user

```python
def test_login_inactive_user(self)
```

Test login with inactive user

**Type:** Instance method

#### test_login_nonexistent_user

```python
def test_login_nonexistent_user(self)
```

Test login with nonexistent user

**Type:** Instance method

#### test_login_with_next_parameter

```python
def test_login_with_next_parameter(self)
```

Test login with next parameter for redirect

**Type:** Instance method

#### test_login_already_authenticated

```python
def test_login_already_authenticated(self)
```

Test login when user is already authenticated

**Type:** Instance method

#### test_login_session_context_maintained

```python
def test_login_session_context_maintained(self)
```

Test that session context is properly maintained after login

**Type:** Instance method

#### test_login_last_login_updated

```python
def test_login_last_login_updated(self)
```

Test that last_login timestamp is updated on successful login

**Type:** Instance method

#### test_login_default_platform_selection

```python
def test_login_default_platform_selection(self)
```

Test that default platform is properly selected during login

**Type:** Instance method

#### test_login_database_error_handling

```python
def test_login_database_error_handling(self)
```

Test proper error handling for database errors during login

**Type:** Instance method

#### test_login_form_validation

```python
def test_login_form_validation(self)
```

Test login form validation

**Type:** Instance method

#### test_login_remember_me_functionality

```python
def test_login_remember_me_functionality(self)
```

Test remember me functionality

**Type:** Instance method

#### test_login_session_scope_usage

```python
def test_login_session_scope_usage(self)
```

Test that login uses request-scoped session manager properly

**Type:** Instance method

#### test_login_platform_data_extraction

```python
def test_login_platform_data_extraction(self)
```

Test that platform data is properly extracted to avoid DetachedInstanceError

**Type:** Instance method

### TestLoginErrorRecovery

```python
class TestLoginErrorRecovery(unittest.TestCase)
```

Test error recovery scenarios for login

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

#### test_detached_instance_error_recovery

```python
def test_detached_instance_error_recovery(self)
```

Test recovery from DetachedInstanceError during login

**Type:** Instance method

#### test_session_manager_error_recovery

```python
def test_session_manager_error_recovery(self)
```

Test recovery when session manager fails

**Type:** Instance method


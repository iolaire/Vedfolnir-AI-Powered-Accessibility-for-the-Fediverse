# tests.test_dashboard_session_management

Tests for dashboard route with session-aware decorators to prevent DetachedInstanceError.

This test suite validates Task 12 requirements:
- Dashboard view function uses with_db_session decorator
- Dashboard uses require_platform_context decorator for platform-dependent functionality
- All database queries in dashboard use request-scoped session
- Error handling for platform context loading failures

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_dashboard_session_management.py`

## Classes

### TestDashboardSessionManagement

```python
class TestDashboardSessionManagement(unittest.TestCase)
```

Test dashboard route with session-aware decorators

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

Create test users for dashboard testing

**Type:** Instance method

#### _setup_dashboard_route

```python
def _setup_dashboard_route(self)
```

Set up the dashboard route with proper decorators and dependencies

**Type:** Instance method

#### _login_user

```python
def _login_user(self, user)
```

Helper to log in a user and create session

**Type:** Instance method

#### test_dashboard_with_platforms_success

```python
def test_dashboard_with_platforms_success(self)
```

Test successful dashboard access with platforms

**Type:** Instance method

#### test_dashboard_without_platforms_redirects

```python
def test_dashboard_without_platforms_redirects(self)
```

Test dashboard redirects to setup when user has no platforms

**Type:** Instance method

#### test_dashboard_requires_authentication

```python
def test_dashboard_requires_authentication(self)
```

Test dashboard requires user authentication

**Type:** Instance method

#### test_dashboard_with_db_session_decorator

```python
def test_dashboard_with_db_session_decorator(self)
```

Test that dashboard uses with_db_session decorator properly

**Type:** Instance method

#### test_dashboard_require_platform_context_decorator

```python
def test_dashboard_require_platform_context_decorator(self)
```

Test that dashboard uses require_platform_context decorator

**Type:** Instance method

#### test_dashboard_platform_context_loading_success

```python
def test_dashboard_platform_context_loading_success(self)
```

Test successful platform context loading

**Type:** Instance method

#### test_dashboard_database_error_handling

```python
def test_dashboard_database_error_handling(self)
```

Test dashboard handles database errors gracefully

**Type:** Instance method

#### test_dashboard_session_scope_usage

```python
def test_dashboard_session_scope_usage(self)
```

Test that dashboard properly uses request-scoped session

**Type:** Instance method

#### test_dashboard_platform_statistics_loading

```python
def test_dashboard_platform_statistics_loading(self)
```

Test that dashboard loads platform-specific statistics

**Type:** Instance method

#### test_dashboard_detached_instance_prevention

```python
def test_dashboard_detached_instance_prevention(self)
```

Test that dashboard prevents DetachedInstanceError by using session-aware objects

**Type:** Instance method

#### test_dashboard_fallback_to_general_stats

```python
def test_dashboard_fallback_to_general_stats(self)
```

Test dashboard falls back to general stats when no platform context

**Type:** Instance method

#### test_dashboard_error_recovery

```python
def test_dashboard_error_recovery(self)
```

Test dashboard error recovery mechanisms

**Type:** Instance method

### TestDashboardDecorators

```python
class TestDashboardDecorators(unittest.TestCase)
```

Test dashboard decorators functionality

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

#### test_decorators_exist_and_importable

```python
def test_decorators_exist_and_importable(self)
```

Test that the required decorators exist and can be imported

**Type:** Instance method

#### test_dashboard_uses_decorators

```python
def test_dashboard_uses_decorators(self)
```

Test that the dashboard route in web_app.py uses the required decorators

**Type:** Instance method


# tests.test_detached_instance_fix_web_routes

Web Routes Tests for DetachedInstanceError Fix

Tests for web application routes to ensure they work correctly with the
DetachedInstanceError fix implementation. Uses Flask application context
and standardized mock user helpers.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_detached_instance_fix_web_routes.py`

## Classes

### WebRoutesDetachedInstanceFixTest

```python
class WebRoutesDetachedInstanceFixTest(unittest.TestCase)
```

Test web routes with DetachedInstanceError fix

**Methods:**

#### setUpClass

```python
def setUpClass(cls)
```

Set up test Flask application

**Decorators:**
- `@classmethod`

**Type:** Class method

#### _add_test_routes

```python
def _add_test_routes(cls)
```

Add test routes to the Flask app

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

#### _login_user

```python
def _login_user(self)
```

Helper to log in test user

**Type:** Instance method

#### test_dashboard_route_with_session_management

```python
def test_dashboard_route_with_session_management(self)
```

Test dashboard route with session management

**Type:** Instance method

#### test_platform_switching_route

```python
def test_platform_switching_route(self)
```

Test platform switching route

**Type:** Instance method

#### test_user_profile_route

```python
def test_user_profile_route(self)
```

Test user profile route

**Type:** Instance method

#### test_api_endpoint_route

```python
def test_api_endpoint_route(self)
```

Test API endpoint route

**Type:** Instance method

#### test_error_handling_route

```python
def test_error_handling_route(self)
```

Test error handling in routes

**Type:** Instance method

#### test_unauthenticated_access

```python
def test_unauthenticated_access(self)
```

Test unauthenticated access to protected routes

**Type:** Instance method

#### test_session_persistence_across_requests

```python
def test_session_persistence_across_requests(self)
```

Test session persistence across multiple requests

**Type:** Instance method

### WebRoutesAdvancedTest

```python
class WebRoutesAdvancedTest(unittest.TestCase)
```

Advanced web routes tests

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

#### test_multiple_user_sessions

```python
def test_multiple_user_sessions(self)
```

Test multiple user sessions with different roles

**Type:** Instance method

#### test_custom_platform_route_access

```python
def test_custom_platform_route_access(self)
```

Test route access with custom platform configurations

**Type:** Instance method

#### test_concurrent_route_access

```python
def test_concurrent_route_access(self)
```

Test concurrent access to routes

**Type:** Instance method


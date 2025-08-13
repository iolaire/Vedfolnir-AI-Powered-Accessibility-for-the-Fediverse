# tests.test_session_decorators_integration

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_session_decorators_integration.py`

## Classes

### TestSessionDecoratorsIntegration

```python
class TestSessionDecoratorsIntegration(unittest.TestCase)
```

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up integration test environment

**Type:** Instance method

#### test_dashboard_access_with_platform_context

```python
def test_dashboard_access_with_platform_context(self)
```

Test dashboard access with proper platform context

**Type:** Instance method

#### test_dashboard_access_without_platforms

```python
def test_dashboard_access_without_platforms(self)
```

Test dashboard access when user has no platforms

**Type:** Instance method

#### test_app_management_access_with_session_attachment

```python
def test_app_management_access_with_session_attachment(self)
```

Test app management access with proper session attachment

**Type:** Instance method

#### test_app_management_access_with_detached_user

```python
def test_app_management_access_with_detached_user(self)
```

Test app management access when user becomes detached

**Type:** Instance method

#### test_session_manager_integration

```python
def test_session_manager_integration(self)
```

Test integration with RequestScopedSessionManager

**Type:** Instance method

#### test_decorator_error_recovery

```python
def test_decorator_error_recovery(self)
```

Test error recovery in decorators

**Type:** Instance method

#### test_platform_context_error_handling

```python
def test_platform_context_error_handling(self)
```

Test platform context error handling

**Type:** Instance method

#### test_multiple_decorator_interaction

```python
def test_multiple_decorator_interaction(self)
```

Test interaction between multiple decorators

**Type:** Instance method

#### test_session_cleanup_on_error

```python
def test_session_cleanup_on_error(self)
```

Test that sessions are properly cleaned up on errors

**Type:** Instance method

#### test_unauthenticated_user_handling

```python
def test_unauthenticated_user_handling(self)
```

Test handling of unauthenticated users

**Type:** Instance method

#### test_session_manager_missing

```python
def test_session_manager_missing(self)
```

Test behavior when session manager is missing

**Type:** Instance method


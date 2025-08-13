# tests.test_session_aware_decorators

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_session_aware_decorators.py`

## Classes

### TestSessionAwareDecorators

```python
class TestSessionAwareDecorators(unittest.TestCase)
```

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test Flask app and mocks

**Type:** Instance method

#### test_with_db_session_success

```python
def test_with_db_session_success(self, mock_current_user)
```

Test with_db_session decorator with successful execution

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_with_db_session_user_reattachment

```python
def test_with_db_session_user_reattachment(self, mock_current_user)
```

Test with_db_session decorator reattaches detached user

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_with_db_session_detached_error

```python
def test_with_db_session_detached_error(self, mock_current_user)
```

Test with_db_session decorator handles DetachedInstanceError

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_with_db_session_no_session_manager

```python
def test_with_db_session_no_session_manager(self, mock_current_user)
```

Test with_db_session decorator when session manager is missing

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_require_platform_context_success

```python
def test_require_platform_context_success(self, mock_current_user)
```

Test require_platform_context decorator with valid platform

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_require_platform_context_unauthenticated

```python
def test_require_platform_context_unauthenticated(self, mock_current_user)
```

Test require_platform_context decorator with unauthenticated user

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_require_platform_context_no_platforms

```python
def test_require_platform_context_no_platforms(self, mock_current_user)
```

Test require_platform_context decorator when user has no platforms

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_require_platform_context_no_active_platform

```python
def test_require_platform_context_no_active_platform(self, mock_current_user)
```

Test require_platform_context decorator when no active platform

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_require_platform_context_detached_platforms

```python
def test_require_platform_context_detached_platforms(self, mock_current_user)
```

Test require_platform_context decorator handles detached platforms

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_handle_detached_instance_error_decorator

```python
def test_handle_detached_instance_error_decorator(self)
```

Test handle_detached_instance_error decorator catches and handles errors

**Type:** Instance method

#### test_handle_detached_instance_error_with_cache_invalidation

```python
def test_handle_detached_instance_error_with_cache_invalidation(self, mock_current_user)
```

Test handle_detached_instance_error decorator invalidates cache

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_ensure_user_session_attachment_success

```python
def test_ensure_user_session_attachment_success(self, mock_current_user)
```

Test ensure_user_session_attachment decorator with authenticated user

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_ensure_user_session_attachment_detached_user

```python
def test_ensure_user_session_attachment_detached_user(self, mock_current_user)
```

Test ensure_user_session_attachment decorator handles detached user

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_ensure_user_session_attachment_unauthenticated

```python
def test_ensure_user_session_attachment_unauthenticated(self, mock_current_user)
```

Test ensure_user_session_attachment decorator with unauthenticated user

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_ensure_user_session_attachment_reattachment

```python
def test_ensure_user_session_attachment_reattachment(self, mock_current_user)
```

Test ensure_user_session_attachment decorator reattaches user

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_decorator_stacking

```python
def test_decorator_stacking(self)
```

Test that decorators can be stacked properly

**Type:** Instance method

#### test_sqlalchemy_error_handling

```python
def test_sqlalchemy_error_handling(self, mock_current_user)
```

Test that decorators handle general SQLAlchemy errors

**Decorators:**
- `@patch('session_aware_decorators.current_user')`

**Type:** Instance method

#### test_logging_on_errors

```python
def test_logging_on_errors(self, mock_logger)
```

Test that errors are properly logged

**Decorators:**
- `@patch('session_aware_decorators.logger')`

**Type:** Instance method


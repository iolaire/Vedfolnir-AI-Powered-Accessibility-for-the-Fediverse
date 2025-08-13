# tests.test_session_decorators_simple

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_session_decorators_simple.py`

## Classes

### MockUser

```python
class MockUser
```

Simple mock user class to avoid AsyncMock issues

**Properties:**
- `id`

**Methods:**

#### __init__

```python
def __init__(self, authenticated, user_id, platforms, active_platform, raise_detached)
```

**Type:** Instance method

#### get_active_platform

```python
def get_active_platform(self)
```

**Type:** Instance method

### TestSessionDecoratorsSimple

```python
class TestSessionDecoratorsSimple(unittest.TestCase)
```

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test Flask app

**Type:** Instance method

#### test_with_db_session_success

```python
def test_with_db_session_success(self)
```

Test with_db_session decorator with authenticated user

**Type:** Instance method

#### test_with_db_session_detached_error

```python
def test_with_db_session_detached_error(self)
```

Test with_db_session decorator handles DetachedInstanceError

**Type:** Instance method

#### test_require_platform_context_success

```python
def test_require_platform_context_success(self)
```

Test require_platform_context decorator with valid platform

**Type:** Instance method

#### test_require_platform_context_no_platforms

```python
def test_require_platform_context_no_platforms(self)
```

Test require_platform_context decorator when user has no platforms

**Type:** Instance method

#### test_require_platform_context_no_active_platform

```python
def test_require_platform_context_no_active_platform(self)
```

Test require_platform_context decorator when no active platform

**Type:** Instance method

#### test_require_platform_context_unauthenticated

```python
def test_require_platform_context_unauthenticated(self)
```

Test require_platform_context decorator with unauthenticated user

**Type:** Instance method

#### test_handle_detached_instance_error

```python
def test_handle_detached_instance_error(self)
```

Test handle_detached_instance_error decorator

**Type:** Instance method

#### test_ensure_user_session_attachment_success

```python
def test_ensure_user_session_attachment_success(self)
```

Test ensure_user_session_attachment decorator

**Type:** Instance method

#### test_missing_session_manager

```python
def test_missing_session_manager(self)
```

Test behavior when session manager is missing

**Type:** Instance method


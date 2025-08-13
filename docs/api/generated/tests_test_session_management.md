# tests.test_session_management

Tests for platform-aware session management

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_session_management.py`

## Classes

### TestSessionManagement

```python
class TestSessionManagement(unittest.TestCase)
```

Test session management functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test database and session manager

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test database

**Type:** Instance method

#### _create_test_data

```python
def _create_test_data(self)
```

Create test user and platform data

**Type:** Instance method

#### test_create_user_session

```python
def test_create_user_session(self)
```

Test creating a user session

**Type:** Instance method

#### test_create_user_session_with_platform

```python
def test_create_user_session_with_platform(self)
```

Test creating a user session with specific platform

**Type:** Instance method

#### test_create_session_invalid_user

```python
def test_create_session_invalid_user(self)
```

Test creating session with invalid user

**Type:** Instance method

#### test_create_session_invalid_platform

```python
def test_create_session_invalid_platform(self)
```

Test creating session with invalid platform

**Type:** Instance method

#### test_get_session_context

```python
def test_get_session_context(self)
```

Test getting session context

**Type:** Instance method

#### test_get_session_context_invalid

```python
def test_get_session_context_invalid(self)
```

Test getting context for invalid session

**Type:** Instance method

#### test_update_platform_context

```python
def test_update_platform_context(self)
```

Test updating platform context

**Type:** Instance method

#### test_update_platform_context_invalid_session

```python
def test_update_platform_context_invalid_session(self)
```

Test updating platform context with invalid session

**Type:** Instance method

#### test_update_platform_context_invalid_platform

```python
def test_update_platform_context_invalid_platform(self)
```

Test updating platform context with invalid platform

**Type:** Instance method

#### test_validate_session

```python
def test_validate_session(self)
```

Test session validation

**Type:** Instance method

#### test_cleanup_user_sessions

```python
def test_cleanup_user_sessions(self)
```

Test cleaning up user sessions

**Type:** Instance method

#### test_cleanup_user_sessions_keep_current

```python
def test_cleanup_user_sessions_keep_current(self)
```

Test cleaning up user sessions while keeping current

**Type:** Instance method

#### test_cleanup_expired_sessions

```python
def test_cleanup_expired_sessions(self)
```

Test cleaning up expired sessions

**Type:** Instance method


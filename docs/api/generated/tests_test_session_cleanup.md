# tests.test_session_cleanup

Tests for session cleanup data integrity

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_session_cleanup.py`

## Classes

### TestSessionCleanup

```python
class TestSessionCleanup(unittest.TestCase)
```

Test session cleanup maintains data integrity

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

#### _create_test_data

```python
def _create_test_data(self)
```

Create test user and platform data

**Type:** Instance method

#### test_cleanup_expired_sessions_preserves_active_sessions

```python
def test_cleanup_expired_sessions_preserves_active_sessions(self)
```

Test that expired session cleanup doesn't affect active sessions

**Type:** Instance method

#### test_cleanup_user_sessions_preserves_other_users

```python
def test_cleanup_user_sessions_preserves_other_users(self)
```

Test that user session cleanup doesn't affect other users' sessions

**Type:** Instance method

#### test_cleanup_user_sessions_keep_current_preserves_specified_session

```python
def test_cleanup_user_sessions_keep_current_preserves_specified_session(self)
```

Test that cleanup with keep_current preserves the specified session

**Type:** Instance method

#### test_cleanup_maintains_platform_connection_integrity

```python
def test_cleanup_maintains_platform_connection_integrity(self)
```

Test that session cleanup doesn't affect platform connections

**Type:** Instance method

#### test_cleanup_maintains_user_integrity

```python
def test_cleanup_maintains_user_integrity(self)
```

Test that session cleanup doesn't affect user data

**Type:** Instance method

#### test_cleanup_handles_database_constraints

```python
def test_cleanup_handles_database_constraints(self)
```

Test that cleanup properly handles database constraints and relationships

**Type:** Instance method

#### test_cleanup_concurrent_operations

```python
def test_cleanup_concurrent_operations(self)
```

Test that cleanup works correctly with concurrent session operations

**Type:** Instance method


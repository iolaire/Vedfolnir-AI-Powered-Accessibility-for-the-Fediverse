# tests.test_platform_switching

Tests for platform switching functionality

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_platform_switching.py`

## Classes

### TestPlatformSwitching

```python
class TestPlatformSwitching(unittest.TestCase)
```

Test platform switching updates session immediately

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

#### test_session_manager_platform_switch_immediate

```python
def test_session_manager_platform_switch_immediate(self)
```

Test that session manager updates platform context immediately

**Type:** Instance method

#### test_platform_switch_updates_last_used

```python
def test_platform_switch_updates_last_used(self)
```

Test that platform switching updates the platform's last_used timestamp

**Type:** Instance method

#### test_platform_switch_invalid_platform

```python
def test_platform_switch_invalid_platform(self)
```

Test that switching to invalid platform fails gracefully

**Type:** Instance method

#### test_platform_switch_unauthorized_platform

```python
def test_platform_switch_unauthorized_platform(self)
```

Test that switching to another user's platform fails

**Type:** Instance method

#### test_concurrent_platform_switches

```python
def test_concurrent_platform_switches(self)
```

Test that concurrent platform switches work correctly

**Type:** Instance method

#### test_platform_switch_session_integration

```python
def test_platform_switch_session_integration(self)
```

Test that platform switching integrates properly with session management

**Type:** Instance method


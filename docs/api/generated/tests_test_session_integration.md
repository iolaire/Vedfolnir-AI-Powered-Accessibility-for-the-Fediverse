# tests.test_session_integration

Integration tests for session management with web app

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_session_integration.py`

## Classes

### TestSessionIntegration

```python
class TestSessionIntegration(unittest.TestCase)
```

Test session management integration with web app

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

#### test_session_creation_on_login

```python
def test_session_creation_on_login(self)
```

Test that session is created when user logs in

**Type:** Instance method

#### test_platform_context_injection

```python
def test_platform_context_injection(self)
```

Test that platform context is properly injected into templates

**Type:** Instance method

#### test_session_validation

```python
def test_session_validation(self)
```

Test session validation functionality

**Type:** Instance method

#### test_platform_switching

```python
def test_platform_switching(self)
```

Test platform switching functionality

**Type:** Instance method


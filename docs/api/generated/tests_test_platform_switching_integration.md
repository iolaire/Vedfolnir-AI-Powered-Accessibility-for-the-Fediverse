# tests.test_platform_switching_integration

Integration tests for platform switching with caption generation

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_platform_switching_integration.py`

## Classes

### TestPlatformSwitchingIntegration

```python
class TestPlatformSwitchingIntegration(unittest.TestCase)
```

Test cases for platform switching integration with caption generation

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_platform_switch_with_no_active_task

```python
def test_platform_switch_with_no_active_task(self)
```

Test platform switching when no caption generation task is active

**Type:** Instance method

#### test_platform_switch_with_active_task

```python
def test_platform_switch_with_active_task(self)
```

Test platform switching when caption generation task is active

**Type:** Instance method

#### test_platform_switch_cancel_failure

```python
def test_platform_switch_cancel_failure(self)
```

Test platform switching when task cancellation fails

**Type:** Instance method

#### test_platform_availability_check

```python
def test_platform_availability_check(self)
```

Test checking platform availability for caption generation

**Type:** Instance method

#### test_platform_context_validation

```python
def test_platform_context_validation(self)
```

Test platform context validation during caption generation

**Type:** Instance method

#### test_platform_context_validation_failure

```python
def test_platform_context_validation_failure(self)
```

Test platform context validation failure

**Type:** Instance method

#### test_cross_platform_task_isolation

```python
def test_cross_platform_task_isolation(self)
```

Test that tasks are properly isolated between platforms

**Type:** Instance method

#### test_platform_switch_settings_preservation

```python
def test_platform_switch_settings_preservation(self)
```

Test that platform-specific settings are preserved during switches

**Type:** Instance method


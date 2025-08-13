# tests.test_platform_switching_session_management

Test suite for platform switching API with session management.
Tests Task 13 requirements: Update platform switching API with session management.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_platform_switching_session_management.py`

## Classes

### TestPlatformSwitchingSessionManagement

```python
class TestPlatformSwitchingSessionManagement(unittest.TestCase)
```

Test platform switching API with proper session management

**Methods:**

#### test_api_switch_platform_has_session_decorators

```python
def test_api_switch_platform_has_session_decorators(self)
```

Test that api_switch_platform has the required decorators

**Type:** Instance method

#### test_api_switch_platform_uses_request_session_manager

```python
def test_api_switch_platform_uses_request_session_manager(self)
```

Test that api_switch_platform uses request_session_manager.session_scope()

**Type:** Instance method

#### test_api_switch_platform_validates_platform_ownership

```python
def test_api_switch_platform_validates_platform_ownership(self)
```

Test that api_switch_platform validates platform ownership and accessibility

**Type:** Instance method

#### test_api_switch_platform_handles_active_tasks

```python
def test_api_switch_platform_handles_active_tasks(self)
```

Test that api_switch_platform handles active caption generation tasks

**Type:** Instance method

#### test_api_switch_platform_updates_session_context

```python
def test_api_switch_platform_updates_session_context(self)
```

Test that api_switch_platform updates session context properly

**Type:** Instance method

#### test_api_switch_platform_extracts_platform_data_safely

```python
def test_api_switch_platform_extracts_platform_data_safely(self)
```

Test that api_switch_platform extracts platform data to avoid DetachedInstanceError

**Type:** Instance method

#### test_api_switch_platform_error_handling

```python
def test_api_switch_platform_error_handling(self)
```

Test that api_switch_platform has proper error handling

**Type:** Instance method

#### test_task_13_requirements_implementation

```python
def test_task_13_requirements_implementation(self)
```

Test that all Task 13 requirements are implemented

**Type:** Instance method

#### test_platform_switching_session_management_integration

```python
def test_platform_switching_session_management_integration(self)
```

Test that platform switching integrates properly with session management

**Type:** Instance method


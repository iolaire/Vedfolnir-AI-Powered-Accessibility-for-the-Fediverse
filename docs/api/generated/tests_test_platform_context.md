# tests.test_platform_context

Unit tests for platform context management

Tests the PlatformContextManager functionality including:
- Context setting and validation
- Platform filtering
- Data injection
- Error handling

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_platform_context.py`

## Classes

### TestPlatformContextManager

```python
class TestPlatformContextManager(PlatformTestCase)
```

Test PlatformContextManager functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test with context manager

**Type:** Instance method

#### test_set_context_valid

```python
def test_set_context_valid(self)
```

Test setting valid platform context

**Type:** Instance method

#### test_set_context_invalid_user

```python
def test_set_context_invalid_user(self)
```

Test setting context with invalid user

**Type:** Instance method

#### test_set_context_invalid_platform

```python
def test_set_context_invalid_platform(self)
```

Test setting context with invalid platform

**Type:** Instance method

#### test_set_context_platform_not_owned

```python
def test_set_context_platform_not_owned(self)
```

Test setting context with platform not owned by user

**Type:** Instance method

#### test_require_context_with_context

```python
def test_require_context_with_context(self)
```

Test requiring context when context is set

**Type:** Instance method

#### test_require_context_without_context

```python
def test_require_context_without_context(self)
```

Test requiring context when no context is set

**Type:** Instance method

#### test_clear_context

```python
def test_clear_context(self)
```

Test clearing platform context

**Type:** Instance method

#### test_apply_platform_filter_post

```python
def test_apply_platform_filter_post(self)
```

Test applying platform filter to Post queries

**Type:** Instance method

#### test_apply_platform_filter_image

```python
def test_apply_platform_filter_image(self)
```

Test applying platform filter to Image queries

**Type:** Instance method

#### test_apply_platform_filter_without_context

```python
def test_apply_platform_filter_without_context(self)
```

Test applying platform filter without context

**Type:** Instance method

#### test_inject_platform_data

```python
def test_inject_platform_data(self)
```

Test injecting platform data into dictionaries

**Type:** Instance method

#### test_inject_platform_data_without_context

```python
def test_inject_platform_data_without_context(self)
```

Test injecting platform data without context

**Type:** Instance method

#### test_get_activitypub_config

```python
def test_get_activitypub_config(self)
```

Test getting ActivityPub config from context

**Type:** Instance method

#### test_get_activitypub_config_without_context

```python
def test_get_activitypub_config_without_context(self)
```

Test getting ActivityPub config without context

**Type:** Instance method

#### test_context_scope_manager

```python
def test_context_scope_manager(self)
```

Test context scope manager

**Type:** Instance method

#### test_context_scope_manager_exception

```python
def test_context_scope_manager_exception(self)
```

Test context scope manager with exception

**Type:** Instance method

#### test_validate_platform_access

```python
def test_validate_platform_access(self)
```

Test platform access validation

**Type:** Instance method

#### test_get_platform_statistics

```python
def test_get_platform_statistics(self)
```

Test getting platform-specific statistics

**Type:** Instance method

### TestPlatformContextError

```python
class TestPlatformContextError(unittest.TestCase)
```

Test PlatformContextError exception

**Methods:**

#### test_error_creation

```python
def test_error_creation(self)
```

Test creating PlatformContextError

**Type:** Instance method

#### test_error_with_context

```python
def test_error_with_context(self)
```

Test error with additional context

**Type:** Instance method

### TestPlatformContextIntegration

```python
class TestPlatformContextIntegration(PlatformTestCase)
```

Test platform context integration with other components

**Methods:**

#### test_context_with_database_operations

```python
def test_context_with_database_operations(self)
```

Test context integration with database operations

**Type:** Instance method

#### test_context_switching_performance

```python
def test_context_switching_performance(self)
```

Test performance of context switching

**Type:** Instance method

#### test_concurrent_context_isolation

```python
def test_concurrent_context_isolation(self)
```

Test that contexts are isolated between instances

**Type:** Instance method


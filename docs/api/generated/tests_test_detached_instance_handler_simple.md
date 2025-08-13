# tests.test_detached_instance_handler_simple

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_detached_instance_handler_simple.py`

## Classes

### MockSessionManager

```python
class MockSessionManager
```

Mock session manager for testing

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### get_request_session

```python
def get_request_session(self)
```

**Type:** Instance method

### MockSQLAlchemyObject

```python
class MockSQLAlchemyObject
```

Mock SQLAlchemy object for testing

**Methods:**

#### __init__

```python
def __init__(self, id, name)
```

**Type:** Instance method

### TestDetachedInstanceHandlerSimple

```python
class TestDetachedInstanceHandlerSimple(unittest.TestCase)
```

Test DetachedInstanceHandler core functionality (simplified)

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_handler_initialization

```python
def test_handler_initialization(self)
```

Test DetachedInstanceHandler initialization

**Type:** Instance method

#### test_handle_detached_instance_merge_success

```python
def test_handle_detached_instance_merge_success(self)
```

Test successful object recovery using merge

**Type:** Instance method

#### test_handle_detached_instance_merge_fails_reload_success

```python
def test_handle_detached_instance_merge_fails_reload_success(self)
```

Test object recovery using reload when merge fails

**Type:** Instance method

#### test_handle_detached_instance_both_fail

```python
def test_handle_detached_instance_both_fail(self)
```

Test exception when both merge and reload fail

**Type:** Instance method

#### test_handle_detached_instance_custom_session

```python
def test_handle_detached_instance_custom_session(self)
```

Test using custom session instead of request session

**Type:** Instance method

#### test_safe_access_success

```python
def test_safe_access_success(self)
```

Test successful safe attribute access

**Type:** Instance method

#### test_safe_access_attribute_error

```python
def test_safe_access_attribute_error(self)
```

Test safe access with AttributeError returns default

**Type:** Instance method

#### test_safe_access_no_default

```python
def test_safe_access_no_default(self)
```

Test safe access without default returns None

**Type:** Instance method

#### test_safe_relationship_access_success

```python
def test_safe_relationship_access_success(self)
```

Test successful safe relationship access

**Type:** Instance method

#### test_safe_relationship_access_default_empty_list

```python
def test_safe_relationship_access_default_empty_list(self)
```

Test safe relationship access returns empty list by default

**Type:** Instance method

#### test_safe_relationship_access_custom_default

```python
def test_safe_relationship_access_custom_default(self)
```

Test safe relationship access with custom default

**Type:** Instance method

#### test_ensure_attached_already_in_session

```python
def test_ensure_attached_already_in_session(self)
```

Test ensure_attached when object is already in session

**Type:** Instance method

#### test_ensure_attached_not_in_session

```python
def test_ensure_attached_not_in_session(self)
```

Test ensure_attached when object is not in session

**Type:** Instance method

#### test_ensure_attached_recovery_fails

```python
def test_ensure_attached_recovery_fails(self)
```

Test ensure_attached when recovery fails returns original object

**Type:** Instance method

#### test_ensure_attached_custom_session

```python
def test_ensure_attached_custom_session(self)
```

Test ensure_attached with custom session

**Type:** Instance method

### TestGlobalErrorHandlersSimple

```python
class TestGlobalErrorHandlersSimple(unittest.TestCase)
```

Test global error handler creation (simplified)

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_create_global_detached_instance_handler

```python
def test_create_global_detached_instance_handler(self)
```

Test creation of global error handlers

**Type:** Instance method

#### test_handler_methods_exist

```python
def test_handler_methods_exist(self)
```

Test that all required handler methods exist

**Type:** Instance method

#### test_handler_with_different_object_types

```python
def test_handler_with_different_object_types(self)
```

Test handler works with different mock object types

**Type:** Instance method

#### test_safe_access_with_various_attributes

```python
def test_safe_access_with_various_attributes(self)
```

Test safe access with various attribute types

**Type:** Instance method

#### test_error_handling_robustness

```python
def test_error_handling_robustness(self)
```

Test that handler is robust against various error conditions

**Type:** Instance method


# tests.test_detached_instance_handler

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_detached_instance_handler.py`

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

### TestDetachedInstanceHandler

```python
class TestDetachedInstanceHandler(unittest.TestCase)
```

Test DetachedInstanceHandler functionality

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

#### test_handle_detached_instance_no_id

```python
def test_handle_detached_instance_no_id(self)
```

Test exception when object has no id for reload

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

#### test_safe_access_detached_instance_error_recovery

```python
def test_safe_access_detached_instance_error_recovery(self)
```

Test safe access with DetachedInstanceError recovery

**Type:** Instance method

#### test_safe_access_attribute_error

```python
def test_safe_access_attribute_error(self)
```

Test safe access with AttributeError returns default

**Type:** Instance method

#### test_safe_access_recovery_fails

```python
def test_safe_access_recovery_fails(self)
```

Test safe access when recovery fails returns default

**Type:** Instance method

#### test_safe_relationship_access_success

```python
def test_safe_relationship_access_success(self)
```

Test successful safe relationship access

**Type:** Instance method

#### test_safe_relationship_access_detached_instance_error

```python
def test_safe_relationship_access_detached_instance_error(self)
```

Test safe relationship access with DetachedInstanceError recovery

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

### TestGlobalErrorHandlers

```python
class TestGlobalErrorHandlers(unittest.TestCase)
```

Test global error handler creation and functionality

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

#### test_get_detached_instance_handler_success

```python
def test_get_detached_instance_handler_success(self)
```

Test successful retrieval of handler

**Type:** Instance method

#### test_get_detached_instance_handler_not_configured

```python
def test_get_detached_instance_handler_not_configured(self)
```

Test exception when handler is not configured

**Type:** Instance method

### TestIntegrationWithMockUsers

```python
class TestIntegrationWithMockUsers(unittest.TestCase)
```

Test DetachedInstanceHandler integration with mock users

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures with mock user management

**Type:** Instance method

#### test_handle_detached_user_object

```python
def test_handle_detached_user_object(self)
```

Test handling detached User object

**Type:** Instance method

#### test_handle_detached_platform_object

```python
def test_handle_detached_platform_object(self)
```

Test handling detached PlatformConnection object

**Type:** Instance method

#### test_safe_access_user_attributes

```python
def test_safe_access_user_attributes(self)
```

Test safe access to user attributes

**Type:** Instance method

#### test_safe_access_platform_attributes

```python
def test_safe_access_platform_attributes(self)
```

Test safe access to platform attributes

**Type:** Instance method

#### test_safe_relationship_access_user_platforms

```python
def test_safe_relationship_access_user_platforms(self)
```

Test safe access to user platform relationships

**Type:** Instance method

#### test_ensure_attached_with_mock_objects

```python
def test_ensure_attached_with_mock_objects(self)
```

Test ensure_attached with mock user and platform objects

**Type:** Instance method


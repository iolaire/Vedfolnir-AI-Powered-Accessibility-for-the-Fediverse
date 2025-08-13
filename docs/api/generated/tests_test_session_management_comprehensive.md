# tests.test_session_management_comprehensive

Comprehensive Unit Tests for Session Management

This module provides comprehensive unit tests for the session management components
to prevent DetachedInstanceError and ensure proper database session handling.

Requirements tested: 1.4, 2.4, 4.4, 7.4

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_session_management_comprehensive.py`

## Classes

### TestRequestScopedSessionManager

```python
class TestRequestScopedSessionManager(unittest.TestCase)
```

Test RequestScopedSessionManager functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_initialization

```python
def test_initialization(self)
```

Test RequestScopedSessionManager initialization

**Type:** Instance method

#### test_get_request_session_creates_new_session

```python
def test_get_request_session_creates_new_session(self)
```

Test that get_request_session creates new session when none exists

**Type:** Instance method

#### test_get_request_session_returns_existing_session

```python
def test_get_request_session_returns_existing_session(self)
```

Test that get_request_session returns existing session

**Type:** Instance method

#### test_get_request_session_outside_request_context

```python
def test_get_request_session_outside_request_context(self)
```

Test that get_request_session raises error outside request context

**Type:** Instance method

#### test_close_request_session_success

```python
def test_close_request_session_success(self)
```

Test successful session closure

**Type:** Instance method

#### test_close_request_session_with_error

```python
def test_close_request_session_with_error(self)
```

Test session closure when close() raises exception

**Type:** Instance method

#### test_close_request_session_outside_context

```python
def test_close_request_session_outside_context(self)
```

Test close_request_session outside request context

**Type:** Instance method

#### test_session_scope_success

```python
def test_session_scope_success(self)
```

Test successful session_scope context manager

**Type:** Instance method

#### test_session_scope_with_exception

```python
def test_session_scope_with_exception(self)
```

Test session_scope context manager with exception

**Type:** Instance method

#### test_ensure_session_attachment_already_attached

```python
def test_ensure_session_attachment_already_attached(self)
```

Test ensure_session_attachment when object is already attached

**Type:** Instance method

#### test_ensure_session_attachment_needs_merge

```python
def test_ensure_session_attachment_needs_merge(self)
```

Test ensure_session_attachment when object needs merging

**Type:** Instance method

#### test_ensure_session_attachment_none_object

```python
def test_ensure_session_attachment_none_object(self)
```

Test ensure_session_attachment with None object

**Type:** Instance method

#### test_is_session_active_true

```python
def test_is_session_active_true(self)
```

Test is_session_active returns True when session exists

**Type:** Instance method

#### test_is_session_active_false

```python
def test_is_session_active_false(self)
```

Test is_session_active returns False when no session

**Type:** Instance method

#### test_is_session_active_outside_context

```python
def test_is_session_active_outside_context(self)
```

Test is_session_active outside request context

**Type:** Instance method

#### test_get_session_info

```python
def test_get_session_info(self)
```

Test get_session_info returns correct information

**Type:** Instance method

### TestSessionAwareUser

```python
class TestSessionAwareUser(unittest.TestCase)
```

Test SessionAwareUser class and property access

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_initialization

```python
def test_initialization(self)
```

Test SessionAwareUser initialization

**Type:** Instance method

#### test_get_attached_user_success

```python
def test_get_attached_user_success(self, mock_has_context)
```

Test _get_attached_user successful attachment

**Decorators:**
- `@patch('session_aware_user.has_request_context', return_value=True)`

**Type:** Instance method

#### test_get_attached_user_outside_context

```python
def test_get_attached_user_outside_context(self, mock_has_context)
```

Test _get_attached_user outside request context

**Decorators:**
- `@patch('session_aware_user.has_request_context', return_value=False)`

**Type:** Instance method

#### test_get_attached_user_reattachment_fails

```python
def test_get_attached_user_reattachment_fails(self, mock_has_context)
```

Test _get_attached_user when reattachment fails, falls back to reload

**Decorators:**
- `@patch('session_aware_user.has_request_context', return_value=True)`

**Type:** Instance method

#### test_platforms_property_cached

```python
def test_platforms_property_cached(self, mock_has_context)
```

Test platforms property returns cached result

**Decorators:**
- `@patch('session_aware_user.has_request_context', return_value=True)`

**Type:** Instance method

#### test_platforms_property_loads_from_user

```python
def test_platforms_property_loads_from_user(self, mock_has_context)
```

Test platforms property loads from user when cache invalid

**Decorators:**
- `@patch('session_aware_user.has_request_context', return_value=True)`

**Type:** Instance method

#### test_platforms_property_detached_error_recovery

```python
def test_platforms_property_detached_error_recovery(self, mock_has_context)
```

Test platforms property recovers from DetachedInstanceError

**Decorators:**
- `@patch('session_aware_user.has_request_context', return_value=True)`

**Type:** Instance method

#### test_get_active_platform_default_found

```python
def test_get_active_platform_default_found(self)
```

Test get_active_platform returns default platform

**Type:** Instance method

#### test_get_active_platform_first_active

```python
def test_get_active_platform_first_active(self)
```

Test get_active_platform returns first active when no default

**Type:** Instance method

#### test_get_platform_by_id

```python
def test_get_platform_by_id(self)
```

Test get_platform_by_id finds correct platform

**Type:** Instance method

#### test_get_platform_by_type

```python
def test_get_platform_by_type(self)
```

Test get_platform_by_type finds correct platform

**Type:** Instance method

#### test_refresh_platforms

```python
def test_refresh_platforms(self)
```

Test refresh_platforms invalidates cache

**Type:** Instance method

#### test_getattr_proxy_success

```python
def test_getattr_proxy_success(self)
```

Test __getattr__ proxies to user object successfully

**Type:** Instance method

#### test_getattr_detached_error_recovery

```python
def test_getattr_detached_error_recovery(self)
```

Test __getattr__ recovers from DetachedInstanceError

**Type:** Instance method

#### test_flask_login_properties

```python
def test_flask_login_properties(self)
```

Test Flask-Login required properties

**Type:** Instance method

#### test_repr

```python
def test_repr(self)
```

Test string representation

**Type:** Instance method

### TestDetachedInstanceHandler

```python
class TestDetachedInstanceHandler(unittest.TestCase)
```

Test DetachedInstanceHandler recovery mechanisms

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_initialization

```python
def test_initialization(self)
```

Test DetachedInstanceHandler initialization

**Type:** Instance method

#### test_handle_detached_instance_merge_success

```python
def test_handle_detached_instance_merge_success(self)
```

Test successful object merge recovery

**Type:** Instance method

#### test_handle_detached_instance_merge_fails_reload_success

```python
def test_handle_detached_instance_merge_fails_reload_success(self)
```

Test object reload when merge fails

**Type:** Instance method

#### test_handle_detached_instance_both_fail

```python
def test_handle_detached_instance_both_fail(self)
```

Test when both merge and reload fail

**Type:** Instance method

#### test_handle_detached_instance_no_id

```python
def test_handle_detached_instance_no_id(self)
```

Test handling object without id attribute

**Type:** Instance method

#### test_safe_access_success

```python
def test_safe_access_success(self)
```

Test successful safe attribute access

**Type:** Instance method

#### test_safe_access_detached_error_recovery

```python
def test_safe_access_detached_error_recovery(self)
```

Test safe_access recovers from DetachedInstanceError

**Type:** Instance method

#### test_safe_access_attribute_error

```python
def test_safe_access_attribute_error(self)
```

Test safe_access handles AttributeError

**Type:** Instance method

#### test_safe_access_recovery_fails

```python
def test_safe_access_recovery_fails(self)
```

Test safe_access when recovery fails

**Type:** Instance method

#### test_safe_relationship_access_success

```python
def test_safe_relationship_access_success(self)
```

Test successful safe relationship access

**Type:** Instance method

#### test_safe_relationship_access_detached_recovery

```python
def test_safe_relationship_access_detached_recovery(self)
```

Test safe_relationship_access recovers from DetachedInstanceError

**Type:** Instance method

#### test_ensure_attached_already_in_session

```python
def test_ensure_attached_already_in_session(self)
```

Test ensure_attached when object already in session

**Type:** Instance method

#### test_ensure_attached_needs_recovery

```python
def test_ensure_attached_needs_recovery(self)
```

Test ensure_attached when object needs recovery

**Type:** Instance method

#### test_create_global_detached_instance_handler

```python
def test_create_global_detached_instance_handler(self)
```

Test creation of global error handler

**Type:** Instance method

### TestSafeTemplateContext

```python
class TestSafeTemplateContext(unittest.TestCase)
```

Test template context processor error handling

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_safe_template_context_unauthenticated

```python
def test_safe_template_context_unauthenticated(self)
```

Test safe_template_context with unauthenticated user

**Type:** Instance method

#### test_safe_template_context_authenticated_success

```python
def test_safe_template_context_authenticated_success(self)
```

Test safe_template_context with authenticated user success

**Type:** Instance method

#### test_safe_template_context_missing_components

```python
def test_safe_template_context_missing_components(self)
```

Test safe_template_context with missing session manager

**Type:** Instance method

#### test_safe_template_context_detached_error

```python
def test_safe_template_context_detached_error(self)
```

Test safe_template_context handles DetachedInstanceError

**Type:** Instance method

#### test_get_safe_user_data_success

```python
def test_get_safe_user_data_success(self)
```

Test _get_safe_user_data successful extraction

**Type:** Instance method

#### test_get_safe_user_data_error

```python
def test_get_safe_user_data_error(self)
```

Test _get_safe_user_data handles errors

**Type:** Instance method

#### test_get_safe_platforms_data_success

```python
def test_get_safe_platforms_data_success(self)
```

Test _get_safe_platforms_data successful extraction

**Type:** Instance method

#### test_get_safe_platforms_data_fallback_query

```python
def test_get_safe_platforms_data_fallback_query(self)
```

Test _get_safe_platforms_data uses fallback query

**Type:** Instance method


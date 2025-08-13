# tests.test_safe_template_context_simple

Simplified Tests for Safe Template Context Processor

This module tests the safe template context processor functionality
with simplified mocking to avoid Flask context issues.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_safe_template_context_simple.py`

## Classes

### MockUser

```python
class MockUser
```

Mock user class for testing

**Methods:**

#### __init__

```python
def __init__(self, user_id, username, email, role, is_active)
```

**Type:** Instance method

#### get_id

```python
def get_id(self)
```

**Type:** Instance method

### MockPlatform

```python
class MockPlatform
```

Mock platform class for testing

**Methods:**

#### __init__

```python
def __init__(self, platform_id, name, platform_type, instance_url, username, is_active, is_default)
```

**Type:** Instance method

#### to_dict

```python
def to_dict(self)
```

**Type:** Instance method

### TestSafeTemplateContextSimple

```python
class TestSafeTemplateContextSimple(unittest.TestCase)
```

Simplified test cases for safe template context processor

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_get_safe_user_data_success

```python
def test_get_safe_user_data_success(self)
```

Test successful user data extraction

**Type:** Instance method

#### test_get_safe_user_data_with_error

```python
def test_get_safe_user_data_with_error(self)
```

Test user data extraction with error

**Type:** Instance method

#### test_get_safe_platforms_data_success

```python
def test_get_safe_platforms_data_success(self)
```

Test successful platform data extraction

**Type:** Instance method

#### test_get_safe_platforms_data_with_default

```python
def test_get_safe_platforms_data_with_default(self)
```

Test platform data extraction with default platform

**Type:** Instance method

#### test_get_safe_platforms_data_fallback_query

```python
def test_get_safe_platforms_data_fallback_query(self)
```

Test platform data extraction with fallback query

**Type:** Instance method

#### test_platform_to_safe_dict_with_to_dict_method

```python
def test_platform_to_safe_dict_with_to_dict_method(self)
```

Test platform conversion using to_dict method

**Type:** Instance method

#### test_platform_to_safe_dict_manual_extraction

```python
def test_platform_to_safe_dict_manual_extraction(self)
```

Test platform conversion with manual extraction

**Type:** Instance method

#### test_platform_to_safe_dict_with_detached_error

```python
def test_platform_to_safe_dict_with_detached_error(self)
```

Test platform conversion handles DetachedInstanceError

**Type:** Instance method

#### test_platform_to_safe_dict_with_error

```python
def test_platform_to_safe_dict_with_error(self)
```

Test platform conversion handles general errors

**Type:** Instance method

#### test_query_platforms_fallback_success

```python
def test_query_platforms_fallback_success(self, mock_platform_connection)
```

Test successful fallback platform query

**Decorators:**
- `@patch('safe_template_context.PlatformConnection', create=True)`

**Type:** Instance method

#### test_query_platforms_fallback_no_user_id

```python
def test_query_platforms_fallback_no_user_id(self, mock_platform_connection)
```

Test fallback query when user ID is not available

**Decorators:**
- `@patch('safe_template_context.PlatformConnection', create=True)`

**Type:** Instance method

#### test_query_platforms_fallback_with_error

```python
def test_query_platforms_fallback_with_error(self, mock_platform_connection)
```

Test fallback query handles errors

**Decorators:**
- `@patch('safe_template_context.PlatformConnection', create=True)`

**Type:** Instance method

#### test_handle_detached_error_fallback

```python
def test_handle_detached_error_fallback(self)
```

Test detached error fallback handling

**Type:** Instance method

#### test_handle_detached_error_fallback_with_error

```python
def test_handle_detached_error_fallback_with_error(self)
```

Test detached error fallback handling when get_id fails

**Type:** Instance method

#### test_create_safe_template_context_processor

```python
def test_create_safe_template_context_processor(self)
```

Test template context processor registration

**Type:** Instance method

#### test_get_safe_platforms_data_empty_platforms

```python
def test_get_safe_platforms_data_empty_platforms(self)
```

Test platform data extraction with no platforms

**Type:** Instance method

#### test_get_safe_platforms_data_with_error

```python
def test_get_safe_platforms_data_with_error(self)
```

Test platform data extraction handles errors gracefully

**Type:** Instance method

#### test_platform_to_safe_dict_missing_to_dict

```python
def test_platform_to_safe_dict_missing_to_dict(self)
```

Test platform conversion when to_dict method is missing

**Type:** Instance method


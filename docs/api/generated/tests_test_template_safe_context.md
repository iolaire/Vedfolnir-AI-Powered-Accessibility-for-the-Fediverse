# tests.test_template_safe_context

Test Template Safe Context Implementation

This module tests that all templates use safe context objects instead of
direct current_user and current_platform access to prevent DetachedInstanceError.

Requirements: 5.1, 5.2, 5.3, 5.4

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_template_safe_context.py`

## Classes

### TestTemplateSafeContext

```python
class TestTemplateSafeContext(unittest.TestCase)
```

Test template safe context implementation

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_safe_template_context_with_authenticated_user

```python
def test_safe_template_context_with_authenticated_user(self)
```

Test safe template context with authenticated user

**Type:** Instance method

#### test_safe_template_context_with_unauthenticated_user

```python
def test_safe_template_context_with_unauthenticated_user(self)
```

Test safe template context with unauthenticated user

**Type:** Instance method

#### test_safe_template_context_with_detached_instance_error

```python
def test_safe_template_context_with_detached_instance_error(self)
```

Test safe template context handles DetachedInstanceError

**Type:** Instance method

#### test_template_context_processor_registration

```python
def test_template_context_processor_registration(self)
```

Test template context processor registration

**Type:** Instance method

#### test_base_template_uses_safe_context

```python
def test_base_template_uses_safe_context(self)
```

Test that base template uses safe context objects

**Type:** Instance method

#### test_platform_switching_uses_safe_context

```python
def test_platform_switching_uses_safe_context(self)
```

Test that platform switching uses safe context

**Type:** Instance method

#### test_admin_permission_check_uses_safe_context

```python
def test_admin_permission_check_uses_safe_context(self)
```

Test that admin permission checks use safe context

**Type:** Instance method

#### test_template_error_handling

```python
def test_template_error_handling(self)
```

Test template error handling when template_error is True

**Type:** Instance method

#### test_platform_to_safe_dict_conversion

```python
def test_platform_to_safe_dict_conversion(self)
```

Test platform to safe dictionary conversion

**Type:** Instance method

#### test_safe_user_data_extraction

```python
def test_safe_user_data_extraction(self)
```

Test safe user data extraction

**Type:** Instance method

#### test_fallback_platform_query

```python
def test_fallback_platform_query(self)
```

Test fallback platform query when relationship access fails

**Type:** Instance method

### TestTemplateIntegration

```python
class TestTemplateIntegration(unittest.TestCase)
```

Test template integration with safe context

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_dashboard_template_integration

```python
def test_dashboard_template_integration(self)
```

Test dashboard template uses safe context

**Type:** Instance method

#### test_platform_management_template_integration

```python
def test_platform_management_template_integration(self)
```

Test platform management template uses safe context

**Type:** Instance method


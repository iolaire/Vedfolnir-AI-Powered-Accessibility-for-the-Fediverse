# tests.test_platform_adapter_factory

Tests for PlatformAdapterFactory and platform adapter creation.

This module tests the platform adapter factory to ensure it correctly creates
adapters for different platforms and handles error scenarios properly.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_platform_adapter_factory.py`

## Classes

### MockConfig

```python
class MockConfig
```

Mock configuration for testing

**Decorators:**
- `@dataclass`

### TestPlatformAdapterFactory

```python
class TestPlatformAdapterFactory(unittest.TestCase)
```

Test PlatformAdapterFactory functionality

**Methods:**

#### test_create_adapter_explicit_pixelfed

```python
def test_create_adapter_explicit_pixelfed(self)
```

Test creating Pixelfed adapter with explicit configuration

**Type:** Instance method

#### test_create_adapter_explicit_mastodon

```python
def test_create_adapter_explicit_mastodon(self)
```

Test creating Mastodon adapter with explicit configuration

**Type:** Instance method

#### test_create_adapter_explicit_pleroma

```python
def test_create_adapter_explicit_pleroma(self)
```

Test creating Pleroma adapter with explicit configuration

**Type:** Instance method

#### test_create_adapter_unsupported_platform

```python
def test_create_adapter_unsupported_platform(self)
```

Test creating adapter with unsupported platform type

**Type:** Instance method

#### test_create_adapter_missing_instance_url

```python
def test_create_adapter_missing_instance_url(self)
```

Test creating adapter with missing instance URL

**Type:** Instance method

#### test_create_adapter_no_instance_url_attribute

```python
def test_create_adapter_no_instance_url_attribute(self)
```

Test creating adapter with no instance_url attribute

**Type:** Instance method

#### test_create_adapter_legacy_platform_type

```python
def test_create_adapter_legacy_platform_type(self)
```

Test creating adapter with legacy platform_type attribute

**Type:** Instance method

#### test_create_adapter_auto_detection_pixelfed

```python
def test_create_adapter_auto_detection_pixelfed(self)
```

Test auto-detection of Pixelfed platform

**Type:** Instance method

#### test_create_adapter_auto_detection_mastodon

```python
def test_create_adapter_auto_detection_mastodon(self)
```

Test auto-detection of Mastodon platform

**Type:** Instance method

#### test_create_adapter_auto_detection_pleroma

```python
def test_create_adapter_auto_detection_pleroma(self)
```

Test auto-detection of Pleroma platform

**Type:** Instance method

#### test_create_adapter_auto_detection_failure

```python
def test_create_adapter_auto_detection_failure(self)
```

Test auto-detection failure when no platform matches

**Type:** Instance method

#### test_create_adapter_detection_error_handling

```python
def test_create_adapter_detection_error_handling(self)
```

Test handling of errors during platform detection

**Type:** Instance method

#### test_create_adapter_case_insensitive_platform_type

```python
def test_create_adapter_case_insensitive_platform_type(self)
```

Test that platform type matching is case insensitive

**Type:** Instance method

#### test_create_adapter_whitespace_platform_type

```python
def test_create_adapter_whitespace_platform_type(self)
```

Test handling of platform type with whitespace

**Type:** Instance method

### TestPlatformAdapterRegistration

```python
class TestPlatformAdapterRegistration(unittest.TestCase)
```

Test platform adapter registration functionality

**Methods:**

#### test_register_adapter_success

```python
def test_register_adapter_success(self)
```

Test successful adapter registration

**Type:** Instance method

#### test_register_adapter_invalid_class

```python
def test_register_adapter_invalid_class(self)
```

Test registering adapter with invalid class

**Type:** Instance method

#### test_register_adapter_overwrite_existing

```python
def test_register_adapter_overwrite_existing(self)
```

Test overwriting existing adapter registration

**Type:** Instance method

### TestPlatformDetection

```python
class TestPlatformDetection(unittest.TestCase)
```

Test platform detection methods

**Methods:**

#### test_pixelfed_detection_known_instances

```python
def test_pixelfed_detection_known_instances(self)
```

Test Pixelfed detection with known instances

**Type:** Instance method

#### test_pixelfed_detection_pixelfed_in_domain

```python
def test_pixelfed_detection_pixelfed_in_domain(self)
```

Test Pixelfed detection with 'pixelfed' in domain

**Type:** Instance method

#### test_pixelfed_detection_false_cases

```python
def test_pixelfed_detection_false_cases(self)
```

Test Pixelfed detection returns False for non-Pixelfed instances

**Type:** Instance method

#### test_mastodon_detection_known_instances

```python
def test_mastodon_detection_known_instances(self)
```

Test Mastodon detection with known instances

**Type:** Instance method

#### test_mastodon_detection_mastodon_in_domain

```python
def test_mastodon_detection_mastodon_in_domain(self)
```

Test Mastodon detection with 'mastodon' or 'mstdn' in domain

**Type:** Instance method

#### test_mastodon_detection_false_cases

```python
def test_mastodon_detection_false_cases(self)
```

Test Mastodon detection returns False for non-Mastodon instances

**Type:** Instance method

#### test_pleroma_detection_known_instances

```python
def test_pleroma_detection_known_instances(self)
```

Test Pleroma detection with known instances

**Type:** Instance method

#### test_pleroma_detection_pleroma_in_domain

```python
def test_pleroma_detection_pleroma_in_domain(self)
```

Test Pleroma detection with 'pleroma' in domain

**Type:** Instance method

#### test_pleroma_detection_false_cases

```python
def test_pleroma_detection_false_cases(self)
```

Test Pleroma detection returns False for non-Pleroma instances

**Type:** Instance method

#### test_detection_error_handling

```python
def test_detection_error_handling(self)
```

Test platform detection error handling

**Type:** Instance method


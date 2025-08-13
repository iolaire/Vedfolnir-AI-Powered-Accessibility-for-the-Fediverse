# tests.test_configuration_validation_comprehensive

Comprehensive configuration validation tests.

This module tests configuration validation for both platforms,
backward compatibility with existing Pixelfed configs,
and error messages for invalid configurations.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_configuration_validation_comprehensive.py`

## Classes

### TestActivityPubConfigValidation

```python
class TestActivityPubConfigValidation(unittest.TestCase)
```

Test ActivityPubConfig validation for both platforms

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test fixtures

**Type:** Instance method

#### test_pixelfed_config_validation_success

```python
def test_pixelfed_config_validation_success(self)
```

Test successful Pixelfed configuration validation

**Type:** Instance method

#### test_mastodon_config_validation_success

```python
def test_mastodon_config_validation_success(self)
```

Test successful Mastodon configuration validation

**Type:** Instance method

#### test_config_validation_missing_instance_url

```python
def test_config_validation_missing_instance_url(self)
```

Test configuration validation with missing instance URL

**Type:** Instance method

#### test_config_validation_missing_access_token

```python
def test_config_validation_missing_access_token(self)
```

Test configuration validation with missing access token

**Type:** Instance method

#### test_mastodon_config_validation_missing_client_key

```python
def test_mastodon_config_validation_missing_client_key(self)
```

Test Mastodon configuration validation with missing client key

**Type:** Instance method

#### test_mastodon_config_validation_missing_client_secret

```python
def test_mastodon_config_validation_missing_client_secret(self)
```

Test Mastodon configuration validation with missing client secret

**Type:** Instance method

#### test_config_validation_unsupported_api_type

```python
def test_config_validation_unsupported_api_type(self)
```

Test configuration validation with unsupported API type falls back to pixelfed

**Type:** Instance method

#### test_config_validation_empty_values

```python
def test_config_validation_empty_values(self)
```

Test configuration validation with empty values

**Type:** Instance method

#### test_config_validation_whitespace_values

```python
def test_config_validation_whitespace_values(self)
```

Test configuration validation with whitespace-only values

**Type:** Instance method

### TestBackwardCompatibility

```python
class TestBackwardCompatibility(unittest.TestCase)
```

Test backward compatibility with existing Pixelfed configurations

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test fixtures

**Type:** Instance method

#### test_backward_compatibility_no_api_type

```python
def test_backward_compatibility_no_api_type(self)
```

Test backward compatibility when no API type is specified

**Type:** Instance method

#### test_backward_compatibility_legacy_platform_type

```python
def test_backward_compatibility_legacy_platform_type(self)
```

Test backward compatibility with legacy ACTIVITYPUB_PLATFORM_TYPE

**Type:** Instance method

#### test_backward_compatibility_legacy_pixelfed_api_flag

```python
def test_backward_compatibility_legacy_pixelfed_api_flag(self)
```

Test backward compatibility with legacy PIXELFED_API flag

**Type:** Instance method

#### test_backward_compatibility_api_type_precedence

```python
def test_backward_compatibility_api_type_precedence(self)
```

Test that ACTIVITYPUB_API_TYPE takes precedence over legacy settings

**Type:** Instance method

#### test_backward_compatibility_existing_pixelfed_config

```python
def test_backward_compatibility_existing_pixelfed_config(self)
```

Test that existing Pixelfed configurations continue to work

**Type:** Instance method

#### test_backward_compatibility_case_insensitive_api_type

```python
def test_backward_compatibility_case_insensitive_api_type(self)
```

Test that API type is case insensitive for backward compatibility

**Type:** Instance method

### TestConfigurationErrorMessages

```python
class TestConfigurationErrorMessages(unittest.TestCase)
```

Test error messages for invalid configurations

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test fixtures

**Type:** Instance method

#### test_clear_error_message_missing_instance_url

```python
def test_clear_error_message_missing_instance_url(self)
```

Test clear error message for missing instance URL

**Type:** Instance method

#### test_clear_error_message_missing_access_token

```python
def test_clear_error_message_missing_access_token(self)
```

Test clear error message for missing access token

**Type:** Instance method

#### test_clear_error_message_mastodon_missing_client_key

```python
def test_clear_error_message_mastodon_missing_client_key(self)
```

Test clear error message for missing Mastodon client key

**Type:** Instance method

#### test_clear_error_message_mastodon_missing_client_secret

```python
def test_clear_error_message_mastodon_missing_client_secret(self)
```

Test clear error message for missing Mastodon client secret

**Type:** Instance method

#### test_clear_error_message_unsupported_platform

```python
def test_clear_error_message_unsupported_platform(self)
```

Test that unsupported platform types fall back to pixelfed

**Type:** Instance method

#### test_helpful_error_message_for_common_mistakes

```python
def test_helpful_error_message_for_common_mistakes(self)
```

Test helpful error messages for common configuration mistakes

**Type:** Instance method

### TestPlatformAdapterFactoryConfigValidation

```python
class TestPlatformAdapterFactoryConfigValidation(unittest.TestCase)
```

Test platform adapter factory configuration validation

**Methods:**

#### test_platform_adapter_factory_with_valid_pixelfed_config

```python
def test_platform_adapter_factory_with_valid_pixelfed_config(self)
```

Test platform adapter factory with valid Pixelfed configuration

**Type:** Instance method

#### test_platform_adapter_factory_with_valid_mastodon_config

```python
def test_platform_adapter_factory_with_valid_mastodon_config(self)
```

Test platform adapter factory with valid Mastodon configuration

**Type:** Instance method

#### test_platform_adapter_factory_with_invalid_config

```python
def test_platform_adapter_factory_with_invalid_config(self)
```

Test platform adapter factory with invalid configuration

**Type:** Instance method

#### test_platform_adapter_factory_missing_config_attributes

```python
def test_platform_adapter_factory_missing_config_attributes(self)
```

Test platform adapter factory with missing configuration attributes

**Type:** Instance method

### TestConfigurationIntegration

```python
class TestConfigurationIntegration(unittest.TestCase)
```

Test configuration integration with the overall system

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test fixtures

**Type:** Instance method

#### test_end_to_end_pixelfed_configuration

```python
def test_end_to_end_pixelfed_configuration(self)
```

Test end-to-end Pixelfed configuration validation

**Type:** Instance method

#### test_end_to_end_mastodon_configuration

```python
def test_end_to_end_mastodon_configuration(self)
```

Test end-to-end Mastodon configuration validation

**Type:** Instance method

#### test_configuration_validation_chain

```python
def test_configuration_validation_chain(self)
```

Test that configuration validation works through the entire chain

**Type:** Instance method

#### test_configuration_with_optional_fields

```python
def test_configuration_with_optional_fields(self)
```

Test configuration with optional fields

**Type:** Instance method

#### test_configuration_environment_variable_precedence

```python
def test_configuration_environment_variable_precedence(self)
```

Test that environment variables take precedence over defaults

**Type:** Instance method


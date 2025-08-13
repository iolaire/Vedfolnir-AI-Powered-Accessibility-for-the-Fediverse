# tests.test_config_multi_platform

Unit tests for multi-platform configuration support.

Tests configuration parsing, validation, and backward compatibility
for both Pixelfed and Mastodon platforms.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_config_multi_platform.py`

## Classes

### TestActivityPubConfigMultiPlatform

```python
class TestActivityPubConfigMultiPlatform(unittest.TestCase)
```

Test ActivityPub configuration for multi-platform support

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_pixelfed_configuration_valid

```python
def test_pixelfed_configuration_valid(self)
```

Test valid Pixelfed configuration

**Type:** Instance method

#### test_mastodon_configuration_valid

```python
def test_mastodon_configuration_valid(self)
```

Test valid Mastodon configuration

**Type:** Instance method

#### test_default_behavior_no_api_type

```python
def test_default_behavior_no_api_type(self)
```

Test default behavior when ACTIVITYPUB_API_TYPE is not set (should default to pixelfed)

**Type:** Instance method

#### test_mastodon_missing_client_key_error

```python
def test_mastodon_missing_client_key_error(self)
```

Test configuration validation error for missing Mastodon client key

**Type:** Instance method

#### test_mastodon_missing_client_secret_error

```python
def test_mastodon_missing_client_secret_error(self)
```

Test configuration validation error for missing Mastodon client secret

**Type:** Instance method

#### test_pixelfed_missing_credentials_error

```python
def test_pixelfed_missing_credentials_error(self)
```

Test configuration validation error for missing Pixelfed credentials

**Type:** Instance method

#### test_missing_instance_url_error

```python
def test_missing_instance_url_error(self)
```

Test configuration validation error for missing instance URL

**Type:** Instance method

#### test_backward_compatibility_pixelfed_api_flag

```python
def test_backward_compatibility_pixelfed_api_flag(self)
```

Test backward compatibility with existing PIXELFED_API flag

**Type:** Instance method

#### test_backward_compatibility_platform_type

```python
def test_backward_compatibility_platform_type(self)
```

Test backward compatibility with ACTIVITYPUB_PLATFORM_TYPE

**Type:** Instance method

#### test_environment_variable_precedence

```python
def test_environment_variable_precedence(self)
```

Test that ACTIVITYPUB_API_TYPE takes precedence over legacy variables

**Type:** Instance method

#### test_configuration_object_creation_pixelfed

```python
def test_configuration_object_creation_pixelfed(self)
```

Test configuration object creation for Pixelfed platform

**Type:** Instance method

#### test_configuration_object_creation_mastodon

```python
def test_configuration_object_creation_mastodon(self)
```

Test configuration object creation for Mastodon platform

**Type:** Instance method

#### test_unsupported_api_type_fallback

```python
def test_unsupported_api_type_fallback(self)
```

Test that unsupported API types fall back to pixelfed

**Type:** Instance method

#### test_case_insensitive_api_type

```python
def test_case_insensitive_api_type(self)
```

Test that API type is case insensitive

**Type:** Instance method

### TestConfigIntegration

```python
class TestConfigIntegration(unittest.TestCase)
```

Integration tests for configuration loading in different deployment scenarios

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_full_config_pixelfed_deployment

```python
def test_full_config_pixelfed_deployment(self)
```

Test complete configuration loading for Pixelfed deployment

**Type:** Instance method

#### test_full_config_mastodon_deployment

```python
def test_full_config_mastodon_deployment(self)
```

Test complete configuration loading for Mastodon deployment

**Type:** Instance method

#### test_legacy_pixelfed_deployment_compatibility

```python
def test_legacy_pixelfed_deployment_compatibility(self)
```

Test that legacy Pixelfed deployments continue to work

**Type:** Instance method

#### test_migration_from_platform_type_to_api_type

```python
def test_migration_from_platform_type_to_api_type(self)
```

Test migration from ACTIVITYPUB_PLATFORM_TYPE to ACTIVITYPUB_API_TYPE

**Type:** Instance method

#### test_minimal_pixelfed_configuration

```python
def test_minimal_pixelfed_configuration(self)
```

Test minimal required configuration for Pixelfed

**Type:** Instance method

#### test_invalid_mastodon_configuration_raises_error

```python
def test_invalid_mastodon_configuration_raises_error(self)
```

Test that invalid Mastodon configuration raises appropriate error

**Type:** Instance method


# tests.test_configuration_examples

Test suite for configuration example files.

This test suite validates that all example configuration files:
1. Contain all required variables for their respective platforms
2. Are syntactically valid
3. Can be loaded by the application
4. Have properly formatted and realistic values
5. Don't contain real credentials
6. Have appropriate defaults for optional variables

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_configuration_examples.py`

## Classes

### TestConfigurationExamples

```python
class TestConfigurationExamples(unittest.TestCase)
```

Test configuration example files

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_example_files_exist

```python
def test_example_files_exist(self)
```

Test that all example configuration files exist

**Type:** Instance method

#### test_mastodon_example_contains_required_variables

```python
def test_mastodon_example_contains_required_variables(self)
```

Test that .env.example.mastodon contains all required Mastodon variables

**Type:** Instance method

#### test_pixelfed_example_contains_required_variables

```python
def test_pixelfed_example_contains_required_variables(self)
```

Test that .env.example.pixelfed contains all required Pixelfed variables

**Type:** Instance method

#### test_example_configurations_are_syntactically_valid

```python
def test_example_configurations_are_syntactically_valid(self)
```

Test that example configurations are syntactically valid

**Type:** Instance method

#### test_example_configurations_can_be_loaded_by_application

```python
def test_example_configurations_can_be_loaded_by_application(self)
```

Test that example configurations can be loaded by the application

**Type:** Instance method

#### test_example_values_are_properly_formatted_and_realistic

```python
def test_example_values_are_properly_formatted_and_realistic(self)
```

Test that all example values are properly formatted and realistic

**Type:** Instance method

#### test_example_configurations_dont_contain_real_credentials

```python
def test_example_configurations_dont_contain_real_credentials(self)
```

Test that example configurations don't contain real credentials

**Type:** Instance method

#### test_missing_optional_variables_have_appropriate_defaults

```python
def test_missing_optional_variables_have_appropriate_defaults(self)
```

Test that missing optional variables have appropriate defaults

**Type:** Instance method

#### test_configuration_validation_completeness

```python
def test_configuration_validation_completeness(self)
```

Test that all configuration variables in examples are documented and used

**Type:** Instance method

#### test_platform_specific_variables_are_correctly_separated

```python
def test_platform_specific_variables_are_correctly_separated(self)
```

Test that platform-specific variables are only in appropriate example files

**Type:** Instance method

#### test_rate_limiting_configuration_is_platform_appropriate

```python
def test_rate_limiting_configuration_is_platform_appropriate(self)
```

Test that rate limiting configuration is appropriate for each platform

**Type:** Instance method


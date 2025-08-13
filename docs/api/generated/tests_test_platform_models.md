# tests.test_platform_models

Unit tests for platform-aware models

Tests all platform-aware model functionality including:
- PlatformConnection model operations
- User model platform methods
- Model relationships and constraints
- Credential encryption/decryption

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_platform_models.py`

## Classes

### TestPlatformConnectionModel

```python
class TestPlatformConnectionModel(PlatformTestCase)
```

Test PlatformConnection model functionality

**Methods:**

#### test_platform_connection_creation

```python
def test_platform_connection_creation(self)
```

Test creating platform connections

**Type:** Instance method

#### test_credential_encryption

```python
def test_credential_encryption(self)
```

Test credential encryption and decryption

**Type:** Instance method

#### test_client_credentials_encryption

```python
def test_client_credentials_encryption(self)
```

Test client key and secret encryption

**Type:** Instance method

#### test_to_activitypub_config

```python
def test_to_activitypub_config(self)
```

Test conversion to ActivityPub config

**Type:** Instance method

#### test_unique_constraints

```python
def test_unique_constraints(self)
```

Test unique constraints on platform connections

**Type:** Instance method

#### test_platform_validation

```python
def test_platform_validation(self)
```

Test platform type validation

**Type:** Instance method

### TestUserModelPlatformMethods

```python
class TestUserModelPlatformMethods(PlatformTestCase)
```

Test User model platform-related methods

**Methods:**

#### test_get_active_platforms

```python
def test_get_active_platforms(self)
```

Test getting user's active platforms

**Type:** Instance method

#### test_get_default_platform

```python
def test_get_default_platform(self)
```

Test getting user's default platform

**Type:** Instance method

#### test_get_platform_by_type

```python
def test_get_platform_by_type(self)
```

Test getting platform by type

**Type:** Instance method

#### test_get_platform_by_name

```python
def test_get_platform_by_name(self)
```

Test getting platform by name

**Type:** Instance method

#### test_set_default_platform

```python
def test_set_default_platform(self)
```

Test setting default platform

**Type:** Instance method

#### test_has_platform_access

```python
def test_has_platform_access(self)
```

Test platform access validation

**Type:** Instance method

### TestPlatformAwareModels

```python
class TestPlatformAwareModels(PlatformTestCase)
```

Test platform awareness in Post and Image models

**Methods:**

#### test_post_platform_consistency

```python
def test_post_platform_consistency(self)
```

Test post platform consistency validation

**Type:** Instance method

#### test_image_platform_consistency

```python
def test_image_platform_consistency(self)
```

Test image platform consistency validation

**Type:** Instance method

#### test_platform_relationships

```python
def test_platform_relationships(self)
```

Test platform relationships work correctly

**Type:** Instance method

### TestUserSessionModel

```python
class TestUserSessionModel(PlatformTestCase)
```

Test UserSession model functionality

**Methods:**

#### test_user_session_creation

```python
def test_user_session_creation(self)
```

Test creating user sessions

**Type:** Instance method

#### test_session_relationships

```python
def test_session_relationships(self)
```

Test session relationships

**Type:** Instance method

#### test_session_unique_constraint

```python
def test_session_unique_constraint(self)
```

Test session ID unique constraint

**Type:** Instance method

### TestModelValidation

```python
class TestModelValidation(PlatformTestCase)
```

Test model validation and constraints

**Methods:**

#### test_required_fields

```python
def test_required_fields(self)
```

Test required field validation

**Type:** Instance method

#### test_field_length_constraints

```python
def test_field_length_constraints(self)
```

Test field length constraints

**Type:** Instance method

#### test_boolean_defaults

```python
def test_boolean_defaults(self)
```

Test boolean field defaults

**Type:** Instance method


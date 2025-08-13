# tests.test_mastodon_authentication

Tests for Mastodon authentication functionality.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_mastodon_authentication.py`

## Classes

### MockConfig

```python
class MockConfig
```

Mock configuration for testing

**Decorators:**
- `@dataclass`

### TestMastodonAuthentication

```python
class TestMastodonAuthentication(unittest.TestCase)
```

Test cases for Mastodon authentication

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_config_validation_success

```python
def test_config_validation_success(self)
```

Test successful configuration validation

**Type:** Instance method

#### test_config_validation_missing_client_key

```python
def test_config_validation_missing_client_key(self)
```

Test configuration validation with missing client key

**Type:** Instance method

#### test_config_validation_missing_client_secret

```python
def test_config_validation_missing_client_secret(self)
```

Test configuration validation with missing client secret

**Type:** Instance method

#### test_config_validation_missing_access_token

```python
def test_config_validation_missing_access_token(self)
```

Test configuration validation with missing access token

**Type:** Instance method

#### test_config_validation_missing_instance_url

```python
def test_config_validation_missing_instance_url(self)
```

Test configuration validation with missing instance URL

**Type:** Instance method

#### test_authenticate_success

```python
async def test_authenticate_success(self)
```

Test successful authentication

**Type:** Instance method

#### test_authenticate_invalid_token

```python
async def test_authenticate_invalid_token(self)
```

Test authentication with invalid access token

**Type:** Instance method

#### test_authenticate_forbidden_token

```python
async def test_authenticate_forbidden_token(self)
```

Test authentication with token lacking permissions

**Type:** Instance method

#### test_authenticate_network_error

```python
async def test_authenticate_network_error(self)
```

Test authentication with network error

**Type:** Instance method

#### test_authenticate_timeout_error

```python
async def test_authenticate_timeout_error(self)
```

Test authentication with timeout error

**Type:** Instance method

#### test_authenticate_missing_access_token

```python
async def test_authenticate_missing_access_token(self)
```

Test authentication with missing access token

**Type:** Instance method

#### test_validate_token_success

```python
async def test_validate_token_success(self)
```

Test successful token validation

**Type:** Instance method

#### test_validate_token_invalid

```python
async def test_validate_token_invalid(self)
```

Test token validation with invalid token

**Type:** Instance method

#### test_validate_token_no_headers

```python
async def test_validate_token_no_headers(self)
```

Test token validation with no auth headers

**Type:** Instance method

#### test_get_auth_headers_success

```python
def test_get_auth_headers_success(self)
```

Test getting auth headers when authenticated

**Type:** Instance method

#### test_get_auth_headers_not_authenticated

```python
def test_get_auth_headers_not_authenticated(self)
```

Test getting auth headers when not authenticated

**Type:** Instance method

#### test_refresh_token_if_needed_valid

```python
async def test_refresh_token_if_needed_valid(self)
```

Test token refresh when token is still valid

**Type:** Instance method

#### test_refresh_token_if_needed_invalid

```python
async def test_refresh_token_if_needed_invalid(self)
```

Test token refresh when token is invalid

**Type:** Instance method

#### test_authenticate_with_different_mastodon_instances

```python
async def test_authenticate_with_different_mastodon_instances(self)
```

Test authentication with different Mastodon instance configurations

**Type:** Instance method

#### test_authenticate_reuse_valid_token

```python
async def test_authenticate_reuse_valid_token(self)
```

Test that authentication reuses valid existing token

**Type:** Instance method

### TestMastodonAuthenticationSync

```python
class TestMastodonAuthenticationSync(TestMastodonAuthentication)
```

Synchronous wrapper for async tests

**Methods:**

#### test_authenticate_success_sync

```python
def test_authenticate_success_sync(self)
```

**Type:** Instance method

#### test_authenticate_invalid_token_sync

```python
def test_authenticate_invalid_token_sync(self)
```

**Type:** Instance method

#### test_authenticate_forbidden_token_sync

```python
def test_authenticate_forbidden_token_sync(self)
```

**Type:** Instance method

#### test_authenticate_network_error_sync

```python
def test_authenticate_network_error_sync(self)
```

**Type:** Instance method

#### test_authenticate_timeout_error_sync

```python
def test_authenticate_timeout_error_sync(self)
```

**Type:** Instance method

#### test_authenticate_missing_access_token_sync

```python
def test_authenticate_missing_access_token_sync(self)
```

**Type:** Instance method

#### test_validate_token_success_sync

```python
def test_validate_token_success_sync(self)
```

**Type:** Instance method

#### test_validate_token_invalid_sync

```python
def test_validate_token_invalid_sync(self)
```

**Type:** Instance method

#### test_validate_token_no_headers_sync

```python
def test_validate_token_no_headers_sync(self)
```

**Type:** Instance method

#### test_refresh_token_if_needed_valid_sync

```python
def test_refresh_token_if_needed_valid_sync(self)
```

**Type:** Instance method

#### test_refresh_token_if_needed_invalid_sync

```python
def test_refresh_token_if_needed_invalid_sync(self)
```

**Type:** Instance method

#### test_authenticate_with_different_mastodon_instances_sync

```python
def test_authenticate_with_different_mastodon_instances_sync(self)
```

**Type:** Instance method

#### test_authenticate_reuse_valid_token_sync

```python
def test_authenticate_reuse_valid_token_sync(self)
```

**Type:** Instance method

## Functions

### run_async_test

```python
def run_async_test(coro)
```

Helper function to run async tests


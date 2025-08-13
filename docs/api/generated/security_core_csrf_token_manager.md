# security.core.csrf_token_manager

CSRF Token Manager

Centralized CSRF token generation, validation, and management system.
Provides secure token handling with entropy validation, session binding,
and expiration management.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/core/csrf_token_manager.py`

## Classes

### CSRFTokenManager

```python
class CSRFTokenManager
```

Centralized CSRF token management system

**Methods:**

#### __init__

```python
def __init__(self, secret_key: Optional[str], token_lifetime: int)
```

Initialize CSRF token manager

Args:
    secret_key: Secret key for token signing (uses Flask secret key if None)
    token_lifetime: Token lifetime in seconds (default: 1 hour)

**Type:** Instance method

#### generate_token

```python
def generate_token(self, session_id: Optional[str]) -> str
```

Generate a secure CSRF token

Args:
    session_id: Session identifier (uses current session if None)
    
Returns:
    Secure CSRF token string

**Type:** Instance method

#### validate_token

```python
def validate_token(self, token: str, session_id: Optional[str]) -> bool
```

Validate a CSRF token

Args:
    token: CSRF token to validate
    session_id: Session identifier (uses current session if None)
    
Returns:
    True if token is valid, False otherwise

**Type:** Instance method

#### is_token_expired

```python
def is_token_expired(self, token: str) -> bool
```

Check if a CSRF token is expired

Args:
    token: CSRF token to check
    
Returns:
    True if token is expired, False otherwise

**Type:** Instance method

#### is_token_expired_by_timestamp

```python
def is_token_expired_by_timestamp(self, timestamp: int) -> bool
```

Check if a timestamp is expired

Args:
    timestamp: Unix timestamp to check
    
Returns:
    True if timestamp is expired, False otherwise

**Type:** Instance method

#### refresh_token

```python
def refresh_token(self, session_id: Optional[str]) -> str
```

Generate a new CSRF token (refresh)

Args:
    session_id: Session identifier (uses current session if None)
    
Returns:
    New CSRF token

**Type:** Instance method

#### extract_token_info

```python
def extract_token_info(self, token: str) -> Dict[str, Any]
```

Extract information from a CSRF token for debugging

Args:
    token: CSRF token to analyze
    
Returns:
    Dictionary with token information

**Type:** Instance method

#### _get_current_session_id

```python
def _get_current_session_id(self) -> str
```

Get current session ID

Returns:
    Current session ID

**Type:** Instance method

#### _generate_request_based_id

```python
def _generate_request_based_id(self) -> str
```

Generate a request-based session ID as fallback

Returns:
    Request-based session identifier

**Type:** Instance method

#### _sign_token

```python
def _sign_token(self, payload: str) -> str
```

Sign a token payload

Args:
    payload: Token payload to sign
    
Returns:
    Token signature

**Type:** Instance method

#### _verify_token_signature

```python
def _verify_token_signature(self, token: str) -> bool
```

Verify token signature

Args:
    token: Token to verify
    
Returns:
    True if signature is valid, False otherwise

**Type:** Instance method

#### _get_secret_key

```python
def _get_secret_key(self) -> str
```

Get secret key for token signing

Returns:
    Secret key string

**Type:** Instance method

#### _validate_token_entropy

```python
def _validate_token_entropy(self, random_bytes: bytes) -> bool
```

Validate that token has sufficient entropy

Args:
    random_bytes: Random bytes from token
    
Returns:
    True if entropy is sufficient, False otherwise

**Type:** Instance method

### CSRFTokenError

```python
class CSRFTokenError(Exception)
```

Exception raised for CSRF token errors

### CSRFValidationContext

```python
class CSRFValidationContext
```

Context information for CSRF validation

**Methods:**

#### __init__

```python
def __init__(self, request_method: str, endpoint: str, user_id: Optional[int])
```

Initialize validation context

Args:
    request_method: HTTP request method
    endpoint: Request endpoint
    user_id: User ID if available

**Type:** Instance method

#### _get_session_id

```python
def _get_session_id(self) -> str
```

Get session ID for context

**Type:** Instance method

#### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

Convert context to dictionary

Returns:
    Dictionary representation of context

**Type:** Instance method

## Functions

### get_csrf_token_manager

```python
def get_csrf_token_manager() -> CSRFTokenManager
```

Get the global CSRF token manager instance

Returns:
    CSRFTokenManager instance

### initialize_csrf_token_manager

```python
def initialize_csrf_token_manager(app) -> CSRFTokenManager
```

Initialize CSRF token manager for Flask app

Args:
    app: Flask application instance
    
Returns:
    Initialized CSRFTokenManager


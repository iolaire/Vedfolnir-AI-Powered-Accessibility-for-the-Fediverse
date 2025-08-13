# security.core.security_middleware

Security middleware for Flask application

Implements comprehensive security headers, input validation, and protection mechanisms.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/core/security_middleware.py`

## Classes

### SecurityMiddleware

```python
class SecurityMiddleware
```

Comprehensive security middleware for Flask applications

**Methods:**

#### __init__

```python
def __init__(self, app)
```

**Type:** Instance method

#### init_app

```python
def init_app(self, app)
```

Initialize security middleware with Flask app

**Type:** Instance method

#### before_request

```python
def before_request(self)
```

Security checks before each request

**Type:** Instance method

#### after_request

```python
def after_request(self, response)
```

Add security headers after each request

**Type:** Instance method

#### _check_rate_limit

```python
def _check_rate_limit(self)
```

Check rate limiting for the current request

**Type:** Instance method

#### _validate_request_data

```python
def _validate_request_data(self)
```

Validate request data for security issues

**Type:** Instance method

#### _validate_json_data

```python
def _validate_json_data(self, data, max_depth, current_depth)
```

Validate JSON data recursively

**Type:** Instance method

#### _validate_form_data

```python
def _validate_form_data(self, form_data)
```

Validate form data

**Type:** Instance method

#### _validate_query_params

```python
def _validate_query_params(self, query_params)
```

Validate query parameters

**Type:** Instance method

#### _validate_string_content

```python
def _validate_string_content(self, content)
```

Validate string content for malicious patterns

**Type:** Instance method

#### _check_suspicious_patterns

```python
def _check_suspicious_patterns(self)
```

Check for suspicious request patterns

**Type:** Instance method

#### _add_security_headers

```python
def _add_security_headers(self, response)
```

Add comprehensive security headers

**Type:** Instance method

#### _log_security_event

```python
def _log_security_event(self, response)
```

Log security-relevant events

**Type:** Instance method

## Functions

### require_https

```python
def require_https(f)
```

Decorator to require HTTPS for sensitive endpoints

### validate_csrf_token

```python
def validate_csrf_token(f)
```

Decorator to validate CSRF tokens

### sanitize_filename

```python
def sanitize_filename(filename)
```

Sanitize filename for safe storage

### generate_secure_token

```python
def generate_secure_token(length)
```

Generate cryptographically secure random token

### hash_password_secure

```python
def hash_password_secure(password, salt)
```

Securely hash password with salt

### verify_password_secure

```python
def verify_password_secure(password, hashed)
```

Verify password against secure hash

### validate_input_length

```python
def validate_input_length(max_length)
```

Decorator to validate input length

### rate_limit

```python
def rate_limit(limit, window_seconds, requests_per_minute)
```

Decorator to add rate limiting to endpoints


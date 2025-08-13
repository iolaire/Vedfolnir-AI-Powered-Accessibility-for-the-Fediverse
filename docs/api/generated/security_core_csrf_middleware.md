# security.core.csrf_middleware

CSRF Validation Middleware

Flask middleware for consistent CSRF validation across all routes
with automatic token generation and exemption handling.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/core/csrf_middleware.py`

## Classes

### CSRFMiddleware

```python
class CSRFMiddleware
```

CSRF validation middleware for Flask applications

**Methods:**

#### __init__

```python
def __init__(self, app)
```

Initialize CSRF middleware

Args:
    app: Flask application instance (optional)

**Type:** Instance method

#### init_app

```python
def init_app(self, app)
```

Initialize middleware with Flask app

Args:
    app: Flask application instance

**Type:** Instance method

#### before_request

```python
def before_request(self)
```

Process request before route handler

**Type:** Instance method

#### after_request

```python
def after_request(self, response)
```

Process response after route handler

Args:
    response: Flask response object
    
Returns:
    Modified response object

**Type:** Instance method

#### _is_request_exempt

```python
def _is_request_exempt(self) -> bool
```

Check if current request is exempt from CSRF validation

Returns:
    True if request is exempt, False otherwise

**Type:** Instance method

#### _validate_csrf_token

```python
def _validate_csrf_token(self)
```

Validate CSRF token for current request

**Type:** Instance method

#### exempt_endpoint

```python
def exempt_endpoint(self, endpoint: str)
```

Add endpoint to CSRF exemption list

Args:
    endpoint: Endpoint name to exempt

**Type:** Instance method

#### exempt_path

```python
def exempt_path(self, path: str)
```

Add path to CSRF exemption list

Args:
    path: Path pattern to exempt

**Type:** Instance method

#### exempt_method

```python
def exempt_method(self, method: str)
```

Add HTTP method to CSRF exemption list

Args:
    method: HTTP method to exempt

**Type:** Instance method

#### add_validation_callback

```python
def add_validation_callback(self, callback: Callable[[any], bool])
```

Add custom validation callback

Args:
    callback: Function that takes request and returns bool (True = exempt)

**Type:** Instance method

#### remove_exemption

```python
def remove_exemption(self, endpoint: Optional[str], path: Optional[str], method: Optional[str])
```

Remove exemption from CSRF validation

Args:
    endpoint: Endpoint to remove from exemption
    path: Path to remove from exemption
    method: Method to remove from exemption

**Type:** Instance method

#### get_exemptions

```python
def get_exemptions(self) -> dict
```

Get current exemption configuration

Returns:
    Dictionary of current exemptions

**Type:** Instance method

## Functions

### csrf_exempt

```python
def csrf_exempt(f)
```

Decorator to exempt a route from CSRF validation

Args:
    f: Route function to exempt
    
Returns:
    Decorated function

### require_csrf

```python
def require_csrf(f)
```

Decorator to explicitly require CSRF validation for a route

Args:
    f: Route function that requires CSRF validation
    
Returns:
    Decorated function

### initialize_csrf_middleware

```python
def initialize_csrf_middleware(app) -> CSRFMiddleware
```

Initialize CSRF middleware for Flask app

Args:
    app: Flask application instance
    
Returns:
    Initialized CSRFMiddleware instance

### get_csrf_middleware

```python
def get_csrf_middleware() -> Optional[CSRFMiddleware]
```

Get the global CSRF middleware instance

Returns:
    CSRFMiddleware instance or None

### set_csrf_middleware

```python
def set_csrf_middleware(middleware: CSRFMiddleware)
```

Set the global CSRF middleware instance

Args:
    middleware: CSRFMiddleware instance


# security.core.csrf_error_handler

CSRF Error Handler

Comprehensive CSRF validation error handling with user-friendly responses,
form data preservation, and security event logging.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/core/csrf_error_handler.py`

## Classes

### CSRFErrorHandler

```python
class CSRFErrorHandler
```

Handles CSRF validation failures with comprehensive error processing

**Methods:**

#### __init__

```python
def __init__(self)
```

Initialize CSRF error handler

**Type:** Instance method

#### handle_csrf_failure

```python
def handle_csrf_failure(self, error: Exception, context: Optional[CSRFValidationContext]) -> Tuple[Any, int]
```

Handle CSRF validation failure

Args:
    error: CSRF error exception
    context: Validation context information
    
Returns:
    Tuple of (response, status_code)

**Type:** Instance method

#### _classify_csrf_error

```python
def _classify_csrf_error(self, error: Exception) -> str
```

Classify the type of CSRF error

Args:
    error: CSRF error exception
    
Returns:
    Error type string

**Type:** Instance method

#### _create_json_error_response

```python
def _create_json_error_response(self, error_type: str, context: CSRFValidationContext, preserved_data: Optional[str]) -> Tuple[Dict[str, Any], int]
```

Create JSON error response for AJAX requests

Args:
    error_type: Type of CSRF error
    context: Validation context
    preserved_data: Preserved form data
    
Returns:
    Tuple of (json_response, status_code)

**Type:** Instance method

#### _create_html_error_response

```python
def _create_html_error_response(self, error_type: str, context: CSRFValidationContext, preserved_data: Optional[str]) -> Tuple[Any, int]
```

Create HTML error response for form submissions

Args:
    error_type: Type of CSRF error
    context: Validation context
    preserved_data: Preserved form data
    
Returns:
    Tuple of (html_response, status_code)

**Type:** Instance method

#### _create_fallback_error_response

```python
def _create_fallback_error_response(self) -> Tuple[Any, int]
```

Create fallback error response when error handler fails

Returns:
    Tuple of (response, status_code)

**Type:** Instance method

#### _get_retry_guidance

```python
def _get_retry_guidance(self, error_type: str) -> str
```

Get retry guidance for specific error type

Args:
    error_type: Type of CSRF error
    
Returns:
    Retry guidance string

**Type:** Instance method

#### log_csrf_violation

```python
def log_csrf_violation(self, error: Exception, context: CSRFValidationContext) -> None
```

Log CSRF security violation

Args:
    error: CSRF error exception
    context: Validation context

**Type:** Instance method

#### preserve_form_data

```python
def preserve_form_data(self, form_data: Dict[str, Any]) -> Optional[str]
```

Preserve form data for recovery after CSRF error

Args:
    form_data: Form data to preserve
    
Returns:
    Serialized form data or None

**Type:** Instance method

#### recover_preserved_data

```python
def recover_preserved_data(self) -> Optional[Dict[str, Any]]
```

Recover preserved form data from session

Returns:
    Recovered form data or None

**Type:** Instance method

#### generate_retry_guidance

```python
def generate_retry_guidance(self, context: CSRFValidationContext) -> str
```

Generate specific retry guidance based on context

Args:
    context: Validation context
    
Returns:
    Specific retry guidance

**Type:** Instance method

## Functions

### get_csrf_error_handler

```python
def get_csrf_error_handler() -> CSRFErrorHandler
```

Get the global CSRF error handler instance

Returns:
    CSRFErrorHandler instance

### register_csrf_error_handlers

```python
def register_csrf_error_handlers(app)
```

Register CSRF error handlers with Flask app

Args:
    app: Flask application instance


# tests.security.test_csrf_security_suite

CSRF Security Test Suite

Comprehensive unit and integration tests for CSRF token generation, validation,
and protection across all forms and AJAX endpoints.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/security/test_csrf_security_suite.py`

## Classes

### TestCSRFTokenGeneration

```python
class TestCSRFTokenGeneration(unittest.TestCase)
```

Test CSRF token generation and entropy validation

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test environment

**Type:** Instance method

#### test_token_generation_basic

```python
def test_token_generation_basic(self)
```

Test basic CSRF token generation

**Type:** Instance method

#### test_token_entropy_validation

```python
def test_token_entropy_validation(self)
```

Test that CSRF tokens have sufficient entropy

**Type:** Instance method

#### test_token_session_binding

```python
def test_token_session_binding(self)
```

Test that tokens are properly bound to sessions

**Type:** Instance method

#### test_token_expiration

```python
def test_token_expiration(self)
```

Test CSRF token expiration handling

**Type:** Instance method

#### test_token_signature_validation

```python
def test_token_signature_validation(self)
```

Test CSRF token signature validation

**Type:** Instance method

#### test_token_malformed_handling

```python
def test_token_malformed_handling(self)
```

Test handling of malformed CSRF tokens

**Type:** Instance method

#### test_token_info_extraction

```python
def test_token_info_extraction(self)
```

Test CSRF token information extraction

**Type:** Instance method

### TestCSRFTokenValidation

```python
class TestCSRFTokenValidation(unittest.TestCase)
```

Test CSRF token validation logic

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### tearDown

```python
def tearDown(self)
```

Clean up test environment

**Type:** Instance method

#### test_valid_token_validation

```python
def test_valid_token_validation(self)
```

Test validation of valid CSRF tokens

**Type:** Instance method

#### test_invalid_session_rejection

```python
def test_invalid_session_rejection(self)
```

Test rejection of tokens with wrong session ID

**Type:** Instance method

#### test_expired_token_rejection

```python
def test_expired_token_rejection(self)
```

Test rejection of expired tokens

**Type:** Instance method

#### test_tampered_token_rejection

```python
def test_tampered_token_rejection(self)
```

Test rejection of tampered tokens

**Type:** Instance method

#### test_validation_context_creation

```python
def test_validation_context_creation(self)
```

Test CSRF validation context creation

**Type:** Instance method

### TestCSRFFormProtection

```python
class TestCSRFFormProtection(unittest.TestCase)
```

Test CSRF protection for form submissions

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test Flask app with forms

**Type:** Instance method

#### test_form_csrf_token_required

```python
def test_form_csrf_token_required(self)
```

Test that forms require CSRF tokens

**Type:** Instance method

#### test_form_csrf_token_validation

```python
def test_form_csrf_token_validation(self)
```

Test form submission with valid CSRF token

**Type:** Instance method

#### test_form_csrf_exempt_decorator

```python
def test_form_csrf_exempt_decorator(self)
```

Test that @csrf_exempt decorator works

**Type:** Instance method

#### test_form_invalid_csrf_token

```python
def test_form_invalid_csrf_token(self)
```

Test form submission with invalid CSRF token

**Type:** Instance method

### TestCSRFAjaxProtection

```python
class TestCSRFAjaxProtection(unittest.TestCase)
```

Test CSRF protection for AJAX requests

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test Flask app with AJAX endpoints

**Type:** Instance method

#### test_ajax_csrf_token_required

```python
def test_ajax_csrf_token_required(self)
```

Test that AJAX requests require CSRF tokens

**Type:** Instance method

#### test_ajax_csrf_token_validation

```python
def test_ajax_csrf_token_validation(self)
```

Test AJAX request with valid CSRF token

**Type:** Instance method

#### test_ajax_csrf_token_in_meta_tag

```python
def test_ajax_csrf_token_in_meta_tag(self)
```

Test CSRF token retrieval from meta tag for AJAX

**Type:** Instance method

#### test_ajax_csrf_error_response

```python
def test_ajax_csrf_error_response(self)
```

Test AJAX CSRF error response format

**Type:** Instance method

#### test_ajax_csrf_exempt_endpoint

```python
def test_ajax_csrf_exempt_endpoint(self)
```

Test AJAX request to CSRF-exempt endpoint

**Type:** Instance method

### TestCSRFMiddleware

```python
class TestCSRFMiddleware(unittest.TestCase)
```

Test CSRF middleware functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test Flask app with middleware

**Type:** Instance method

#### test_middleware_get_request_exemption

```python
def test_middleware_get_request_exemption(self)
```

Test that GET requests are exempt from CSRF validation

**Type:** Instance method

#### test_middleware_post_request_protection

```python
def test_middleware_post_request_protection(self)
```

Test that POST requests require CSRF validation

**Type:** Instance method

#### test_middleware_exemption_configuration

```python
def test_middleware_exemption_configuration(self)
```

Test middleware exemption configuration

**Type:** Instance method

#### test_middleware_validation_callback

```python
def test_middleware_validation_callback(self)
```

Test custom validation callback

**Type:** Instance method

### TestCSRFErrorHandling

```python
class TestCSRFErrorHandling(unittest.TestCase)
```

Test CSRF error handling and user experience

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test Flask app with error handling

**Type:** Instance method

#### test_csrf_error_classification

```python
def test_csrf_error_classification(self)
```

Test CSRF error type classification

**Type:** Instance method

#### test_form_data_preservation

```python
def test_form_data_preservation(self)
```

Test form data preservation during CSRF errors

**Type:** Instance method

#### test_csrf_error_logging

```python
def test_csrf_error_logging(self)
```

Test CSRF error logging

**Type:** Instance method

#### test_retry_guidance_generation

```python
def test_retry_guidance_generation(self)
```

Test retry guidance generation

**Type:** Instance method

#### test_preserved_data_recovery

```python
def test_preserved_data_recovery(self)
```

Test preserved form data recovery

**Type:** Instance method


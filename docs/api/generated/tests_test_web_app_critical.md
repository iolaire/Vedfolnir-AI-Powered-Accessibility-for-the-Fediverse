# tests.test_web_app_critical

Critical Web Application Tests

Tests for core web application functionality that must work correctly.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_web_app_critical.py`

## Classes

### TestWebAppCritical

```python
class TestWebAppCritical(unittest.TestCase)
```

Critical web application functionality tests

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_app_initialization

```python
def test_app_initialization(self)
```

Test that the web application initializes correctly

**Type:** Instance method

#### test_security_headers_present

```python
def test_security_headers_present(self)
```

Test that security headers are present in responses

**Type:** Instance method

#### test_error_handling

```python
def test_error_handling(self)
```

Test that errors are handled securely

**Type:** Instance method

#### test_session_management

```python
def test_session_management(self)
```

Test session management functionality

**Type:** Instance method

#### test_form_handling

```python
def test_form_handling(self)
```

Test form handling and validation

**Type:** Instance method

#### test_json_api_endpoints

```python
def test_json_api_endpoints(self)
```

Test JSON API endpoint functionality

**Type:** Instance method

#### test_static_file_serving

```python
def test_static_file_serving(self)
```

Test static file serving

**Type:** Instance method

#### test_template_rendering

```python
def test_template_rendering(self)
```

Test template rendering functionality

**Type:** Instance method

#### test_request_context

```python
def test_request_context(self)
```

Test Flask request context functionality

**Type:** Instance method

#### test_before_after_request_hooks

```python
def test_before_after_request_hooks(self)
```

Test before and after request hooks

**Type:** Instance method

### TestWebAppSecurity

```python
class TestWebAppSecurity(unittest.TestCase)
```

Web application security tests

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_xss_prevention

```python
def test_xss_prevention(self)
```

Test XSS prevention in templates

**Type:** Instance method

#### test_sql_injection_prevention

```python
def test_sql_injection_prevention(self)
```

Test SQL injection prevention

**Type:** Instance method

#### test_csrf_token_validation

```python
def test_csrf_token_validation(self)
```

Test CSRF token validation

**Type:** Instance method

### TestWebAppPerformance

```python
class TestWebAppPerformance(unittest.TestCase)
```

Web application performance tests

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test environment

**Type:** Instance method

#### test_response_time

```python
def test_response_time(self)
```

Test response time for basic requests

**Type:** Instance method

#### test_concurrent_requests

```python
def test_concurrent_requests(self)
```

Test handling of concurrent requests

**Type:** Instance method

## Functions

### run_critical_tests

```python
def run_critical_tests()
```

Run all critical web app tests


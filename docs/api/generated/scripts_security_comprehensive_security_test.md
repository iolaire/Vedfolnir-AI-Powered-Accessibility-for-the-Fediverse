# scripts.security.comprehensive_security_test

Comprehensive Security Testing

Performs comprehensive security testing including CSRF protection validation,
template security audit, and OWASP compliance testing.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/security/comprehensive_security_test.py`

## Classes

### ComprehensiveSecurityTester

```python
class ComprehensiveSecurityTester
```

Comprehensive security testing framework

**Methods:**

#### __init__

```python
def __init__(self)
```

Initialize security tester

**Type:** Instance method

#### run_csrf_protection_tests

```python
def run_csrf_protection_tests(self) -> Dict[str, Any]
```

Run CSRF protection tests

**Type:** Instance method

#### run_template_security_audit

```python
def run_template_security_audit(self) -> Dict[str, Any]
```

Run template security audit

**Type:** Instance method

#### run_owasp_compliance_tests

```python
def run_owasp_compliance_tests(self) -> Dict[str, Any]
```

Run OWASP compliance tests

**Type:** Instance method

#### run_penetration_tests

```python
def run_penetration_tests(self) -> Dict[str, Any]
```

Run basic penetration tests

**Type:** Instance method

#### run_comprehensive_test_suite

```python
def run_comprehensive_test_suite(self) -> Dict[str, Any]
```

Run complete comprehensive security test suite

**Type:** Instance method

#### _test_csrf_token_generation

```python
def _test_csrf_token_generation(self) -> float
```

Test CSRF token generation

**Type:** Instance method

#### _test_csrf_token_validation

```python
def _test_csrf_token_validation(self) -> float
```

Test CSRF token validation

**Type:** Instance method

#### _test_csrf_session_binding

```python
def _test_csrf_session_binding(self) -> float
```

Test CSRF session binding

**Type:** Instance method

#### _test_csrf_token_expiration

```python
def _test_csrf_token_expiration(self) -> float
```

Test CSRF token expiration

**Type:** Instance method

#### _test_owasp_csrf_compliance

```python
def _test_owasp_csrf_compliance(self) -> float
```

Test OWASP CSRF compliance

**Type:** Instance method

#### _test_owasp_input_validation

```python
def _test_owasp_input_validation(self) -> float
```

Test OWASP input validation compliance

**Type:** Instance method

#### _test_owasp_authentication

```python
def _test_owasp_authentication(self) -> float
```

Test OWASP authentication compliance

**Type:** Instance method

#### _test_owasp_session_management

```python
def _test_owasp_session_management(self) -> float
```

Test OWASP session management compliance

**Type:** Instance method

#### _test_owasp_security_headers

```python
def _test_owasp_security_headers(self) -> float
```

Test OWASP security headers compliance

**Type:** Instance method

#### _test_csrf_bypass

```python
def _test_csrf_bypass(self) -> float
```

Test CSRF bypass attempts

**Type:** Instance method

#### _test_xss_injection

```python
def _test_xss_injection(self) -> float
```

Test XSS injection attempts

**Type:** Instance method

#### _test_sql_injection

```python
def _test_sql_injection(self) -> float
```

Test SQL injection attempts

**Type:** Instance method

#### _test_session_fixation

```python
def _test_session_fixation(self) -> float
```

Test session fixation attempts

**Type:** Instance method

#### _save_test_results

```python
def _save_test_results(self, results: Dict[str, Any]) -> None
```

Save test results to file

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main testing function


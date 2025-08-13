# security.security_audit

Comprehensive Security Audit for Web-Integrated Caption Generation

This script performs a thorough security audit of the web-integrated caption generation system,
identifying vulnerabilities and providing detailed remediation recommendations.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/security_audit.py`

## Classes

### SeverityLevel

```python
class SeverityLevel(Enum)
```

**Class Variables:**
- `CRITICAL`
- `HIGH`
- `MEDIUM`
- `LOW`
- `INFO`

### SecurityVulnerability

```python
class SecurityVulnerability
```

Represents a security vulnerability

**Decorators:**
- `@dataclass`

**Methods:**

#### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

**Type:** Instance method

### SecurityAuditor

```python
class SecurityAuditor
```

Main security auditor class

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### run_audit

```python
def run_audit(self) -> Dict[str, Any]
```

Run comprehensive security audit

**Type:** Instance method

#### _audit_authentication

```python
def _audit_authentication(self)
```

Audit authentication and authorization mechanisms

**Type:** Instance method

#### _audit_input_validation

```python
def _audit_input_validation(self)
```

Audit input validation across all endpoints

**Type:** Instance method

#### _audit_csrf_protection

```python
def _audit_csrf_protection(self)
```

Audit CSRF protection implementation

**Type:** Instance method

#### _audit_security_headers

```python
def _audit_security_headers(self)
```

Audit security headers implementation

**Type:** Instance method

#### _audit_websocket_security

```python
def _audit_websocket_security(self)
```

Audit WebSocket security implementation

**Type:** Instance method

#### _audit_database_security

```python
def _audit_database_security(self)
```

Audit database security

**Type:** Instance method

#### _audit_file_operations

```python
def _audit_file_operations(self)
```

Audit file operations security

**Type:** Instance method

#### _audit_session_management

```python
def _audit_session_management(self)
```

Audit session management security

**Type:** Instance method

#### _audit_error_handling

```python
def _audit_error_handling(self)
```

Audit error handling for information disclosure

**Type:** Instance method

#### _audit_logging_security

```python
def _audit_logging_security(self)
```

Audit logging for security issues

**Type:** Instance method

#### _check_missing_auth_decorators

```python
def _check_missing_auth_decorators(self)
```

Check for routes missing authentication decorators

**Type:** Instance method

#### _check_password_policies

```python
def _check_password_policies(self)
```

Check for weak password policies

**Type:** Instance method

#### _check_session_fixation

```python
def _check_session_fixation(self)
```

Check for session fixation vulnerabilities

**Type:** Instance method

#### _check_privilege_escalation

```python
def _check_privilege_escalation(self)
```

Check for privilege escalation vulnerabilities

**Type:** Instance method

#### _check_path_traversal

```python
def _check_path_traversal(self)
```

Check for path traversal vulnerabilities

**Type:** Instance method

#### _check_command_injection

```python
def _check_command_injection(self)
```

Check for command injection vulnerabilities

**Type:** Instance method

#### _check_deserialization

```python
def _check_deserialization(self)
```

Check for unsafe deserialization

**Type:** Instance method

#### _check_csrf_token_strength

```python
def _check_csrf_token_strength(self)
```

Check CSRF token generation strength

**Type:** Instance method

#### _check_csrf_validation

```python
def _check_csrf_validation(self)
```

Check CSRF token validation implementation

**Type:** Instance method

#### _check_csp_policy

```python
def _check_csp_policy(self)
```

Check Content Security Policy implementation

**Type:** Instance method

#### _check_hsts

```python
def _check_hsts(self)
```

Check HSTS implementation

**Type:** Instance method

#### _check_websocket_validation

```python
def _check_websocket_validation(self)
```

Check WebSocket message validation

**Type:** Instance method

#### _check_websocket_rate_limiting

```python
def _check_websocket_rate_limiting(self)
```

Check WebSocket rate limiting

**Type:** Instance method

#### _check_orm_sql_injection

```python
def _check_orm_sql_injection(self)
```

Check for SQL injection in ORM queries

**Type:** Instance method

#### _check_database_connections

```python
def _check_database_connections(self)
```

Check database connection security

**Type:** Instance method

#### _check_file_upload_security

```python
def _check_file_upload_security(self)
```

Check file upload security

**Type:** Instance method

#### _check_file_download_security

```python
def _check_file_download_security(self)
```

Check file download security

**Type:** Instance method

#### _check_file_path_validation

```python
def _check_file_path_validation(self)
```

Check file path validation

**Type:** Instance method

#### _check_session_config

```python
def _check_session_config(self)
```

Check session configuration

**Type:** Instance method

#### _check_session_timeout

```python
def _check_session_timeout(self)
```

Check session timeout configuration

**Type:** Instance method

#### _check_session_invalidation

```python
def _check_session_invalidation(self)
```

Check session invalidation on logout

**Type:** Instance method

#### _check_error_disclosure

```python
def _check_error_disclosure(self)
```

Check for information disclosure in error messages

**Type:** Instance method

#### _check_stack_trace_exposure

```python
def _check_stack_trace_exposure(self)
```

Check for stack trace exposure

**Type:** Instance method

#### _check_sensitive_logging

```python
def _check_sensitive_logging(self)
```

Check for sensitive data in logs

**Type:** Instance method

#### _check_log_injection

```python
def _check_log_injection(self)
```

Check for log injection vulnerabilities

**Type:** Instance method

#### _check_insufficient_logging

```python
def _check_insufficient_logging(self)
```

Check for insufficient security logging

**Type:** Instance method

#### _check_missing_csrf_tokens

```python
def _check_missing_csrf_tokens(self)
```

Check for POST routes missing CSRF protection

**Type:** Instance method

#### _check_sql_injection

```python
def _check_sql_injection(self)
```

Check for potential SQL injection vulnerabilities

**Type:** Instance method

#### _check_xss_vulnerabilities

```python
def _check_xss_vulnerabilities(self)
```

Check for XSS vulnerabilities

**Type:** Instance method

#### _check_security_headers

```python
def _check_security_headers(self)
```

Check for proper security headers implementation

**Type:** Instance method

#### _check_websocket_auth

```python
def _check_websocket_auth(self)
```

Check WebSocket authentication implementation

**Type:** Instance method

#### _check_sensitive_data_exposure

```python
def _check_sensitive_data_exposure(self)
```

Check for sensitive data exposure

**Type:** Instance method

#### _check_debug_mode

```python
def _check_debug_mode(self)
```

Check for debug mode enabled

**Type:** Instance method

#### _generate_report

```python
def _generate_report(self) -> Dict[str, Any]
```

Generate comprehensive security audit report

**Type:** Instance method

#### _generate_recommendations

```python
def _generate_recommendations(self) -> List[str]
```

Generate high-level security recommendations

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main function to run security audit


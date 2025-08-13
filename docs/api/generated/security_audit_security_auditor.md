# security.audit.security_auditor

Comprehensive Security Auditor for Web Caption Generation System

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/audit/security_auditor.py`

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

### SecurityFinding

```python
class SecurityFinding
```

**Decorators:**
- `@dataclass`

### SecurityAuditor

```python
class SecurityAuditor
```

Comprehensive security auditor for the web application

**Methods:**

#### __init__

```python
def __init__(self, project_root: str)
```

**Type:** Instance method

#### audit_all

```python
def audit_all(self) -> List[SecurityFinding]
```

Run comprehensive security audit

**Type:** Instance method

#### audit_web_routes

```python
def audit_web_routes(self)
```

Audit web routes for authentication and authorization

**Type:** Instance method

#### audit_input_validation

```python
def audit_input_validation(self)
```

Audit input validation across all endpoints

**Type:** Instance method

#### audit_csrf_protection

```python
def audit_csrf_protection(self)
```

Audit CSRF protection implementation

**Type:** Instance method

#### audit_security_headers

```python
def audit_security_headers(self)
```

Audit security headers implementation

**Type:** Instance method

#### audit_websocket_security

```python
def audit_websocket_security(self)
```

Audit WebSocket security implementation

**Type:** Instance method

#### audit_database_security

```python
def audit_database_security(self)
```

Audit database operations for SQL injection

**Type:** Instance method

#### audit_file_operations

```python
def audit_file_operations(self)
```

Audit file upload/download operations

**Type:** Instance method

#### audit_authentication

```python
def audit_authentication(self)
```

Audit authentication implementation

**Type:** Instance method

#### audit_session_management

```python
def audit_session_management(self)
```

Audit session management security

**Type:** Instance method

#### audit_error_handling

```python
def audit_error_handling(self)
```

Audit error handling for information disclosure

**Type:** Instance method

#### audit_logging_security

```python
def audit_logging_security(self)
```

Audit logging for sensitive data exposure

**Type:** Instance method

#### generate_report

```python
def generate_report(self) -> Dict[str, Any]
```

Generate comprehensive security audit report

**Type:** Instance method

## Functions

### main

```python
def main()
```

Run security audit


# security.features.session_security

Session Security Hardening Features

Implements session fingerprinting, suspicious activity detection, and security audit logging
for enhanced session security validation.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/features/session_security.py`

## Classes

### SuspiciousActivityType

```python
class SuspiciousActivityType(Enum)
```

Types of suspicious session activities

**Class Variables:**
- `RAPID_PLATFORM_SWITCHING`
- `UNUSUAL_ACCESS_PATTERN`
- `SESSION_FINGERPRINT_MISMATCH`
- `CONCURRENT_SESSION_ABUSE`
- `GEOGRAPHIC_ANOMALY`
- `USER_AGENT_CHANGE`
- `IP_ADDRESS_CHANGE`

### SessionFingerprint

```python
class SessionFingerprint
```

Session fingerprint for enhanced security validation

**Decorators:**
- `@dataclass`

**Methods:**

#### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

**Type:** Instance method

#### from_dict

```python
def from_dict(cls, data: Dict[str, Any]) -> 'SessionFingerprint'
```

**Decorators:**
- `@classmethod`

**Type:** Class method

### SecurityAuditEvent

```python
class SecurityAuditEvent
```

Security audit event for session operations

**Decorators:**
- `@dataclass`

**Methods:**

#### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

**Type:** Instance method

### SessionSecurityHardening

```python
class SessionSecurityHardening
```

Enhanced session security with fingerprinting and suspicious activity detection

**Methods:**

#### __init__

```python
def __init__(self, session_manager)
```

**Type:** Instance method

#### create_session_fingerprint

```python
def create_session_fingerprint(self, request_data: Optional[Dict[str, Any]]) -> SessionFingerprint
```

Create session fingerprint from request data

**Type:** Instance method

#### validate_session_fingerprint

```python
def validate_session_fingerprint(self, session_id: str, current_fingerprint: SessionFingerprint) -> Tuple[bool, Optional[str]]
```

Validate session fingerprint against stored fingerprint

**Type:** Instance method

#### detect_suspicious_session_activity

```python
def detect_suspicious_session_activity(self, session_id: str, user_id: int, activity_type: str, details: Dict[str, Any]) -> bool
```

Detect suspicious session activity patterns

**Type:** Instance method

#### create_security_audit_event

```python
def create_security_audit_event(self, session_id: str, user_id: int, event_type: str, severity: str, details: Dict[str, Any]) -> SecurityAuditEvent
```

Create security audit event for session operations

**Type:** Instance method

#### validate_session_security

```python
def validate_session_security(self, session_id: str, user_id: int) -> Tuple[bool, List[str]]
```

Comprehensive session security validation

**Type:** Instance method

#### invalidate_suspicious_sessions

```python
def invalidate_suspicious_sessions(self, user_id: int, reason: str) -> int
```

Invalidate all sessions for a user due to suspicious activity

**Type:** Instance method

#### get_session_security_metrics

```python
def get_session_security_metrics(self, session_id: str) -> Dict[str, Any]
```

Get security metrics for a session

**Type:** Instance method

#### cleanup_expired_data

```python
def cleanup_expired_data(self, max_age_hours: int) -> Dict[str, int]
```

Clean up expired fingerprints and activity logs

**Type:** Instance method

#### _hash_value

```python
def _hash_value(self, value: str) -> str
```

Create hash of a value for fingerprinting

**Type:** Instance method

#### _get_client_ip

```python
def _get_client_ip(self) -> str
```

Get client IP address from request

**Type:** Instance method

#### _log_suspicious_activity

```python
def _log_suspicious_activity(self, session_id: str, activity_type: SuspiciousActivityType, details: Dict[str, Any])
```

Log suspicious activity for monitoring

**Type:** Instance method

#### _log_audit_event

```python
def _log_audit_event(self, event: SecurityAuditEvent)
```

Log security audit event

**Type:** Instance method

## Functions

### initialize_session_security

```python
def initialize_session_security(session_manager)
```

Initialize session security with session manager

### validate_session_security

```python
def validate_session_security(session_id: str, user_id: int) -> Tuple[bool, List[str]]
```

Convenience function for session security validation

### create_session_fingerprint

```python
def create_session_fingerprint(request_data: Optional[Dict[str, Any]]) -> SessionFingerprint
```

Convenience function for creating session fingerprint

### detect_suspicious_activity

```python
def detect_suspicious_activity(session_id: str, user_id: int, activity_type: str, details: Dict[str, Any]) -> bool
```

Convenience function for detecting suspicious activity


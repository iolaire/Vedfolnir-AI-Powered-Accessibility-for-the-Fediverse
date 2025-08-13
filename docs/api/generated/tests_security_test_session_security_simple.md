# tests.security.test_session_security_simple

Simple tests for session security hardening features without Flask context

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/security/test_session_security_simple.py`

## Classes

### TestSessionSecurityBasic

```python
class TestSessionSecurityBasic(unittest.TestCase)
```

Basic tests for session security hardening functionality

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_session_fingerprint_creation_with_data

```python
def test_session_fingerprint_creation_with_data(self)
```

Test session fingerprint creation with provided data

**Type:** Instance method

#### test_session_fingerprint_serialization

```python
def test_session_fingerprint_serialization(self)
```

Test session fingerprint serialization/deserialization

**Type:** Instance method

#### test_validate_session_fingerprint_first_time

```python
def test_validate_session_fingerprint_first_time(self)
```

Test fingerprint validation for first time (should store and pass)

**Type:** Instance method

#### test_validate_session_fingerprint_matching

```python
def test_validate_session_fingerprint_matching(self)
```

Test fingerprint validation with matching fingerprint

**Type:** Instance method

#### test_validate_session_fingerprint_user_agent_change

```python
def test_validate_session_fingerprint_user_agent_change(self)
```

Test fingerprint validation with user agent change (should fail)

**Type:** Instance method

#### test_validate_session_fingerprint_ip_change

```python
def test_validate_session_fingerprint_ip_change(self)
```

Test fingerprint validation with IP change (should pass but update)

**Type:** Instance method

#### test_detect_suspicious_rapid_platform_switching

```python
def test_detect_suspicious_rapid_platform_switching(self)
```

Test detection of rapid platform switching

**Type:** Instance method

#### test_detect_suspicious_unusual_access_pattern

```python
def test_detect_suspicious_unusual_access_pattern(self)
```

Test detection of unusual access patterns

**Type:** Instance method

#### test_detect_suspicious_concurrent_session_abuse

```python
def test_detect_suspicious_concurrent_session_abuse(self)
```

Test detection of concurrent session abuse

**Type:** Instance method

#### test_get_session_security_metrics

```python
def test_get_session_security_metrics(self)
```

Test getting session security metrics

**Type:** Instance method

#### test_cleanup_expired_data

```python
def test_cleanup_expired_data(self)
```

Test cleanup of expired fingerprints and activity logs

**Type:** Instance method

#### test_security_audit_event_creation

```python
def test_security_audit_event_creation(self)
```

Test security audit event creation without Flask context

**Type:** Instance method

#### test_security_audit_event_serialization

```python
def test_security_audit_event_serialization(self)
```

Test security audit event serialization

**Type:** Instance method

#### test_error_handling

```python
def test_error_handling(self)
```

Test error handling in security hardening

**Type:** Instance method

#### test_hash_value_method

```python
def test_hash_value_method(self)
```

Test the hash value method

**Type:** Instance method


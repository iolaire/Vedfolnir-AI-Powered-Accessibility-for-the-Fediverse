# security.monitoring.csrf_security_metrics

CSRF Security Metrics System

Comprehensive CSRF violation tracking, compliance metrics, and real-time alerting.
Integrates with the existing security monitoring infrastructure.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/monitoring/csrf_security_metrics.py`

## Classes

### CSRFViolationType

```python
class CSRFViolationType(Enum)
```

Types of CSRF violations

**Class Variables:**
- `MISSING_TOKEN`
- `INVALID_TOKEN`
- `EXPIRED_TOKEN`
- `TOKEN_MISMATCH`
- `MALFORMED_TOKEN`
- `REPLAY_ATTACK`
- `SESSION_MISMATCH`

### CSRFComplianceLevel

```python
class CSRFComplianceLevel(Enum)
```

CSRF compliance levels

**Class Variables:**
- `EXCELLENT`
- `GOOD`
- `FAIR`
- `POOR`

### CSRFViolationEvent

```python
class CSRFViolationEvent
```

CSRF violation event data

**Decorators:**
- `@dataclass`

### CSRFComplianceMetrics

```python
class CSRFComplianceMetrics
```

CSRF compliance metrics

**Decorators:**
- `@dataclass`

### CSRFSecurityMetrics

```python
class CSRFSecurityMetrics
```

CSRF security metrics and monitoring system

**Methods:**

#### __init__

```python
def __init__(self, config: Optional[Dict[str, Any]])
```

Initialize CSRF security metrics

**Type:** Instance method

#### track_csrf_violation

```python
def track_csrf_violation(self, violation_type: CSRFViolationType, source_ip: str, endpoint: str, user_agent: str, user_id: str, session_id: str, request_method: str, error_details: Dict[str, Any]) -> str
```

Track a CSRF violation

**Type:** Instance method

#### track_csrf_protection

```python
def track_csrf_protection(self, endpoint: str, protected: bool)
```

Track CSRF protection usage

**Type:** Instance method

#### _log_csrf_violation

```python
def _log_csrf_violation(self, violation: CSRFViolationEvent)
```

Log CSRF violation to standard logging

**Type:** Instance method

#### _check_csrf_alert_conditions

```python
def _check_csrf_alert_conditions(self, violation: CSRFViolationEvent)
```

Check if violation triggers alert conditions

**Type:** Instance method

#### _trigger_csrf_alert

```python
def _trigger_csrf_alert(self, alert_type: str, message: str, details: Dict[str, Any])
```

Trigger CSRF security alert

**Type:** Instance method

#### get_compliance_metrics

```python
def get_compliance_metrics(self, time_period: str) -> CSRFComplianceMetrics
```

Get CSRF compliance metrics

**Type:** Instance method

#### get_csrf_dashboard_data

```python
def get_csrf_dashboard_data(self) -> Dict[str, Any]
```

Get CSRF dashboard data for monitoring interface

**Type:** Instance method

#### _background_metrics_collection

```python
def _background_metrics_collection(self)
```

Background thread for metrics collection and cleanup

**Type:** Instance method

#### _cleanup_old_data

```python
def _cleanup_old_data(self)
```

Clean up old metrics data

**Type:** Instance method

#### _generate_periodic_reports

```python
def _generate_periodic_reports(self)
```

Generate periodic CSRF security reports

**Type:** Instance method

## Functions

### get_csrf_security_metrics

```python
def get_csrf_security_metrics() -> CSRFSecurityMetrics
```

Get the global CSRF security metrics instance

### track_csrf_violation

```python
def track_csrf_violation(violation_type: str, source_ip: str, endpoint: str, user_agent: str, user_id: str, session_id: str, request_method: str, error_details: Dict[str, Any]) -> str
```

Convenience function to track CSRF violations

### track_csrf_protection

```python
def track_csrf_protection(endpoint: str, protected: bool)
```

Convenience function to track CSRF protection usage


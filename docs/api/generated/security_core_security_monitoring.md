# security.core.security_monitoring

Security monitoring and alerting system

Implements comprehensive security event monitoring, logging, and alerting.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/core/security_monitoring.py`

## Classes

### SecurityEventType

```python
class SecurityEventType(Enum)
```

Types of security events

**Class Variables:**
- `LOGIN_SUCCESS`
- `LOGIN_FAILURE`
- `BRUTE_FORCE_ATTEMPT`
- `SUSPICIOUS_REQUEST`
- `RATE_LIMIT_EXCEEDED`
- `SQL_INJECTION_ATTEMPT`
- `XSS_ATTEMPT`
- `PATH_TRAVERSAL_ATTEMPT`
- `UNAUTHORIZED_ACCESS`
- `PRIVILEGE_ESCALATION`
- `DATA_BREACH_ATTEMPT`
- `MALICIOUS_FILE_UPLOAD`
- `SESSION_HIJACKING`
- `CSRF_ATTACK`
- `SECURITY_MISCONFIGURATION`

### SecurityEventSeverity

```python
class SecurityEventSeverity(Enum)
```

Severity levels for security events

**Class Variables:**
- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

### SecurityEvent

```python
class SecurityEvent
```

Security event data structure

**Decorators:**
- `@dataclass`

### SecurityMonitor

```python
class SecurityMonitor
```

Comprehensive security monitoring system

**Methods:**

#### __init__

```python
def __init__(self, config)
```

**Type:** Instance method

#### _get_alert_thresholds

```python
def _get_alert_thresholds(self)
```

Get alert thresholds from configuration

**Type:** Instance method

#### log_security_event

```python
def log_security_event(self, event_type: SecurityEventType, severity: SecurityEventSeverity, source_ip: str, endpoint: str, user_agent: str, user_id: str, details: Dict[str, Any])
```

Log a security event

**Type:** Instance method

#### _generate_event_id

```python
def _generate_event_id(self)
```

Generate unique event ID

**Type:** Instance method

#### _log_event

```python
def _log_event(self, event: SecurityEvent)
```

Log event to standard logging system

**Type:** Instance method

#### _check_alert_conditions

```python
def _check_alert_conditions(self, event: SecurityEvent)
```

Check if event triggers any alert conditions

**Type:** Instance method

#### _check_brute_force_attack

```python
def _check_brute_force_attack(self, event: SecurityEvent, current_time: datetime, time_window: timedelta)
```

Check for brute force attack patterns

**Type:** Instance method

#### _check_suspicious_patterns

```python
def _check_suspicious_patterns(self, event: SecurityEvent, current_time: datetime, time_window: timedelta)
```

Check for suspicious activity patterns

**Type:** Instance method

#### _check_rate_limit_violations

```python
def _check_rate_limit_violations(self, event: SecurityEvent, current_time: datetime, time_window: timedelta)
```

Check for repeated rate limit violations

**Type:** Instance method

#### _trigger_alert

```python
def _trigger_alert(self, event_type: SecurityEventType, severity: SecurityEventSeverity, message: str, details: Dict[str, Any])
```

Trigger a security alert

**Type:** Instance method

#### _send_alert_notification

```python
def _send_alert_notification(self, alert_data: Dict[str, Any])
```

Send alert notification (implement based on your alerting system)

**Type:** Instance method

#### _background_monitor

```python
def _background_monitor(self)
```

Background thread for continuous monitoring

**Type:** Instance method

#### _cleanup_old_events

```python
def _cleanup_old_events(self)
```

Clean up old events to prevent memory issues

**Type:** Instance method

#### _generate_security_metrics

```python
def _generate_security_metrics(self)
```

Generate security metrics for monitoring

**Type:** Instance method

#### _get_top_source_ips

```python
def _get_top_source_ips(self, events: List[SecurityEvent], limit: int)
```

Get top source IPs by event count

**Type:** Instance method

#### get_security_dashboard_data

```python
def get_security_dashboard_data(self)
```

Get data for security dashboard

**Type:** Instance method

#### _get_events_by_hour

```python
def _get_events_by_hour(self, events: List[SecurityEvent])
```

Get event counts by hour

**Type:** Instance method

#### _get_top_event_types

```python
def _get_top_event_types(self, events: List[SecurityEvent], limit: int)
```

Get top event types by count

**Type:** Instance method

## Functions

### log_security_event

```python
def log_security_event(event_type: SecurityEventType, severity: SecurityEventSeverity, source_ip: str, endpoint: str, user_agent: str, user_id: str, details: Dict[str, Any])
```

Convenience function to log security events


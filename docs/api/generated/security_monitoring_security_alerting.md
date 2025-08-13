# security.monitoring.security_alerting

Security Alerting System

Real-time security alerting for CSRF violations and security incidents.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/monitoring/security_alerting.py`

## Classes

### AlertSeverity

```python
class AlertSeverity(Enum)
```

Alert severity levels

**Class Variables:**
- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

### SecurityAlert

```python
class SecurityAlert
```

Security alert data structure

**Decorators:**
- `@dataclass`

### SecurityAlertManager

```python
class SecurityAlertManager
```

Manages security alerts and notifications

**Methods:**

#### __init__

```python
def __init__(self)
```

Initialize security alert manager

**Type:** Instance method

#### trigger_csrf_violation_alert

```python
def trigger_csrf_violation_alert(self, violation_count: int, source_ip: str, time_window: str) -> str
```

Trigger CSRF violation alert

**Type:** Instance method

#### trigger_security_compliance_alert

```python
def trigger_security_compliance_alert(self, compliance_rate: float, component: str) -> str
```

Trigger security compliance alert

**Type:** Instance method

#### _process_alert

```python
def _process_alert(self, alert: SecurityAlert) -> str
```

Process and distribute security alert

**Type:** Instance method

#### _send_alert_notifications

```python
def _send_alert_notifications(self, alert: SecurityAlert) -> None
```

Send alert notifications

**Type:** Instance method

#### get_recent_alerts

```python
def get_recent_alerts(self, hours: int) -> List[SecurityAlert]
```

Get recent security alerts

**Type:** Instance method

#### get_alert_summary

```python
def get_alert_summary(self) -> Dict[str, Any]
```

Get alert summary for dashboard

**Type:** Instance method

## Functions

### get_security_alert_manager

```python
def get_security_alert_manager() -> SecurityAlertManager
```

Get global security alert manager instance

### trigger_csrf_violation_alert

```python
def trigger_csrf_violation_alert(violation_count: int, source_ip: str) -> str
```

Convenience function to trigger CSRF violation alert


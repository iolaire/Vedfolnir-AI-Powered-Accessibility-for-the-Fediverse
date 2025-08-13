# session_alerting_system

Session Management Alerting System

Provides comprehensive alerting capabilities for session management issues including
threshold monitoring, alert escalation, notification delivery, and alert management.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_alerting_system.py`

## Classes

### AlertSeverity

```python
class AlertSeverity(Enum)
```

Alert severity levels

**Class Variables:**
- `INFO`
- `WARNING`
- `CRITICAL`

### AlertStatus

```python
class AlertStatus(Enum)
```

Alert status

**Class Variables:**
- `ACTIVE`
- `ACKNOWLEDGED`
- `RESOLVED`

### Alert

```python
class Alert
```

Session management alert

**Decorators:**
- `@dataclass`

### AlertRule

```python
class AlertRule
```

Alert rule configuration

**Decorators:**
- `@dataclass`

### SessionAlertingSystem

```python
class SessionAlertingSystem
```

Comprehensive alerting system for session management

**Methods:**

#### __init__

```python
def __init__(self, health_checker: SessionHealthChecker)
```

**Type:** Instance method

#### _initialize_default_rules

```python
def _initialize_default_rules(self)
```

Initialize default alert rules

**Type:** Instance method

#### _start_monitoring

```python
def _start_monitoring(self)
```

Start background monitoring for alerts

**Type:** Instance method

#### check_alerts

```python
def check_alerts(self) -> List[Alert]
```

Check for new alerts based on current system health

**Type:** Instance method

#### _evaluate_condition

```python
def _evaluate_condition(self, value: float, condition: str, threshold: float) -> bool
```

Evaluate alert condition

**Type:** Instance method

#### _create_alert

```python
def _create_alert(self, rule: AlertRule, metric_value: float, component_health) -> Alert
```

Create a new alert

**Type:** Instance method

#### _find_similar_alert

```python
def _find_similar_alert(self, component: str, title: str) -> Optional[Alert]
```

Find similar active alert

**Type:** Instance method

#### _process_new_alert

```python
def _process_new_alert(self, alert: Alert)
```

Process a new alert

**Type:** Instance method

#### _send_notifications

```python
def _send_notifications(self, alert: Alert)
```

Send alert notifications

**Type:** Instance method

#### _check_resolved_alerts

```python
def _check_resolved_alerts(self, system_health)
```

Check if any active alerts should be resolved

**Type:** Instance method

#### acknowledge_alert

```python
def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool
```

Acknowledge an alert

**Type:** Instance method

#### resolve_alert

```python
def resolve_alert(self, alert_id: str, resolved_by: str) -> bool
```

Manually resolve an alert

**Type:** Instance method

#### get_active_alerts

```python
def get_active_alerts(self, severity: Optional[AlertSeverity]) -> List[Alert]
```

Get active alerts, optionally filtered by severity

**Type:** Instance method

#### get_alert_summary

```python
def get_alert_summary(self) -> Dict[str, Any]
```

Get alert summary statistics

**Type:** Instance method

#### add_notification_handler

```python
def add_notification_handler(self, handler: Callable[[Alert], None])
```

Add a notification handler

**Type:** Instance method

#### add_alert_rule

```python
def add_alert_rule(self, rule: AlertRule)
```

Add a custom alert rule

**Type:** Instance method

#### update_alert_rule

```python
def update_alert_rule(self, rule_name: str, **kwargs) -> bool
```

Update an existing alert rule

**Type:** Instance method

#### disable_alert_rule

```python
def disable_alert_rule(self, rule_name: str) -> bool
```

Disable an alert rule

**Type:** Instance method

#### enable_alert_rule

```python
def enable_alert_rule(self, rule_name: str) -> bool
```

Enable an alert rule

**Type:** Instance method

#### export_alerts

```python
def export_alerts(self, include_resolved: bool) -> List[Dict[str, Any]]
```

Export alerts for external analysis

**Type:** Instance method

#### _alert_to_dict

```python
def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]
```

Convert alert to dictionary

**Type:** Instance method

## Functions

### log_notification_handler

```python
def log_notification_handler(alert: Alert)
```

Log alert notifications

### console_notification_handler

```python
def console_notification_handler(alert: Alert)
```

Print alert to console

### get_alerting_system

```python
def get_alerting_system(health_checker: SessionHealthChecker) -> SessionAlertingSystem
```

Get or create global alerting system instance


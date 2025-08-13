# session_monitoring

Session Monitoring and Logging Infrastructure
Provides comprehensive monitoring, metrics collection, and diagnostic capabilities for session management

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_monitoring.py`

## Classes

### SessionMetric

```python
class SessionMetric
```

Data class for session metrics

**Decorators:**
- `@dataclass`

### SessionEvent

```python
class SessionEvent
```

Data class for session events

**Decorators:**
- `@dataclass`

### SessionMonitor

```python
class SessionMonitor
```

Comprehensive session monitoring and metrics collection

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager, config: Optional[SessionConfig])
```

**Type:** Instance method

#### _initialize_monitoring

```python
def _initialize_monitoring(self)
```

Initialize monitoring system

**Type:** Instance method

#### log_system_startup

```python
def log_system_startup(self)
```

Log system startup information

**Type:** Instance method

#### record_metric

```python
def record_metric(self, metric_type: str, session_id: str, user_id: int, value: float, metadata: Optional[Dict[str, Any]])
```

Record a session metric

Args:
    metric_type: Type of metric (e.g., 'session_duration', 'sync_time')
    session_id: Session ID
    user_id: User ID
    value: Metric value
    metadata: Additional metadata

**Type:** Instance method

#### record_event

```python
def record_event(self, event: SessionEvent)
```

Record a session event

Args:
    event: SessionEvent object

**Type:** Instance method

#### log_session_created

```python
def log_session_created(self, session_id: str, user_id: int, platform_id: Optional[int])
```

Log session creation

**Type:** Instance method

#### log_session_expired

```python
def log_session_expired(self, session_id: str, user_id: int, reason: str)
```

Log session expiration

**Type:** Instance method

#### log_session_error

```python
def log_session_error(self, session_id: str, user_id: int, error_type: str, error_details: str)
```

Log session error

**Type:** Instance method

#### log_platform_switch

```python
def log_platform_switch(self, session_id: str, user_id: int, old_platform_id: Optional[int], new_platform_id: int, switch_duration: float)
```

Log platform switch

**Type:** Instance method

#### log_suspicious_activity

```python
def log_suspicious_activity(self, session_id: str, user_id: int, activity_type: str, details: Dict[str, Any])
```

Log suspicious session activity

**Type:** Instance method

#### get_session_statistics

```python
def get_session_statistics(self) -> Dict[str, Any]
```

Get comprehensive session statistics

Returns:
    Dictionary with session statistics

**Type:** Instance method

#### get_session_health_report

```python
def get_session_health_report(self) -> Dict[str, Any]
```

Generate session health report

Returns:
    Dictionary with health report

**Type:** Instance method

#### _check_metric_alerts

```python
def _check_metric_alerts(self, metric: SessionMetric)
```

Check if metric triggers any alerts

**Type:** Instance method

#### _check_event_alerts

```python
def _check_event_alerts(self, event: SessionEvent)
```

Check if event triggers any alerts

**Type:** Instance method

#### export_metrics

```python
def export_metrics(self, start_time: Optional[datetime], end_time: Optional[datetime]) -> List[Dict[str, Any]]
```

Export metrics for external analysis

Args:
    start_time: Start time for export (optional)
    end_time: End time for export (optional)
    
Returns:
    List of metric dictionaries

**Type:** Instance method

#### cleanup_old_data

```python
def cleanup_old_data(self, retention_days: int)
```

Clean up old monitoring data

Args:
    retention_days: Number of days to retain data

**Type:** Instance method

## Functions

### get_session_monitor

```python
def get_session_monitor(db_manager: DatabaseManager, config: Optional[SessionConfig]) -> Optional[SessionMonitor]
```

Get or create global session monitor instance


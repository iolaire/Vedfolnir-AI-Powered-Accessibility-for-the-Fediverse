# session_performance_monitor

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_performance_monitor.py`

## Classes

### SessionMetrics

```python
class SessionMetrics
```

Container for session performance metrics

**Decorators:**
- `@dataclass`

### RequestMetrics

```python
class RequestMetrics
```

Container for request-level performance metrics

**Decorators:**
- `@dataclass`

### SessionPerformanceMonitor

```python
class SessionPerformanceMonitor
```

Performance monitoring system for database session management.

Tracks metrics for:
- Session creation and cleanup operations
- DetachedInstanceError recovery events
- Database session pool usage
- Performance timing for session-aware operations

**Methods:**

#### __init__

```python
def __init__(self, logger_name: str)
```

Initialize the performance monitor.

Args:
    logger_name: Name for the logger instance

**Type:** Instance method

#### start_request_monitoring

```python
def start_request_monitoring(self, endpoint: str) -> str
```

Start monitoring for a request.

Args:
    endpoint: Request endpoint name
    
Returns:
    Request ID for tracking

**Type:** Instance method

#### end_request_monitoring

```python
def end_request_monitoring(self, request_id: str)
```

End monitoring for a request and log performance metrics.

Args:
    request_id: Request ID to end monitoring for

**Type:** Instance method

#### record_session_creation

```python
def record_session_creation(self, duration: float)
```

Record a session creation event.

Args:
    duration: Time taken to create the session in seconds

**Type:** Instance method

#### record_session_closure

```python
def record_session_closure(self, duration: float)
```

Record a session closure event.

Args:
    duration: Time taken to close the session in seconds

**Type:** Instance method

#### record_session_commit

```python
def record_session_commit(self)
```

Record a session commit event.

**Type:** Instance method

#### record_session_rollback

```python
def record_session_rollback(self)
```

Record a session rollback event.

**Type:** Instance method

#### record_detached_instance_recovery

```python
def record_detached_instance_recovery(self, object_type: str, duration: float, success: bool)
```

Record a DetachedInstanceError recovery event.

Args:
    object_type: Type of object that was recovered
    duration: Time taken for recovery in seconds
    success: Whether the recovery was successful

**Type:** Instance method

#### record_session_reattachment

```python
def record_session_reattachment(self, object_type: str)
```

Record a session reattachment event.

Args:
    object_type: Type of object that was reattached

**Type:** Instance method

#### record_session_error

```python
def record_session_error(self, error_type: str, error_message: str)
```

Record a session-related error.

Args:
    error_type: Type of error that occurred
    error_message: Error message

**Type:** Instance method

#### update_pool_metrics

```python
def update_pool_metrics(self, engine: Engine)
```

Update database connection pool metrics.

Args:
    engine: SQLAlchemy engine to get pool metrics from

**Type:** Instance method

#### time_operation

```python
def time_operation(self, operation_name: str)
```

Context manager for timing operations.

Args:
    operation_name: Name of the operation being timed

**Decorators:**
- `@contextmanager`

**Type:** Instance method

#### get_current_metrics

```python
def get_current_metrics(self) -> Dict[str, Any]
```

Get current performance metrics.

Returns:
    Dictionary containing current metrics

**Type:** Instance method

#### get_performance_summary

```python
def get_performance_summary(self) -> str
```

Get a formatted performance summary.

Returns:
    Formatted string with performance summary

**Type:** Instance method

#### log_periodic_summary

```python
def log_periodic_summary(self, interval_seconds: int)
```

Log a periodic performance summary.

Args:
    interval_seconds: Interval between summaries in seconds

**Type:** Instance method

#### _add_request_operation

```python
def _add_request_operation(self, operation: str)
```

Add an operation to the current request's metrics.

Args:
    operation: Name of the operation

**Type:** Instance method

#### _log_request_performance

```python
def _log_request_performance(self, request_metric: RequestMetrics, duration: float)
```

Log performance metrics for a completed request.

Args:
    request_metric: Request metrics to log
    duration: Total request duration

**Type:** Instance method

## Functions

### get_performance_monitor

```python
def get_performance_monitor() -> SessionPerformanceMonitor
```

Get the global performance monitor instance.

Returns:
    SessionPerformanceMonitor instance

### initialize_performance_monitoring

```python
def initialize_performance_monitoring(app, session_manager, engine)
```

Initialize performance monitoring for the Flask application.

Args:
    app: Flask application instance
    session_manager: RequestScopedSessionManager instance
    engine: SQLAlchemy engine instance


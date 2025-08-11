# Session Performance Monitoring

## Overview

The session performance monitoring system provides comprehensive tracking and analysis of database session management performance in the Vedfolnir application. It monitors session creation, cleanup, DetachedInstanceError recovery events, and database connection pool usage.

## Features

### Core Monitoring Capabilities

- **Session Lifecycle Tracking**: Monitor session creation, closure, commits, and rollbacks
- **DetachedInstanceError Recovery**: Track recovery attempts and success rates
- **Performance Timing**: Measure operation durations and identify slow operations
- **Database Pool Monitoring**: Track connection pool utilization and health
- **Request-Level Metrics**: Associate operations with specific HTTP requests
- **Error Tracking**: Monitor and categorize session-related errors

### Performance Metrics

The system tracks the following key metrics:

#### Session Metrics
- Session creations and closures
- Active session count and peak usage
- Session commits and rollbacks
- Session errors and error rates
- Average session duration

#### Recovery Metrics
- DetachedInstanceError recovery attempts
- Session reattachment operations
- Recovery success rates
- Recovery operation timing

#### Performance Timing
- Average session creation time
- Average session cleanup time
- Average recovery operation time
- Performance threshold alerts

#### Database Pool Metrics
- Pool size and utilization
- Checked out connections
- Pool overflow events
- Connection check-in/check-out rates

## Usage

### Programmatic Access

```python
from session_performance_monitor import get_performance_monitor

# Get the global monitor instance
monitor = get_performance_monitor()

# Record operations
monitor.record_session_creation(0.1)  # 0.1 seconds
monitor.record_detached_instance_recovery("User", 0.05, True)
monitor.record_session_closure(0.08)

# Get current metrics
metrics = monitor.get_current_metrics()
print(f"Active sessions: {metrics['session_metrics']['active_sessions']}")

# Get performance summary
summary = monitor.get_performance_summary()
print(summary)
```

### CLI Commands

The system provides Flask CLI commands for monitoring:

```bash
# Show current status
flask session-monitoring status

# Show detailed summary
flask session-monitoring summary

# Export metrics as JSON
flask session-monitoring metrics --format json

# Check for performance alerts
flask session-monitoring alerts --threshold 1.0

# Enable periodic logging
flask session-monitoring enable-periodic-logging --interval 300
```

### Web Interface

Access the monitoring dashboard at `/admin/session-monitoring/dashboard` (admin access required).

#### Available Endpoints

- `GET /admin/session-monitoring/status` - Current metrics (JSON)
- `GET /admin/session-monitoring/summary` - Performance summary (JSON)
- `GET /admin/session-monitoring/alerts` - Performance alerts (JSON)
- `GET /admin/session-monitoring/dashboard` - Web dashboard (HTML)
- `GET /admin/session-monitoring/health` - Health check endpoint (JSON)

### Health Check Integration

The monitoring system provides a health check endpoint for external monitoring systems:

```bash
curl http://localhost:5000/admin/session-monitoring/health
```

Response format:
```json
{
  "status": "healthy|degraded|unhealthy",
  "timestamp": "2025-01-11T10:30:00Z",
  "issues": [],
  "metrics_summary": {
    "active_sessions": 5,
    "error_rate": 0.02,
    "recovery_rate": 0.05,
    "pool_utilization": 0.3
  }
}
```

## Configuration

### Performance Thresholds

The monitoring system uses configurable thresholds for alerting:

```python
monitor = SessionPerformanceMonitor()
monitor.slow_session_threshold = 1.0  # seconds
monitor.high_recovery_rate_threshold = 0.1  # 10%
monitor.max_active_sessions_threshold = 50
```

### Periodic Logging

Enable periodic performance summaries in your application logs:

```python
# Log summary every 5 minutes (300 seconds)
monitor.log_periodic_summary(300)
```

## Integration

### Automatic Integration

The monitoring system is automatically integrated when the application starts:

```python
from session_performance_monitor import initialize_performance_monitoring

# Initialize during app setup
monitor = initialize_performance_monitoring(app, session_manager, engine)
```

### Manual Integration

For custom integration, use the monitoring hooks in your session management code:

```python
from session_performance_monitor import get_performance_monitor

def create_session():
    start_time = time.time()
    try:
        session = create_db_session()
        duration = time.time() - start_time
        get_performance_monitor().record_session_creation(duration)
        return session
    except Exception as e:
        get_performance_monitor().record_session_error("creation_failed", str(e))
        raise
```

## Monitoring Best Practices

### Performance Thresholds

- **Session Creation**: < 0.5 seconds (normal), > 1.0 seconds (slow)
- **Session Cleanup**: < 0.2 seconds (normal), > 0.5 seconds (slow)
- **Recovery Operations**: < 0.1 seconds (normal), > 0.5 seconds (slow)
- **Error Rate**: < 1% (healthy), > 5% (concerning)
- **Recovery Rate**: < 5% (healthy), > 10% (concerning)

### Alert Conditions

The system generates alerts for:

- Slow operations exceeding thresholds
- High error rates (> 5%)
- High recovery rates (> 10%)
- Database pool near exhaustion (> 80% utilization)
- Excessive active sessions

### Troubleshooting

#### High Recovery Rates

If you see high DetachedInstanceError recovery rates:

1. Check session management patterns
2. Verify proper session scoping
3. Review lazy loading configurations
4. Ensure proper session cleanup

#### Slow Operations

For slow session operations:

1. Check database connectivity
2. Review connection pool configuration
3. Analyze database query performance
4. Monitor system resources

#### Pool Exhaustion

If connection pool utilization is high:

1. Increase pool size if needed
2. Check for connection leaks
3. Review session cleanup patterns
4. Monitor concurrent request load

## Security Considerations

- Admin-only access to monitoring endpoints
- Sanitized logging to prevent information disclosure
- Rate limiting on monitoring endpoints
- Secure error handling and reporting

## Performance Impact

The monitoring system is designed to have minimal performance impact:

- Lightweight metric collection
- Thread-safe operations
- Configurable detail levels
- Optional request-level tracking
- Efficient memory usage with bounded collections

## Testing

Run the integration tests to verify monitoring functionality:

```bash
python test_session_monitoring_integration.py
```

Run the unit tests:

```bash
python -m unittest tests.test_session_performance_monitoring -v
```
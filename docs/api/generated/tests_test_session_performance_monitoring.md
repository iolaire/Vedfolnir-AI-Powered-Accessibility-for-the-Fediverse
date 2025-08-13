# tests.test_session_performance_monitoring

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_session_performance_monitoring.py`

## Classes

### TestSessionMetrics

```python
class TestSessionMetrics(unittest.TestCase)
```

Test SessionMetrics dataclass

**Methods:**

#### test_session_metrics_initialization

```python
def test_session_metrics_initialization(self)
```

Test SessionMetrics initializes with correct defaults

**Type:** Instance method

### TestRequestMetrics

```python
class TestRequestMetrics(unittest.TestCase)
```

Test RequestMetrics dataclass

**Methods:**

#### test_request_metrics_initialization

```python
def test_request_metrics_initialization(self)
```

Test RequestMetrics initializes correctly

**Type:** Instance method

### TestSessionPerformanceMonitor

```python
class TestSessionPerformanceMonitor(unittest.TestCase)
```

Test SessionPerformanceMonitor class

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_monitor_initialization

```python
def test_monitor_initialization(self)
```

Test monitor initializes correctly

**Type:** Instance method

#### test_start_request_monitoring

```python
def test_start_request_monitoring(self, mock_g, mock_request, mock_has_context)
```

Test starting request monitoring

**Decorators:**
- `@patch('session_performance_monitor.has_request_context')`
- `@patch('session_performance_monitor.request')`
- `@patch('session_performance_monitor.g')`

**Type:** Instance method

#### test_start_request_monitoring_no_context

```python
def test_start_request_monitoring_no_context(self, mock_has_context)
```

Test starting request monitoring without request context

**Decorators:**
- `@patch('session_performance_monitor.has_request_context')`

**Type:** Instance method

#### test_record_session_creation

```python
def test_record_session_creation(self)
```

Test recording session creation

**Type:** Instance method

#### test_record_session_creation_updates_peak

```python
def test_record_session_creation_updates_peak(self)
```

Test that session creation updates peak active sessions

**Type:** Instance method

#### test_record_session_closure

```python
def test_record_session_closure(self)
```

Test recording session closure

**Type:** Instance method

#### test_record_session_commit

```python
def test_record_session_commit(self)
```

Test recording session commit

**Type:** Instance method

#### test_record_session_rollback

```python
def test_record_session_rollback(self)
```

Test recording session rollback

**Type:** Instance method

#### test_record_detached_instance_recovery

```python
def test_record_detached_instance_recovery(self)
```

Test recording detached instance recovery

**Type:** Instance method

#### test_record_detached_instance_recovery_with_request

```python
def test_record_detached_instance_recovery_with_request(self, mock_g)
```

Test recording recovery with active request

**Decorators:**
- `@patch('session_performance_monitor.g')`

**Type:** Instance method

#### test_record_session_reattachment

```python
def test_record_session_reattachment(self)
```

Test recording session reattachment

**Type:** Instance method

#### test_record_session_error

```python
def test_record_session_error(self)
```

Test recording session error

**Type:** Instance method

#### test_update_pool_metrics

```python
def test_update_pool_metrics(self)
```

Test updating pool metrics

**Type:** Instance method

#### test_update_pool_metrics_no_pool

```python
def test_update_pool_metrics_no_pool(self)
```

Test updating pool metrics with engine that has no pool

**Type:** Instance method

#### test_time_operation_context_manager

```python
def test_time_operation_context_manager(self)
```

Test timing operation context manager

**Type:** Instance method

#### test_get_current_metrics

```python
def test_get_current_metrics(self)
```

Test getting current metrics

**Type:** Instance method

#### test_get_performance_summary

```python
def test_get_performance_summary(self)
```

Test getting performance summary

**Type:** Instance method

#### test_log_periodic_summary

```python
def test_log_periodic_summary(self)
```

Test periodic summary logging

**Type:** Instance method

#### test_thread_safety

```python
def test_thread_safety(self)
```

Test thread safety of metrics recording

**Type:** Instance method

### TestGlobalMonitorFunctions

```python
class TestGlobalMonitorFunctions(unittest.TestCase)
```

Test global monitor functions

**Methods:**

#### test_get_performance_monitor_singleton

```python
def test_get_performance_monitor_singleton(self)
```

Test that get_performance_monitor returns singleton

**Type:** Instance method

#### test_initialize_performance_monitoring

```python
def test_initialize_performance_monitoring(self, mock_monitor_class)
```

Test initialize_performance_monitoring function

**Decorators:**
- `@patch('session_performance_monitor.SessionPerformanceMonitor')`

**Type:** Instance method

### TestPerformanceMonitoringIntegration

```python
class TestPerformanceMonitoringIntegration(unittest.TestCase)
```

Integration tests for performance monitoring

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up integration test fixtures

**Type:** Instance method

#### test_full_session_lifecycle_monitoring

```python
def test_full_session_lifecycle_monitoring(self)
```

Test monitoring a complete session lifecycle

**Type:** Instance method

#### test_error_scenario_monitoring

```python
def test_error_scenario_monitoring(self)
```

Test monitoring error scenarios

**Type:** Instance method

#### test_performance_threshold_alerts

```python
def test_performance_threshold_alerts(self)
```

Test performance threshold detection

**Type:** Instance method


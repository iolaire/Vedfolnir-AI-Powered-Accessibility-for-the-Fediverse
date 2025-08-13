# admin_monitoring

Administrative Monitoring and Controls

This module provides comprehensive monitoring and control capabilities for administrators
to manage caption generation tasks, system resources, and performance metrics.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/admin_monitoring.py`

## Classes

### AdminMonitoringService

```python
class AdminMonitoringService
```

Service for administrative monitoring and control of caption generation system

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager)
```

**Type:** Instance method

#### get_system_overview

```python
def get_system_overview(self) -> Dict[str, Any]
```

Get comprehensive system overview for admin dashboard

**Type:** Instance method

#### get_active_tasks

```python
def get_active_tasks(self, limit: int) -> List[Dict[str, Any]]
```

Get list of active caption generation tasks

**Type:** Instance method

#### get_task_history

```python
def get_task_history(self, hours: int, limit: int) -> List[Dict[str, Any]]
```

Get task history for specified time period

**Type:** Instance method

#### get_performance_metrics

```python
def get_performance_metrics(self, days: int) -> Dict[str, Any]
```

Get performance metrics for specified period

**Type:** Instance method

#### cancel_task

```python
def cancel_task(self, task_id: str, admin_user_id: int, reason: str) -> Dict[str, Any]
```

Cancel a task as administrator

**Type:** Instance method

#### cleanup_old_tasks

```python
def cleanup_old_tasks(self, days: int, dry_run: bool) -> Dict[str, Any]
```

Clean up old completed/failed tasks

**Type:** Instance method

#### get_user_activity

```python
def get_user_activity(self, days: int) -> List[Dict[str, Any]]
```

Get user activity statistics

**Type:** Instance method

#### get_system_limits

```python
def get_system_limits(self) -> Dict[str, Any]
```

Get current system limits and configuration

**Type:** Instance method

#### update_system_limits

```python
def update_system_limits(self, limits: Dict[str, Any]) -> Dict[str, Any]
```

Update system limits (placeholder for future configuration management)

**Type:** Instance method

#### _get_system_resources

```python
def _get_system_resources(self) -> Dict[str, Any]
```

Get current system resource usage

**Type:** Instance method

#### _task_to_dict

```python
def _task_to_dict(self, task: CaptionGenerationTask) -> Dict[str, Any]
```

Convert task object to dictionary for JSON serialization

**Type:** Instance method


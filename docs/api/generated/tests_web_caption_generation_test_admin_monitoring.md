# tests.web_caption_generation.test_admin_monitoring

Tests for administrative monitoring and controls

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/web_caption_generation/test_admin_monitoring.py`

## Classes

### TestAdminMonitoring

```python
class TestAdminMonitoring(unittest.TestCase)
```

Tests for administrative monitoring and controls

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_get_system_overview

```python
def test_get_system_overview(self)
```

Test system overview retrieval

**Type:** Instance method

#### test_get_resource_monitoring

```python
def test_get_resource_monitoring(self, mock_psutil)
```

Test resource monitoring data retrieval

**Decorators:**
- `@patch('admin_monitoring.psutil')`

**Type:** Instance method

#### test_get_active_tasks

```python
def test_get_active_tasks(self)
```

Test active tasks retrieval

**Type:** Instance method

#### test_cancel_task_as_admin

```python
def test_cancel_task_as_admin(self)
```

Test admin task cancellation

**Type:** Instance method

#### test_cancel_task_unauthorized

```python
def test_cancel_task_unauthorized(self)
```

Test task cancellation by non-admin user

**Type:** Instance method

#### test_get_performance_metrics

```python
def test_get_performance_metrics(self)
```

Test performance metrics retrieval

**Type:** Instance method

#### test_get_user_activity

```python
def test_get_user_activity(self)
```

Test user activity tracking

**Type:** Instance method

#### test_cleanup_old_tasks

```python
def test_cleanup_old_tasks(self)
```

Test cleanup of old tasks

**Type:** Instance method

#### test_get_system_configuration

```python
def test_get_system_configuration(self)
```

Test system configuration retrieval

**Type:** Instance method

#### test_update_system_limits

```python
def test_update_system_limits(self)
```

Test system limits update

**Type:** Instance method

#### test_get_error_statistics

```python
def test_get_error_statistics(self)
```

Test error statistics retrieval

**Type:** Instance method

#### test_generate_admin_report

```python
def test_generate_admin_report(self)
```

Test comprehensive admin report generation

**Type:** Instance method

#### test_authorization_check

```python
def test_authorization_check(self)
```

Test admin authorization checking

**Type:** Instance method


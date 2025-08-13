# tests.test_task_queue_manager

Unit tests for Task Queue Manager

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/tests/test_task_queue_manager.py`

## Classes

### TestTaskQueueManager

```python
class TestTaskQueueManager(unittest.TestCase)
```

Test cases for TaskQueueManager

**Methods:**

#### setUp

```python
def setUp(self)
```

Set up test fixtures

**Type:** Instance method

#### test_enqueue_task_success

```python
def test_enqueue_task_success(self)
```

Test successful task enqueueing

**Type:** Instance method

#### test_enqueue_task_user_has_active_task

```python
def test_enqueue_task_user_has_active_task(self)
```

Test enqueueing fails when user has active task

**Type:** Instance method

#### test_get_task_status_found

```python
def test_get_task_status_found(self)
```

Test getting task status when task exists

**Type:** Instance method

#### test_get_task_status_not_found

```python
def test_get_task_status_not_found(self)
```

Test getting task status when task doesn't exist

**Type:** Instance method

#### test_cancel_task_success

```python
def test_cancel_task_success(self)
```

Test successful task cancellation

**Type:** Instance method

#### test_cancel_task_unauthorized

```python
def test_cancel_task_unauthorized(self)
```

Test task cancellation fails for unauthorized user

**Type:** Instance method

#### test_cancel_task_cannot_be_cancelled

```python
def test_cancel_task_cannot_be_cancelled(self)
```

Test task cancellation fails when task cannot be cancelled

**Type:** Instance method

#### test_get_next_task_at_max_concurrent

```python
def test_get_next_task_at_max_concurrent(self)
```

Test getting next task when at max concurrent tasks

**Type:** Instance method

#### test_get_next_task_success

```python
def test_get_next_task_success(self)
```

Test successful next task retrieval

**Type:** Instance method

#### test_complete_task_success

```python
def test_complete_task_success(self)
```

Test successful task completion

**Type:** Instance method

#### test_complete_task_with_error

```python
def test_complete_task_with_error(self)
```

Test task completion with error

**Type:** Instance method

#### test_cleanup_completed_tasks

```python
def test_cleanup_completed_tasks(self)
```

Test cleanup of old completed tasks

**Type:** Instance method

#### test_get_user_active_task

```python
def test_get_user_active_task(self)
```

Test getting user's active task

**Type:** Instance method

#### test_get_queue_stats

```python
def test_get_queue_stats(self)
```

Test getting queue statistics

**Type:** Instance method

#### test_get_user_task_history

```python
def test_get_user_task_history(self)
```

Test getting user task history

**Type:** Instance method


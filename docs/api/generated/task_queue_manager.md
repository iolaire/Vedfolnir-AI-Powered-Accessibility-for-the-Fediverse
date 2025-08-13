# task_queue_manager

Task Queue Manager for Caption Generation

This module manages the queuing and execution of caption generation tasks,
ensuring single-task-per-user enforcement and proper resource management.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/task_queue_manager.py`

## Classes

### TaskQueueManager

```python
class TaskQueueManager
```

Manages caption generation task queue with single-task-per-user enforcement

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager, max_concurrent_tasks: int)
```

**Type:** Instance method

#### enqueue_task

```python
def enqueue_task(self, task: CaptionGenerationTask) -> str
```

Enqueue a caption generation task

Args:
    task: The CaptionGenerationTask to enqueue
    
Returns:
    str: The task ID if successful
    
Raises:
    ValueError: If user already has an active task
    SQLAlchemyError: If database operation fails

**Type:** Instance method

#### get_task_status

```python
def get_task_status(self, task_id: str) -> Optional[TaskStatus]
```

Get the status of a task

Args:
    task_id: The task ID to check
    
Returns:
    TaskStatus or None if task not found

**Type:** Instance method

#### get_task

```python
def get_task(self, task_id: str) -> Optional[CaptionGenerationTask]
```

Get a task by ID

Args:
    task_id: The task ID to retrieve
    
Returns:
    CaptionGenerationTask or None if not found

**Type:** Instance method

#### cancel_task

```python
def cancel_task(self, task_id: str, user_id: int) -> bool
```

Cancel a task

Args:
    task_id: The task ID to cancel
    user_id: Optional user ID for authorization check
    
Returns:
    bool: True if task was cancelled, False otherwise

**Type:** Instance method

#### get_next_task

```python
def get_next_task(self) -> Optional[CaptionGenerationTask]
```

Get the next task to execute, considering priority

Returns:
    CaptionGenerationTask or None if no tasks available

**Type:** Instance method

#### complete_task

```python
def complete_task(self, task_id: str, success: bool, error_message: str) -> bool
```

Mark a task as completed

Args:
    task_id: The task ID to complete
    success: Whether the task completed successfully
    error_message: Optional error message if task failed
    
Returns:
    bool: True if task was marked as completed

**Type:** Instance method

#### cleanup_completed_tasks

```python
def cleanup_completed_tasks(self, older_than_hours: int) -> int
```

Clean up completed tasks older than specified hours

Args:
    older_than_hours: Remove tasks completed more than this many hours ago
    
Returns:
    int: Number of tasks cleaned up

**Type:** Instance method

#### get_user_active_task

```python
def get_user_active_task(self, user_id: int) -> Optional[CaptionGenerationTask]
```

Get the active task for a user

Args:
    user_id: The user ID to check
    
Returns:
    CaptionGenerationTask or None if no active task

**Type:** Instance method

#### get_queue_stats

```python
def get_queue_stats(self) -> Dict[str, int]
```

Get statistics about the task queue

Returns:
    Dict with queue statistics

**Type:** Instance method

#### get_user_task_history

```python
def get_user_task_history(self, user_id: int, limit: int) -> List[CaptionGenerationTask]
```

Get task history for a user

Args:
    user_id: The user ID
    limit: Maximum number of tasks to return
    
Returns:
    List of CaptionGenerationTask objects

**Type:** Instance method


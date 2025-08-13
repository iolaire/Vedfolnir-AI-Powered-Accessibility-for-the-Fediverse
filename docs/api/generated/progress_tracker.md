# progress_tracker

Progress Tracking System for Caption Generation

This module provides real-time progress tracking for caption generation tasks,
storing progress data and providing retrieval methods with user authorization.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/progress_tracker.py`

## Classes

### ProgressStatus

```python
class ProgressStatus
```

Progress status data structure

**Decorators:**
- `@dataclass`

**Methods:**

#### to_dict

```python
def to_dict(self) -> Dict[str, Any]
```

Convert to dictionary for JSON serialization

**Type:** Instance method

### ProgressTracker

```python
class ProgressTracker
```

Tracks progress of caption generation tasks with real-time updates

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager)
```

**Type:** Instance method

#### create_progress_session

```python
def create_progress_session(self, task_id: str, user_id: int) -> str
```

Create a progress tracking session for a task

Args:
    task_id: The task ID to track
    user_id: The user ID for authorization
    
Returns:
    str: Session ID (same as task_id for simplicity)
    
Raises:
    ValueError: If task not found or user not authorized

**Type:** Instance method

#### update_progress

```python
def update_progress(self, task_id: str, current_step: str, progress_percent: int, details: Dict[str, Any]) -> bool
```

Update progress for a task

Args:
    task_id: The task ID to update
    current_step: Description of current processing step
    progress_percent: Progress percentage (0-100)
    details: Optional additional details
    
Returns:
    bool: True if update was successful

**Type:** Instance method

#### get_progress

```python
def get_progress(self, task_id: str, user_id: int) -> Optional[ProgressStatus]
```

Get current progress for a task

Args:
    task_id: The task ID to check
    user_id: Optional user ID for authorization check
    
Returns:
    ProgressStatus or None if not found or unauthorized

**Type:** Instance method

#### complete_progress

```python
def complete_progress(self, task_id: str, results: GenerationResults) -> bool
```

Mark progress as complete and store results

Args:
    task_id: The task ID to complete
    results: The generation results
    
Returns:
    bool: True if completion was successful

**Type:** Instance method

#### register_callback

```python
def register_callback(self, task_id: str, callback: Callable[[ProgressStatus], None])
```

Register a callback for progress updates

Args:
    task_id: The task ID to monitor
    callback: Function to call with progress updates

**Type:** Instance method

#### unregister_callback

```python
def unregister_callback(self, task_id: str, callback: Callable[[ProgressStatus], None])
```

Unregister a callback for progress updates

Args:
    task_id: The task ID to stop monitoring
    callback: The callback function to remove

**Type:** Instance method

#### cleanup_callbacks

```python
def cleanup_callbacks(self, task_id: str)
```

Clean up all callbacks for a task

Args:
    task_id: The task ID to clean up

**Type:** Instance method

#### _notify_callbacks

```python
def _notify_callbacks(self, task_id: str, progress_status: ProgressStatus)
```

Notify all registered callbacks for a task

Args:
    task_id: The task ID
    progress_status: The progress status to send

**Type:** Instance method

#### get_active_progress_sessions

```python
def get_active_progress_sessions(self) -> Dict[str, ProgressStatus]
```

Get all active progress sessions

Returns:
    Dict mapping task_id to ProgressStatus for active tasks

**Type:** Instance method

#### create_progress_callback

```python
def create_progress_callback(self, task_id: str) -> Callable[[str, int, Dict[str, Any]], None]
```

Create a progress callback function for use with caption generation

Args:
    task_id: The task ID to update
    
Returns:
    Callable that can be used as a progress callback

**Type:** Instance method


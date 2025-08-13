# sse_progress_handler

Server-Sent Events (SSE) Progress Handler

This module provides real-time progress updates using Server-Sent Events instead of WebSockets.
SSE is simpler, more reliable, and works better with strict CORS policies.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/sse_progress_handler.py`

## Classes

### SSEProgressHandler

```python
class SSEProgressHandler
```

Handles Server-Sent Events for real-time progress updates

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager, progress_tracker: ProgressTracker, task_queue_manager: TaskQueueManager)
```

**Type:** Instance method

#### create_event_stream

```python
def create_event_stream(self, task_id: str) -> Generator[str, None, None]
```

Create a Server-Sent Events stream for a specific task

Args:
    task_id: The task ID to monitor
    
Yields:
    SSE formatted strings with progress updates

**Type:** Instance method

#### _check_rate_limit

```python
def _check_rate_limit(self, user_id: str) -> bool
```

Check if user is within rate limits

**Type:** Instance method

#### _verify_task_access

```python
def _verify_task_access(self, task_id: str, user_id: int) -> bool
```

Verify user has access to the specified task

**Type:** Instance method

#### _is_task_active

```python
def _is_task_active(self, task_id: str) -> bool
```

Check if task is still active/running

**Type:** Instance method

#### broadcast_progress_update

```python
def broadcast_progress_update(self, task_id: str, progress_data: dict)
```

Broadcast progress update to all connected clients for a task
Note: In SSE, clients poll for updates rather than receiving pushes

**Type:** Instance method

#### broadcast_task_completion

```python
def broadcast_task_completion(self, task_id: str, results: dict)
```

Broadcast task completion to all connected clients

**Type:** Instance method

#### broadcast_task_error

```python
def broadcast_task_error(self, task_id: str, error_message: str)
```

Broadcast task error to all connected clients

**Type:** Instance method

#### cleanup_task_connections

```python
def cleanup_task_connections(self, task_id: str)
```

Clean up all connections for a completed task

**Type:** Instance method

#### get_connection_count

```python
def get_connection_count(self, task_id: str) -> int
```

Get number of active connections for a task

**Type:** Instance method

#### get_total_connections

```python
def get_total_connections(self) -> int
```

Get total number of active connections

**Type:** Instance method


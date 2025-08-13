# websocket_progress_handler

WebSocket Progress Handler for Caption Generation

This module provides real-time progress updates to web clients using WebSocket connections.
It handles connection management, user authentication, and progress broadcasting.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/websocket_progress_handler.py`

## Classes

### WebSocketProgressHandler

```python
class WebSocketProgressHandler
```

Handles WebSocket connections for real-time progress updates

**Methods:**

#### __init__

```python
def __init__(self, socketio: SocketIO, db_manager: DatabaseManager, progress_tracker: ProgressTracker, task_queue_manager: TaskQueueManager)
```

**Type:** Instance method

#### _register_handlers

```python
def _register_handlers(self)
```

Register SocketIO event handlers with security enhancements

**Type:** Instance method

#### _check_connection_rate_limit

```python
def _check_connection_rate_limit(self, limit, window_seconds)
```

Check WebSocket connection rate limiting

**Type:** Instance method

#### connect

```python
def connect(self, task_id: str, user_id: int) -> bool
```

Connect to progress updates for a task (programmatic interface)

Args:
    task_id: The task ID to monitor
    user_id: The user ID for authorization
    
Returns:
    bool: True if connection was successful

**Type:** Instance method

#### broadcast_progress

```python
def broadcast_progress(self, task_id: str, progress_data: Dict) -> None
```

Broadcast progress update to all connected clients for a task

Args:
    task_id: The task ID
    progress_data: Progress data to broadcast

**Type:** Instance method

#### disconnect

```python
def disconnect(self, task_id: str, user_id: int) -> None
```

Disconnect from progress updates for a task (programmatic interface)

Args:
    task_id: The task ID to stop monitoring
    user_id: The user ID

**Type:** Instance method

#### _verify_task_access

```python
def _verify_task_access(self, task_id: str, user_id: int) -> bool
```

Verify that a user has access to a task

Args:
    task_id: The task ID to check
    user_id: The user ID to verify
    
Returns:
    bool: True if user has access

**Type:** Instance method

#### _cleanup_connection

```python
def _cleanup_connection(self, session_id: str) -> None
```

Clean up connection tracking when a client disconnects

Args:
    session_id: The session ID that disconnected

**Type:** Instance method

#### _create_progress_callback

```python
def _create_progress_callback(self, task_id: str)
```

Create a progress callback that broadcasts to WebSocket clients

Args:
    task_id: The task ID to broadcast for
    
Returns:
    Callable progress callback function

**Type:** Instance method

#### get_active_connections

```python
def get_active_connections(self) -> Dict[str, int]
```

Get count of active connections per task

Returns:
    Dict mapping task_id to connection count

**Type:** Instance method

#### broadcast_task_completion

```python
def broadcast_task_completion(self, task_id: str, results: Dict) -> None
```

Broadcast task completion to all connected clients

Args:
    task_id: The completed task ID
    results: Task completion results

**Type:** Instance method

#### broadcast_task_error

```python
def broadcast_task_error(self, task_id: str, error_message: str) -> None
```

Broadcast task error to all connected clients

Args:
    task_id: The failed task ID
    error_message: Error message

**Type:** Instance method

#### cleanup_task_connections

```python
def cleanup_task_connections(self, task_id: str) -> None
```

Clean up all connections for a completed task

Args:
    task_id: The task ID to clean up

**Type:** Instance method

#### get_connection_stats

```python
def get_connection_stats(self) -> Dict[str, any]
```

Get statistics about WebSocket connections

Returns:
    Dict with connection statistics

**Type:** Instance method


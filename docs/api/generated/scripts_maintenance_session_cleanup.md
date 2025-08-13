# scripts.maintenance.session_cleanup

Session Cleanup and Maintenance Utility

Provides automated cleanup of expired sessions with configurable intervals,
comprehensive logging, and health monitoring capabilities.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/maintenance/session_cleanup.py`

## Classes

### SessionCleanupService

```python
class SessionCleanupService
```

Automated session cleanup service with configurable intervals

**Methods:**

#### __init__

```python
def __init__(self, config: Config)
```

**Type:** Instance method

#### start_daemon

```python
def start_daemon(self)
```

Start the cleanup daemon

**Type:** Instance method

#### run_cleanup_cycle

```python
def run_cleanup_cycle(self) -> Dict[str, Any]
```

Run a single cleanup cycle

**Type:** Instance method

#### _cleanup_orphaned_sessions

```python
def _cleanup_orphaned_sessions(self) -> int
```

Clean up sessions that reference non-existent users

**Type:** Instance method

#### _optimize_session_tables

```python
def _optimize_session_tables(self) -> int
```

Optimize session-related database tables

**Type:** Instance method

#### get_cleanup_statistics

```python
def get_cleanup_statistics(self) -> Dict[str, Any]
```

Get cleanup service statistics

**Type:** Instance method

#### force_cleanup

```python
def force_cleanup(self, max_age_hours: Optional[int]) -> Dict[str, Any]
```

Force immediate cleanup with optional custom age limit

**Type:** Instance method

#### _signal_handler

```python
def _signal_handler(self, signum, frame)
```

Handle shutdown signals

**Type:** Instance method

#### stop

```python
def stop(self)
```

Stop the cleanup service

**Type:** Instance method

## Functions

### main

```python
def main()
```

Main entry point


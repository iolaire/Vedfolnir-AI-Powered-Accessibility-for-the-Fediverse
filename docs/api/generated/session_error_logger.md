# session_error_logger

Session Error Logger

Specialized logging configuration for database session errors and DetachedInstanceError
tracking with comprehensive context and monitoring capabilities.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_error_logger.py`

## Classes

### SessionErrorLogger

```python
class SessionErrorLogger
```

Specialized logger for session-related errors with structured logging

**Methods:**

#### __init__

```python
def __init__(self, log_dir: str, max_bytes: int, backup_count: int)
```

Initialize session error logger

Args:
    log_dir: Directory for log files
    max_bytes: Maximum size per log file
    backup_count: Number of backup files to keep

**Type:** Instance method

#### _setup_handlers

```python
def _setup_handlers(self)
```

Setup logging handlers for session errors

**Type:** Instance method

#### log_detached_instance_error

```python
def log_detached_instance_error(self, error: Exception, endpoint: str, context: Dict[str, Any])
```

Log DetachedInstanceError with comprehensive context

Args:
    error: The DetachedInstanceError that occurred
    endpoint: Endpoint where error occurred
    context: Additional context information

**Type:** Instance method

#### log_sqlalchemy_error

```python
def log_sqlalchemy_error(self, error: Exception, endpoint: str, context: Dict[str, Any])
```

Log SQLAlchemy error with context

Args:
    error: The SQLAlchemy error that occurred
    endpoint: Endpoint where error occurred
    context: Additional context information

**Type:** Instance method

#### log_session_recovery

```python
def log_session_recovery(self, object_type: str, recovery_time: float, success: bool, endpoint: str)
```

Log session recovery attempt

Args:
    object_type: Type of object being recovered
    recovery_time: Time taken for recovery attempt
    success: Whether recovery was successful
    endpoint: Endpoint where recovery occurred

**Type:** Instance method

#### log_session_validation_failure

```python
def log_session_validation_failure(self, endpoint: str, reason: str, context: Dict[str, Any])
```

Log session validation failure

Args:
    endpoint: Endpoint where validation failed
    reason: Reason for validation failure
    context: Additional context information

**Type:** Instance method

#### log_high_error_frequency

```python
def log_high_error_frequency(self, error_type: str, endpoint: str, count: int, threshold: int)
```

Log when error frequency exceeds threshold

Args:
    error_type: Type of error
    endpoint: Endpoint with high error count
    count: Current error count
    threshold: Threshold that was exceeded

**Type:** Instance method

#### _build_error_context

```python
def _build_error_context(self, error: Optional[Exception], endpoint: str, context: Dict[str, Any]) -> Dict[str, Any]
```

Build comprehensive error context

Args:
    error: The exception that occurred (if any)
    endpoint: Endpoint where error occurred
    context: Additional context information
    
Returns:
    Dictionary with error context

**Type:** Instance method

### JsonFormatter

```python
class JsonFormatter(logging.Formatter)
```

JSON formatter for structured logging

**Methods:**

#### format

```python
def format(self, record)
```

Format log record as JSON

**Type:** Instance method

## Functions

### get_session_error_logger

```python
def get_session_error_logger() -> SessionErrorLogger
```

Get the global session error logger instance

Returns:
    SessionErrorLogger instance

### initialize_session_error_logging

```python
def initialize_session_error_logging(app)
```

Initialize session error logging for Flask app

Args:
    app: Flask application instance


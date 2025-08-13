# logger

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/logger.py`

## Constants

- `ERROR_SUMMARY`

## Classes

### StructuredFormatter

```python
class StructuredFormatter(logging.Formatter)
```

Custom formatter that outputs logs in a structured format (JSON or text)

**Methods:**

#### __init__

```python
def __init__(self, use_json: bool, include_traceback: bool)
```

Initialize the formatter

Args:
    use_json: Whether to output logs as JSON
    include_traceback: Whether to include traceback in error logs

**Type:** Instance method

#### format

```python
def format(self, record: logging.LogRecord) -> str
```

Format the log record

Args:
    record: The log record to format
    
Returns:
    Formatted log string

**Type:** Instance method

### ErrorCollector

```python
class ErrorCollector
```

Collects error information during processing for summary reporting

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### add_error

```python
def add_error(self, error_type: str, message: str, component: str, details: Optional[Dict[str, Any]], exception: Optional[Exception]) -> None
```

Add an error to the collector

Args:
    error_type: Type of error (e.g., "API", "Database", "Processing")
    message: Error message
    component: Component where the error occurred
    details: Additional error details
    exception: Exception object if available

**Type:** Instance method

#### get_summary

```python
def get_summary(self) -> str
```

Get a summary of collected errors

Returns:
    Formatted error summary

**Type:** Instance method

#### get_detailed_report

```python
def get_detailed_report(self) -> Dict[str, Any]
```

Get a detailed report of collected errors

Returns:
    Dictionary with error information

**Type:** Instance method

#### reset

```python
def reset(self) -> None
```

Reset the error collector

**Type:** Instance method

## Functions

### setup_logging

```python
def setup_logging(log_level: str, log_file: Optional[str], use_json: bool, include_traceback: bool) -> None
```

Set up logging with structured formatter

Args:
    log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    log_file: Path to log file, or None to disable file logging
    use_json: Whether to output logs as JSON
    include_traceback: Whether to include traceback in error logs

### log_with_context

```python
def log_with_context(logger: logging.Logger, level: int, msg: str, extra: Optional[Dict[str, Any]], **kwargs) -> None
```

Log a message with additional context

Args:
    logger: Logger to use
    level: Log level
    msg: Log message
    extra: Additional context to include in the log
    **kwargs: Additional keyword arguments to pass to the logger

### log_error

```python
def log_error(logger: logging.Logger, error_type: str, message: str, component: str, details: Optional[Dict[str, Any]], exception: Optional[Exception]) -> None
```

Log an error and add it to the error collector

Args:
    logger: Logger to use
    error_type: Type of error (e.g., "API", "Database", "Processing")
    message: Error message
    component: Component where the error occurred
    details: Additional error details
    exception: Exception object if available

### log_error_summary

```python
def log_error_summary(logger: logging.Logger) -> None
```

Log a summary of collected errors

Args:
    logger: Logger to use

### get_error_summary

```python
def get_error_summary() -> str
```

Get a summary of collected errors

Returns:
    Formatted error summary

### get_error_report

```python
def get_error_report() -> Dict[str, Any]
```

Get a detailed report of collected errors

Returns:
    Dictionary with error information

### reset_error_collector

```python
def reset_error_collector() -> None
```

Reset the error collector


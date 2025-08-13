# scripts.maintenance.retry_stats

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/scripts/maintenance/retry_stats.py`

## Classes

### RetryStats

```python
class RetryStats
```

Track retry statistics for monitoring and reporting

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method

#### record_operation

```python
def record_operation(self, retried: bool, attempts: int, success: bool, exception_type: Optional[Type[Exception]], status_code: Optional[int], retry_time: float, function_name: Optional[str], endpoint: Optional[str]) -> None
```

Record statistics for an operation

Args:
    retried: Whether the operation was retried
    attempts: Number of attempts made (including the first attempt)
    success: Whether the operation was ultimately successful
    exception_type: Type of exception that triggered retries
    status_code: HTTP status code that triggered retries
    retry_time: Total time spent in retries
    function_name: Name of the function being retried
    endpoint: API endpoint or URL path being accessed

**Type:** Instance method

#### get_summary

```python
def get_summary(self) -> str
```

Get a summary of retry statistics

Returns:
    A formatted string with retry statistics summary

**Type:** Instance method

#### get_detailed_report

```python
def get_detailed_report(self) -> Dict[str, Any]
```

Get a detailed report of retry statistics in dictionary format

Returns:
    A dictionary with detailed retry statistics

**Type:** Instance method

#### reset

```python
def reset(self) -> None
```

Reset all statistics

**Type:** Instance method

## Functions

### extract_endpoint_from_args

```python
def extract_endpoint_from_args(args, kwargs) -> Optional[str]
```

Extract endpoint information from function arguments

Args:
    args: Positional arguments
    kwargs: Keyword arguments
    
Returns:
    Endpoint string or None if not found

### get_retry_stats_summary

```python
def get_retry_stats_summary() -> str
```

Get a summary of retry statistics

Returns:
    A formatted string with retry statistics summary

### get_retry_stats_detailed

```python
def get_retry_stats_detailed() -> Dict[str, Any]
```

Get detailed retry statistics in dictionary format

Returns:
    A dictionary with detailed retry statistics

### reset_retry_stats

```python
def reset_retry_stats() -> None
```

Reset all retry statistics


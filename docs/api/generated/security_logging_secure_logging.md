# security.logging.secure_logging

Secure Logging Utilities

Provides secure logging that prevents sensitive data exposure and log injection.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/logging/secure_logging.py`

## Classes

### SecureLogger

```python
class SecureLogger
```

Secure logger that sanitizes sensitive data

**Methods:**

#### __init__

```python
def __init__(self, name: str)
```

**Type:** Instance method

#### _sanitize_message

```python
def _sanitize_message(self, message: str) -> str
```

Sanitize log message to remove sensitive data

**Type:** Instance method

#### debug

```python
def debug(self, message: Any, *args, **kwargs)
```

Log debug message securely

**Type:** Instance method

#### info

```python
def info(self, message: Any, *args, **kwargs)
```

Log info message securely

**Type:** Instance method

#### warning

```python
def warning(self, message: Any, *args, **kwargs)
```

Log warning message securely

**Type:** Instance method

#### error

```python
def error(self, message: Any, *args, **kwargs)
```

Log error message securely

**Type:** Instance method

#### critical

```python
def critical(self, message: Any, *args, **kwargs)
```

Log critical message securely

**Type:** Instance method

#### exception

```python
def exception(self, message: Any, *args, **kwargs)
```

Log exception message securely

**Type:** Instance method

## Functions

### get_secure_logger

```python
def get_secure_logger(name: str) -> SecureLogger
```

Get a secure logger instance

### log_security_event

```python
def log_security_event(event_type: str, details: Dict[str, Any])
```

Log security events with proper sanitization


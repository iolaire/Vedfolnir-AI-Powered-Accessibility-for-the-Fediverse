# security.core.security_utils

Security utilities for the Vedfolnir application.

This module provides security-related utility functions including input sanitization,
log injection prevention, and other security measures.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/core/security_utils.py`

## Functions

### sanitize_for_log

```python
def sanitize_for_log(value: Any) -> str
```

Sanitize a value for safe logging to prevent log injection attacks.

This function removes or escapes potentially dangerous characters that could
be used for log injection attacks, including newlines, carriage returns,
and other control characters.

Args:
    value: The value to sanitize (will be converted to string)
    
Returns:
    Sanitized string safe for logging

### sanitize_filename

```python
def sanitize_filename(filename: str) -> str
```

Sanitize a filename to prevent directory traversal and other file system attacks.

Args:
    filename: The filename to sanitize
    
Returns:
    Sanitized filename safe for file system operations

### validate_url

```python
def validate_url(url: str) -> bool
```

Validate that a URL is safe and well-formed.

Args:
    url: The URL to validate
    
Returns:
    True if the URL is valid and safe, False otherwise

### sanitize_html_input

```python
def sanitize_html_input(text: str) -> str
```

Sanitize HTML input to prevent XSS attacks.

Args:
    text: The text to sanitize
    
Returns:
    Sanitized text with HTML entities escaped

### validate_image_extension

```python
def validate_image_extension(filename: str) -> bool
```

Validate that a filename has a safe image extension.

Args:
    filename: The filename to validate
    
Returns:
    True if the extension is a safe image format, False otherwise

### truncate_text

```python
def truncate_text(text: str, max_length: int, suffix: str) -> str
```

Safely truncate text to a maximum length.

Args:
    text: The text to truncate
    max_length: Maximum allowed length
    suffix: Suffix to add when truncating
    
Returns:
    Truncated text

### validate_user_input

```python
def validate_user_input(text: str, max_length: int, allow_html: bool) -> Optional[str]
```

Validate and sanitize user input.

Args:
    text: The text to validate
    max_length: Maximum allowed length
    allow_html: Whether to allow HTML (will be escaped if False)
    
Returns:
    Sanitized text if valid, None if invalid

### generate_safe_id

```python
def generate_safe_id(prefix: str, length: int) -> str
```

Generate a safe identifier string.

Args:
    prefix: Optional prefix for the ID
    length: Length of the random part
    
Returns:
    Safe identifier string

### is_safe_path

```python
def is_safe_path(path: str, base_dir: str) -> bool
```

Check if a file path is safe (within the base directory).

Args:
    path: The file path to check
    base_dir: The base directory that should contain the path
    
Returns:
    True if the path is safe, False otherwise

### mask_sensitive_data

```python
def mask_sensitive_data(data: str, mask_char: str, visible_chars: int) -> str
```

Mask sensitive data for logging or display.

Args:
    data: The sensitive data to mask
    mask_char: Character to use for masking
    visible_chars: Number of characters to leave visible at the end
    
Returns:
    Masked string


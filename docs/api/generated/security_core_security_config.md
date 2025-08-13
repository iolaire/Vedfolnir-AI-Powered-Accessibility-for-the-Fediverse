# security.core.security_config

Security Configuration for Vedfolnir

This module contains security-related configuration settings and constants
to ensure consistent security practices across the application.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/security/core/security_config.py`

## Constants

- `SECURITY_HEADERS`
- `SENSITIVE_PATTERNS`
- `ALLOWED_HTML_TAGS`
- `ALLOWED_HTML_ATTRIBUTES`

## Classes

### SecurityConfig

```python
class SecurityConfig
```

Security configuration settings

**Decorators:**
- `@dataclass`

**Methods:**

#### __post_init__

```python
def __post_init__(self)
```

Initialize default values that depend on environment

**Type:** Instance method

#### get_csp_header

```python
def get_csp_header(self) -> str
```

Generate Content Security Policy header value

**Type:** Instance method

#### is_secure_environment

```python
def is_secure_environment(self) -> bool
```

Check if running in a secure environment (HTTPS)

**Type:** Instance method


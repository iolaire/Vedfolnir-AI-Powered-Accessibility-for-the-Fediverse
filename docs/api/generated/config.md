# config

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/config.py`

## Classes

### RetryConfig

```python
class RetryConfig
```

Configuration for retry behavior

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

**Decorators:**
- `@classmethod`

**Type:** Class method

### RateLimitConfig

```python
class RateLimitConfig
```

Configuration for rate limiting behavior

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

Create a RateLimitConfig from environment variables

**Decorators:**
- `@classmethod`

**Type:** Class method

### ConfigurationError

```python
class ConfigurationError(Exception)
```

Raised when configuration is invalid or incomplete

### ActivityPubConfig

```python
class ActivityPubConfig
```

Configuration for ActivityPub client

**Decorators:**
- `@dataclass`

**Methods:**

#### __post_init__

```python
def __post_init__(self)
```

Validate configuration after initialization

**Type:** Instance method

#### _validate_configuration

```python
def _validate_configuration(self)
```

Validate platform-specific configuration requirements

**Type:** Instance method

#### from_env

```python
def from_env(cls)
```

**Decorators:**
- `@classmethod`

**Type:** Class method

### CaptionConfig

```python
class CaptionConfig
```

Configuration for caption generation and formatting

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

Create a CaptionConfig from environment variables

**Decorators:**
- `@classmethod`

**Type:** Class method

### FallbackConfig

```python
class FallbackConfig
```

Configuration for caption generation fallback mechanisms

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

Create a FallbackConfig from environment variables

**Decorators:**
- `@classmethod`

**Type:** Class method

### OllamaConfig

```python
class OllamaConfig
```

Configuration for Ollama with llava model

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

**Decorators:**
- `@classmethod`

**Type:** Class method

### DatabaseConfig

```python
class DatabaseConfig
```

Configuration for database connection and performance

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

**Decorators:**
- `@classmethod`

**Type:** Class method

### StorageConfig

```python
class StorageConfig
```

Configuration for storage paths

**Decorators:**
- `@dataclass`

**Methods:**

#### __post_init__

```python
def __post_init__(self)
```

**Type:** Instance method

#### from_env

```python
def from_env(cls)
```

**Decorators:**
- `@classmethod`

**Type:** Class method

### AuthConfig

```python
class AuthConfig
```

Configuration for authentication

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

**Decorators:**
- `@classmethod`

**Type:** Class method

### BatchUpdateConfig

```python
class BatchUpdateConfig
```

Configuration for batch update functionality

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

**Decorators:**
- `@classmethod`

**Type:** Class method

### WebAppConfig

```python
class WebAppConfig
```

Configuration for Flask web app

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

**Decorators:**
- `@classmethod`

**Type:** Class method

### Config

```python
class Config
```

Main configuration class

**Properties:**
- `session`

**Methods:**

#### __init__

```python
def __init__(self)
```

**Type:** Instance method


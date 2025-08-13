# session_config

Session Management Configuration System

Provides comprehensive configuration management for session timeouts, cleanup intervals,
feature flags, and environment-specific settings for the session management system.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_config.py`

## Classes

### SessionEnvironment

```python
class SessionEnvironment(Enum)
```

Session management environment types

**Class Variables:**
- `DEVELOPMENT`
- `TESTING`
- `STAGING`
- `PRODUCTION`

### SessionTimeoutConfig

```python
class SessionTimeoutConfig
```

Configuration for session timeout behavior

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

Create SessionTimeoutConfig from environment variables

**Decorators:**
- `@classmethod`

**Type:** Class method

### SessionCleanupConfig

```python
class SessionCleanupConfig
```

Configuration for session cleanup behavior

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

Create SessionCleanupConfig from environment variables

**Decorators:**
- `@classmethod`

**Type:** Class method

### SessionSyncConfig

```python
class SessionSyncConfig
```

Configuration for cross-tab session synchronization

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

Create SessionSyncConfig from environment variables

**Decorators:**
- `@classmethod`

**Type:** Class method

### SessionSecurityConfig

```python
class SessionSecurityConfig
```

Configuration for session security features

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

Create SessionSecurityConfig from environment variables

**Decorators:**
- `@classmethod`

**Type:** Class method

### SessionMonitoringConfig

```python
class SessionMonitoringConfig
```

Configuration for session monitoring and metrics

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

Create SessionMonitoringConfig from environment variables

**Decorators:**
- `@classmethod`

**Type:** Class method

### SessionFeatureFlags

```python
class SessionFeatureFlags
```

Feature flags for session management components

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

Create SessionFeatureFlags from environment variables

**Decorators:**
- `@classmethod`

**Type:** Class method

### SessionConfig

```python
class SessionConfig
```

Comprehensive session management configuration

**Decorators:**
- `@dataclass`

**Methods:**

#### from_env

```python
def from_env(cls)
```

Create SessionConfig from environment variables

**Decorators:**
- `@classmethod`

**Type:** Class method

#### get_environment_specific_config

```python
def get_environment_specific_config(self) -> Dict[str, Any]
```

Get environment-specific configuration overrides

**Type:** Instance method

#### apply_environment_overrides

```python
def apply_environment_overrides(self)
```

Apply environment-specific configuration overrides

**Type:** Instance method

#### validate_configuration

```python
def validate_configuration(self) -> List[str]
```

Validate configuration and return list of issues

**Type:** Instance method

#### get_config_summary

```python
def get_config_summary(self) -> Dict[str, Any]
```

Get a summary of current configuration

**Type:** Instance method

## Functions

### get_session_config

```python
def get_session_config() -> SessionConfig
```

Get or create global session configuration instance

### reload_session_config

```python
def reload_session_config()
```

Reload session configuration from environment


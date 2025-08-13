# health_check

Health check module for Vedfolnir system monitoring.

This module provides health check functionality for various system components
including database connectivity, Ollama service, ActivityPub client, and
overall system status.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/health_check.py`

## Classes

### HealthStatus

```python
class HealthStatus(Enum)
```

Health check status enumeration

**Class Variables:**
- `HEALTHY`
- `DEGRADED`
- `UNHEALTHY`

### ComponentHealth

```python
class ComponentHealth
```

Health status for a system component

**Decorators:**
- `@dataclass`

### SystemHealth

```python
class SystemHealth
```

Overall system health status

**Decorators:**
- `@dataclass`

### HealthChecker

```python
class HealthChecker
```

System health checker

**Methods:**

#### __init__

```python
def __init__(self, config: Config, db_manager: DatabaseManager)
```

**Type:** Instance method

#### get_uptime

```python
def get_uptime(self) -> float
```

Get system uptime in seconds

**Type:** Instance method

#### check_database_health

```python
async def check_database_health(self) -> ComponentHealth
```

Check database connectivity and performance

**Type:** Instance method

#### check_ollama_health

```python
async def check_ollama_health(self) -> ComponentHealth
```

Check Ollama service connectivity and model availability

**Type:** Instance method

#### check_activitypub_health

```python
async def check_activitypub_health(self) -> ComponentHealth
```

Check ActivityPub connectivity using platform-aware configuration

**Type:** Instance method

#### check_storage_health

```python
async def check_storage_health(self) -> ComponentHealth
```

Check file storage health

**Type:** Instance method

#### check_system_health

```python
async def check_system_health(self) -> SystemHealth
```

Perform comprehensive system health check

**Type:** Instance method

#### to_dict

```python
def to_dict(self, system_health: SystemHealth) -> Dict[str, Any]
```

Convert SystemHealth to dictionary for JSON serialization

**Type:** Instance method


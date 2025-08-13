# session_health_checker

Session Management Health Checker

Provides comprehensive health checking for session management components including
database sessions, cross-tab synchronization, platform switching, and performance monitoring.

**File Path:** `/Volumes/Gold/DevContainerTesting/vedfolnir/session_health_checker.py`

## Classes

### SessionHealthStatus

```python
class SessionHealthStatus(Enum)
```

Session health status enumeration

**Class Variables:**
- `HEALTHY`
- `DEGRADED`
- `UNHEALTHY`

### SessionComponentHealth

```python
class SessionComponentHealth
```

Health status for a session management component

**Decorators:**
- `@dataclass`

### SessionSystemHealth

```python
class SessionSystemHealth
```

Overall session system health status

**Decorators:**
- `@dataclass`

### SessionHealthChecker

```python
class SessionHealthChecker
```

Comprehensive health checker for session management system

**Methods:**

#### __init__

```python
def __init__(self, db_manager: DatabaseManager, session_manager: SessionManager)
```

**Type:** Instance method

#### check_database_session_health

```python
def check_database_session_health(self) -> SessionComponentHealth
```

Check database session management health

**Type:** Instance method

#### check_session_monitoring_health

```python
def check_session_monitoring_health(self) -> SessionComponentHealth
```

Check session monitoring system health

**Type:** Instance method

#### check_platform_switching_health

```python
def check_platform_switching_health(self) -> SessionComponentHealth
```

Check platform switching functionality health

**Type:** Instance method

#### check_session_cleanup_health

```python
def check_session_cleanup_health(self) -> SessionComponentHealth
```

Check session cleanup system health

**Type:** Instance method

#### check_session_security_health

```python
def check_session_security_health(self) -> SessionComponentHealth
```

Check session security system health

**Type:** Instance method

#### check_comprehensive_session_health

```python
def check_comprehensive_session_health(self) -> SessionSystemHealth
```

Perform comprehensive session system health check

**Type:** Instance method

#### to_dict

```python
def to_dict(self, system_health: SessionSystemHealth) -> Dict[str, Any]
```

Convert SessionSystemHealth to dictionary for JSON serialization

**Type:** Instance method

## Functions

### get_session_health_checker

```python
def get_session_health_checker(db_manager: DatabaseManager, session_manager: SessionManager) -> SessionHealthChecker
```

Get or create global session health checker instance


# Configuration Integration System - API Reference

## Overview

The Configuration Integration System provides a comprehensive solution for managing system configuration with real-time updates, caching, and service integration. This document provides detailed API reference for all components.

## Table of Contents

1. [ConfigurationService](#configurationservice)
2. [Configuration Adapters](#configuration-adapters)
3. [Feature Flag Service](#feature-flag-service)
4. [Maintenance Mode Service](#maintenance-mode-service)
5. [Configuration Event Bus](#configuration-event-bus)
6. [Configuration Cache](#configuration-cache)
7. [Error Handling](#error-handling)
8. [Data Models](#data-models)

## ConfigurationService

The core service providing cached, high-performance access to configuration values.

### Class: `ConfigurationService`

**Location**: `configuration_service.py`

#### Constructor

```python
def __init__(self, db_manager: DatabaseManager, cache_size: int = 1000, 
             default_ttl: int = 300, environment_prefix: str = "VEDFOLNIR_CONFIG_")
```

**Parameters**:
- `db_manager`: Database manager instance
- `cache_size`: Maximum cache size (default: 1000)
- `default_ttl`: Default cache TTL in seconds (default: 300)
- `environment_prefix`: Environment variable prefix for overrides

#### Core Methods

##### `get_config(key: str, default: Any = None) -> Any`

Retrieves configuration value with fallback chain.

**Parameters**:
- `key`: Configuration key
- `default`: Default value if not found

**Returns**: Configuration value or default

**Fallback Chain**:
1. Cache (if available)
2. Environment variable (`{prefix}{KEY}`)
3. Database value
4. Schema default
5. Provided default

**Example**:
```python
config_service = ConfigurationService(db_manager)
max_jobs = config_service.get_config('max_concurrent_jobs', 10)
```

##### `get_config_with_metadata(key: str) -> Optional[ConfigurationValue]`

Retrieves configuration value with complete metadata.

**Returns**: `ConfigurationValue` object with source, type, and timing information

**Example**:
```python
config_value = config_service.get_config_with_metadata('session_timeout_minutes')
print(f"Value: {config_value.value}, Source: {config_value.source.value}")
```

##### `refresh_config(key: str = None) -> bool`

Refreshes configuration cache.

**Parameters**:
- `key`: Specific key to refresh, or None for all

**Returns**: True if successful

##### `subscribe_to_changes(key: str, callback: Callable) -> str`

Subscribes to configuration changes.

**Parameters**:
- `key`: Configuration key to watch
- `callback`: Function called with `(key, old_value, new_value)`

**Returns**: Subscription ID for unsubscribing

**Example**:
```python
def on_timeout_change(key, old_value, new_value):
    print(f"Timeout changed from {old_value} to {new_value}")

subscription_id = config_service.subscribe_to_changes(
    'session_timeout_minutes', 
    on_timeout_change
)
```

##### `unsubscribe(subscription_id: str) -> bool`

Removes a configuration change subscription.

##### `is_restart_required() -> bool`

Checks if any pending configuration changes require application restart.

##### `get_pending_restart_configs() -> List[str]`

Returns list of configuration keys requiring restart.

##### `get_cache_stats() -> Dict[str, Any]`

Returns cache and service statistics including hit rates and performance metrics.

## Configuration Adapters

Adapters connect existing services with the configuration system for dynamic updates.

### TaskQueueConfigurationAdapter

**Location**: `task_queue_configuration_adapter.py`

Connects TaskQueueManager with ConfigurationService for dynamic concurrency and timeout control.

#### Constructor

```python
def __init__(self, task_queue_manager: TaskQueueManager, config_service: ConfigurationService)
```

#### Configuration Keys

- `max_concurrent_jobs`: Maximum concurrent task execution
- `default_job_timeout`: Default timeout for job execution  
- `queue_size_limit`: Maximum number of queued jobs

#### Methods

##### `update_concurrency_limits() -> bool`

Updates task queue concurrency limits from configuration.

##### `update_timeout_settings() -> bool`

Updates job timeout settings from configuration.

##### `update_queue_size_limits() -> bool`

Updates queue size limits with proper error handling.

### SessionConfigurationAdapter

**Location**: `session_configuration_adapter.py`

Connects session management systems with configuration service.

#### Constructor

```python
def __init__(self, config_service: ConfigurationService, 
             redis_session_manager: Optional[RedisSessionManager] = None,
             unified_session_manager: Optional[UnifiedSessionManager] = None,
             flask_session_interface: Optional[FlaskRedisSessionInterface] = None)
```

#### Configuration Keys

- `session_timeout_minutes`: Session timeout in minutes
- `session_security_enabled`: Enable session security features
- `rate_limit_per_user_per_hour`: Rate limiting threshold
- `max_concurrent_sessions_per_user`: Maximum concurrent sessions
- `session_fingerprinting_enabled`: Enable session fingerprinting
- `audit_log_retention_days`: Audit log retention period

#### Methods

##### `update_session_timeout(timeout_minutes: int) -> bool`

Updates session timeout for all session managers.

##### `update_security_settings(security_enabled: bool) -> bool`

Updates session security settings.

##### `update_rate_limiting(rate_limit: int) -> bool`

Updates rate limiting configuration.

### AlertConfigurationAdapter

**Location**: `alert_configuration_adapter.py`

Connects AlertManager with ConfigurationService for dynamic alert thresholds.

#### Constructor

```python
def __init__(self, alert_manager: AlertManager, config_service: ConfigurationService,
             event_bus: Optional[ConfigurationEventBus] = None,
             threshold_validator: Optional[AlertThresholdValidator] = None)
```

#### Configuration Keys

- `alert_job_failure_rate_threshold`: Job failure rate threshold (0.0-1.0)
- `alert_repeated_failure_count_threshold`: Repeated failure count threshold
- `alert_resource_usage_threshold`: Resource usage threshold (0.0-1.0)
- `alert_queue_backup_threshold`: Queue backup threshold
- `alert_ai_service_timeout_threshold`: AI service timeout threshold
- `alert_performance_degradation_threshold`: Performance degradation threshold

#### Methods

##### `update_alert_thresholds() -> bool`

Updates all alert thresholds from configuration.

##### `update_notification_channels() -> bool`

Updates notification channel configuration.

##### `validate_threshold_change(key: str, value: Any) -> ValidationResult`

Validates threshold changes before applying.

## Feature Flag Service

**Location**: `feature_flag_service.py`

Centralized feature flag management with real-time updates.

### Class: `FeatureFlagService`

#### Constructor

```python
def __init__(self, config_service: ConfigurationService)
```

#### Methods

##### `is_enabled(feature: str) -> bool`

Checks if a feature flag is enabled.

**Example**:
```python
flag_service = FeatureFlagService(config_service)
if flag_service.is_enabled('enable_batch_processing'):
    # Execute batch processing logic
    pass
```

##### `get_all_flags() -> Dict[str, bool]`

Returns all feature flags and their current states.

##### `refresh_flags() -> None`

Refreshes feature flag cache from configuration.

##### `subscribe_to_flag_changes(feature: str, callback: Callable) -> str`

Subscribes to feature flag changes.

## Maintenance Mode Service

**Location**: `maintenance_mode_service.py`

Centralized maintenance mode control with immediate effect.

### Class: `MaintenanceModeService`

#### Constructor

```python
def __init__(self, config_service: ConfigurationService)
```

#### Methods

##### `is_maintenance_mode() -> bool`

Checks if maintenance mode is currently active.

##### `get_maintenance_reason() -> str`

Returns the current maintenance reason message.

##### `get_maintenance_status() -> MaintenanceStatus`

Returns complete maintenance status information.

**Example**:
```python
maintenance_service = MaintenanceModeService(config_service)
if maintenance_service.is_maintenance_mode():
    reason = maintenance_service.get_maintenance_reason()
    return f"System under maintenance: {reason}", 503
```

## Configuration Event Bus

**Location**: `configuration_event_bus.py`

Event system for configuration change notifications.

### Class: `ConfigurationEventBus`

#### Methods

##### `publish(event: ConfigurationChangeEvent) -> None`

Publishes a configuration change event.

##### `subscribe(key: str, callback: Callable) -> str`

Subscribes to configuration changes for a specific key.

##### `unsubscribe(subscription_id: str) -> bool`

Removes a subscription.

## Configuration Cache

**Location**: `configuration_cache.py`

High-performance caching layer with intelligent invalidation.

### Class: `ConfigurationCache`

#### Methods

##### `get(key: str) -> Optional[ConfigurationValue]`

Retrieves cached configuration value.

##### `set(key: str, value: ConfigurationValue, ttl: int = None) -> None`

Stores configuration value in cache.

##### `invalidate(key: str) -> None`

Invalidates specific cache entry.

##### `get_stats() -> CacheStats`

Returns cache performance statistics.

## Error Handling

### Exception Hierarchy

```python
class ConfigurationError(Exception):
    """Base configuration error"""

class ConfigurationNotFoundError(ConfigurationError):
    """Configuration key not found"""

class ConfigurationValidationError(ConfigurationError):
    """Configuration validation failed"""

class ConfigurationCacheError(ConfigurationError):
    """Configuration cache error"""

class ConfigurationServiceUnavailableError(ConfigurationError):
    """Configuration service unavailable"""
```

### Error Handling Patterns

#### Graceful Degradation

```python
try:
    value = config_service.get_config('critical_setting')
except ConfigurationServiceUnavailableError:
    # Fall back to hardcoded default
    value = DEFAULT_CRITICAL_SETTING
    logger.warning("Using fallback value due to configuration service unavailability")
```

#### Validation Error Handling

```python
try:
    config_service.notify_change('invalid_key', old_value, new_value)
except ConfigurationValidationError as e:
    logger.error(f"Configuration validation failed: {e}")
    # Revert to previous value
    config_service.notify_change('invalid_key', new_value, old_value)
```

## Data Models

### ConfigurationValue

```python
@dataclass
class ConfigurationValue:
    key: str
    value: Any
    data_type: str
    source: ConfigurationSource
    requires_restart: bool
    last_updated: datetime
    cached_at: datetime
    ttl: int
```

### ConfigurationSource

```python
class ConfigurationSource(Enum):
    ENVIRONMENT = "environment"
    DATABASE = "database"
    DEFAULT = "default"
    CACHE = "cache"
```

### CacheStats

```python
@dataclass
class CacheStats:
    hits: int
    misses: int
    hit_rate: float
    total_keys: int
    memory_usage: int
    evictions: int
```

## Performance Considerations

### Caching Strategy

- **Default TTL**: 300 seconds (5 minutes)
- **Cache Size**: 1000 entries with LRU eviction
- **Hit Rate Target**: >90% for optimal performance
- **Memory Usage**: ~1-2MB for typical configuration sets

### Best Practices

1. **Use appropriate TTL**: Short TTL for frequently changing values, longer for stable ones
2. **Batch configuration reads**: Group related configuration access when possible
3. **Subscribe to changes**: Use event subscriptions instead of polling
4. **Handle errors gracefully**: Always provide fallback values
5. **Monitor performance**: Track cache hit rates and response times

### Performance Monitoring

```python
# Get performance statistics
stats = config_service.get_cache_stats()
print(f"Cache hit rate: {stats['hit_rate']:.2%}")
print(f"Total requests: {stats['total_requests']}")
print(f"Cache size: {stats['cache']['size']}/{stats['cache']['maxsize']}")
```

## Integration Examples

### Adding New Service Integration

```python
class MyServiceConfigurationAdapter:
    def __init__(self, my_service: MyService, config_service: ConfigurationService):
        self.my_service = my_service
        self.config_service = config_service
        
        # Subscribe to relevant configuration changes
        self.config_service.subscribe_to_changes(
            'my_service_setting',
            self._handle_setting_change
        )
    
    def _handle_setting_change(self, key: str, old_value: Any, new_value: Any):
        """Handle configuration change"""
        try:
            self.my_service.update_setting(new_value)
            logger.info(f"Updated {key} from {old_value} to {new_value}")
        except Exception as e:
            logger.error(f"Failed to update {key}: {e}")
```

### Configuration-Aware Service

```python
class ConfigurationAwareService:
    def __init__(self, config_service: ConfigurationService):
        self.config_service = config_service
    
    def process_request(self):
        # Get current configuration
        timeout = self.config_service.get_config('request_timeout', 30)
        max_retries = self.config_service.get_config('max_retries', 3)
        
        # Use configuration in processing
        return self._process_with_config(timeout, max_retries)
```

This API reference provides comprehensive documentation for integrating with and extending the configuration system.
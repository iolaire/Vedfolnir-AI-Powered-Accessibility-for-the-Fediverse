# Session Management Configuration Guide

This guide covers the comprehensive session management configuration system in Vedfolnir, including timeout settings, cleanup intervals, feature flags, and environment-specific configurations.

## Overview

The session management configuration system provides fine-grained control over all aspects of session behavior, from timeout settings to cross-tab synchronization and security features. The system supports environment-specific configurations and feature flags for flexible deployment scenarios.

## Configuration Components

### 1. Session Timeout Configuration

Controls session lifetime and expiration behavior:

```bash
# Session lifetime (default: 48 hours)
SESSION_LIFETIME_SECONDS=172800

# Idle timeout (default: 24 hours)
SESSION_IDLE_TIMEOUT_SECONDS=86400

# Absolute timeout (default: 7 days)
SESSION_ABSOLUTE_TIMEOUT_SECONDS=604800

# Grace periods
SESSION_EXPIRATION_GRACE_SECONDS=300  # 5 minutes
SESSION_CLEANUP_GRACE_SECONDS=600     # 10 minutes

# Warning threshold (default: 15 minutes)
SESSION_WARNING_THRESHOLD_SECONDS=900
```

### 2. Session Cleanup Configuration

Controls automated session cleanup behavior:

```bash
# Cleanup intervals
SESSION_CLEANUP_INTERVAL_SECONDS=1800      # 30 minutes
SESSION_BATCH_CLEANUP_INTERVAL_SECONDS=21600  # 6 hours
SESSION_DEEP_CLEANUP_INTERVAL_SECONDS=86400   # 24 hours

# Cleanup batch settings
SESSION_CLEANUP_BATCH_SIZE=100
SESSION_MAX_CLEANUP_BATCHES=10

# Cleanup thresholds
SESSION_MAX_EXPIRED_THRESHOLD=1000
SESSION_CLEANUP_TRIGGER_THRESHOLD=500

# Retention settings
SESSION_EXPIRED_RETENTION_DAYS=7
SESSION_AUDIT_RETENTION_DAYS=30
```

### 3. Cross-Tab Synchronization Configuration

Controls session synchronization across browser tabs:

```bash
# Synchronization intervals
SESSION_SYNC_CHECK_INTERVAL_SECONDS=2
SESSION_HEARTBEAT_INTERVAL_SECONDS=30

# Synchronization timeouts
SESSION_SYNC_TIMEOUT_SECONDS=5
SESSION_TAB_RESPONSE_TIMEOUT_SECONDS=3

# Storage settings
SESSION_LOCALSTORAGE_PREFIX=vedfolnir_session_
SESSION_MAX_SYNC_DATA_SIZE=1024
```

### 4. Session Security Configuration

Controls security features and validation:

```bash
# Security features
SESSION_ENABLE_FINGERPRINTING=true
SESSION_ENABLE_SUSPICIOUS_DETECTION=true
SESSION_ENABLE_AUDIT_LOGGING=true

# Security limits
SESSION_MAX_CONCURRENT_PER_USER=5
SESSION_SUSPICIOUS_ACTIVITY_THRESHOLD=10
SESSION_MAX_PLATFORM_SWITCHES_PER_HOUR=50

# Security check interval
SESSION_SECURITY_CHECK_INTERVAL_SECONDS=300
```

### 5. Session Monitoring Configuration

Controls performance monitoring and metrics collection:

```bash
# Monitoring features
SESSION_ENABLE_PERFORMANCE_MONITORING=true
SESSION_ENABLE_METRICS_COLLECTION=true
SESSION_ENABLE_HEALTH_CHECKS=true

# Monitoring intervals
SESSION_METRICS_INTERVAL_SECONDS=60
SESSION_HEALTH_CHECK_INTERVAL_SECONDS=300

# Buffer sizes
SESSION_METRICS_BUFFER_SIZE=1000
SESSION_EVENTS_BUFFER_SIZE=500

# Alert thresholds
SESSION_ALERT_CREATION_RATE=100.0
SESSION_ALERT_FAILURE_RATE=10.0
SESSION_ALERT_AVG_DURATION=3600.0
SESSION_ALERT_CONCURRENT_SESSIONS=1000.0
SESSION_ALERT_SUSPICIOUS_RATE=5.0
```

### 6. Session Feature Flags

Controls which session management features are enabled:

```bash
# Core features
SESSION_FEATURE_CROSS_TAB_SYNC=true
SESSION_FEATURE_PLATFORM_SWITCHING=true
SESSION_FEATURE_PERSISTENCE=true

# Advanced features
SESSION_FEATURE_OPTIMISTIC_UI=true
SESSION_FEATURE_BACKGROUND_CLEANUP=true
SESSION_FEATURE_ANALYTICS=true

# Experimental features (disabled by default)
SESSION_FEATURE_CLUSTERING=false
SESSION_FEATURE_DISTRIBUTED=false
SESSION_FEATURE_CACHING=false
```

## Environment-Specific Configurations

The system supports different configurations for different environments:

### Development Environment

```bash
SESSION_ENVIRONMENT=development
SESSION_DEBUG_MODE=true
SESSION_LIFETIME_SECONDS=86400  # 24 hours
SESSION_CLEANUP_INTERVAL_SECONDS=900  # 15 minutes
SESSION_ENABLE_PERFORMANCE_MONITORING=true
SESSION_ENABLE_ANALYTICS=true
```

### Testing Environment

```bash
SESSION_ENVIRONMENT=testing
SESSION_DEBUG_MODE=true
SESSION_LIFETIME_SECONDS=1800  # 30 minutes
SESSION_CLEANUP_INTERVAL_SECONDS=300  # 5 minutes
SESSION_ENABLE_PERFORMANCE_MONITORING=false
SESSION_ENABLE_ANALYTICS=false
SESSION_CLEANUP_BATCH_SIZE=10
```

### Staging Environment

```bash
SESSION_ENVIRONMENT=staging
SESSION_DEBUG_MODE=false
SESSION_LIFETIME_SECONDS=172800  # 48 hours
SESSION_CLEANUP_INTERVAL_SECONDS=1800  # 30 minutes
SESSION_ENABLE_PERFORMANCE_MONITORING=true
SESSION_ENABLE_ANALYTICS=true
```

### Production Environment

```bash
SESSION_ENVIRONMENT=production
SESSION_DEBUG_MODE=false
SESSION_LIFETIME_SECONDS=172800  # 48 hours
SESSION_CLEANUP_INTERVAL_SECONDS=3600  # 1 hour
SESSION_ENABLE_PERFORMANCE_MONITORING=true
SESSION_ENABLE_ANALYTICS=true
SESSION_CLEANUP_BATCH_SIZE=200
SESSION_MAX_CLEANUP_BATCHES=20
```

## Configuration Management

### Using the Configuration Manager

The session configuration manager provides tools for managing and validating configurations:

```bash
# Validate current configuration
python scripts/maintenance/session_config_manager.py --validate

# Show current configuration
python scripts/maintenance/session_config_manager.py --show

# Set environment
python scripts/maintenance/session_config_manager.py --set-env production

# Optimize for environment
python scripts/maintenance/session_config_manager.py --optimize-for production

# Generate configuration template
python scripts/maintenance/session_config_manager.py --generate-template --output session.env
```

### Programmatic Configuration

```python
from session_config import get_session_config, reload_session_config

# Get current configuration
config = get_session_config()

# Check configuration values
print(f"Session lifetime: {config.timeout.session_lifetime}")
print(f"Cleanup enabled: {config.features.enable_background_cleanup}")
print(f"Environment: {config.environment.value}")

# Reload configuration after environment changes
reload_session_config()
```

## Custom Settings

You can add custom session settings using the `SESSION_CUSTOM_` prefix:

```bash
# Custom settings
SESSION_CUSTOM_MAX_RETRIES=3
SESSION_CUSTOM_SPECIAL_MODE=enabled
SESSION_CUSTOM_DEBUG_LEVEL=verbose
```

Access custom settings in code:

```python
config = get_session_config()
max_retries = config.custom_settings.get('max_retries', '3')
special_mode = config.custom_settings.get('special_mode', 'disabled')
```

## Configuration Validation

The system includes comprehensive validation to ensure configuration consistency:

### Validation Rules

1. **Timeout Validation**:
   - Idle timeout must be less than session lifetime
   - Expiration grace period must be less than idle timeout
   - Warning threshold must be reasonable

2. **Cleanup Validation**:
   - Cleanup batch size must be positive
   - Cleanup interval must be less than batch cleanup interval
   - Thresholds must be reasonable

3. **Sync Validation**:
   - Sync timeout must be less than heartbeat interval
   - Response timeout must be reasonable

4. **Security Validation**:
   - Max concurrent sessions must be positive
   - Activity thresholds must be reasonable

5. **Monitoring Validation**:
   - Buffer sizes must be positive
   - Alert thresholds must be reasonable

### Running Validation

```bash
# Validate configuration
python scripts/maintenance/session_config_manager.py --validate

# Example output:
# 🔍 Validating session configuration...
# ❌ Configuration has issues:
#    - Idle timeout should be less than session lifetime
#    - Cleanup batch size must be positive
```

## Integration with Session Manager

The session manager automatically uses the configuration system:

```python
from session_manager import SessionManager
from session_config import get_session_config
from database import DatabaseManager

# Create session manager with configuration
db_manager = DatabaseManager(config)
session_config = get_session_config()
session_manager = SessionManager(db_manager, session_config)

# Configuration is automatically applied
# - Timeout settings control session expiration
# - Cleanup settings control automated cleanup
# - Feature flags control available features
# - Security settings control validation
```

## Performance Considerations

### Cleanup Performance

- **Batch Size**: Larger batches are more efficient but use more memory
- **Cleanup Interval**: More frequent cleanup reduces database size but increases CPU usage
- **Trigger Threshold**: Higher thresholds reduce unnecessary cleanup operations

### Monitoring Performance

- **Buffer Sizes**: Larger buffers provide more data but use more memory
- **Collection Interval**: More frequent collection provides better granularity but increases overhead
- **Alert Thresholds**: Appropriate thresholds prevent alert spam

### Synchronization Performance

- **Check Interval**: More frequent checks provide better responsiveness but increase overhead
- **Timeout Settings**: Shorter timeouts provide faster feedback but may cause false positives
- **Data Size Limits**: Smaller limits reduce storage usage but may limit functionality

## Troubleshooting

### Common Configuration Issues

1. **Session Expiring Too Quickly**:
   ```bash
   # Increase session lifetime
   SESSION_LIFETIME_SECONDS=259200  # 72 hours
   
   # Increase idle timeout
   SESSION_IDLE_TIMEOUT_SECONDS=172800  # 48 hours
   ```

2. **Cleanup Running Too Frequently**:
   ```bash
   # Increase cleanup interval
   SESSION_CLEANUP_INTERVAL_SECONDS=3600  # 1 hour
   
   # Increase trigger threshold
   SESSION_CLEANUP_TRIGGER_THRESHOLD=1000
   ```

3. **Cross-Tab Sync Issues**:
   ```bash
   # Increase sync timeout
   SESSION_SYNC_TIMEOUT_SECONDS=10
   
   # Increase check interval for slower systems
   SESSION_SYNC_CHECK_INTERVAL_SECONDS=5
   ```

4. **Performance Issues**:
   ```bash
   # Disable expensive features in production
   SESSION_ENABLE_PERFORMANCE_MONITORING=false
   SESSION_ENABLE_METRICS_COLLECTION=false
   
   # Reduce buffer sizes
   SESSION_METRICS_BUFFER_SIZE=500
   SESSION_EVENTS_BUFFER_SIZE=250
   ```

### Debugging Configuration

1. **Enable Debug Mode**:
   ```bash
   SESSION_DEBUG_MODE=true
   ```

2. **Check Configuration**:
   ```bash
   python scripts/maintenance/session_config_manager.py --show
   ```

3. **Validate Settings**:
   ```bash
   python scripts/maintenance/session_config_manager.py --validate
   ```

4. **Monitor Logs**:
   ```bash
   tail -f logs/webapp.log | grep -i session
   ```

## Best Practices

### Development

- Use shorter session lifetimes for faster testing
- Enable debug mode and detailed logging
- Use smaller cleanup batches for faster iteration
- Enable all monitoring features for debugging

### Testing

- Use very short session lifetimes (minutes)
- Disable expensive monitoring features
- Use small batch sizes for predictable behavior
- Enable debug mode for test debugging

### Production

- Use longer session lifetimes for better UX
- Disable debug mode for performance
- Use larger batch sizes for efficiency
- Enable monitoring for operational visibility
- Set appropriate alert thresholds

### Security

- Enable all security features in production
- Set reasonable concurrent session limits
- Monitor suspicious activity patterns
- Use audit logging for compliance
- Regularly review security configurations

## Migration Guide

### Upgrading from Previous Versions

1. **Backup Current Configuration**:
   ```bash
   cp .env .env.backup
   ```

2. **Generate New Template**:
   ```bash
   python scripts/maintenance/session_config_manager.py --generate-template --output .env.new
   ```

3. **Merge Configurations**:
   - Copy existing settings to new template
   - Add new session configuration settings
   - Validate merged configuration

4. **Test Configuration**:
   ```bash
   python scripts/maintenance/session_config_manager.py --validate
   ```

5. **Apply Configuration**:
   ```bash
   mv .env.new .env
   ```

### Configuration Schema Changes

The configuration system is designed to be backward compatible. New settings are added with sensible defaults, and deprecated settings are supported with warnings.

## API Reference

### SessionConfig Class

Main configuration class containing all session management settings.

**Properties**:
- `environment`: Current environment (development, testing, staging, production)
- `debug_mode`: Enable debug logging and verbose output
- `timeout`: Session timeout configuration
- `cleanup`: Session cleanup configuration
- `sync`: Cross-tab synchronization configuration
- `security`: Session security configuration
- `monitoring`: Session monitoring configuration
- `features`: Session feature flags
- `custom_settings`: Custom configuration settings

**Methods**:
- `from_env()`: Create configuration from environment variables
- `validate_configuration()`: Validate configuration and return issues
- `get_config_summary()`: Get summary of current configuration
- `get_environment_specific_config()`: Get environment-specific overrides
- `apply_environment_overrides()`: Apply environment-specific settings

### Global Functions

- `get_session_config()`: Get global session configuration instance
- `reload_session_config()`: Reload configuration from environment

## Examples

### Basic Configuration

```python
from session_config import get_session_config

# Get configuration
config = get_session_config()

# Check if feature is enabled
if config.features.enable_cross_tab_sync:
    print("Cross-tab sync is enabled")

# Get timeout settings
session_lifetime = config.timeout.session_lifetime
print(f"Session lifetime: {session_lifetime}")
```

### Environment-Specific Setup

```python
import os
from session_config import SessionConfig, SessionEnvironment

# Set environment
os.environ['SESSION_ENVIRONMENT'] = 'production'

# Create configuration
config = SessionConfig.from_env()
config.apply_environment_overrides()

# Validate configuration
issues = config.validate_configuration()
if issues:
    print(f"Configuration issues: {issues}")
else:
    print("Configuration is valid")
```

### Custom Configuration

```python
from session_config import SessionConfig, SessionTimeoutConfig
from datetime import timedelta

# Create custom timeout configuration
timeout_config = SessionTimeoutConfig(
    session_lifetime=timedelta(hours=72),
    idle_timeout=timedelta(hours=36),
    absolute_timeout=timedelta(days=14)
)

# Create session configuration with custom timeout
config = SessionConfig(timeout=timeout_config)

# Validate custom configuration
issues = config.validate_configuration()
print(f"Validation issues: {issues}")
```

This comprehensive configuration system provides the flexibility and control needed for robust session management across different deployment environments and use cases.
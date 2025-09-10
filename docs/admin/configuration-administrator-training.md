# Configuration System Administrator Training

## Overview

This training guide provides comprehensive instruction for administrators managing the Configuration Integration System. It covers daily operations, troubleshooting, and best practices.

## Table of Contents

1. [System Overview](#system-overview)
2. [Daily Operations](#daily-operations)
3. [Configuration Management](#configuration-management)
4. [Monitoring and Alerting](#monitoring-and-alerting)
5. [Troubleshooting Guide](#troubleshooting-guide)
6. [Emergency Procedures](#emergency-procedures)
7. [Best Practices](#best-practices)

## System Overview

### Architecture Components

The Configuration Integration System consists of:

1. **Configuration Service**: Core service providing cached configuration access
2. **Service Adapters**: Connect existing services to configuration system
3. **Event Bus**: Handles configuration change notifications
4. **Admin Interface**: Web-based configuration management
5. **Monitoring System**: Health checks and performance monitoring

### Key Concepts

- **Configuration Keys**: Unique identifiers for configuration values
- **Configuration Sources**: Environment variables, database, schema defaults
- **Cache TTL**: Time-to-live for cached configuration values
- **Hot Reload**: Configurations that update without restart
- **Restart Required**: Configurations requiring application restart

## Daily Operations

### Morning Checklist

```bash
#!/bin/bash
# Daily Configuration System Health Check

echo "=== Daily Configuration System Health Check ==="
echo "Date: $(date)"
echo

# 1. Check system health
echo "1. Checking system health..."
python3 -c "
from app.core.configuration.core.configuration_service import ConfigurationService
from app.core.database.core.database_manager import DatabaseManager
from config import Config

try:
    config = Config()
    db_manager = DatabaseManager(config)
    config_service = ConfigurationService(db_manager)
    
    # Test configuration access
    value = config_service.get_config('session_timeout_minutes', 120)
    print(f'   ✅ Configuration access: OK (session_timeout={value})')
    
    # Check cache performance
    stats = config_service.get_cache_stats()
    print(f'   ✅ Cache performance: {stats[\"hit_rate\"]:.2%} hit rate')
    
    # Check database connectivity
    with db_manager.get_session() as session:
        session.execute('SELECT 1')
    print('   ✅ Database connectivity: OK')
    
except Exception as e:
    print(f'   ❌ Health check failed: {e}')
"

# 2. Check for alerts
echo "2. Checking for active alerts..."
if [ -f "configuration_alerts.log" ]; then
    ALERT_COUNT=$(tail -n 100 configuration_alerts.log | grep "$(date +%Y-%m-%d)" | wc -l)
    if [ $ALERT_COUNT -gt 0 ]; then
        echo "   ⚠️  $ALERT_COUNT alerts today"
        echo "   Recent alerts:"
        tail -n 5 configuration_alerts.log
    else
        echo "   ✅ No alerts today"
    fi
else
    echo "   ✅ No alert log found"
fi

# 3. Check disk space
echo "3. Checking disk space..."
DISK_USAGE=$(df . | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 80 ]; then
    echo "   ⚠️  Disk usage: ${DISK_USAGE}% (high)"
else
    echo "   ✅ Disk usage: ${DISK_USAGE}% (normal)"
fi

# 4. Check memory usage
echo "4. Checking memory usage..."
python3 -c "
import psutil
memory = psutil.virtual_memory()
if memory.percent > 80:
    print(f'   ⚠️  Memory usage: {memory.percent:.1f}% (high)')
else:
    print(f'   ✅ Memory usage: {memory.percent:.1f}% (normal)')
"

echo
echo "=== Daily Health Check Complete ==="
```

### Configuration Review Process

Daily configuration review should include:

1. **Review Recent Changes**
   ```python
   # Check recent configuration changes
   python3 -c "
   from system_configuration_manager import SystemConfigurationManager
   from app.core.database.core.database_manager import DatabaseManager
   from config import Config
   from datetime import datetime, timedelta
   
   config = Config()
   db_manager = DatabaseManager(config)
   config_manager = SystemConfigurationManager(db_manager)
   
   # Get changes from last 24 hours
   yesterday = datetime.utcnow() - timedelta(days=1)
   
   with db_manager.get_session() as session:
       recent_changes = session.query(SystemConfiguration).filter(
           SystemConfiguration.updated_at > yesterday
       ).all()
       
       if recent_changes:
           print('Recent configuration changes:')
           for change in recent_changes:
               print(f'  {change.key}: {change.value} (by {change.updated_by})')
       else:
           print('No recent configuration changes')
   "
   ```

2. **Validate Critical Configurations**
   ```python
   # Validate critical configuration values
   critical_configs = [
       'max_concurrent_jobs',
       'session_timeout_minutes', 
       'rate_limit_per_user_per_hour',
       'maintenance_mode'
   ]
   
   for key in critical_configs:
       value = config_service.get_config(key)
       print(f'{key}: {value}')
   ```

3. **Check Restart Requirements**
   ```python
   # Check if any configurations require restart
   if config_service.is_restart_required():
       pending = config_service.get_pending_restart_configs()
       print(f'⚠️  Restart required for: {", ".join(pending)}')
   else:
       print('✅ No restart required')
   ```

## Configuration Management

### Adding New Configurations

Step-by-step process for adding new configurations:

1. **Define Configuration Schema**
   ```python
   from system_configuration_manager import SystemConfigurationManager, ConfigurationCategory, ConfigurationDataType
   
   config_manager = SystemConfigurationManager(db_manager)
   
   config_manager.add_configuration_schema(
       key="new_feature_timeout",
       category=ConfigurationCategory.PERFORMANCE,
       data_type=ConfigurationDataType.INTEGER,
       default_value=60,
       description="Timeout for new feature in seconds",
       requires_restart=False,
       validation_rules={"min_value": 10, "max_value": 300}
   )
   ```

2. **Set Initial Value**
   ```python
   config_manager.update_configuration(
       key="new_feature_timeout",
       value=60,
       updated_by="admin_user"
   )
   ```

3. **Test Configuration Access**
   ```python
   # Test that configuration can be accessed
   value = config_service.get_config("new_feature_timeout")
   print(f"New configuration value: {value}")
   ```

### Modifying Existing Configurations

Safe procedure for modifying configurations:

1. **Check Current Value**
   ```python
   current_value = config_service.get_config("max_concurrent_jobs")
   print(f"Current value: {current_value}")
   ```

2. **Validate New Value**
   ```python
   new_value = 15
   
   # Check if value is within acceptable range
   schema = config_manager.get_configuration_schema("max_concurrent_jobs")
   if schema and schema.validation_rules:
       min_val = schema.validation_rules.get("min_value", 0)
       max_val = schema.validation_rules.get("max_value", 100)
       
       if not (min_val <= new_value <= max_val):
           print(f"❌ Value {new_value} outside range [{min_val}, {max_val}]")
       else:
           print(f"✅ Value {new_value} is valid")
   ```

3. **Apply Change**
   ```python
   config_manager.update_configuration(
       key="max_concurrent_jobs",
       value=new_value,
       updated_by="admin_user"
   )
   ```

4. **Verify Change Propagation**
   ```python
   import time
   time.sleep(5)  # Wait for propagation
   
   updated_value = config_service.get_config("max_concurrent_jobs")
   if updated_value == new_value:
       print("✅ Configuration updated successfully")
   else:
       print("❌ Configuration update failed")
   ```

### Bulk Configuration Updates

For updating multiple related configurations:

```python
#!/usr/bin/env python3
"""
Bulk Configuration Update Script
"""

def bulk_update_configurations(updates, updated_by="admin"):
    """
    Update multiple configurations safely
    
    Args:
        updates: Dict of {key: value} pairs
        updated_by: User making the changes
    """
    from system_configuration_manager import SystemConfigurationManager
    from app.core.database.core.database_manager import DatabaseManager
    from config import Config
    
    config = Config()
    db_manager = DatabaseManager(config)
    config_manager = SystemConfigurationManager(db_manager)
    
    print(f"=== Bulk Configuration Update ===")
    print(f"Updating {len(updates)} configurations")
    print(f"Updated by: {updated_by}")
    print()
    
    success_count = 0
    
    for key, value in updates.items():
        try:
            # Get current value for logging
            current_value = config_service.get_config(key)
            
            # Update configuration
            config_manager.update_configuration(
                key=key,
                value=value,
                updated_by=updated_by
            )
            
            print(f"✅ {key}: {current_value} → {value}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ {key}: Failed - {e}")
    
    print(f"\nBulk update complete: {success_count}/{len(updates)} successful")
    
    # Wait for propagation
    print("Waiting for configuration propagation...")
    time.sleep(10)
    
    # Verify updates
    print("Verifying updates...")
    for key, expected_value in updates.items():
        try:
            actual_value = config_service.get_config(key)
            if actual_value == expected_value:
                print(f"✅ {key}: Verified")
            else:
                print(f"❌ {key}: Expected {expected_value}, got {actual_value}")
        except Exception as e:
            print(f"❌ {key}: Verification failed - {e}")

# Example usage
performance_updates = {
    "max_concurrent_jobs": 12,
    "default_job_timeout": 360,
    "cache_size": 1200
}

bulk_update_configurations(performance_updates, "performance_tuning")
```

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Configuration Access Performance**
   - Average response time < 50ms
   - 95th percentile < 100ms
   - Error rate < 1%

2. **Cache Performance**
   - Hit rate > 80%
   - Cache utilization < 90%
   - Eviction rate monitoring

3. **Database Performance**
   - Query response time < 100ms
   - Connection pool utilization < 80%
   - Failed connection attempts

4. **System Resources**
   - Memory usage < 500MB
   - CPU usage < 70%
   - Disk space > 10% free

### Setting Up Alerts

Configure alerts for critical thresholds:

```python
# Alert configuration
alert_thresholds = {
    "config_access_time_ms": {
        "warning": 50,
        "critical": 100
    },
    "cache_hit_rate": {
        "warning": 0.7,
        "critical": 0.5
    },
    "memory_usage_mb": {
        "warning": 400,
        "critical": 500
    },
    "database_response_time_ms": {
        "warning": 100,
        "critical": 200
    }
}
```

### Alert Response Procedures

When alerts are triggered:

1. **Warning Level Alerts**
   - Log the alert
   - Check system status
   - Monitor for escalation
   - Schedule investigation if persistent

2. **Critical Level Alerts**
   - Immediate investigation
   - Check system health
   - Consider rollback if necessary
   - Escalate to senior administrator

## Troubleshooting Guide

### Common Issues and Solutions

#### Issue: Low Cache Hit Rate

**Symptoms**: Cache hit rate below 70%

**Investigation**:
```python
# Check cache statistics
stats = config_service.get_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")
print(f"Cache size: {stats['cache']['size']}/{stats['cache']['maxsize']}")
print(f"Total requests: {stats['total_requests']}")
```

**Solutions**:
1. Increase cache size
2. Increase TTL for stable configurations
3. Check for cache invalidation issues

#### Issue: Slow Configuration Access

**Symptoms**: Configuration access time > 100ms

**Investigation**:
```python
import time

# Benchmark configuration access
start_time = time.time()
value = config_service.get_config('session_timeout_minutes')
access_time = (time.time() - start_time) * 1000

print(f"Access time: {access_time:.2f}ms")

# Check database performance
start_time = time.time()
with db_manager.get_session() as session:
    session.execute("SELECT 1")
db_time = (time.time() - start_time) * 1000

print(f"Database time: {db_time:.2f}ms")
```

**Solutions**:
1. Check database performance
2. Optimize database queries
3. Increase cache size
4. Check network connectivity

#### Issue: Configuration Changes Not Propagating

**Symptoms**: Services not reflecting configuration changes

**Investigation**:
```python
# Check if configuration was updated in database
with db_manager.get_session() as session:
    config = session.query(SystemConfiguration).filter_by(
        key='problematic_key'
    ).first()
    if config:
        print(f"Database value: {config.value}")
        print(f"Last updated: {config.updated_at}")
    else:
        print("Configuration not found in database")

# Check cached value
cached_value = config_service.get_config('problematic_key')
print(f"Cached value: {cached_value}")

# Check event subscriptions
# This would depend on how subscriptions are tracked
```

**Solutions**:
1. Clear configuration cache
2. Check event bus functionality
3. Verify service adapter subscriptions
4. Restart configuration service

## Emergency Procedures

### Emergency Configuration Reset

When configuration system is corrupted:

```bash
#!/bin/bash
# Emergency Configuration Reset

echo "EMERGENCY CONFIGURATION RESET"
echo "This will reset all configurations to schema defaults"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    python3 -c "
from system_configuration_manager import SystemConfigurationManager
from app.core.database.core.database_manager import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)
config_manager = SystemConfigurationManager(db_manager)

# Reset all configurations to defaults
schemas = config_manager.get_all_configuration_schemas()
reset_count = 0

for schema in schemas:
    if schema.default_value is not None:
        try:
            config_manager.update_configuration(
                key=schema.key,
                value=schema.default_value,
                updated_by='emergency_reset'
            )
            print(f'Reset {schema.key} to {schema.default_value}')
            reset_count += 1
        except Exception as e:
            print(f'Failed to reset {schema.key}: {e}')

print(f'Emergency reset complete: {reset_count} configurations reset')
"
else
    echo "Reset cancelled"
fi
```

### Emergency Service Restart

When configuration system is unresponsive:

```bash
#!/bin/bash
# Emergency Service Restart

echo "EMERGENCY SERVICE RESTART"

# Stop services
echo "Stopping services..."
pkill -f "python.*web_app.py"
pkill -f "monitor_configuration_system.py"
sleep 10

# Clear cache files if they exist
echo "Clearing cache..."
rm -f /tmp/config_cache_*

# Restart services
echo "Restarting services..."
python web_app.py & sleep 10

# Verify restart
echo "Verifying restart..."
python3 -c "
import requests
import time

time.sleep(5)
try:
    response = requests.get('http://localhost:5000/health', timeout=10)
    if response.status_code == 200:
        print('✅ Service restart successful')
    else:
        print(f'❌ Service restart failed: {response.status_code}')
except Exception as e:
    print(f'❌ Service restart failed: {e}')
"
```

## Best Practices

### Configuration Management Best Practices

1. **Always backup before changes**
2. **Test changes in staging first**
3. **Make incremental changes**
4. **Document all changes**
5. **Monitor after changes**

### Security Best Practices

1. **Use strong authentication**
2. **Audit all configuration changes**
3. **Encrypt sensitive configurations**
4. **Limit administrative access**
5. **Regular security reviews**

### Performance Best Practices

1. **Monitor cache hit rates**
2. **Optimize database queries**
3. **Use appropriate TTL values**
4. **Regular performance testing**
5. **Capacity planning**

This training guide provides administrators with the knowledge and tools needed to effectively manage the Configuration Integration System.
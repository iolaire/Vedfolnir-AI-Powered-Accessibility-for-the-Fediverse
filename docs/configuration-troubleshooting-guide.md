# Configuration System Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting procedures for the Configuration Integration System. Use this guide to diagnose and resolve common configuration-related issues.

## Table of Contents

1. [Quick Diagnostic Tools](#quick-diagnostic-tools)
2. [Common Issues](#common-issues)
3. [Service-Specific Issues](#service-specific-issues)
4. [Performance Issues](#performance-issues)
5. [Cache-Related Issues](#cache-related-issues)
6. [Database Issues](#database-issues)
7. [Event System Issues](#event-system-issues)
8. [Emergency Procedures](#emergency-procedures)

## Quick Diagnostic Tools

### Configuration System Health Check

```python
#!/usr/bin/env python3
"""
Configuration System Health Check Tool
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import Config
from database import DatabaseManager
from configuration_service import ConfigurationService
from system_configuration_manager import SystemConfigurationManager

def run_health_check():
    """Run comprehensive configuration system health check"""
    print("=== Configuration System Health Check ===\n")
    
    try:
        # Initialize components
        config = Config()
        db_manager = DatabaseManager(config)
        config_service = ConfigurationService(db_manager)
        
        # Test 1: Database connectivity
        print("1. Testing database connectivity...")
        try:
            with db_manager.get_session() as session:
                result = session.execute("SELECT 1").scalar()
                print("   ✅ Database connection: OK")
        except Exception as e:
            print(f"   ❌ Database connection: FAILED - {e}")
            return False
        
        # Test 2: Configuration service initialization
        print("2. Testing configuration service...")
        try:
            test_value = config_service.get_config('test_key', 'default')
            print("   ✅ Configuration service: OK")
        except Exception as e:
            print(f"   ❌ Configuration service: FAILED - {e}")
            return False
        
        # Test 3: Cache functionality
        print("3. Testing cache functionality...")
        try:
            stats = config_service.get_cache_stats()
            print(f"   ✅ Cache: OK (size: {stats['cache']['size']}, hit rate: {stats['hit_rate']:.2%})")
        except Exception as e:
            print(f"   ❌ Cache: FAILED - {e}")
        
        # Test 4: Configuration schema
        print("4. Testing configuration schema...")
        try:
            system_config_manager = SystemConfigurationManager(db_manager)
            schema_count = len(system_config_manager.get_all_configuration_schemas())
            print(f"   ✅ Configuration schema: OK ({schema_count} schemas loaded)")
        except Exception as e:
            print(f"   ❌ Configuration schema: FAILED - {e}")
        
        # Test 5: Event system
        print("5. Testing event system...")
        try:
            subscription_id = config_service.subscribe_to_changes('test_key', lambda k, o, n: None)
            config_service.unsubscribe(subscription_id)
            print("   ✅ Event system: OK")
        except Exception as e:
            print(f"   ❌ Event system: FAILED - {e}")
        
        print("\n=== Health Check Complete ===")
        return True
        
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

if __name__ == "__main__":
    success = run_health_check()
    sys.exit(0 if success else 1)
```

### Configuration Diagnostic Tool

```python
#!/usr/bin/env python3
"""
Configuration Diagnostic Tool
"""

def diagnose_configuration_key(config_service, key):
    """Diagnose specific configuration key"""
    print(f"=== Diagnosing Configuration Key: {key} ===\n")
    
    try:
        # Get configuration with metadata
        config_value = config_service.get_config_with_metadata(key)
        
        if config_value:
            print(f"Key: {config_value.key}")
            print(f"Value: {config_value.value}")
            print(f"Type: {config_value.data_type}")
            print(f"Source: {config_value.source.value}")
            print(f"Requires Restart: {config_value.requires_restart}")
            print(f"Last Updated: {config_value.last_updated}")
            print(f"Cached At: {config_value.cached_at}")
            print(f"TTL: {config_value.ttl}")
        else:
            print("❌ Configuration key not found")
            
            # Check if key exists in schema
            schema = config_service.system_config_manager.get_configuration_schema(key)
            if schema:
                print(f"✅ Schema exists: {schema.description}")
                print(f"   Default value: {schema.default_value}")
            else:
                print("❌ No schema found for this key")
        
        # Check environment override
        env_key = f"{config_service.environment_prefix}{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value:
            print(f"🔧 Environment override: {env_key}={env_value}")
        
        # Check cache status
        with config_service._cache_lock:
            cached = key in config_service._cache
            print(f"Cache status: {'Cached' if cached else 'Not cached'}")
        
    except Exception as e:
        print(f"❌ Error diagnosing configuration: {e}")
        import traceback
        traceback.print_exc()

def diagnose_service_adapter(adapter_name, adapter):
    """Diagnose service adapter"""
    print(f"=== Diagnosing Service Adapter: {adapter_name} ===\n")
    
    try:
        # Check subscriptions
        if hasattr(adapter, '_subscriptions'):
            print(f"Active subscriptions: {len(adapter._subscriptions)}")
            for key, subscription_id in adapter._subscriptions.items():
                print(f"  {key}: {subscription_id}")
        
        # Test configuration update
        if hasattr(adapter, 'update_settings'):
            try:
                result = adapter.update_settings()
                print(f"Configuration update test: {'✅ OK' if result else '❌ Failed'}")
            except Exception as e:
                print(f"Configuration update test: ❌ Failed - {e}")
        
    except Exception as e:
        print(f"❌ Error diagnosing adapter: {e}")
```

## Common Issues

### Issue 1: Configuration Changes Not Taking Effect

**Symptoms**:
- Configuration updated in admin interface but service behavior unchanged
- Services using old configuration values

**Diagnosis**:
```python
def diagnose_configuration_propagation(config_service, key):
    """Diagnose configuration propagation issues"""
    print(f"Diagnosing propagation for key: {key}")
    
    # Check current value in service
    current_value = config_service.get_config(key)
    print(f"Current value from service: {current_value}")
    
    # Check database value
    with config_service.db_manager.get_session() as session:
        db_config = session.query(SystemConfiguration).filter_by(key=key).first()
        if db_config:
            print(f"Database value: {db_config.get_typed_value()}")
            print(f"Last updated: {db_config.updated_at}")
        else:
            print("❌ No database record found")
    
    # Check cache
    with config_service._cache_lock:
        cached_value = config_service._cache.get(key)
        if cached_value:
            print(f"Cached value: {cached_value.value}")
            print(f"Cache source: {cached_value.source.value}")
        else:
            print("Not in cache")
    
    # Check environment override
    env_key = f"{config_service.environment_prefix}{key.upper()}"
    env_value = os.getenv(env_key)
    if env_value:
        print(f"🔧 Environment override active: {env_value}")
```

**Solutions**:

1. **Clear cache and refresh**:
```python
config_service.refresh_config(key)
```

2. **Check environment variable overrides**:
```bash
# Check for environment overrides
env | grep VEDFOLNIR_CONFIG_
```

3. **Verify subscription setup**:
```python
# Check if service adapter has subscriptions
adapter._subscriptions  # Should contain subscription IDs
```

4. **Force configuration update**:
```python
# Manually trigger configuration change notification
config_service.notify_change(key, old_value, new_value)
```

### Issue 2: Configuration Service Unavailable

**Symptoms**:
- ConfigurationServiceUnavailableError exceptions
- Services falling back to default values

**Diagnosis**:
```python
def diagnose_service_availability(config_service):
    """Diagnose configuration service availability"""
    try:
        # Test basic functionality
        test_value = config_service.get_config('test_key', 'default')
        print("✅ Configuration service is available")
        
        # Test database connectivity
        with config_service.db_manager.get_session() as session:
            session.execute("SELECT 1")
        print("✅ Database connectivity OK")
        
        # Test cache functionality
        stats = config_service.get_cache_stats()
        print(f"✅ Cache functional (hit rate: {stats['hit_rate']:.2%})")
        
    except Exception as e:
        print(f"❌ Service availability issue: {e}")
        return False
    
    return True
```

**Solutions**:

1. **Check database connectivity**:
```python
# Test database connection
try:
    with db_manager.get_session() as session:
        session.execute("SELECT 1")
    print("Database OK")
except Exception as e:
    print(f"Database issue: {e}")
```

2. **Restart configuration service**:
```python
# Reinitialize configuration service
config_service = ConfigurationService(db_manager)
```

3. **Check system resources**:
```bash
# Check memory and CPU usage
free -h
top -p $(pgrep -f "python.*web_app.py")
```

### Issue 3: Cache Performance Issues

**Symptoms**:
- Low cache hit rates
- Slow configuration access
- High memory usage

**Diagnosis**:
```python
def diagnose_cache_performance(config_service):
    """Diagnose cache performance issues"""
    stats = config_service.get_cache_stats()
    
    print(f"Cache Statistics:")
    print(f"  Hit rate: {stats['hit_rate']:.2%}")
    print(f"  Total requests: {stats['total_requests']}")
    print(f"  Cache size: {stats['cache']['size']}/{stats['cache']['maxsize']}")
    print(f"  TTL: {stats['cache']['ttl']} seconds")
    
    # Performance analysis
    if stats['hit_rate'] < 0.8:
        print("⚠️  Low cache hit rate - consider increasing TTL or cache size")
    
    if stats['cache']['size'] == stats['cache']['maxsize']:
        print("⚠️  Cache at maximum capacity - consider increasing cache size")
    
    # Memory usage analysis
    import psutil
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    print(f"Process memory usage: {memory_mb:.1f} MB")
```

**Solutions**:

1. **Increase cache size**:
```python
# Reinitialize with larger cache
config_service = ConfigurationService(db_manager, cache_size=2000)
```

2. **Adjust TTL**:
```python
# Increase TTL for stable configurations
config_service = ConfigurationService(db_manager, default_ttl=600)
```

3. **Clear cache if corrupted**:
```python
config_service.refresh_config()  # Clear all cache
```

## Service-Specific Issues

### Task Queue Configuration Issues

**Common Problems**:
- Concurrency limits not updating
- Job timeouts not being applied
- Queue size limits not enforced

**Diagnosis**:
```python
def diagnose_task_queue_configuration(task_queue_adapter):
    """Diagnose task queue configuration issues"""
    print("=== Task Queue Configuration Diagnosis ===")
    
    # Check current configuration values
    config_service = task_queue_adapter.config_service
    
    max_jobs = config_service.get_config('max_concurrent_jobs', 10)
    timeout = config_service.get_config('default_job_timeout', 300)
    queue_limit = config_service.get_config('queue_size_limit', 1000)
    
    print(f"Configuration values:")
    print(f"  Max concurrent jobs: {max_jobs}")
    print(f"  Default timeout: {timeout}")
    print(f"  Queue size limit: {queue_limit}")
    
    # Check task queue manager state
    task_queue = task_queue_adapter.task_queue_manager
    print(f"Task queue state:")
    print(f"  Current max workers: {getattr(task_queue, 'max_workers', 'N/A')}")
    print(f"  Active jobs: {getattr(task_queue, 'active_jobs', 'N/A')}")
    
    # Test configuration update
    try:
        result = task_queue_adapter.update_concurrency_limits()
        print(f"Configuration update test: {'✅ OK' if result else '❌ Failed'}")
    except Exception as e:
        print(f"Configuration update test: ❌ Failed - {e}")
```

**Solutions**:

1. **Force configuration update**:
```python
task_queue_adapter.update_concurrency_limits()
task_queue_adapter.update_timeout_settings()
```

2. **Check subscription status**:
```python
print(f"Active subscriptions: {task_queue_adapter._subscriptions}")
```

3. **Recreate adapter**:
```python
# Recreate adapter if subscriptions are broken
new_adapter = TaskQueueConfigurationAdapter(task_queue_manager, config_service)
```

### Session Configuration Issues

**Common Problems**:
- Session timeouts not updating
- Rate limits not being applied
- Security settings not taking effect

**Diagnosis**:
```python
def diagnose_session_configuration(session_adapter):
    """Diagnose session configuration issues"""
    print("=== Session Configuration Diagnosis ===")
    
    # Check current configuration
    current_config = session_adapter._current_config
    print("Current configuration:")
    for key, value in current_config.items():
        print(f"  {key}: {value}")
    
    # Check session managers
    if session_adapter.redis_session_manager:
        print("✅ Redis session manager available")
    if session_adapter.unified_session_manager:
        print("✅ Unified session manager available")
    if session_adapter.flask_session_interface:
        print("✅ Flask session interface available")
    
    # Test configuration application
    try:
        session_adapter._apply_session_configuration()
        print("✅ Configuration application successful")
    except Exception as e:
        print(f"❌ Configuration application failed: {e}")
```

## Performance Issues

### Slow Configuration Access

**Symptoms**:
- High latency when accessing configuration
- Timeouts in configuration requests

**Diagnosis**:
```python
import time

def benchmark_configuration_access(config_service, key, iterations=100):
    """Benchmark configuration access performance"""
    print(f"Benchmarking configuration access for '{key}' ({iterations} iterations)")
    
    times = []
    for i in range(iterations):
        start_time = time.time()
        value = config_service.get_config(key)
        end_time = time.time()
        times.append(end_time - start_time)
    
    avg_time = sum(times) / len(times)
    max_time = max(times)
    min_time = min(times)
    
    print(f"Results:")
    print(f"  Average time: {avg_time*1000:.2f} ms")
    print(f"  Max time: {max_time*1000:.2f} ms")
    print(f"  Min time: {min_time*1000:.2f} ms")
    
    if avg_time > 0.1:  # 100ms
        print("⚠️  Slow configuration access detected")
    
    return avg_time
```

**Solutions**:

1. **Check database performance**:
```sql
-- Check for slow queries
SHOW PROCESSLIST;
SHOW STATUS LIKE 'Slow_queries';
```

2. **Optimize cache settings**:
```python
# Increase cache size and TTL
config_service = ConfigurationService(
    db_manager, 
    cache_size=2000, 
    default_ttl=600
)
```

3. **Check database indexes**:
```sql
-- Ensure proper indexing on configuration table
SHOW INDEX FROM system_configurations;
```

### High Memory Usage

**Symptoms**:
- Increasing memory usage over time
- Out of memory errors

**Diagnosis**:
```python
import psutil
import gc

def diagnose_memory_usage(config_service):
    """Diagnose memory usage issues"""
    process = psutil.Process()
    memory_info = process.memory_info()
    
    print(f"Memory Usage:")
    print(f"  RSS: {memory_info.rss / 1024 / 1024:.1f} MB")
    print(f"  VMS: {memory_info.vms / 1024 / 1024:.1f} MB")
    
    # Check cache size
    cache_stats = config_service.get_cache_stats()
    print(f"Cache Statistics:")
    print(f"  Size: {cache_stats['cache']['size']}")
    print(f"  Max size: {cache_stats['cache']['maxsize']}")
    
    # Check for memory leaks
    gc.collect()
    objects_before = len(gc.get_objects())
    
    # Perform some operations
    for i in range(100):
        config_service.get_config(f'test_key_{i}', 'default')
    
    gc.collect()
    objects_after = len(gc.get_objects())
    
    print(f"Object count change: {objects_after - objects_before}")
    
    if objects_after - objects_before > 50:
        print("⚠️  Possible memory leak detected")
```

**Solutions**:

1. **Reduce cache size**:
```python
config_service = ConfigurationService(db_manager, cache_size=500)
```

2. **Force garbage collection**:
```python
import gc
gc.collect()
```

3. **Check for subscription leaks**:
```python
# Clean up unused subscriptions
for adapter in service_adapters:
    adapter.cleanup()
```

## Database Issues

### Configuration Table Corruption

**Symptoms**:
- Database errors when accessing configuration
- Inconsistent configuration values

**Diagnosis**:
```sql
-- Check table integrity
CHECK TABLE system_configurations;

-- Check for duplicate keys
SELECT key, COUNT(*) as count 
FROM system_configurations 
GROUP BY key 
HAVING count > 1;

-- Check for invalid data types
SELECT key, value, data_type 
FROM system_configurations 
WHERE data_type NOT IN ('string', 'integer', 'float', 'boolean', 'json');
```

**Solutions**:

1. **Repair table**:
```sql
REPAIR TABLE system_configurations;
```

2. **Remove duplicates**:
```sql
-- Remove duplicate configurations (keep latest)
DELETE sc1 FROM system_configurations sc1
INNER JOIN system_configurations sc2 
WHERE sc1.id < sc2.id AND sc1.key = sc2.key;
```

3. **Restore from backup**:
```python
# Restore configuration from backup
def restore_configuration_from_backup(config_manager, backup_file):
    with open(backup_file, 'r') as f:
        backup_data = json.load(f)
    
    for key, config_data in backup_data['configurations'].items():
        config_manager.update_configuration(
            key=key,
            value=config_data['value'],
            updated_by="system_restore"
        )
```

## Event System Issues

### Events Not Propagating

**Symptoms**:
- Configuration changes not triggering service updates
- Subscribers not receiving notifications

**Diagnosis**:
```python
def diagnose_event_system(config_service):
    """Diagnose event system issues"""
    print("=== Event System Diagnosis ===")
    
    # Test event subscription
    test_events = []
    
    def test_callback(key, old_value, new_value):
        test_events.append((key, old_value, new_value))
    
    # Subscribe to test key
    subscription_id = config_service.subscribe_to_changes('test_event_key', test_callback)
    print(f"Created test subscription: {subscription_id}")
    
    # Trigger test event
    config_service.notify_change('test_event_key', 'old', 'new')
    
    # Wait for event processing
    time.sleep(1)
    
    # Check if event was received
    if test_events:
        print("✅ Event system working correctly")
        print(f"Received event: {test_events[0]}")
    else:
        print("❌ Event system not working")
    
    # Clean up
    config_service.unsubscribe(subscription_id)
    
    return len(test_events) > 0
```

**Solutions**:

1. **Check subscription management**:
```python
# List all active subscriptions
with config_service._subscribers_lock:
    for key, subscribers in config_service._subscribers.items():
        print(f"{key}: {len(subscribers)} subscribers")
```

2. **Recreate subscriptions**:
```python
# Recreate all service adapter subscriptions
for adapter in service_adapters:
    adapter.cleanup()
    adapter._setup_configuration_subscriptions()
```

3. **Check for threading issues**:
```python
# Ensure thread safety
import threading
print(f"Current thread: {threading.current_thread().name}")
print(f"Active threads: {threading.active_count()}")
```

## Emergency Procedures

### Emergency Configuration Reset

```bash
#!/bin/bash
# Emergency configuration reset script

echo "EMERGENCY CONFIGURATION RESET"
echo "This will reset all configurations to schema defaults"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" = "yes" ]; then
    python -c "
from system_configuration_manager import SystemConfigurationManager
from database import DatabaseManager
from config import Config

config = Config()
db_manager = DatabaseManager(config)
config_manager = SystemConfigurationManager(db_manager)

# Reset all configurations to defaults
schemas = config_manager.get_all_configuration_schemas()
for schema in schemas:
    if schema.default_value is not None:
        config_manager.update_configuration(
            key=schema.key,
            value=schema.default_value,
            updated_by='emergency_reset'
        )
        print(f'Reset {schema.key} to {schema.default_value}')

print('Emergency reset completed')
"
else
    echo "Reset cancelled"
fi
```

### Emergency Service Restart

```python
def emergency_service_restart():
    """Emergency restart of configuration-dependent services"""
    print("EMERGENCY SERVICE RESTART")
    
    try:
        # Stop all service adapters
        for adapter in service_adapters:
            adapter.cleanup()
        
        # Clear configuration cache
        config_service.refresh_config()
        
        # Reinitialize service adapters
        service_adapters.clear()
        initialize_all_service_adapters()
        
        print("✅ Emergency restart completed")
        
    except Exception as e:
        print(f"❌ Emergency restart failed: {e}")
        raise
```

### Emergency Contact Procedures

When configuration issues cannot be resolved:

1. **Escalate to senior administrator**
2. **Contact database administrator if database issues**
3. **Consider system maintenance mode if critical**
4. **Document all actions taken**
5. **Prepare incident report**

This troubleshooting guide provides comprehensive procedures for diagnosing and resolving configuration system issues. Always start with the quick diagnostic tools before proceeding to specific issue resolution.
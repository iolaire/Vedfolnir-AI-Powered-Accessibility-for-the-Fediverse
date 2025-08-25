# Configuration Integration Guide

## Overview

This guide provides step-by-step instructions for integrating new services with the Configuration Integration System. Follow these patterns to ensure consistent, reliable configuration management across all application components.

## Table of Contents

1. [Integration Patterns](#integration-patterns)
2. [Creating Configuration Adapters](#creating-configuration-adapters)
3. [Service Integration Steps](#service-integration-steps)
4. [Configuration Schema Setup](#configuration-schema-setup)
5. [Testing Integration](#testing-integration)
6. [Best Practices](#best-practices)
7. [Troubleshooting](#troubleshooting)

## Integration Patterns

### Pattern 1: Configuration Adapter (Recommended)

Use this pattern for services that need dynamic configuration updates without restart.

**When to use**:
- Service has configurable parameters that can change at runtime
- Real-time configuration updates are required
- Service needs to react to configuration changes immediately

**Example**: TaskQueueManager, SessionManager, AlertManager

### Pattern 2: Direct Configuration Access

Use this pattern for services that only need configuration at startup or can handle periodic refresh.

**When to use**:
- Configuration is read-only after initialization
- Service can handle configuration refresh through restart
- Simple configuration needs without complex change handling

**Example**: Database connection settings, logging configuration

### Pattern 3: Configuration-Aware Service

Use this pattern for new services designed with configuration integration in mind.

**When to use**:
- Building new services from scratch
- Want tight integration with configuration system
- Need advanced features like validation and impact assessment

## Creating Configuration Adapters

### Step 1: Define Configuration Keys

Identify the configuration keys your service needs:

```python
class MyServiceConfigurationAdapter:
    # Configuration keys
    SETTING_1_KEY = "my_service_setting_1"
    SETTING_2_KEY = "my_service_setting_2"
    TIMEOUT_KEY = "my_service_timeout"
```

### Step 2: Create Adapter Class

```python
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
My Service Configuration Adapter

Connects MyService with ConfigurationService to enable dynamic configuration updates.
"""

import logging
import threading
from typing import Optional, Dict, Any, Callable

from configuration_service import ConfigurationService, ConfigurationError

logger = logging.getLogger(__name__)


class MyServiceConfigurationError(Exception):
    """My service configuration error"""
    pass


class MyServiceConfigurationAdapter:
    """
    Adapter class connecting MyService with ConfigurationService
    
    Provides dynamic configuration updates for:
    - setting_1: Description of setting 1
    - setting_2: Description of setting 2
    - timeout: Service timeout in seconds
    """
    
    def __init__(self, my_service, config_service: ConfigurationService):
        """
        Initialize the adapter
        
        Args:
            my_service: MyService instance to configure
            config_service: ConfigurationService instance
        """
        self.my_service = my_service
        self.config_service = config_service
        self._lock = threading.RLock()
        self._subscriptions: Dict[str, str] = {}
        
        # Configuration keys
        self.SETTING_1_KEY = "my_service_setting_1"
        self.SETTING_2_KEY = "my_service_setting_2"
        self.TIMEOUT_KEY = "my_service_timeout"
        
        # Initialize with current configuration
        self._initialize_configuration()
        
        # Subscribe to configuration changes
        self._setup_configuration_subscriptions()
    
    def _initialize_configuration(self):
        """Initialize service with current configuration values"""
        try:
            # Apply current configuration
            self.update_settings()
            
            logger.info("My service configuration adapter initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing my service configuration: {str(e)}")
            raise MyServiceConfigurationError(f"Failed to initialize configuration: {str(e)}")
    
    def _setup_configuration_subscriptions(self):
        """Set up subscriptions for configuration changes"""
        try:
            # Subscribe to setting_1 changes
            subscription_id = self.config_service.subscribe_to_changes(
                self.SETTING_1_KEY,
                self._handle_setting_1_change
            )
            self._subscriptions[self.SETTING_1_KEY] = subscription_id
            
            # Subscribe to setting_2 changes
            subscription_id = self.config_service.subscribe_to_changes(
                self.SETTING_2_KEY,
                self._handle_setting_2_change
            )
            self._subscriptions[self.SETTING_2_KEY] = subscription_id
            
            # Subscribe to timeout changes
            subscription_id = self.config_service.subscribe_to_changes(
                self.TIMEOUT_KEY,
                self._handle_timeout_change
            )
            self._subscriptions[self.TIMEOUT_KEY] = subscription_id
            
            logger.info("Configuration subscriptions set up successfully")
            
        except Exception as e:
            logger.error(f"Error setting up configuration subscriptions: {str(e)}")
    
    def update_settings(self) -> bool:
        """Update service settings from configuration"""
        try:
            with self._lock:
                # Get current configuration values
                setting_1 = self.config_service.get_config(self.SETTING_1_KEY, "default_value")
                setting_2 = self.config_service.get_config(self.SETTING_2_KEY, 100)
                timeout = self.config_service.get_config(self.TIMEOUT_KEY, 30)
                
                # Apply to service
                self.my_service.update_setting_1(setting_1)
                self.my_service.update_setting_2(setting_2)
                self.my_service.update_timeout(timeout)
                
                logger.info(f"Updated service settings: setting_1={setting_1}, setting_2={setting_2}, timeout={timeout}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating service settings: {str(e)}")
            return False
    
    def _handle_setting_1_change(self, key: str, old_value: Any, new_value: Any):
        """Handle setting_1 configuration change"""
        try:
            with self._lock:
                self.my_service.update_setting_1(new_value)
                logger.info(f"Updated {key} from {old_value} to {new_value}")
        except Exception as e:
            logger.error(f"Error handling {key} change: {str(e)}")
    
    def _handle_setting_2_change(self, key: str, old_value: Any, new_value: Any):
        """Handle setting_2 configuration change"""
        try:
            with self._lock:
                # Validate new value
                if not isinstance(new_value, int) or new_value < 0:
                    logger.error(f"Invalid value for {key}: {new_value}")
                    return
                
                self.my_service.update_setting_2(new_value)
                logger.info(f"Updated {key} from {old_value} to {new_value}")
        except Exception as e:
            logger.error(f"Error handling {key} change: {str(e)}")
    
    def _handle_timeout_change(self, key: str, old_value: Any, new_value: Any):
        """Handle timeout configuration change"""
        try:
            with self._lock:
                # Validate timeout value
                if not isinstance(new_value, (int, float)) or new_value <= 0:
                    logger.error(f"Invalid timeout value: {new_value}")
                    return
                
                self.my_service.update_timeout(new_value)
                logger.info(f"Updated {key} from {old_value} to {new_value}")
        except Exception as e:
            logger.error(f"Error handling {key} change: {str(e)}")
    
    def cleanup(self):
        """Clean up subscriptions and resources"""
        try:
            # Unsubscribe from all configuration changes
            for key, subscription_id in self._subscriptions.items():
                self.config_service.unsubscribe(subscription_id)
                logger.debug(f"Unsubscribed from {key} changes")
            
            self._subscriptions.clear()
            logger.info("My service configuration adapter cleaned up successfully")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
```

### Step 3: Add Factory Function (Optional)

```python
def create_my_service_configuration_adapter(my_service, config_service: ConfigurationService) -> MyServiceConfigurationAdapter:
    """
    Factory function to create a my service configuration adapter
    
    Args:
        my_service: MyService instance
        config_service: ConfigurationService instance
        
    Returns:
        MyServiceConfigurationAdapter instance
    """
    return MyServiceConfigurationAdapter(
        my_service=my_service,
        config_service=config_service
    )
```

## Service Integration Steps

### Step 1: Identify Configuration Requirements

1. **List configurable parameters**: What settings should be configurable?
2. **Determine update requirements**: Can settings change at runtime?
3. **Define validation rules**: What are valid values for each setting?
4. **Assess restart requirements**: Which settings require application restart?

### Step 2: Update Service Implementation

Modify your service to support dynamic configuration updates:

```python
class MyService:
    def __init__(self):
        self.setting_1 = "default_value"
        self.setting_2 = 100
        self.timeout = 30
    
    def update_setting_1(self, value: str):
        """Update setting_1 with validation"""
        if not isinstance(value, str):
            raise ValueError("setting_1 must be a string")
        self.setting_1 = value
    
    def update_setting_2(self, value: int):
        """Update setting_2 with validation"""
        if not isinstance(value, int) or value < 0:
            raise ValueError("setting_2 must be a non-negative integer")
        self.setting_2 = value
    
    def update_timeout(self, value: float):
        """Update timeout with validation"""
        if not isinstance(value, (int, float)) or value <= 0:
            raise ValueError("timeout must be a positive number")
        self.timeout = value
```

### Step 3: Add Configuration Schema

Add configuration schema entries to the database:

```python
# In your migration or setup script
from system_configuration_manager import SystemConfigurationManager, ConfigurationCategory, ConfigurationDataType

def add_my_service_configuration_schema(db_manager):
    """Add configuration schema for MyService"""
    config_manager = SystemConfigurationManager(db_manager)
    
    # Add setting_1 configuration
    config_manager.add_configuration_schema(
        key="my_service_setting_1",
        category=ConfigurationCategory.PERFORMANCE,
        data_type=ConfigurationDataType.STRING,
        default_value="default_value",
        description="Description of setting 1",
        requires_restart=False,
        validation_rules={"min_length": 1, "max_length": 100}
    )
    
    # Add setting_2 configuration
    config_manager.add_configuration_schema(
        key="my_service_setting_2",
        category=ConfigurationCategory.PERFORMANCE,
        data_type=ConfigurationDataType.INTEGER,
        default_value=100,
        description="Description of setting 2",
        requires_restart=False,
        validation_rules={"min_value": 0, "max_value": 1000}
    )
    
    # Add timeout configuration
    config_manager.add_configuration_schema(
        key="my_service_timeout",
        category=ConfigurationCategory.PERFORMANCE,
        data_type=ConfigurationDataType.FLOAT,
        default_value=30.0,
        description="Service timeout in seconds",
        requires_restart=False,
        validation_rules={"min_value": 1.0, "max_value": 300.0}
    )
```

### Step 4: Initialize Adapter in Application

```python
# In your application initialization
def initialize_my_service_integration(app, db_manager, config_service):
    """Initialize MyService with configuration integration"""
    
    # Create service instance
    my_service = MyService()
    
    # Create configuration adapter
    my_service_adapter = MyServiceConfigurationAdapter(
        my_service=my_service,
        config_service=config_service
    )
    
    # Store references for cleanup
    app.my_service = my_service
    app.my_service_adapter = my_service_adapter
    
    return my_service, my_service_adapter
```

### Step 5: Add Cleanup Handling

```python
# In your application shutdown
def cleanup_my_service_integration(app):
    """Clean up MyService configuration integration"""
    if hasattr(app, 'my_service_adapter'):
        app.my_service_adapter.cleanup()
```

## Configuration Schema Setup

### Schema Categories

Choose appropriate category for your configuration:

- `SYSTEM`: Core system settings
- `PERFORMANCE`: Performance-related settings
- `SECURITY`: Security-related settings
- `FEATURE_FLAGS`: Feature toggle settings
- `MAINTENANCE`: Maintenance and operational settings
- `MONITORING`: Monitoring and alerting settings

### Data Types

Supported configuration data types:

- `STRING`: Text values
- `INTEGER`: Whole numbers
- `FLOAT`: Decimal numbers
- `BOOLEAN`: True/false values
- `JSON`: Complex structured data

### Validation Rules

Common validation rule patterns:

```python
# String validation
validation_rules = {
    "min_length": 1,
    "max_length": 100,
    "pattern": r"^[a-zA-Z0-9_]+$"
}

# Numeric validation
validation_rules = {
    "min_value": 0,
    "max_value": 1000
}

# Boolean validation (usually none needed)
validation_rules = {}

# JSON validation
validation_rules = {
    "schema": {
        "type": "object",
        "properties": {
            "key": {"type": "string"}
        }
    }
}
```

## Testing Integration

### Unit Tests

Create comprehensive unit tests for your adapter:

```python
import unittest
from unittest.mock import Mock, patch
from my_service_configuration_adapter import MyServiceConfigurationAdapter

class TestMyServiceConfigurationAdapter(unittest.TestCase):
    def setUp(self):
        self.mock_service = Mock()
        self.mock_config_service = Mock()
        self.adapter = MyServiceConfigurationAdapter(
            self.mock_service,
            self.mock_config_service
        )
    
    def test_initialization(self):
        """Test adapter initialization"""
        # Verify configuration was loaded
        self.mock_config_service.get_config.assert_called()
        
        # Verify subscriptions were created
        self.mock_config_service.subscribe_to_changes.assert_called()
    
    def test_setting_update(self):
        """Test configuration setting update"""
        # Simulate configuration change
        self.adapter._handle_setting_1_change("my_service_setting_1", "old", "new")
        
        # Verify service was updated
        self.mock_service.update_setting_1.assert_called_with("new")
    
    def test_validation_error_handling(self):
        """Test handling of validation errors"""
        # Configure service to raise validation error
        self.mock_service.update_setting_2.side_effect = ValueError("Invalid value")
        
        # Should not raise exception
        self.adapter._handle_setting_2_change("my_service_setting_2", 100, -1)
        
        # Verify error was logged (check logs in actual implementation)
```

### Integration Tests

Test the complete integration flow:

```python
def test_end_to_end_configuration_update(self):
    """Test complete configuration update flow"""
    # Create real instances
    config_service = ConfigurationService(db_manager)
    my_service = MyService()
    adapter = MyServiceConfigurationAdapter(my_service, config_service)
    
    # Update configuration through admin interface
    with db_manager.get_session() as session:
        config = session.query(SystemConfiguration).filter_by(
            key="my_service_setting_1"
        ).first()
        config.value = "new_value"
        session.commit()
    
    # Notify configuration service of change
    config_service.notify_change("my_service_setting_1", "old_value", "new_value")
    
    # Verify service was updated
    self.assertEqual(my_service.setting_1, "new_value")
```

## Best Practices

### 1. Error Handling

- Always handle configuration errors gracefully
- Provide fallback values for critical settings
- Log configuration errors with appropriate severity
- Don't let configuration errors crash the service

### 2. Validation

- Validate configuration values before applying
- Provide clear error messages for invalid values
- Use type hints for better code clarity
- Document validation rules in schema

### 3. Performance

- Use appropriate cache TTL for your configuration
- Batch related configuration reads when possible
- Avoid frequent configuration access in hot paths
- Monitor configuration access patterns

### 4. Threading

- Use thread-safe operations for configuration updates
- Protect shared state with appropriate locking
- Consider async patterns for non-blocking updates
- Test concurrent access scenarios

### 5. Logging

- Log configuration changes with INFO level
- Log errors with ERROR level
- Include old and new values in change logs
- Use structured logging for better analysis

### 6. Documentation

- Document all configuration keys and their purpose
- Provide examples of valid values
- Document restart requirements clearly
- Keep documentation up to date

## Troubleshooting

### Common Issues

#### 1. Configuration Not Updating

**Symptoms**: Service doesn't reflect configuration changes

**Possible Causes**:
- Subscription not set up correctly
- Configuration cache not invalidated
- Service update method not called

**Solutions**:
```python
# Check subscription status
subscriptions = adapter._subscriptions
print(f"Active subscriptions: {subscriptions}")

# Force configuration refresh
config_service.refresh_config("my_service_setting_1")

# Manually trigger update
adapter.update_settings()
```

#### 2. Validation Errors

**Symptoms**: Configuration changes rejected

**Possible Causes**:
- Invalid value format
- Value outside allowed range
- Type mismatch

**Solutions**:
```python
# Check configuration schema
schema = config_service.system_config_manager.get_configuration_schema("my_service_setting_1")
print(f"Schema: {schema}")

# Validate value manually
try:
    adapter._handle_setting_1_change("my_service_setting_1", "old", "new")
except Exception as e:
    print(f"Validation error: {e}")
```

#### 3. Memory Leaks

**Symptoms**: Memory usage increases over time

**Possible Causes**:
- Subscriptions not cleaned up
- Cache growing without bounds
- Event handlers holding references

**Solutions**:
```python
# Clean up subscriptions
adapter.cleanup()

# Check cache statistics
stats = config_service.get_cache_stats()
print(f"Cache size: {stats['cache']['size']}")

# Monitor subscription count
print(f"Active subscriptions: {len(adapter._subscriptions)}")
```

#### 4. Performance Issues

**Symptoms**: Slow configuration access

**Possible Causes**:
- Cache misses
- Database connection issues
- Inefficient configuration access patterns

**Solutions**:
```python
# Check cache hit rate
stats = config_service.get_cache_stats()
print(f"Hit rate: {stats['hit_rate']:.2%}")

# Optimize configuration access
# Batch related reads
settings = {
    'setting_1': config_service.get_config('my_service_setting_1'),
    'setting_2': config_service.get_config('my_service_setting_2'),
    'timeout': config_service.get_config('my_service_timeout')
}
```

### Debugging Tools

#### Configuration Service Debug

```python
def debug_configuration_service(config_service, key):
    """Debug configuration service for specific key"""
    try:
        # Get with metadata
        config_value = config_service.get_config_with_metadata(key)
        if config_value:
            print(f"Key: {config_value.key}")
            print(f"Value: {config_value.value}")
            print(f"Source: {config_value.source.value}")
            print(f"Type: {config_value.data_type}")
            print(f"Requires restart: {config_value.requires_restart}")
            print(f"Last updated: {config_value.last_updated}")
        else:
            print(f"Configuration key '{key}' not found")
    except Exception as e:
        print(f"Error getting configuration: {e}")
```

#### Adapter Debug

```python
def debug_adapter(adapter):
    """Debug configuration adapter"""
    print(f"Active subscriptions: {len(adapter._subscriptions)}")
    for key, subscription_id in adapter._subscriptions.items():
        print(f"  {key}: {subscription_id}")
    
    # Test configuration access
    try:
        adapter.update_settings()
        print("Configuration update successful")
    except Exception as e:
        print(f"Configuration update failed: {e}")
```

This guide provides comprehensive instructions for integrating any service with the configuration system. Follow these patterns for consistent, reliable configuration management.
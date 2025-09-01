# Notification System Configuration Guide

## Overview

This guide provides comprehensive documentation for configuring the unified notification system. It covers environment variables, WebSocket settings, notification behavior customization, and advanced configuration options.

## Environment Variables

### Core Notification System Configuration

```bash
# Enable/Disable Notification System
NOTIFICATION_SYSTEM_ENABLED=true

# Redis Configuration for Notifications
NOTIFICATION_REDIS_PREFIX=vedfolnir:notifications:
NOTIFICATION_DEFAULT_TTL=3600
NOTIFICATION_MAX_QUEUE_SIZE=1000
NOTIFICATION_CLEANUP_INTERVAL=300

# Notification Delivery Settings
NOTIFICATION_RETRY_ATTEMPTS=3
NOTIFICATION_RETRY_DELAY=1000
NOTIFICATION_BATCH_SIZE=10
NOTIFICATION_BATCH_TIMEOUT=1000
```

### WebSocket Configuration

```bash
# WebSocket Server Settings
WEBSOCKET_CORS_ORIGINS=http://127.0.0.1:5000,http://localhost:5000
WEBSOCKET_PING_TIMEOUT=60000
WEBSOCKET_PING_INTERVAL=25000
WEBSOCKET_MAX_HTTP_BUFFER_SIZE=1000000

# WebSocket Namespaces
WEBSOCKET_NAMESPACE_USER=/user
WEBSOCKET_NAMESPACE_ADMIN=/admin
WEBSOCKET_NAMESPACE_SYSTEM=/system

# WebSocket Security
WEBSOCKET_AUTH_REQUIRED=true
WEBSOCKET_RATE_LIMIT_ENABLED=true
WEBSOCKET_RATE_LIMIT_REQUESTS=100
WEBSOCKET_RATE_LIMIT_WINDOW=60
```

### Notification UI Configuration

```bash
# UI Behavior Settings
NOTIFICATION_AUTO_HIDE_DURATION=5000
NOTIFICATION_MAX_DISPLAY=5
NOTIFICATION_POSITION=top-right
NOTIFICATION_ANIMATION_DURATION=300
NOTIFICATION_STACK_LIMIT=10

# UI Styling
NOTIFICATION_THEME=default
NOTIFICATION_CUSTOM_CSS_ENABLED=false
NOTIFICATION_CUSTOM_CSS_PATH=/static/css/custom-notifications.css

# Accessibility Settings
NOTIFICATION_SCREEN_READER_ENABLED=true
NOTIFICATION_HIGH_CONTRAST_MODE=false
NOTIFICATION_REDUCED_MOTION=false
```

### Performance and Monitoring

```bash
# Performance Settings
NOTIFICATION_PERFORMANCE_MONITORING=true
NOTIFICATION_METRICS_COLLECTION=true
NOTIFICATION_HEALTH_CHECK_INTERVAL=30

# Logging Configuration
NOTIFICATION_LOG_LEVEL=INFO
NOTIFICATION_LOG_FILE=/var/log/vedfolnir/notifications.log
NOTIFICATION_DEBUG_MODE=false

# Database Settings
NOTIFICATION_DB_POOL_SIZE=10
NOTIFICATION_DB_TIMEOUT=30
NOTIFICATION_DB_RETRY_ATTEMPTS=3
```

## Configuration Files

### 1. Main Configuration (config.py)

```python
class NotificationConfig:
    """Notification system configuration"""
    
    # Core settings
    NOTIFICATION_SYSTEM_ENABLED = os.getenv('NOTIFICATION_SYSTEM_ENABLED', 'true').lower() == 'true'
    NOTIFICATION_REDIS_PREFIX = os.getenv('NOTIFICATION_REDIS_PREFIX', 'vedfolnir:notifications:')
    NOTIFICATION_DEFAULT_TTL = int(os.getenv('NOTIFICATION_DEFAULT_TTL', '3600'))
    
    # WebSocket settings
    WEBSOCKET_CORS_ORIGINS = os.getenv('WEBSOCKET_CORS_ORIGINS', 'http://127.0.0.1:5000').split(',')
    WEBSOCKET_PING_TIMEOUT = int(os.getenv('WEBSOCKET_PING_TIMEOUT', '60000'))
    WEBSOCKET_PING_INTERVAL = int(os.getenv('WEBSOCKET_PING_INTERVAL', '25000'))
    
    # UI settings
    NOTIFICATION_AUTO_HIDE_DURATION = int(os.getenv('NOTIFICATION_AUTO_HIDE_DURATION', '5000'))
    NOTIFICATION_MAX_DISPLAY = int(os.getenv('NOTIFICATION_MAX_DISPLAY', '5'))
    NOTIFICATION_POSITION = os.getenv('NOTIFICATION_POSITION', 'top-right')
    
    # Performance settings
    NOTIFICATION_BATCH_SIZE = int(os.getenv('NOTIFICATION_BATCH_SIZE', '10'))
    NOTIFICATION_RETRY_ATTEMPTS = int(os.getenv('NOTIFICATION_RETRY_ATTEMPTS', '3'))
    
    @classmethod
    def validate_config(cls):
        """Validate notification configuration"""
        errors = []
        
        # Validate required settings
        if not cls.NOTIFICATION_REDIS_PREFIX:
            errors.append("NOTIFICATION_REDIS_PREFIX cannot be empty")
        
        if cls.NOTIFICATION_DEFAULT_TTL <= 0:
            errors.append("NOTIFICATION_DEFAULT_TTL must be positive")
        
        if cls.NOTIFICATION_MAX_DISPLAY <= 0:
            errors.append("NOTIFICATION_MAX_DISPLAY must be positive")
        
        # Validate position
        valid_positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'top-center', 'bottom-center']
        if cls.NOTIFICATION_POSITION not in valid_positions:
            errors.append(f"NOTIFICATION_POSITION must be one of: {', '.join(valid_positions)}")
        
        return errors
```

### 2. WebSocket Configuration (websocket_config.py)

```python
class WebSocketNotificationConfig:
    """WebSocket-specific notification configuration"""
    
    def __init__(self, app_config):
        self.app_config = app_config
        
    def get_socketio_config(self):
        """Get Socket.IO configuration for notifications"""
        return {
            'cors_allowed_origins': self.app_config.WEBSOCKET_CORS_ORIGINS,
            'ping_timeout': self.app_config.WEBSOCKET_PING_TIMEOUT,
            'ping_interval': self.app_config.WEBSOCKET_PING_INTERVAL,
            'max_http_buffer_size': self.app_config.WEBSOCKET_MAX_HTTP_BUFFER_SIZE,
            'logger': self.app_config.NOTIFICATION_DEBUG_MODE,
            'engineio_logger': self.app_config.NOTIFICATION_DEBUG_MODE,
            'async_mode': 'threading'
        }
    
    def get_namespace_config(self):
        """Get namespace configuration"""
        return {
            'user': self.app_config.WEBSOCKET_NAMESPACE_USER,
            'admin': self.app_config.WEBSOCKET_NAMESPACE_ADMIN,
            'system': self.app_config.WEBSOCKET_NAMESPACE_SYSTEM
        }
```

### 3. UI Configuration (notification-ui-config.js)

```javascript
// Notification UI Configuration
const NotificationUIConfig = {
    // Display settings
    position: process.env.NOTIFICATION_POSITION || 'top-right',
    autoHideDuration: parseInt(process.env.NOTIFICATION_AUTO_HIDE_DURATION) || 5000,
    maxDisplay: parseInt(process.env.NOTIFICATION_MAX_DISPLAY) || 5,
    animationDuration: parseInt(process.env.NOTIFICATION_ANIMATION_DURATION) || 300,
    
    // Styling
    theme: process.env.NOTIFICATION_THEME || 'default',
    customCSS: process.env.NOTIFICATION_CUSTOM_CSS_ENABLED === 'true',
    
    // Accessibility
    screenReader: process.env.NOTIFICATION_SCREEN_READER_ENABLED !== 'false',
    highContrast: process.env.NOTIFICATION_HIGH_CONTRAST_MODE === 'true',
    reducedMotion: process.env.NOTIFICATION_REDUCED_MOTION === 'true',
    
    // Notification types configuration
    types: {
        SUCCESS: {
            icon: '✅',
            color: '#28a745',
            autoHide: true,
            duration: 4000
        },
        WARNING: {
            icon: '⚠️',
            color: '#ffc107',
            autoHide: true,
            duration: 6000
        },
        ERROR: {
            icon: '❌',
            color: '#dc3545',
            autoHide: false,
            duration: 0
        },
        INFO: {
            icon: 'ℹ️',
            color: '#17a2b8',
            autoHide: true,
            duration: 5000
        },
        PROGRESS: {
            icon: '🔄',
            color: '#6f42c1',
            autoHide: false,
            duration: 0,
            showProgress: true
        }
    },
    
    // Position configurations
    positions: {
        'top-left': { top: '20px', left: '20px' },
        'top-right': { top: '20px', right: '20px' },
        'top-center': { top: '20px', left: '50%', transform: 'translateX(-50%)' },
        'bottom-left': { bottom: '20px', left: '20px' },
        'bottom-right': { bottom: '20px', right: '20px' },
        'bottom-center': { bottom: '20px', left: '50%', transform: 'translateX(-50%)' }
    }
};
```

## Advanced Configuration Options

### 1. Custom Notification Types

```python
# Define custom notification types
CUSTOM_NOTIFICATION_TYPES = {
    'MAINTENANCE': {
        'icon': '🔧',
        'color': '#fd7e14',
        'auto_hide': False,
        'priority': 'HIGH',
        'requires_action': True
    },
    'SECURITY': {
        'icon': '🔒',
        'color': '#e83e8c',
        'auto_hide': False,
        'priority': 'CRITICAL',
        'requires_action': True,
        'admin_only': True
    },
    'SYSTEM_UPDATE': {
        'icon': '📦',
        'color': '#20c997',
        'auto_hide': True,
        'duration': 8000,
        'priority': 'NORMAL'
    }
}
```

### 2. Role-Based Configuration

```python
# Role-based notification settings
ROLE_NOTIFICATION_CONFIG = {
    'admin': {
        'namespaces': ['/admin', '/system', '/user'],
        'max_notifications': 20,
        'auto_hide_duration': 0,  # Never auto-hide for admins
        'priority_filter': ['LOW', 'NORMAL', 'HIGH', 'CRITICAL'],
        'categories': ['system', 'security', 'maintenance', 'user', 'platform']
    },
    'user': {
        'namespaces': ['/user'],
        'max_notifications': 5,
        'auto_hide_duration': 5000,
        'priority_filter': ['NORMAL', 'HIGH', 'CRITICAL'],
        'categories': ['platform', 'caption', 'system']
    },
    'reviewer': {
        'namespaces': ['/user'],
        'max_notifications': 10,
        'auto_hide_duration': 3000,
        'priority_filter': ['NORMAL', 'HIGH', 'CRITICAL'],
        'categories': ['platform', 'caption', 'system', 'review']
    }
}
```

### 3. Performance Tuning

```python
# Performance optimization settings
NOTIFICATION_PERFORMANCE_CONFIG = {
    # Connection pooling
    'websocket_pool_size': 100,
    'websocket_max_connections': 1000,
    
    # Message batching
    'batch_enabled': True,
    'batch_size': 10,
    'batch_timeout': 1000,  # ms
    
    # Caching
    'cache_enabled': True,
    'cache_ttl': 300,  # seconds
    'cache_max_size': 1000,
    
    # Rate limiting
    'rate_limit_enabled': True,
    'rate_limit_requests': 100,
    'rate_limit_window': 60,  # seconds
    
    # Cleanup
    'cleanup_interval': 300,  # seconds
    'retention_period': 86400,  # 24 hours
}
```

## Environment-Specific Configurations

### Development Environment

```bash
# Development settings (.env.development)
NOTIFICATION_SYSTEM_ENABLED=true
NOTIFICATION_DEBUG_MODE=true
NOTIFICATION_LOG_LEVEL=DEBUG

# Relaxed CORS for development
WEBSOCKET_CORS_ORIGINS=http://127.0.0.1:5000,http://localhost:5000,http://localhost:3000

# Shorter timeouts for faster development
NOTIFICATION_AUTO_HIDE_DURATION=3000
NOTIFICATION_RETRY_DELAY=500

# Enhanced logging
NOTIFICATION_PERFORMANCE_MONITORING=true
NOTIFICATION_METRICS_COLLECTION=true
```

### Production Environment

```bash
# Production settings (.env.production)
NOTIFICATION_SYSTEM_ENABLED=true
NOTIFICATION_DEBUG_MODE=false
NOTIFICATION_LOG_LEVEL=INFO

# Strict CORS for production
WEBSOCKET_CORS_ORIGINS=https://yourdomain.com

# Optimized performance settings
NOTIFICATION_BATCH_SIZE=20
NOTIFICATION_MAX_QUEUE_SIZE=5000
NOTIFICATION_CLEANUP_INTERVAL=600

# Security settings
WEBSOCKET_AUTH_REQUIRED=true
WEBSOCKET_RATE_LIMIT_ENABLED=true
NOTIFICATION_RATE_LIMIT_REQUESTS=50
```

### Testing Environment

```bash
# Testing settings (.env.testing)
NOTIFICATION_SYSTEM_ENABLED=true
NOTIFICATION_DEBUG_MODE=true
NOTIFICATION_LOG_LEVEL=DEBUG

# Fast timeouts for testing
NOTIFICATION_AUTO_HIDE_DURATION=1000
NOTIFICATION_RETRY_DELAY=100
NOTIFICATION_CLEANUP_INTERVAL=60

# Reduced limits for testing
NOTIFICATION_MAX_DISPLAY=3
NOTIFICATION_MAX_QUEUE_SIZE=100
```

## Configuration Validation

### Validation Script

Create: `scripts/validate_notification_config.py`

```python
#!/usr/bin/env python3
# Copyright (C) 2025 iolaire mcfadden.
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU Affero General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Notification Configuration Validator
Validates notification system configuration and provides recommendations
"""

import os
import sys
import json
from urllib.parse import urlparse

def validate_notification_config():
    """Validate notification system configuration"""
    
    print("🔍 Validating Notification System Configuration...")
    
    errors = []
    warnings = []
    recommendations = []
    
    # Check core settings
    enabled = os.getenv('NOTIFICATION_SYSTEM_ENABLED', 'true').lower()
    if enabled not in ['true', 'false']:
        errors.append("NOTIFICATION_SYSTEM_ENABLED must be 'true' or 'false'")
    
    # Validate Redis settings
    redis_prefix = os.getenv('NOTIFICATION_REDIS_PREFIX', '')
    if not redis_prefix:
        errors.append("NOTIFICATION_REDIS_PREFIX cannot be empty")
    elif not redis_prefix.endswith(':'):
        warnings.append("NOTIFICATION_REDIS_PREFIX should end with ':'")
    
    # Validate TTL settings
    try:
        ttl = int(os.getenv('NOTIFICATION_DEFAULT_TTL', '3600'))
        if ttl <= 0:
            errors.append("NOTIFICATION_DEFAULT_TTL must be positive")
        elif ttl < 300:
            warnings.append("NOTIFICATION_DEFAULT_TTL is very short (< 5 minutes)")
    except ValueError:
        errors.append("NOTIFICATION_DEFAULT_TTL must be a valid integer")
    
    # Validate WebSocket CORS
    cors_origins = os.getenv('WEBSOCKET_CORS_ORIGINS', '')
    if cors_origins:
        origins = [origin.strip() for origin in cors_origins.split(',')]
        for origin in origins:
            try:
                parsed = urlparse(origin)
                if not parsed.scheme or not parsed.netloc:
                    errors.append(f"Invalid CORS origin: {origin}")
            except Exception:
                errors.append(f"Invalid CORS origin format: {origin}")
    else:
        warnings.append("WEBSOCKET_CORS_ORIGINS not set - may cause connection issues")
    
    # Validate UI settings
    try:
        max_display = int(os.getenv('NOTIFICATION_MAX_DISPLAY', '5'))
        if max_display <= 0:
            errors.append("NOTIFICATION_MAX_DISPLAY must be positive")
        elif max_display > 20:
            warnings.append("NOTIFICATION_MAX_DISPLAY is very high (> 20)")
    except ValueError:
        errors.append("NOTIFICATION_MAX_DISPLAY must be a valid integer")
    
    # Validate position
    position = os.getenv('NOTIFICATION_POSITION', 'top-right')
    valid_positions = ['top-left', 'top-right', 'bottom-left', 'bottom-right', 'top-center', 'bottom-center']
    if position not in valid_positions:
        errors.append(f"NOTIFICATION_POSITION must be one of: {', '.join(valid_positions)}")
    
    # Performance recommendations
    batch_size = int(os.getenv('NOTIFICATION_BATCH_SIZE', '10'))
    if batch_size > 50:
        recommendations.append("Consider reducing NOTIFICATION_BATCH_SIZE for better performance")
    
    queue_size = int(os.getenv('NOTIFICATION_MAX_QUEUE_SIZE', '1000'))
    if queue_size > 10000:
        recommendations.append("Very large NOTIFICATION_MAX_QUEUE_SIZE may impact memory usage")
    
    # Security checks
    auth_required = os.getenv('WEBSOCKET_AUTH_REQUIRED', 'true').lower()
    if auth_required != 'true':
        warnings.append("WEBSOCKET_AUTH_REQUIRED is disabled - security risk")
    
    rate_limit = os.getenv('WEBSOCKET_RATE_LIMIT_ENABLED', 'true').lower()
    if rate_limit != 'true':
        warnings.append("WEBSOCKET_RATE_LIMIT_ENABLED is disabled - may allow abuse")
    
    # Print results
    print("\n" + "=" * 60)
    print("CONFIGURATION VALIDATION RESULTS")
    print("=" * 60)
    
    if errors:
        print(f"\n❌ ERRORS ({len(errors)}):")
        for error in errors:
            print(f"   - {error}")
    
    if warnings:
        print(f"\n⚠️ WARNINGS ({len(warnings)}):")
        for warning in warnings:
            print(f"   - {warning}")
    
    if recommendations:
        print(f"\n💡 RECOMMENDATIONS ({len(recommendations)}):")
        for rec in recommendations:
            print(f"   - {rec}")
    
    if not errors and not warnings:
        print("\n✅ Configuration is valid with no issues!")
    elif not errors:
        print("\n✅ Configuration is valid with minor warnings")
    else:
        print(f"\n❌ Configuration has {len(errors)} error(s) that must be fixed")
    
    return len(errors) == 0

if __name__ == '__main__':
    success = validate_notification_config()
    sys.exit(0 if success else 1)
```

## Configuration Templates

### 1. Minimal Configuration

```bash
# Minimal notification system configuration
NOTIFICATION_SYSTEM_ENABLED=true
WEBSOCKET_CORS_ORIGINS=http://127.0.0.1:5000
NOTIFICATION_POSITION=top-right
NOTIFICATION_AUTO_HIDE_DURATION=5000
```

### 2. High-Performance Configuration

```bash
# High-performance notification configuration
NOTIFICATION_SYSTEM_ENABLED=true
NOTIFICATION_BATCH_SIZE=20
NOTIFICATION_MAX_QUEUE_SIZE=5000
NOTIFICATION_CLEANUP_INTERVAL=300

# WebSocket optimization
WEBSOCKET_PING_TIMEOUT=30000
WEBSOCKET_PING_INTERVAL=10000
WEBSOCKET_MAX_HTTP_BUFFER_SIZE=2000000

# Performance monitoring
NOTIFICATION_PERFORMANCE_MONITORING=true
NOTIFICATION_METRICS_COLLECTION=true
```

### 3. Security-Focused Configuration

```bash
# Security-focused notification configuration
NOTIFICATION_SYSTEM_ENABLED=true
WEBSOCKET_AUTH_REQUIRED=true
WEBSOCKET_RATE_LIMIT_ENABLED=true
WEBSOCKET_RATE_LIMIT_REQUESTS=50
WEBSOCKET_RATE_LIMIT_WINDOW=60

# Strict CORS
WEBSOCKET_CORS_ORIGINS=https://yourdomain.com

# Enhanced logging
NOTIFICATION_LOG_LEVEL=INFO
NOTIFICATION_DEBUG_MODE=false
```

## Troubleshooting Configuration Issues

### Common Configuration Problems

1. **WebSocket Connection Failures**
   ```bash
   # Check CORS configuration
   echo $WEBSOCKET_CORS_ORIGINS
   
   # Verify URL format
   curl -I $WEBSOCKET_CORS_ORIGINS
   ```

2. **Notification Not Displaying**
   ```bash
   # Check UI configuration
   echo $NOTIFICATION_POSITION
   echo $NOTIFICATION_MAX_DISPLAY
   
   # Verify CSS loading
   curl -I http://127.0.0.1:5000/static/css/notifications.css
   ```

3. **Performance Issues**
   ```bash
   # Check batch settings
   echo $NOTIFICATION_BATCH_SIZE
   echo $NOTIFICATION_MAX_QUEUE_SIZE
   
   # Monitor Redis usage
   redis-cli info memory
   ```

### Configuration Reset

```bash
# Reset to default configuration
unset NOTIFICATION_SYSTEM_ENABLED
unset NOTIFICATION_REDIS_PREFIX
unset NOTIFICATION_DEFAULT_TTL
unset WEBSOCKET_CORS_ORIGINS
unset NOTIFICATION_POSITION
unset NOTIFICATION_AUTO_HIDE_DURATION

# Restart application
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

---

**Configuration Guide Version**: 1.0  
**Last Updated**: August 30, 2025  
**Compatibility**: Unified Notification System v1.0+
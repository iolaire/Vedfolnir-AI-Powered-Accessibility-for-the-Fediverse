# WebSocket CORS Configuration Guide

## Overview

This guide provides comprehensive configuration documentation for the WebSocket CORS standardization system in Vedfolnir. The system provides dynamic CORS configuration, unified Socket.IO setup, and robust error handling across development, staging, and production environments.

## Environment Variables

### Core WebSocket Configuration

```bash
# Flask Host and Port (Required)
FLASK_HOST=localhost                    # Host for the Flask application
FLASK_PORT=5000                        # Port for the Flask application

# WebSocket CORS Configuration
SOCKETIO_CORS_ORIGINS=                  # Optional: Override auto-generated CORS origins
SOCKETIO_CORS_CREDENTIALS=true          # Allow credentials in CORS requests
SOCKETIO_CORS_METHODS=GET,POST,OPTIONS  # Allowed HTTP methods

# Transport Configuration
SOCKETIO_TRANSPORTS=websocket,polling   # Allowed transport methods
SOCKETIO_ASYNC_MODE=threading          # Async mode (threading, eventlet, gevent)

# Connection Timeouts
SOCKETIO_PING_TIMEOUT=60               # Ping timeout in seconds
SOCKETIO_PING_INTERVAL=25              # Ping interval in seconds
SOCKETIO_CONNECT_TIMEOUT=60            # Connection timeout in seconds

# Security Configuration
SOCKETIO_CSRF_PROTECTION=true          # Enable CSRF protection for WebSocket events
SOCKETIO_RATE_LIMITING=true            # Enable rate limiting
SOCKETIO_MAX_CONNECTIONS_PER_USER=5    # Maximum concurrent connections per user

# Debug and Logging
SOCKETIO_DEBUG=false                   # Enable debug logging
SOCKETIO_LOG_LEVEL=INFO                # Logging level (DEBUG, INFO, WARNING, ERROR)
```

### Environment-Specific Examples

#### Development Environment (.env.development)
```bash
# Development Configuration
FLASK_HOST=localhost
FLASK_PORT=5000
FLASK_ENV=development
FLASK_DEBUG=true

# WebSocket Development Settings
SOCKETIO_DEBUG=true
SOCKETIO_LOG_LEVEL=DEBUG
SOCKETIO_CORS_CREDENTIALS=true
SOCKETIO_TRANSPORTS=websocket,polling

# Relaxed Security for Development
SOCKETIO_CSRF_PROTECTION=false
SOCKETIO_RATE_LIMITING=false
SOCKETIO_MAX_CONNECTIONS_PER_USER=10

# Development CORS (auto-generated from FLASK_HOST:FLASK_PORT)
# Will generate: http://localhost:5000, https://localhost:5000
```

#### Staging Environment (.env.staging)
```bash
# Staging Configuration
FLASK_HOST=staging.example.com
FLASK_PORT=443
FLASK_ENV=staging
FLASK_DEBUG=false

# WebSocket Staging Settings
SOCKETIO_DEBUG=false
SOCKETIO_LOG_LEVEL=INFO
SOCKETIO_CORS_CREDENTIALS=true
SOCKETIO_TRANSPORTS=websocket,polling

# Enhanced Security for Staging
SOCKETIO_CSRF_PROTECTION=true
SOCKETIO_RATE_LIMITING=true
SOCKETIO_MAX_CONNECTIONS_PER_USER=5

# Staging CORS (auto-generated)
# Will generate: https://staging.example.com:443, http://staging.example.com:443
```

#### Production Environment (.env.production)
```bash
# Production Configuration
FLASK_HOST=app.example.com
FLASK_PORT=443
FLASK_ENV=production
FLASK_DEBUG=false

# WebSocket Production Settings
SOCKETIO_DEBUG=false
SOCKETIO_LOG_LEVEL=WARNING
SOCKETIO_CORS_CREDENTIALS=true
SOCKETIO_TRANSPORTS=websocket,polling
SOCKETIO_ASYNC_MODE=eventlet

# Maximum Security for Production
SOCKETIO_CSRF_PROTECTION=true
SOCKETIO_RATE_LIMITING=true
SOCKETIO_MAX_CONNECTIONS_PER_USER=3
SOCKETIO_PING_TIMEOUT=30
SOCKETIO_PING_INTERVAL=15

# Production CORS (can be explicitly set for security)
SOCKETIO_CORS_ORIGINS=https://app.example.com,https://www.example.com
```

## Dynamic CORS Origin Generation

The system automatically generates CORS origins based on `FLASK_HOST` and `FLASK_PORT`:

### Automatic Generation Rules

1. **Basic Origins**: Creates both HTTP and HTTPS variants
   - `http://{FLASK_HOST}:{FLASK_PORT}`
   - `https://{FLASK_HOST}:{FLASK_PORT}`

2. **Localhost Handling**: For localhost/127.0.0.1, includes both variants
   - `http://localhost:5000`
   - `http://127.0.0.1:5000`
   - `https://localhost:5000`
   - `https://127.0.0.1:5000`

3. **Port Handling**: Standard ports (80, 443) are handled appropriately
   - Port 80: `http://example.com` (no port in URL)
   - Port 443: `https://example.com` (no port in URL)
   - Other ports: `http://example.com:8080`

### Manual CORS Override

To override automatic generation, set `SOCKETIO_CORS_ORIGINS`:

```bash
# Explicit CORS origins (comma-separated)
SOCKETIO_CORS_ORIGINS=https://app.example.com,https://admin.example.com,https://api.example.com
```

## Socket.IO Configuration

### Transport Configuration

```bash
# WebSocket-first with polling fallback (recommended)
SOCKETIO_TRANSPORTS=websocket,polling

# Polling-only (for restrictive networks)
SOCKETIO_TRANSPORTS=polling

# WebSocket-only (for high-performance scenarios)
SOCKETIO_TRANSPORTS=websocket
```

### Connection Management

```bash
# Connection timeouts (in seconds)
SOCKETIO_PING_TIMEOUT=60        # Time to wait for ping response
SOCKETIO_PING_INTERVAL=25       # Interval between pings
SOCKETIO_CONNECT_TIMEOUT=60     # Initial connection timeout

# Buffer sizes
SOCKETIO_MAX_HTTP_BUFFER_SIZE=1000000  # Maximum HTTP buffer size (1MB)
```

### Namespace Configuration

The system uses two main namespaces:

- **User Namespace** (`/`): General user functionality
- **Admin Namespace** (`/admin`): Administrative functionality

```python
# Namespace access is automatically configured based on user roles
# No additional environment configuration required
```

## Authentication Configuration

### Session-Based Authentication

```bash
# Session configuration (handled by Flask session system)
SESSION_COOKIE_NAME=session
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SECURE=true      # Set to false for HTTP development
SESSION_COOKIE_SAMESITE=Lax

# WebSocket authentication uses existing session system
# No additional WebSocket-specific auth configuration required
```

### CSRF Protection

```bash
# CSRF protection for WebSocket events
SOCKETIO_CSRF_PROTECTION=true

# CSRF token validation
CSRF_TOKEN_HEADER=X-CSRFToken
CSRF_COOKIE_NAME=csrf_token
```

## Error Handling Configuration

### Error Recovery Settings

```bash
# Client-side error recovery (configured in JavaScript)
WEBSOCKET_RETRY_ATTEMPTS=5
WEBSOCKET_RETRY_DELAY=1000      # Initial delay in milliseconds
WEBSOCKET_RETRY_MAX_DELAY=30000 # Maximum delay in milliseconds
WEBSOCKET_RETRY_MULTIPLIER=2    # Exponential backoff multiplier

# Transport fallback
WEBSOCKET_FALLBACK_ENABLED=true
WEBSOCKET_FALLBACK_DELAY=5000   # Delay before fallback attempt
```

### Error Logging

```bash
# Error logging configuration
WEBSOCKET_ERROR_LOGGING=true
WEBSOCKET_ERROR_LOG_FILE=logs/websocket_errors.log
WEBSOCKET_ERROR_LOG_LEVEL=ERROR
```

## Performance Configuration

### Connection Limits

```bash
# Per-user connection limits
SOCKETIO_MAX_CONNECTIONS_PER_USER=5

# Global connection limits
SOCKETIO_MAX_TOTAL_CONNECTIONS=1000

# Connection pool settings
SOCKETIO_CONNECTION_POOL_SIZE=100
```

### Message Handling

```bash
# Message queue configuration
SOCKETIO_MESSAGE_QUEUE_SIZE=1000
SOCKETIO_MESSAGE_BATCH_SIZE=10
SOCKETIO_MESSAGE_BATCH_TIMEOUT=100  # milliseconds
```

## Security Configuration

### Rate Limiting

```bash
# Rate limiting settings
SOCKETIO_RATE_LIMITING=true
SOCKETIO_RATE_LIMIT_CONNECTIONS=10  # Connections per minute per IP
SOCKETIO_RATE_LIMIT_MESSAGES=100    # Messages per minute per user
```

### Input Validation

```bash
# Input validation settings
SOCKETIO_INPUT_VALIDATION=true
SOCKETIO_MAX_MESSAGE_SIZE=10240     # Maximum message size in bytes
SOCKETIO_ALLOWED_EVENTS=caption_progress,admin_notification  # Comma-separated
```

## Monitoring Configuration

### Health Checks

```bash
# Health check settings
SOCKETIO_HEALTH_CHECK_ENABLED=true
SOCKETIO_HEALTH_CHECK_INTERVAL=30   # seconds
SOCKETIO_HEALTH_CHECK_ENDPOINT=/health/websocket
```

### Metrics Collection

```bash
# Metrics configuration
SOCKETIO_METRICS_ENABLED=true
SOCKETIO_METRICS_ENDPOINT=/metrics/websocket
SOCKETIO_METRICS_RETENTION=7d       # Retention period
```

## Configuration Validation

The system includes built-in configuration validation:

```python
# Validation is automatic on startup
# Check logs for validation results:
# INFO: WebSocket configuration validated successfully
# WARNING: Using fallback value for SOCKETIO_PING_TIMEOUT
# ERROR: Invalid CORS origin format: invalid-url
```

### Manual Validation

```bash
# Validate configuration manually
python -c "
from websocket_config_manager import WebSocketConfigManager
from config import Config
config = Config()
ws_config = WebSocketConfigManager(config)
if ws_config.validate_configuration():
    print('✅ Configuration is valid')
else:
    print('❌ Configuration has errors')
"
```

## Configuration Migration

### From Legacy WebSocket Implementation

If migrating from a previous WebSocket implementation:

1. **Remove old configuration variables**:
   ```bash
   # Remove these old variables
   unset SOCKETIO_CORS_ALLOWED_ORIGINS
   unset WEBSOCKET_CORS_ORIGINS
   unset OLD_WEBSOCKET_CONFIG
   ```

2. **Add new configuration variables**:
   ```bash
   # Add new standardized variables
   FLASK_HOST=localhost
   FLASK_PORT=5000
   SOCKETIO_CORS_CREDENTIALS=true
   ```

3. **Update client code** (see migration guide below)

## Troubleshooting Configuration

### Common Configuration Issues

1. **CORS Errors**: Check `FLASK_HOST` and `FLASK_PORT` match your actual server
2. **Connection Failures**: Verify `SOCKETIO_TRANSPORTS` includes appropriate methods
3. **Authentication Issues**: Ensure session configuration is correct
4. **Performance Problems**: Adjust timeout and connection limit settings

### Configuration Testing

```bash
# Test WebSocket configuration
python scripts/test_websocket_config.py

# Test CORS configuration
python scripts/test_cors_config.py

# Test authentication integration
python scripts/test_websocket_auth.py
```

## Best Practices

### Development
- Use debug logging and relaxed security settings
- Enable both WebSocket and polling transports
- Set higher connection limits for testing

### Staging
- Mirror production security settings
- Use realistic timeout values
- Enable comprehensive logging

### Production
- Use strict security settings
- Optimize timeout values for your network
- Enable monitoring and health checks
- Use explicit CORS origins for security

### Security
- Always enable CSRF protection in production
- Use HTTPS in production environments
- Set appropriate rate limits
- Regularly review and update security settings

## Configuration Templates

Complete configuration templates are available in:
- `config/websocket.env.development`
- `config/websocket.env.staging`
- `config/websocket.env.production`

Copy the appropriate template and customize for your environment.
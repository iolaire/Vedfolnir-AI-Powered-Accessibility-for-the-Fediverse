# WebSocket Production Readiness Features

## Overview

This document describes the comprehensive production readiness features implemented for the WebSocket CORS Standardization system. These features ensure enterprise-grade reliability, security, performance, and maintainability for production deployments.

## Table of Contents

1. [SSL/TLS Support](#ssltls-support)
2. [Production Logging](#production-logging)
3. [Monitoring Integration](#monitoring-integration)
4. [Backup and Recovery](#backup-and-recovery)
5. [Load Balancer Compatibility](#load-balancer-compatibility)
6. [Configuration Management](#configuration-management)
7. [Deployment Guide](#deployment-guide)
8. [Troubleshooting](#troubleshooting)

## SSL/TLS Support

### Secure WebSocket Connections (WSS)

The system provides comprehensive SSL/TLS support for secure WebSocket connections:

#### Features
- **TLS 1.2+ Support**: Minimum TLS 1.2 with TLS 1.3 support
- **Certificate Management**: Support for certificate files, key files, and CA bundles
- **SSL Context Configuration**: Customizable SSL contexts with security options
- **HTTPS Enforcement**: Automatic HTTP to HTTPS redirection
- **HSTS Support**: HTTP Strict Transport Security headers

#### Configuration

```bash
# SSL Certificate Files
WEBSOCKET_SSL_CERT_FILE=/path/to/certificate.pem
WEBSOCKET_SSL_KEY_FILE=/path/to/private_key.pem
WEBSOCKET_SSL_CA_FILE=/path/to/ca_bundle.pem

# SSL Protocol Configuration
WEBSOCKET_SSL_VERSION=TLSv1_2
WEBSOCKET_SSL_CIPHERS=ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS

# HTTPS Enforcement
WEBSOCKET_FORCE_HTTPS=true
WEBSOCKET_HTTPS_REDIRECT=true

# HSTS Configuration
WEBSOCKET_HSTS_ENABLED=true
WEBSOCKET_HSTS_MAX_AGE=31536000
WEBSOCKET_HSTS_INCLUDE_SUBDOMAINS=true
```

#### Implementation

```python
from websocket_production_config import ProductionWebSocketConfigManager
from websocket_production_factory import ProductionWebSocketFactory

# Initialize production configuration
config_manager = ProductionWebSocketConfigManager(config)

# Check SSL status
if config_manager.is_ssl_enabled():
    ssl_context = config_manager.get_ssl_context()
    print("SSL/TLS enabled with secure context")

# Create production WebSocket factory with SSL
factory = ProductionWebSocketFactory(config, db_manager, session_manager)
socketio = factory.create_production_socketio_instance(app)
```

### Security Best Practices

1. **Certificate Management**
   - Use certificates from trusted Certificate Authorities
   - Implement certificate rotation procedures
   - Monitor certificate expiration dates

2. **SSL Configuration**
   - Disable weak protocols (SSLv2, SSLv3, TLSv1.0, TLSv1.1)
   - Use strong cipher suites
   - Enable Perfect Forward Secrecy

3. **HSTS Implementation**
   - Enable HSTS headers for all HTTPS responses
   - Use appropriate max-age values
   - Include subdomains in HSTS policy

## Production Logging

### Comprehensive Logging System

The production logging system provides structured, high-performance logging with multiple output formats and destinations:

#### Features
- **Structured Logging**: JSON-formatted logs with consistent schema
- **Log Categories**: Connection, message, security, performance, error, and system logs
- **Log Rotation**: Automatic log rotation with configurable size limits
- **Remote Logging**: Support for syslog and log aggregation services
- **Performance Context**: Automatic timing and performance metrics

#### Configuration

```bash
# Log Levels
WEBSOCKET_LOG_LEVEL=INFO
WEBSOCKET_SECURITY_LOG_LEVEL=WARNING
WEBSOCKET_PERFORMANCE_LOG_LEVEL=INFO
WEBSOCKET_ERROR_LOG_LEVEL=ERROR

# Log Files
WEBSOCKET_LOG_FILE=/var/log/vedfolnir/websocket.log
WEBSOCKET_SECURITY_LOG_FILE=/var/log/vedfolnir/websocket_security.log
WEBSOCKET_PERFORMANCE_LOG_FILE=/var/log/vedfolnir/websocket_performance.log
WEBSOCKET_ERROR_LOG_FILE=/var/log/vedfolnir/websocket_errors.log

# Log Format
WEBSOCKET_JSON_LOGGING=true
WEBSOCKET_STRUCTURED_LOGGING=true

# Log Rotation
WEBSOCKET_LOG_ROTATION=true
WEBSOCKET_MAX_LOG_SIZE=100MB
WEBSOCKET_LOG_BACKUP_COUNT=10

# Remote Logging
WEBSOCKET_REMOTE_LOGGING=true
WEBSOCKET_SYSLOG_SERVER=syslog.example.com:514
WEBSOCKET_LOG_AGGREGATION_SERVICE=https://logs.example.com/api/ingest
```

#### Usage Examples

```python
from websocket_production_logging import ProductionWebSocketLogger, WebSocketLogLevel

# Initialize logger
logger = ProductionWebSocketLogger(logging_config)

# Log connection events
logger.log_connection_event(
    event_type="connection_established",
    message="WebSocket connection established",
    session_id="session_123",
    user_id=1,
    connection_id="conn_456",
    client_ip="192.168.1.100"
)

# Log security events
logger.log_security_event(
    event_type="authentication_failed",
    message="WebSocket authentication failed",
    session_id="session_123",
    client_ip="192.168.1.100",
    error_code="AUTH_FAILED",
    level=WebSocketLogLevel.CRITICAL
)

# Performance context logging
with logger.log_performance_context(
    event_type="message_processing",
    message="Processing WebSocket message",
    session_id="session_123"
):
    # Your code here
    process_message()
```

### Log Schema

All logs follow a consistent structured schema:

```json
{
  "timestamp": "2025-01-28T10:30:00.000Z",
  "level": "INFO",
  "category": "connection",
  "event_type": "connection_established",
  "message": "WebSocket connection established",
  "session_id": "session_123",
  "user_id": 1,
  "connection_id": "conn_456",
  "namespace": "/user",
  "client_ip": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "duration_ms": 150.5,
  "metadata": {
    "additional": "context"
  }
}
```

## Monitoring Integration

### Comprehensive Monitoring System

The monitoring system provides real-time metrics, health checks, and alerting for production deployments:

#### Features
- **Metrics Collection**: Connection, message, performance, and security metrics
- **Prometheus Integration**: Native Prometheus metrics export
- **Health Checks**: Kubernetes-compatible health and readiness checks
- **Alerting**: Webhook-based alerting with configurable thresholds
- **Performance Monitoring**: Real-time performance tracking and optimization

#### Configuration

```bash
# Metrics Collection
WEBSOCKET_METRICS_ENABLED=true
WEBSOCKET_METRICS_ENDPOINT=/websocket/metrics
WEBSOCKET_METRICS_FORMAT=prometheus

# Performance Monitoring
WEBSOCKET_PERFORMANCE_MONITORING=true
WEBSOCKET_CONNECTION_METRICS=true
WEBSOCKET_MESSAGE_METRICS=true
WEBSOCKET_ERROR_METRICS=true

# Health Checks
WEBSOCKET_HEALTH_CHECKS=true
WEBSOCKET_HEALTH_ENDPOINT=/websocket/health
WEBSOCKET_DETAILED_HEALTH=true

# Alerting
WEBSOCKET_ALERTING_ENABLED=true
WEBSOCKET_ALERT_WEBHOOK_URL=https://alerts.example.com/webhook
WEBSOCKET_ALERT_THRESHOLDS={"connection_errors":10,"message_errors":50,"response_time_ms":1000,"memory_usage_mb":500}
```

#### Metrics Available

**Connection Metrics:**
- Total connections
- Active connections
- Failed connections
- Connection rate
- Connections by namespace/user

**Message Metrics:**
- Total messages
- Messages per second
- Average message size
- Processing time
- Messages by event type

**Performance Metrics:**
- CPU usage
- Memory usage
- Response time
- Throughput
- Error rate

**Security Metrics:**
- Blocked connections
- Failed authentications
- Rate limited requests
- CSRF failures
- Security events by type

#### Usage Examples

```python
from websocket_production_monitoring import WebSocketProductionMonitor

# Initialize monitor
monitor = WebSocketProductionMonitor(monitoring_config, logger, app, socketio)

# Record connection events
monitor.record_connection_event(
    event_type="connect",
    session_id="session_123",
    user_id=1,
    namespace="/user",
    success=True
)

# Record message events
monitor.record_message_event(
    event_name="chat_message",
    namespace="/user",
    message_size=256,
    processing_time_ms=50.0,
    success=True
)

# Monitor operations
with monitor.monitor_operation(
    operation_name="process_upload",
    session_id="session_123",
    user_id=1
):
    # Your operation here
    process_file_upload()

# Get health status
health = monitor.perform_health_check()
print(f"Health Status: {health.status.value}")
```

### Prometheus Integration

The system provides native Prometheus metrics:

```
# HELP websocket_connections_total Total WebSocket connections
# TYPE websocket_connections_total counter
websocket_connections_total 1234

# HELP websocket_connections_active Active WebSocket connections
# TYPE websocket_connections_active gauge
websocket_connections_active 567

# HELP websocket_message_processing_seconds Message processing time
# TYPE websocket_message_processing_seconds histogram
websocket_message_processing_seconds_bucket{le="0.1"} 100
websocket_message_processing_seconds_bucket{le="0.5"} 200
websocket_message_processing_seconds_bucket{le="1.0"} 250
```

## Backup and Recovery

### State Persistence and Recovery

The backup and recovery system ensures WebSocket state can be preserved and restored:

#### Features
- **Connection State Backup**: Preserve active connection information
- **Session Data Backup**: Backup user session and subscription data
- **Automatic Backups**: Scheduled backup creation with configurable intervals
- **Backup Verification**: Integrity checking with checksums
- **Recovery Procedures**: Automated and manual recovery options
- **Compression Support**: Optional backup compression to save storage

#### Configuration

```bash
# State Backup
WEBSOCKET_STATE_BACKUP=true
WEBSOCKET_BACKUP_INTERVAL=300
WEBSOCKET_BACKUP_LOCATION=/var/backups/vedfolnir/websocket
WEBSOCKET_MAX_BACKUP_FILES=24

# Recovery Configuration
WEBSOCKET_AUTO_RECOVERY=true
WEBSOCKET_RECOVERY_TIMEOUT=30
WEBSOCKET_RECOVERY_RETRIES=3

# State Persistence
WEBSOCKET_PERSIST_CONNECTIONS=true
WEBSOCKET_PERSIST_SUBSCRIPTIONS=true
WEBSOCKET_PERSIST_SESSION_DATA=true

# Backup Compression
WEBSOCKET_COMPRESS_BACKUPS=true
WEBSOCKET_COMPRESSION_LEVEL=6
```

#### Usage Examples

```python
from websocket_backup_recovery import WebSocketBackupManager, BackupType

# Initialize backup manager
backup_manager = WebSocketBackupManager(backup_config, logger, socketio, redis_client)

# Track connections for backup
backup_manager.track_connection(
    session_id="session_123",
    user_id=1,
    connection_id="conn_456",
    namespace="/user",
    client_info={"ip": "192.168.1.100"}
)

# Create manual backup
metadata = backup_manager.create_backup(BackupType.FULL)
print(f"Backup created: {metadata.backup_id}")

# List available backups
backups = backup_manager.list_backups()
for backup in backups:
    print(f"Backup: {backup.backup_id} - {backup.timestamp}")

# Restore from backup
recovery_result = backup_manager.restore_from_backup(backup_id="full_20250128_103000")
print(f"Recovery status: {recovery_result.status.value}")
print(f"Recovered connections: {recovery_result.recovered_connections}")

# Verify backup integrity
is_valid = backup_manager.verify_backup("full_20250128_103000")
print(f"Backup valid: {is_valid}")
```

### Backup Format

Backups are stored in JSON format with the following structure:

```json
{
  "metadata": {
    "backup_type": "full",
    "timestamp": "2025-01-28T10:30:00.000Z",
    "version": "1.0"
  },
  "connections": {
    "conn_456": {
      "session_id": "session_123",
      "user_id": 1,
      "connection_id": "conn_456",
      "namespace": "/user",
      "rooms": ["room_1", "room_2"],
      "connected_at": "2025-01-28T10:25:00.000Z",
      "last_activity": "2025-01-28T10:29:30.000Z",
      "client_info": {
        "ip": "192.168.1.100",
        "user_agent": "Mozilla/5.0..."
      },
      "subscription_data": {
        "notifications": true,
        "updates": ["type_1", "type_2"]
      }
    }
  },
  "sessions": {
    "session_123": {
      "data": {
        "user_id": 1,
        "platform_id": 1,
        "preferences": {}
      },
      "timestamp": "2025-01-28T10:25:00.000Z"
    }
  },
  "redis_sessions": {
    "vedfolnir:session:session_123": {
      "user_id": 1,
      "username": "user1",
      "platform_connection_id": 1
    }
  }
}
```

## Load Balancer Compatibility

### Session Affinity and Multi-Instance Support

The load balancer support ensures WebSocket connections work correctly in multi-instance deployments:

#### Features
- **Session Affinity**: Sticky sessions to ensure consistent routing
- **Health Checks**: Load balancer-compatible health endpoints
- **Proxy Header Support**: Proper handling of proxy headers
- **Server Registration**: Automatic server discovery and registration
- **Connection Tracking**: Multi-instance connection coordination

#### Configuration

```bash
# Session Affinity
WEBSOCKET_SESSION_AFFINITY=true
WEBSOCKET_SESSION_AFFINITY_COOKIE=WEBSOCKET_SERVER
WEBSOCKET_SESSION_AFFINITY_TIMEOUT=3600

# Health Check Configuration
WEBSOCKET_HEALTH_CHECK_PATH=/websocket/health
WEBSOCKET_HEALTH_CHECK_INTERVAL=30
WEBSOCKET_HEALTH_CHECK_TIMEOUT=5
WEBSOCKET_HEALTH_CHECK_RETRIES=3

# Proxy Headers
WEBSOCKET_TRUST_PROXY_HEADERS=true
WEBSOCKET_PROXY_HEADERS=X-Forwarded-For,X-Forwarded-Proto,X-Forwarded-Host,X-Real-IP

# Connection Limits
WEBSOCKET_MAX_CONNECTIONS_PER_SERVER=1000
WEBSOCKET_CONNECTION_TIMEOUT=30

# Sticky Sessions
WEBSOCKET_STICKY_SESSIONS=true
WEBSOCKET_STICKY_SESSION_KEY=websocket_server_id
```

#### Health Check Endpoints

The system provides multiple health check endpoints for different use cases:

**Basic Health Check:**
```
GET /websocket/health
```

Response:
```json
{
  "status": "healthy",
  "server_id": "hostname_1640995200_abc123",
  "timestamp": "2025-01-28T10:30:00.000Z",
  "connections": 150,
  "uptime": 3600
}
```

**Kubernetes Readiness Check:**
```
GET /websocket/health/ready
```

**Kubernetes Liveness Check:**
```
GET /websocket/health/live
```

#### Usage Examples

```python
from websocket_load_balancer_support import WebSocketLoadBalancerSupport

# Initialize load balancer support
lb_support = WebSocketLoadBalancerSupport(lb_config, logger, app, socketio, redis_client)

# Register WebSocket connection
lb_support.register_websocket_connection(
    session_id="session_123",
    connection_id="conn_456",
    user_id=1,
    namespace="/user"
)

# Update server metrics
lb_support.update_server_metrics(
    cpu_usage=45.0,
    memory_usage=512.0,
    response_time_ms=150.0,
    error_rate=0.01
)

# Get health status
health = lb_support.get_health_status()
print(f"Server Status: {health['status']}")

# Set maintenance mode
lb_support.set_maintenance_mode(True)

# Get session affinity info
affinity_info = lb_support.get_session_affinity_info()
print(f"Active affinities: {affinity_info['total_affinities']}")
```

### Load Balancer Configuration Examples

**NGINX Configuration:**
```nginx
upstream websocket_backend {
    ip_hash;  # Enable session affinity
    server app1.example.com:5000;
    server app2.example.com:5000;
    server app3.example.com:5000;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    location /socket.io/ {
        proxy_pass http://websocket_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Health check
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        proxy_connect_timeout 5s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    location /websocket/health {
        proxy_pass http://websocket_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**HAProxy Configuration:**
```
backend websocket_backend
    balance source  # Session affinity based on source IP
    option httpchk GET /websocket/health
    http-check expect status 200
    
    server app1 app1.example.com:5000 check inter 30s
    server app2 app2.example.com:5000 check inter 30s
    server app3 app3.example.com:5000 check inter 30s

frontend websocket_frontend
    bind *:443 ssl crt /etc/ssl/certs/yourdomain.pem
    default_backend websocket_backend
    
    # WebSocket upgrade
    acl is_websocket hdr(Upgrade) -i websocket
    acl is_websocket_path path_beg /socket.io/
    
    use_backend websocket_backend if is_websocket OR is_websocket_path
```

## Configuration Management

### Environment-Based Configuration

All production features are configured through environment variables for easy deployment management:

#### Configuration Categories

1. **Production Mode Settings**
2. **SSL/TLS Configuration**
3. **Load Balancer Configuration**
4. **Logging Configuration**
5. **Monitoring Configuration**
6. **Backup and Recovery Configuration**
7. **Performance Optimization**
8. **Security Settings**

#### Configuration Validation

The system includes comprehensive configuration validation:

```python
from websocket_production_config import ProductionWebSocketConfigManager

config_manager = ProductionWebSocketConfigManager(config)

# Validate configuration
if config_manager.is_production_mode():
    production_config = config_manager.get_production_config()
    
    # Check SSL configuration
    if config_manager.is_ssl_enabled():
        print("SSL/TLS properly configured")
    else:
        print("Warning: SSL/TLS not configured for production")
    
    # Validate components
    if production_config.monitoring_config.metrics_enabled:
        print("Monitoring enabled")
    
    if production_config.backup_config.state_backup_enabled:
        print("Backup system enabled")
```

#### Configuration Templates

See `websocket_production_config.env.example` for complete configuration templates for different environments:

- Development Environment
- Staging Environment
- Production Environment
- Kubernetes/Docker Environment

## Deployment Guide

### Production Deployment Steps

1. **Environment Preparation**
   ```bash
   # Create configuration directory
   mkdir -p /etc/vedfolnir
   
   # Create log directory
   mkdir -p /var/log/vedfolnir
   
   # Create backup directory
   mkdir -p /var/backups/vedfolnir/websocket
   
   # Set proper permissions
   chown -R vedfolnir:vedfolnir /var/log/vedfolnir /var/backups/vedfolnir
   ```

2. **SSL Certificate Setup**
   ```bash
   # Copy SSL certificates
   cp certificate.pem /etc/ssl/vedfolnir/
   cp private_key.pem /etc/ssl/vedfolnir/
   cp ca_bundle.pem /etc/ssl/vedfolnir/
   
   # Set secure permissions
   chmod 600 /etc/ssl/vedfolnir/private_key.pem
   chmod 644 /etc/ssl/vedfolnir/certificate.pem
   ```

3. **Configuration Setup**
   ```bash
   # Copy production configuration
   cp websocket_production_config.env.example /etc/vedfolnir/.env
   
   # Edit configuration for your environment
   nano /etc/vedfolnir/.env
   ```

4. **Application Deployment**
   ```python
   # In your application startup
   from websocket_production_factory import ProductionWebSocketFactory
   
   # Initialize production WebSocket factory
   factory = ProductionWebSocketFactory(config, db_manager, session_manager, redis_client)
   
   # Create production SocketIO instance
   socketio = factory.create_production_socketio_instance(app)
   
   # Start application
   if __name__ == '__main__':
       socketio.run(app, host='0.0.0.0', port=5000, debug=False)
   ```

5. **Monitoring Setup**
   ```bash
   # Configure Prometheus scraping
   # Add to prometheus.yml:
   scrape_configs:
     - job_name: 'vedfolnir-websocket'
       static_configs:
         - targets: ['app1.example.com:5000', 'app2.example.com:5000']
       metrics_path: '/websocket/metrics'
       scrape_interval: 30s
   ```

6. **Load Balancer Configuration**
   - Configure NGINX/HAProxy as shown in examples above
   - Enable health checks
   - Configure session affinity
   - Set up SSL termination

7. **Backup Verification**
   ```bash
   # Verify backup system
   curl http://localhost:5000/websocket/health
   
   # Check backup directory
   ls -la /var/backups/vedfolnir/websocket/
   ```

### Docker Deployment

```dockerfile
FROM python:3.9-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Create directories
RUN mkdir -p /var/log/vedfolnir /var/backups/vedfolnir/websocket

# Set environment variables
ENV WEBSOCKET_PRODUCTION_MODE=true
ENV WEBSOCKET_LOG_FILE=/var/log/vedfolnir/websocket.log
ENV WEBSOCKET_BACKUP_LOCATION=/var/backups/vedfolnir/websocket

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:5000/websocket/health || exit 1

# Expose port
EXPOSE 5000

# Start application
CMD ["python", "web_app.py"]
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vedfolnir-websocket
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vedfolnir-websocket
  template:
    metadata:
      labels:
        app: vedfolnir-websocket
    spec:
      containers:
      - name: vedfolnir
        image: vedfolnir:latest
        ports:
        - containerPort: 5000
        env:
        - name: WEBSOCKET_PRODUCTION_MODE
          value: "true"
        - name: WEBSOCKET_HEALTH_CHECK_PATH
          value: "/healthz"
        - name: WEBSOCKET_METRICS_ENDPOINT
          value: "/metrics"
        livenessProbe:
          httpGet:
            path: /websocket/health/live
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /websocket/health/ready
            port: 5000
          initialDelaySeconds: 5
          periodSeconds: 10
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        volumeMounts:
        - name: ssl-certs
          mountPath: /etc/ssl/vedfolnir
          readOnly: true
        - name: logs
          mountPath: /var/log/vedfolnir
        - name: backups
          mountPath: /var/backups/vedfolnir
      volumes:
      - name: ssl-certs
        secret:
          secretName: vedfolnir-ssl-certs
      - name: logs
        emptyDir: {}
      - name: backups
        persistentVolumeClaim:
          claimName: vedfolnir-backups

---
apiVersion: v1
kind: Service
metadata:
  name: vedfolnir-websocket-service
spec:
  selector:
    app: vedfolnir-websocket
  ports:
  - port: 80
    targetPort: 5000
  type: LoadBalancer
  sessionAffinity: ClientIP
```

## Troubleshooting

### Common Issues and Solutions

#### SSL/TLS Issues

**Problem**: SSL certificate errors
```
SSL: CERTIFICATE_VERIFY_FAILED
```

**Solution**:
1. Verify certificate files exist and have correct permissions
2. Check certificate validity dates
3. Ensure certificate chain is complete
4. Verify hostname matches certificate

```bash
# Check certificate
openssl x509 -in certificate.pem -text -noout

# Verify certificate chain
openssl verify -CAfile ca_bundle.pem certificate.pem

# Test SSL connection
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com
```

#### Connection Issues

**Problem**: WebSocket connections failing
```
WebSocket connection failed: Connection refused
```

**Solution**:
1. Check if WebSocket server is running
2. Verify firewall settings
3. Check load balancer configuration
4. Review proxy headers

```bash
# Test WebSocket connection
curl -i -N -H "Connection: Upgrade" -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Key: test" -H "Sec-WebSocket-Version: 13" \
  http://yourdomain.com/socket.io/

# Check health endpoint
curl http://yourdomain.com/websocket/health
```

#### Load Balancer Issues

**Problem**: Session affinity not working
```
WebSocket connection switching between servers
```

**Solution**:
1. Enable sticky sessions in load balancer
2. Check session affinity cookie configuration
3. Verify proxy headers are trusted
4. Review load balancer health checks

```bash
# Check session affinity
curl -c cookies.txt -b cookies.txt http://yourdomain.com/websocket/health

# Verify server ID consistency
for i in {1..5}; do
  curl -s -b cookies.txt http://yourdomain.com/websocket/health | jq .server_id
done
```

#### Monitoring Issues

**Problem**: Metrics not appearing in Prometheus
```
No metrics available at /websocket/metrics
```

**Solution**:
1. Verify metrics are enabled in configuration
2. Check metrics endpoint accessibility
3. Review Prometheus scraping configuration
4. Check application logs for errors

```bash
# Test metrics endpoint
curl http://yourdomain.com/websocket/metrics

# Check Prometheus configuration
promtool check config prometheus.yml

# Verify scraping targets
curl http://prometheus:9090/api/v1/targets
```

#### Backup Issues

**Problem**: Backup creation failing
```
Failed to create WebSocket backup: Permission denied
```

**Solution**:
1. Check backup directory permissions
2. Verify disk space availability
3. Review backup configuration
4. Check application logs

```bash
# Check backup directory
ls -la /var/backups/vedfolnir/websocket/

# Check disk space
df -h /var/backups/

# Test backup creation
python -c "
from websocket_backup_recovery import WebSocketBackupManager
from websocket_production_config import BackupRecoveryConfig
from websocket_production_logging import ProductionWebSocketLogger

config = BackupRecoveryConfig()
logger = ProductionWebSocketLogger(config)
manager = WebSocketBackupManager(config, logger)
result = manager.create_backup()
print(f'Backup result: {result}')
"
```

### Debugging Tools

#### Log Analysis

```bash
# Monitor WebSocket logs
tail -f /var/log/vedfolnir/websocket.log | jq .

# Filter security events
grep "security" /var/log/vedfolnir/websocket.log | jq .

# Analyze error patterns
grep "ERROR" /var/log/vedfolnir/websocket.log | jq .event_type | sort | uniq -c
```

#### Connection Debugging

```python
# Enable debug logging
import os
os.environ['WEBSOCKET_LOG_LEVEL'] = 'DEBUG'
os.environ['WEBSOCKET_DEBUG_MODE'] = 'true'

# Test connection with detailed logging
from websocket_production_factory import ProductionWebSocketFactory

factory = ProductionWebSocketFactory(config, db_manager, session_manager)
status = factory.get_production_status()
print(json.dumps(status, indent=2))
```

#### Performance Analysis

```bash
# Monitor system resources
htop

# Check memory usage
ps aux | grep python | awk '{print $6}' | awk '{sum+=$1} END {print sum/1024 " MB"}'

# Monitor network connections
netstat -an | grep :5000

# Check WebSocket connections
ss -tuln | grep :5000
```

### Support and Maintenance

#### Regular Maintenance Tasks

1. **Certificate Renewal**
   - Monitor certificate expiration dates
   - Implement automated renewal processes
   - Test certificate updates in staging

2. **Log Rotation**
   - Monitor log file sizes
   - Verify log rotation is working
   - Archive old logs as needed

3. **Backup Verification**
   - Regularly test backup restoration
   - Verify backup integrity
   - Monitor backup storage usage

4. **Performance Monitoring**
   - Review performance metrics
   - Identify optimization opportunities
   - Monitor resource usage trends

5. **Security Updates**
   - Keep SSL/TLS configurations current
   - Monitor security logs for anomalies
   - Update security thresholds as needed

#### Monitoring Alerts

Set up alerts for critical conditions:

```yaml
# Prometheus alerting rules
groups:
- name: websocket
  rules:
  - alert: WebSocketHighErrorRate
    expr: rate(websocket_errors_total[5m]) > 0.1
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: High WebSocket error rate detected

  - alert: WebSocketConnectionsHigh
    expr: websocket_connections_active > 800
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: High number of WebSocket connections

  - alert: WebSocketServerDown
    expr: up{job="vedfolnir-websocket"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: WebSocket server is down
```

This comprehensive production readiness implementation ensures that the WebSocket CORS Standardization system meets enterprise requirements for security, reliability, performance, and maintainability in production environments.
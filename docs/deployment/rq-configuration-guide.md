# RQ System Configuration Guide

## Overview

This guide provides detailed configuration options for the Redis Queue (RQ) system across different environments. The RQ system supports flexible configuration through environment variables, configuration files, and runtime settings.

## Configuration Hierarchy

Configuration is loaded in the following order (later sources override earlier ones):
1. Default values in code
2. Environment-specific configuration files
3. Environment variables
4. Runtime configuration updates

## Core Configuration Options

### RQ System Configuration

| Variable | Default | Description | Required |
|----------|---------|-------------|----------|
| `RQ_ENABLED` | `false` | Enable/disable RQ system | Yes |
| `RQ_REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL | Yes |
| `RQ_DEFAULT_TIMEOUT` | `3600` | Default job timeout (seconds) | No |
| `RQ_RESULT_TTL` | `86400` | Job result TTL (seconds) | No |
| `RQ_JOB_TIMEOUT` | `1800` | Individual job timeout (seconds) | No |

### Worker Configuration

| Variable | Default | Description | Environment |
|----------|---------|-------------|-------------|
| `RQ_WORKER_MODE` | `integrated` | Worker mode: integrated/external/hybrid | All |
| `RQ_WORKER_COUNT` | `2` | Number of integrated workers | All |
| `RQ_WORKER_TIMEOUT` | `30` | Worker shutdown timeout (seconds) | All |
| `RQ_MAX_RETRIES` | `3` | Maximum job retry attempts | All |
| `RQ_RETRY_DELAY` | `60` | Base retry delay (seconds) | All |

### Queue Configuration

| Variable | Default | Description | Notes |
|----------|---------|-------------|-------|
| `RQ_QUEUE_URGENT_WORKERS` | `1` | Workers for urgent queue | High priority |
| `RQ_QUEUE_HIGH_WORKERS` | `2` | Workers for high queue | Admin tasks |
| `RQ_QUEUE_NORMAL_WORKERS` | `2` | Workers for normal queue | Regular users |
| `RQ_QUEUE_LOW_WORKERS` | `1` | Workers for low queue | Background tasks |

### Monitoring Configuration

| Variable | Default | Description | Production |
|----------|---------|-------------|------------|
| `RQ_MONITORING_ENABLED` | `true` | Enable monitoring | Recommended |
| `RQ_HEALTH_CHECK_INTERVAL` | `30` | Health check interval (seconds) | Yes |
| `RQ_CLEANUP_INTERVAL` | `3600` | Cleanup interval (seconds) | Yes |
| `RQ_PERFORMANCE_TRACKING` | `false` | Enable performance metrics | Optional |

### Fallback Configuration

| Variable | Default | Description | Critical |
|----------|---------|-------------|---------|
| `RQ_FALLBACK_ENABLED` | `true` | Enable database fallback | Yes |
| `RQ_FALLBACK_TIMEOUT` | `30` | Redis failure detection (seconds) | Yes |
| `RQ_REDIS_HEALTH_CHECK_INTERVAL` | `30` | Redis health check (seconds) | Yes |
| `RQ_AUTO_RECOVERY_ENABLED` | `true` | Auto-recover from Redis failures | Yes |

## Environment-Specific Configurations

### Development Environment

**File**: `config/rq/development.env`
```bash
# Basic RQ Configuration
RQ_ENABLED=true
RQ_REDIS_URL=redis://localhost:6379/0
RQ_DEFAULT_TIMEOUT=1800
RQ_RESULT_TTL=3600

# Worker Configuration - Minimal for development
RQ_WORKER_MODE=integrated
RQ_WORKER_COUNT=1
RQ_WORKER_TIMEOUT=15
RQ_MAX_RETRIES=2

# Queue Configuration - Single worker for all queues
RQ_QUEUE_URGENT_WORKERS=1
RQ_QUEUE_HIGH_WORKERS=1
RQ_QUEUE_NORMAL_WORKERS=1
RQ_QUEUE_LOW_WORKERS=1

# Monitoring Configuration - Full logging for debugging
RQ_MONITORING_ENABLED=true
RQ_DEBUG_LOGGING=true
RQ_HEALTH_CHECK_INTERVAL=10
RQ_CLEANUP_INTERVAL=300

# Fallback Configuration - Quick detection for testing
RQ_FALLBACK_ENABLED=true
RQ_FALLBACK_TIMEOUT=10
RQ_REDIS_HEALTH_CHECK_INTERVAL=10

# Development-specific settings
RQ_PERFORMANCE_TRACKING=true
RQ_DETAILED_LOGGING=true
RQ_TEST_MODE=true
```

**Usage**:
```bash
# Load development configuration
export $(cat config/rq/development.env | xargs)
python web_app.py & sleep 10
```

### Staging Environment

**File**: `config/rq/staging.env`
```bash
# Basic RQ Configuration
RQ_ENABLED=true
RQ_REDIS_URL=redis://localhost:6379/0
RQ_DEFAULT_TIMEOUT=3600
RQ_RESULT_TTL=86400

# Worker Configuration - Moderate for staging
RQ_WORKER_MODE=integrated
RQ_WORKER_COUNT=2
RQ_WORKER_TIMEOUT=30
RQ_MAX_RETRIES=3

# Queue Configuration - Balanced distribution
RQ_QUEUE_URGENT_WORKERS=1
RQ_QUEUE_HIGH_WORKERS=2
RQ_QUEUE_NORMAL_WORKERS=2
RQ_QUEUE_LOW_WORKERS=1

# Monitoring Configuration - Production-like monitoring
RQ_MONITORING_ENABLED=true
RQ_HEALTH_CHECK_INTERVAL=30
RQ_CLEANUP_INTERVAL=1800
RQ_PERFORMANCE_TRACKING=true

# Fallback Configuration - Production-like resilience
RQ_FALLBACK_ENABLED=true
RQ_FALLBACK_TIMEOUT=30
RQ_REDIS_HEALTH_CHECK_INTERVAL=30
RQ_AUTO_RECOVERY_ENABLED=true

# Staging-specific settings
RQ_ALERTING_ENABLED=false
RQ_DETAILED_METRICS=true
RQ_LOAD_TESTING_MODE=true
```

**Usage**:
```bash
# Load staging configuration
export $(cat config/rq/staging.env | xargs)
gunicorn -w 2 -b 0.0.0.0:8000 web_app:app
```

### Production Environment

**File**: `config/rq/production.env`
```bash
# Basic RQ Configuration
RQ_ENABLED=true
RQ_REDIS_URL=redis://:${REDIS_PASSWORD}@redis-server:6379/0
RQ_DEFAULT_TIMEOUT=3600
RQ_RESULT_TTL=86400
RQ_JOB_TIMEOUT=1800

# Worker Configuration - Optimized for production
RQ_WORKER_MODE=integrated
RQ_WORKER_COUNT=4
RQ_WORKER_TIMEOUT=30
RQ_MAX_RETRIES=3
RQ_RETRY_DELAY=60

# Queue Configuration - Production scaling
RQ_QUEUE_URGENT_WORKERS=2
RQ_QUEUE_HIGH_WORKERS=3
RQ_QUEUE_NORMAL_WORKERS=4
RQ_QUEUE_LOW_WORKERS=2

# Monitoring Configuration - Full production monitoring
RQ_MONITORING_ENABLED=true
RQ_HEALTH_CHECK_INTERVAL=30
RQ_CLEANUP_INTERVAL=3600
RQ_PERFORMANCE_TRACKING=true
RQ_ALERTING_ENABLED=true

# Fallback Configuration - Maximum resilience
RQ_FALLBACK_ENABLED=true
RQ_FALLBACK_TIMEOUT=30
RQ_REDIS_HEALTH_CHECK_INTERVAL=30
RQ_AUTO_RECOVERY_ENABLED=true

# Production-specific settings
RQ_ENCRYPT_TASK_DATA=true
RQ_SANITIZE_ERRORS=true
RQ_AUDIT_LOGGING=true
RQ_CAPACITY_MONITORING=true

# Security settings
RQ_SECURE_CONNECTIONS=true
RQ_VALIDATE_TASK_DATA=true
RQ_RATE_LIMITING=true
```

**Usage**:
```bash
# Load production configuration
export $(cat config/rq/production.env | xargs)
gunicorn -w 4 -b 0.0.0.0:8000 web_app:app
```

## Advanced Configuration Options

### Redis Connection Configuration

```bash
# Basic Redis URL
RQ_REDIS_URL=redis://localhost:6379/0

# Redis with authentication
RQ_REDIS_URL=redis://:password@localhost:6379/0

# Redis with SSL
RQ_REDIS_URL=rediss://localhost:6380/0

# Redis Sentinel configuration
RQ_REDIS_SENTINEL_HOSTS=sentinel1:26379,sentinel2:26379,sentinel3:26379
RQ_REDIS_SENTINEL_SERVICE=mymaster

# Redis Cluster configuration
RQ_REDIS_CLUSTER_NODES=node1:7000,node2:7000,node3:7000
```

### Connection Pool Configuration

```bash
# Redis connection pool settings
RQ_REDIS_MAX_CONNECTIONS=50
RQ_REDIS_CONNECTION_TIMEOUT=5
RQ_REDIS_SOCKET_TIMEOUT=5
RQ_REDIS_RETRY_ON_TIMEOUT=true
RQ_REDIS_HEALTH_CHECK_INTERVAL=30
```

### Task Serialization Configuration

```bash
# Serialization method: pickle, msgpack, json
RQ_SERIALIZATION_METHOD=msgpack

# Compression settings
RQ_COMPRESS_TASK_DATA=true
RQ_COMPRESSION_LEVEL=6

# Encryption settings
RQ_ENCRYPT_TASK_DATA=true
RQ_ENCRYPTION_KEY=your-fernet-key-here
```

### Performance Tuning Configuration

```bash
# Worker performance settings
RQ_WORKER_BURST_MODE=true
RQ_WORKER_BATCH_SIZE=10
RQ_WORKER_PREFETCH_COUNT=5

# Queue performance settings
RQ_QUEUE_BATCH_ENQUEUE=true
RQ_QUEUE_PRIORITY_WEIGHTS=urgent:4,high:3,normal:2,low:1

# Memory management
RQ_MAX_MEMORY_PER_WORKER=512MB
RQ_MEMORY_CLEANUP_THRESHOLD=80
RQ_GARBAGE_COLLECTION_INTERVAL=300
```

### Logging Configuration

```bash
# RQ-specific logging
RQ_LOG_LEVEL=INFO
RQ_LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s
RQ_LOG_FILE=logs/rq.log
RQ_LOG_MAX_SIZE=100MB
RQ_LOG_BACKUP_COUNT=5

# Debug logging
RQ_DEBUG_LOGGING=false
RQ_TRACE_TASK_EXECUTION=false
RQ_LOG_REDIS_COMMANDS=false
```

## Dynamic Configuration Management

### Runtime Configuration Updates

```python
# Update configuration via API
import requests

# Update worker count
requests.post('http://localhost:8000/admin/rq/config', json={
    'worker_count': 6
})

# Update queue priorities
requests.post('http://localhost:8000/admin/rq/config', json={
    'queue_priorities': {
        'urgent': 4,
        'high': 3,
        'normal': 2,
        'low': 1
    }
})
```

### Configuration Validation

```bash
# Validate configuration before deployment
python scripts/config/validate_rq_config.py

# Test configuration with dry run
python scripts/config/test_rq_config.py --dry-run

# Generate configuration report
python scripts/config/generate_rq_config_report.py
```

## Configuration Templates

### Docker Configuration

**File**: `docker/rq/docker-compose.yml`
```yaml
version: '3.8'
services:
  web:
    build: .
    environment:
      - RQ_ENABLED=true
      - RQ_REDIS_URL=redis://redis:6379/0
      - RQ_WORKER_MODE=integrated
      - RQ_WORKER_COUNT=2
    depends_on:
      - redis
      - mysql

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 2gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data

  mysql:
    image: mysql:8.0
    environment:
      - MYSQL_DATABASE=vedfolnir
      - MYSQL_USER=vedfolnir_user
      - MYSQL_PASSWORD=${MYSQL_PASSWORD}
    volumes:
      - mysql_data:/var/lib/mysql

volumes:
  redis_data:
  mysql_data:
```

### Kubernetes Configuration

**File**: `k8s/rq-configmap.yaml`
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: rq-config
data:
  RQ_ENABLED: "true"
  RQ_WORKER_MODE: "integrated"
  RQ_WORKER_COUNT: "4"
  RQ_MONITORING_ENABLED: "true"
  RQ_FALLBACK_ENABLED: "true"
---
apiVersion: v1
kind: Secret
metadata:
  name: rq-secrets
type: Opaque
stringData:
  RQ_REDIS_URL: "redis://:password@redis-service:6379/0"
  RQ_ENCRYPTION_KEY: "your-fernet-key-here"
```

## Configuration Best Practices

### Security Best Practices

1. **Never store passwords in plain text**
   ```bash
   # Use environment variables
   RQ_REDIS_URL=redis://:${REDIS_PASSWORD}@localhost:6379/0
   
   # Or use secrets management
   RQ_REDIS_PASSWORD_FILE=/run/secrets/redis_password
   ```

2. **Enable encryption for sensitive data**
   ```bash
   RQ_ENCRYPT_TASK_DATA=true
   RQ_ENCRYPTION_KEY=${FERNET_KEY}
   ```

3. **Sanitize error messages**
   ```bash
   RQ_SANITIZE_ERRORS=true
   RQ_HIDE_SENSITIVE_DATA=true
   ```

### Performance Best Practices

1. **Tune worker count based on workload**
   ```bash
   # CPU-bound tasks: worker_count = CPU_cores
   # I/O-bound tasks: worker_count = CPU_cores * 2-4
   RQ_WORKER_COUNT=4
   ```

2. **Configure appropriate timeouts**
   ```bash
   # Short tasks
   RQ_DEFAULT_TIMEOUT=300
   
   # Long-running tasks
   RQ_DEFAULT_TIMEOUT=3600
   ```

3. **Enable monitoring in production**
   ```bash
   RQ_MONITORING_ENABLED=true
   RQ_PERFORMANCE_TRACKING=true
   RQ_ALERTING_ENABLED=true
   ```

### Reliability Best Practices

1. **Always enable fallback mechanisms**
   ```bash
   RQ_FALLBACK_ENABLED=true
   RQ_AUTO_RECOVERY_ENABLED=true
   ```

2. **Configure appropriate retry policies**
   ```bash
   RQ_MAX_RETRIES=3
   RQ_RETRY_DELAY=60
   ```

3. **Enable health checks**
   ```bash
   RQ_HEALTH_CHECK_INTERVAL=30
   RQ_REDIS_HEALTH_CHECK_INTERVAL=30
   ```

## Troubleshooting Configuration Issues

### Common Configuration Problems

1. **Redis connection failures**
   ```bash
   # Check Redis connectivity
   redis-cli -u $RQ_REDIS_URL ping
   
   # Verify Redis authentication
   redis-cli -u $RQ_REDIS_URL info server
   ```

2. **Worker startup failures**
   ```bash
   # Check worker configuration
   python -c "from config import Config; print(Config().RQ_WORKER_COUNT)"
   
   # Verify worker mode
   python -c "from config import Config; print(Config().RQ_WORKER_MODE)"
   ```

3. **Queue processing issues**
   ```bash
   # Check queue configuration
   redis-cli llen rq:queue:normal
   
   # Verify worker assignment
   redis-cli keys "rq:workers:*"
   ```

### Configuration Validation Tools

```bash
# Validate all RQ configuration
python scripts/config/validate_rq_config.py --verbose

# Test Redis connectivity
python scripts/config/test_redis_connection.py

# Verify worker configuration
python scripts/config/test_worker_config.py

# Check queue setup
python scripts/config/verify_queue_setup.py
```

## Migration Configuration

### From Database Polling to RQ

```bash
# Phase 1: Enable RQ alongside database polling
RQ_ENABLED=true
RQ_HYBRID_MODE=true
DATABASE_POLLING_ENABLED=true

# Phase 2: Primary RQ with database fallback
RQ_ENABLED=true
RQ_FALLBACK_ENABLED=true
DATABASE_POLLING_ENABLED=false

# Phase 3: RQ only
RQ_ENABLED=true
RQ_FALLBACK_ENABLED=true
DATABASE_POLLING_ENABLED=false
```

### Configuration Migration Script

```bash
# Migrate configuration from old format
python scripts/migration/migrate_config_to_rq.py

# Backup current configuration
cp .env .env.backup.$(date +%Y%m%d_%H%M%S)

# Apply new RQ configuration
python scripts/migration/apply_rq_config.py
```
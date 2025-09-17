# RQ Worker Deployment Guide

## Overview

This guide covers the different deployment strategies for RQ workers in Vedfolnir. The system supports three deployment modes:

1. **Integrated Workers** - Workers run as daemon threads within Gunicorn processes
2. **External Workers** - Workers run as separate `rq worker` processes
3. **Hybrid Deployment** - Combination of both integrated and external workers

## Deployment Modes

### 1. Integrated Workers (Recommended for Development)

Integrated workers run as background threads within the Flask/Gunicorn application process.

**Advantages:**
- Simple deployment and management
- Shared memory and resources with web application
- Automatic startup/shutdown with web application
- Good for development and small-scale deployments

**Disadvantages:**
- Limited scalability
- Resource contention with web requests
- Single point of failure

**Configuration:**
```bash
export WORKER_MODE=integrated
export RQ_URGENT_HIGH_WORKERS=2
export RQ_NORMAL_WORKERS=2
export RQ_LOW_WORKERS=1
```

**Usage:**
```bash
# Automatic startup with Flask app
python web_app.py

# Manual startup for testing
python scripts/rq/start_integrated_workers.py
```

### 2. External Workers (Recommended for Production)

External workers run as separate processes using the `rq worker` command.

**Advantages:**
- Better resource isolation
- Independent scaling
- Can run on different machines
- Better fault tolerance

**Disadvantages:**
- More complex deployment
- Requires process management
- Additional monitoring needed

**Configuration:**
```bash
export WORKER_MODE=external
export RQ_EXTERNAL_WORKER_COUNT=5
export RQ_EXTERNAL_WORKER_TIMEOUT=7200
export REDIS_URL=redis://localhost:6379/0
```

**Usage:**
```bash
# Start external workers
./scripts/rq/start_external_workers.sh start

# Check status
./scripts/rq/start_external_workers.sh status

# Stop workers
./scripts/rq/start_external_workers.sh stop

# Restart workers
./scripts/rq/start_external_workers.sh restart
```

### 3. Hybrid Deployment (Recommended for Production)

Combines integrated workers for high-priority tasks with external workers for normal/low priority tasks.

**Advantages:**
- Optimal resource utilization
- Fast processing for urgent tasks
- Scalable processing for bulk tasks
- Best of both worlds

**Disadvantages:**
- Most complex deployment
- Requires careful configuration
- More monitoring complexity

**Configuration:**
```bash
export WORKER_MODE=hybrid
export RQ_URGENT_HIGH_WORKERS=2      # Integrated workers
export RQ_EXTERNAL_WORKER_COUNT=4    # External workers
export REDIS_URL=redis://localhost:6379/0
```

**Usage:**
```bash
# Start hybrid deployment
python scripts/rq/start_hybrid_deployment.py
```

## Environment Variables

### Redis Configuration
```bash
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your_password
REDIS_DB=0
```

### Worker Configuration
```bash
# Worker mode: integrated, external, hybrid
WORKER_MODE=integrated

# Integrated worker counts
RQ_URGENT_HIGH_WORKERS=2
RQ_NORMAL_WORKERS=2
RQ_LOW_WORKERS=1

# External worker configuration
RQ_EXTERNAL_WORKER_COUNT=5
RQ_EXTERNAL_WORKER_TIMEOUT=7200
RQ_WORKER_MEMORY_LIMIT=512

# Health monitoring
RQ_HEALTH_CHECK_INTERVAL=30
RQ_FAILURE_THRESHOLD=3
```

### Queue Configuration
```bash
RQ_QUEUE_PREFIX=vedfolnir:rq:
RQ_DEFAULT_TIMEOUT=300
RQ_RESULT_TTL=86400
RQ_JOB_TTL=7200
```

## Production Deployment Examples

### Docker Compose Example

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - WORKER_MODE=hybrid
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - redis
      - mysql
    command: gunicorn -w 4 -b 0.0.0.0:8000 web_app:app

  rq-workers:
    build: .
    environment:
      - WORKER_MODE=external
      - REDIS_URL=redis://redis:6379/0
      - RQ_EXTERNAL_WORKER_COUNT=6
    depends_on:
      - redis
      - mysql
    command: ./scripts/rq/start_external_workers.sh start

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  mysql:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: rootpassword
      MYSQL_DATABASE: vedfolnir
```

### Systemd Service Example

```ini
# /etc/systemd/system/vedfolnir-rq-workers.service
[Unit]
Description=Vedfolnir RQ Workers
After=network.target redis.service mysql.service

[Service]
Type=forking
User=vedfolnir
Group=vedfolnir
WorkingDirectory=/opt/vedfolnir
Environment=WORKER_MODE=external
Environment=REDIS_URL=redis://localhost:6379/0
Environment=RQ_EXTERNAL_WORKER_COUNT=6
ExecStart=/opt/vedfolnir/scripts/rq/start_external_workers.sh start
ExecStop=/opt/vedfolnir/scripts/rq/start_external_workers.sh stop
ExecReload=/opt/vedfolnir/scripts/rq/start_external_workers.sh restart
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Kubernetes Deployment Example

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vedfolnir-rq-workers
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vedfolnir-rq-workers
  template:
    metadata:
      labels:
        app: vedfolnir-rq-workers
    spec:
      containers:
      - name: rq-worker
        image: vedfolnir:latest
        command: ["rq", "worker"]
        args: ["--url", "$(REDIS_URL)", "urgent", "high", "normal", "low"]
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379/0"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: vedfolnir-secrets
              key: database-url
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

## Monitoring and Health Checks

### Worker Status Monitoring

```bash
# Check integrated worker status
curl http://localhost:8000/admin/api/rq/status

# Check external worker status
./scripts/rq/start_external_workers.sh status

# Check hybrid deployment status
# (Status endpoint in hybrid deployment script)
```

### Health Check Endpoints

The admin dashboard provides RQ monitoring endpoints:

- `/admin/rq/dashboard` - RQ queue dashboard
- `/admin/api/rq/status` - Worker status API
- `/admin/api/rq/queues` - Queue statistics API
- `/admin/api/rq/health` - Health check API

### Log Monitoring

```bash
# Application logs
tail -f logs/webapp.log | grep RQ

# External worker logs (if using PID directory)
tail -f /tmp/rq_workers/*.log

# System logs
journalctl -u vedfolnir-rq-workers -f
```

## Troubleshooting

### Common Issues

1. **Redis Connection Failed**
   ```bash
   # Check Redis connectivity
   redis-cli -u $REDIS_URL ping
   
   # Check Redis memory usage
   redis-cli -u $REDIS_URL info memory
   ```

2. **Workers Not Starting**
   ```bash
   # Check RQ installation
   rq --version
   
   # Check environment variables
   env | grep RQ
   
   # Check logs for errors
   tail -f logs/webapp.log
   ```

3. **Tasks Stuck in Queue**
   ```bash
   # Check worker status
   rq info --url $REDIS_URL
   
   # Check for failed jobs
   rq info --url $REDIS_URL --only-failures
   
   # Restart stuck tasks (admin function)
   curl -X POST http://localhost:8000/admin/api/rq/restart-stuck-tasks
   ```

4. **High Memory Usage**
   ```bash
   # Monitor worker memory
   ps aux | grep "rq worker"
   
   # Check Redis memory
   redis-cli -u $REDIS_URL info memory
   
   # Adjust worker memory limits
   export RQ_WORKER_MEMORY_LIMIT=256
   ```

### Performance Tuning

1. **Queue Priority Optimization**
   - Use urgent queue sparingly for critical tasks
   - Balance workers across priority levels
   - Monitor queue backlogs

2. **Worker Scaling**
   - Start with 1-2 workers per CPU core
   - Monitor CPU and memory usage
   - Scale based on queue depth and processing time

3. **Redis Optimization**
   - Configure appropriate memory limits
   - Use Redis persistence for durability
   - Monitor Redis performance metrics

## Migration from Database Polling

When migrating from the existing database polling system:

1. **Gradual Migration**
   ```bash
   # Start with hybrid mode
   export WORKER_MODE=hybrid
   
   # Migrate existing tasks
   python scripts/rq/migrate_database_tasks.py
   ```

2. **Fallback Configuration**
   ```bash
   # Enable database fallback
   export DB_SESSION_FALLBACK=true
   
   # Monitor both systems during transition
   ```

3. **Validation**
   ```bash
   # Verify task processing
   python scripts/rq/validate_rq_processing.py
   
   # Compare performance metrics
   ```

## Security Considerations

1. **Redis Security**
   - Use Redis AUTH if available
   - Ensure Redis is not exposed to public networks
   - Configure appropriate Redis persistence

2. **Worker Security**
   - Run workers with minimal privileges
   - Enforce memory and CPU limits
   - Sanitize error messages to prevent information leakage

3. **Network Security**
   - Use TLS for Redis connections in production
   - Implement proper firewall rules
   - Monitor network traffic

## Best Practices

1. **Development**
   - Use integrated workers for development
   - Enable verbose logging
   - Test with small task volumes

2. **Staging**
   - Use hybrid deployment
   - Test with production-like workloads
   - Validate monitoring and alerting

3. **Production**
   - Use external or hybrid workers
   - Implement comprehensive monitoring
   - Set up automated scaling
   - Configure proper backup and recovery

4. **Monitoring**
   - Monitor queue depths and processing times
   - Set up alerts for worker failures
   - Track memory and CPU usage
   - Monitor Redis performance

This deployment guide provides comprehensive coverage of RQ worker deployment strategies for different environments and use cases.
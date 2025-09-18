# RQ System Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting procedures for common Redis Queue (RQ) system issues in Vedfolnir. It covers diagnosis, resolution steps, and prevention strategies for various RQ-related problems.

## Quick Diagnostic Commands

### System Status Check
```bash
# Check RQ system status
curl -s http://localhost:8000/admin/rq/health | jq '.'

# Verify Redis connectivity
redis-cli ping

# Check queue lengths
redis-cli llen rq:queue:urgent
redis-cli llen rq:queue:high
redis-cli llen rq:queue:normal
redis-cli llen rq:queue:low

# Check active workers
redis-cli keys "rq:workers:*"

# Check failed jobs
redis-cli llen rq:queue:failed
```

### Application Logs
```bash
# RQ-specific logs
tail -f logs/webapp.log | grep -E "(RQ|Queue|Worker)"

# Error logs
tail -f logs/webapp.log | grep -E "(ERROR|CRITICAL|EXCEPTION)"

# Performance logs
tail -f logs/webapp.log | grep -E "(Performance|Timing|Slow)"
```

## Common Issues and Solutions

### 1. RQ Workers Not Starting

#### Symptoms
- No workers visible in admin dashboard
- Tasks remain in queues without processing
- Error: "No workers found"

#### Diagnosis
```bash
# Check worker processes
ps aux | grep -E "(rq|worker)"

# Check RQ configuration
python -c "
from config import Config
c = Config()
print(f'RQ Enabled: {c.RQ_ENABLED}')
print(f'Worker Mode: {c.RQ_WORKER_MODE}')
print(f'Worker Count: {c.RQ_WORKER_COUNT}')
"

# Check Redis connection
python -c "
import redis
r = redis.from_url('redis://localhost:6379/0')
print(r.ping())
"
```

#### Solutions

**Solution 1: Configuration Issue**
```bash
# Verify environment variables
echo $RQ_ENABLED
echo $RQ_WORKER_MODE
echo $RQ_WORKER_COUNT

# Update configuration if needed
export RQ_ENABLED=true
export RQ_WORKER_MODE=integrated
export RQ_WORKER_COUNT=2

# Restart application
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

**Solution 2: Redis Connection Issue**
```bash
# Check Redis service
systemctl status redis
systemctl start redis

# Test Redis connectivity
redis-cli ping

# Check Redis configuration
redis-cli config get bind
redis-cli config get port
```

**Solution 3: Worker Initialization Failure**
```bash
# Check for initialization errors
tail -100 logs/webapp.log | grep -A5 -B5 "worker"

# Restart with debug logging
RQ_DEBUG_LOGGING=true python web_app.py & sleep 10

# Check worker startup in logs
tail -f logs/webapp.log | grep "Worker.*started"
```

### 2. Tasks Stuck in Queues

#### Symptoms
- Tasks enqueued but not processing
- Queue lengths increasing
- No task completion notifications

#### Diagnosis
```bash
# Check queue status
redis-cli llen rq:queue:normal
redis-cli lrange rq:queue:normal 0 5

# Check worker status
curl http://localhost:8000/admin/rq/workers

# Check for failed jobs
redis-cli llen rq:queue:failed
redis-cli lrange rq:queue:failed 0 5
```

#### Solutions

**Solution 1: Worker Overload**
```bash
# Scale up workers
curl -X POST http://localhost:8000/admin/rq/scale-workers \
  -H "Content-Type: application/json" \
  -d '{"queue": "normal", "count": 4}'

# Or restart with more workers
export RQ_WORKER_COUNT=4
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

**Solution 2: Task Timeout Issues**
```bash
# Check for timeout errors
tail -100 logs/webapp.log | grep -i timeout

# Increase task timeout
export RQ_DEFAULT_TIMEOUT=7200
export RQ_JOB_TIMEOUT=3600

# Restart application
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

**Solution 3: Clear Stuck Tasks**
```bash
# Move failed jobs back to queue
python scripts/maintenance/requeue_failed_jobs.py

# Clear specific queue if needed
redis-cli del rq:queue:normal

# Restart task processing
curl -X POST http://localhost:8000/admin/rq/restart-workers
```

### 3. Redis Connection Failures

#### Symptoms
- "Connection refused" errors
- Fallback to database mode
- Intermittent task processing

#### Diagnosis
```bash
# Check Redis service status
systemctl status redis

# Test Redis connectivity
redis-cli ping
redis-cli info server

# Check Redis logs
tail -50 /var/log/redis/redis-server.log

# Check network connectivity
netstat -tlnp | grep 6379
```

#### Solutions

**Solution 1: Redis Service Issues**
```bash
# Restart Redis service
systemctl restart redis

# Check Redis configuration
redis-cli config get "*"

# Verify Redis is listening
netstat -tlnp | grep 6379
```

**Solution 2: Connection Pool Issues**
```bash
# Check connection pool settings
python -c "
from config import Config
c = Config()
print(f'Redis URL: {c.RQ_REDIS_URL}')
print(f'Max Connections: {getattr(c, \"RQ_REDIS_MAX_CONNECTIONS\", \"default\")}')
"

# Increase connection pool size
export RQ_REDIS_MAX_CONNECTIONS=50
export RQ_REDIS_CONNECTION_TIMEOUT=10

# Restart application
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

**Solution 3: Redis Memory Issues**
```bash
# Check Redis memory usage
redis-cli info memory

# Check for memory-related errors
redis-cli config get maxmemory
redis-cli config get maxmemory-policy

# Increase Redis memory limit
redis-cli config set maxmemory 4gb
redis-cli config set maxmemory-policy allkeys-lru
```

### 4. Task Processing Failures

#### Symptoms
- Tasks marked as failed
- Error messages in logs
- Incomplete task results

#### Diagnosis
```bash
# Check failed jobs
redis-cli llen rq:queue:failed
redis-cli lrange rq:queue:failed 0 10

# Check error logs
tail -100 logs/webapp.log | grep -E "(ERROR|EXCEPTION|Failed)"

# Check specific task details
python scripts/debug/inspect_failed_task.py <task_id>
```

#### Solutions

**Solution 1: Task Data Issues**
```bash
# Validate task data
python scripts/debug/validate_task_data.py

# Check serialization issues
python -c "
import pickle
import msgpack
# Test serialization methods
"

# Clear corrupted tasks
python scripts/maintenance/cleanup_corrupted_tasks.py
```

**Solution 2: Database Connection Issues**
```bash
# Check database connectivity
python -c "
from config import Config
from app.core.database.core.database_manager import DatabaseManager
db = DatabaseManager(Config())
with db.get_session() as session:
    print('Database connection: OK')
"

# Check for connection leaks
mysql -e "SHOW PROCESSLIST;" | grep vedfolnir

# Restart with fresh connections
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

**Solution 3: Resource Exhaustion**
```bash
# Check system resources
htop
df -h
free -h

# Check worker memory usage
ps aux | grep rq | awk '{print $6}' | sort -n

# Reduce worker count if needed
export RQ_WORKER_COUNT=2
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

### 5. Performance Issues

#### Symptoms
- Slow task processing
- High queue backlogs
- Increased response times

#### Diagnosis
```bash
# Check queue statistics
curl http://localhost:8000/admin/rq/stats

# Monitor task processing times
tail -f logs/webapp.log | grep "Task.*completed.*seconds"

# Check Redis performance
redis-cli --latency -i 1

# Check system performance
iostat 1 5
vmstat 1 5
```

#### Solutions

**Solution 1: Scale Workers**
```bash
# Increase worker count
export RQ_WORKER_COUNT=6
pkill -f "python web_app.py"
python web_app.py & sleep 10

# Add external workers for heavy loads
rq worker urgent high --url redis://localhost:6379/0 &
rq worker normal low --url redis://localhost:6379/0 &
```

**Solution 2: Optimize Redis**
```bash
# Optimize Redis configuration
redis-cli config set maxmemory-policy allkeys-lru
redis-cli config set save "900 1 300 10 60 10000"
redis-cli config set tcp-keepalive 60

# Enable Redis persistence optimization
redis-cli config set rdbcompression yes
redis-cli config set rdbchecksum yes
```

**Solution 3: Database Optimization**
```bash
# Optimize database connections
export DB_POOL_SIZE=30
export DB_MAX_OVERFLOW=50

# Check for slow queries
mysql -e "SHOW PROCESSLIST;" | grep "Query"

# Restart with optimized settings
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

### 6. Fallback Mode Issues

#### Symptoms
- System stuck in database fallback mode
- "Redis unavailable" messages
- Tasks processing via database instead of RQ

#### Diagnosis
```bash
# Check fallback status
curl http://localhost:8000/admin/rq/health | jq '.fallback_active'

# Check Redis health monitoring
tail -50 logs/webapp.log | grep -i "redis.*health"

# Test Redis recovery
redis-cli ping
```

#### Solutions

**Solution 1: Force Redis Recovery**
```bash
# Restart Redis service
systemctl restart redis

# Force RQ system recovery
curl -X POST http://localhost:8000/admin/rq/force-recovery

# Check recovery status
curl http://localhost:8000/admin/rq/health
```

**Solution 2: Reset Health Monitoring**
```bash
# Clear Redis health check failures
redis-cli del rq:health:failures
redis-cli del rq:health:last_check

# Restart health monitoring
curl -X POST http://localhost:8000/admin/rq/restart-health-monitor

# Verify recovery
tail -f logs/webapp.log | grep "Redis.*recovered"
```

**Solution 3: Manual Recovery**
```bash
# Disable fallback temporarily
export RQ_FALLBACK_ENABLED=false

# Restart application
pkill -f "python web_app.py"
python web_app.py & sleep 10

# Re-enable fallback after recovery
export RQ_FALLBACK_ENABLED=true
pkill -f "python web_app.py"
python web_app.py & sleep 10
```

## Advanced Troubleshooting

### Memory Leak Detection

```bash
# Monitor memory usage over time
while true; do
  ps aux | grep "python web_app.py" | awk '{print $6}'
  sleep 60
done

# Check for Redis memory leaks
redis-cli info memory | grep used_memory_human

# Monitor worker memory usage
ps aux | grep rq | awk '{print $2, $6}' | sort -k2 -n
```

### Connection Pool Debugging

```bash
# Check Redis connection pool status
python -c "
import redis
pool = redis.ConnectionPool.from_url('redis://localhost:6379/0')
print(f'Created connections: {pool.created_connections}')
print(f'Available connections: {len(pool._available_connections)}')
print(f'In use connections: {len(pool._in_use_connections)}')
"

# Monitor connection pool over time
watch -n 5 'redis-cli info clients'
```

### Task Serialization Issues

```bash
# Test task serialization
python scripts/debug/test_task_serialization.py

# Check for serialization errors
tail -100 logs/webapp.log | grep -i "serializ"

# Validate task data integrity
python scripts/debug/validate_task_integrity.py
```

### Queue Corruption Recovery

```bash
# Backup current queues
python scripts/backup/backup_rq_queues.py

# Clear corrupted queues
redis-cli del rq:queue:urgent
redis-cli del rq:queue:high
redis-cli del rq:queue:normal
redis-cli del rq:queue:low

# Restore from database
python scripts/recovery/restore_tasks_from_database.py

# Verify queue integrity
python scripts/debug/verify_queue_integrity.py
```

## Monitoring and Alerting

### Health Check Scripts

```bash
# Create health check script
cat > scripts/monitoring/rq_health_check.sh << 'EOF'
#!/bin/bash

# Check RQ system health
HEALTH=$(curl -s http://localhost:8000/admin/rq/health)
STATUS=$(echo $HEALTH | jq -r '.status')

if [ "$STATUS" != "healthy" ]; then
    echo "ALERT: RQ system unhealthy - $HEALTH"
    exit 1
fi

# Check queue backlogs
NORMAL_QUEUE=$(redis-cli llen rq:queue:normal)
if [ "$NORMAL_QUEUE" -gt 100 ]; then
    echo "ALERT: Normal queue backlog - $NORMAL_QUEUE tasks"
    exit 1
fi

echo "RQ system healthy"
exit 0
EOF

chmod +x scripts/monitoring/rq_health_check.sh
```

### Performance Monitoring

```bash
# Create performance monitoring script
cat > scripts/monitoring/rq_performance_monitor.sh << 'EOF'
#!/bin/bash

# Monitor RQ performance metrics
STATS=$(curl -s http://localhost:8000/admin/rq/stats)
echo "$(date): $STATS" >> logs/rq_performance.log

# Check processing times
SLOW_TASKS=$(tail -1000 logs/webapp.log | grep "Task.*completed" | awk '{print $NF}' | awk -F'[^0-9]*' '{print $2}' | awk '$1 > 300' | wc -l)

if [ "$SLOW_TASKS" -gt 10 ]; then
    echo "ALERT: $SLOW_TASKS slow tasks detected"
fi
EOF

chmod +x scripts/monitoring/rq_performance_monitor.sh
```

### Automated Recovery Scripts

```bash
# Create auto-recovery script
cat > scripts/recovery/auto_recover_rq.sh << 'EOF'
#!/bin/bash

# Check if RQ workers are running
WORKERS=$(ps aux | grep -c "rq.*worker")

if [ "$WORKERS" -eq 0 ]; then
    echo "No RQ workers found, restarting application"
    pkill -f "python web_app.py"
    sleep 5
    python web_app.py & sleep 10
fi

# Check Redis connectivity
if ! redis-cli ping > /dev/null 2>&1; then
    echo "Redis not responding, restarting service"
    systemctl restart redis
    sleep 10
fi

# Clear stuck jobs if queue is too large
QUEUE_SIZE=$(redis-cli llen rq:queue:normal)
if [ "$QUEUE_SIZE" -gt 1000 ]; then
    echo "Queue too large ($QUEUE_SIZE), clearing old jobs"
    python scripts/maintenance/cleanup_old_jobs.py
fi
EOF

chmod +x scripts/recovery/auto_recover_rq.sh
```

## Prevention Strategies

### Regular Maintenance

```bash
# Daily maintenance tasks
0 2 * * * /path/to/scripts/maintenance/cleanup_rq_jobs.py
0 3 * * * /path/to/scripts/maintenance/optimize_redis.py
0 4 * * * /path/to/scripts/backup/backup_rq_state.py

# Weekly maintenance tasks
0 1 * * 0 /path/to/scripts/maintenance/analyze_rq_performance.py
0 2 * * 0 /path/to/scripts/maintenance/cleanup_old_logs.py

# Monthly maintenance tasks
0 1 1 * * /path/to/scripts/maintenance/full_rq_health_check.py
```

### Monitoring Setup

```bash
# Set up continuous monitoring
# Add to crontab:
*/5 * * * * /path/to/scripts/monitoring/rq_health_check.sh
*/10 * * * * /path/to/scripts/monitoring/rq_performance_monitor.sh
*/15 * * * * /path/to/scripts/recovery/auto_recover_rq.sh
```

### Configuration Validation

```bash
# Validate configuration before deployment
python scripts/config/validate_rq_config.py --strict

# Test configuration changes
python scripts/config/test_rq_config.py --dry-run

# Monitor configuration drift
python scripts/monitoring/check_config_drift.py
```

## Emergency Procedures

### Complete RQ System Restart

```bash
# 1. Stop all RQ workers
pkill -f "rq.*worker"
pkill -f "python web_app.py"

# 2. Clear Redis RQ data (if needed)
redis-cli flushdb

# 3. Restart Redis
systemctl restart redis

# 4. Restart application
python web_app.py & sleep 10

# 5. Verify system health
curl http://localhost:8000/admin/rq/health
```

### Rollback to Database Processing

```bash
# 1. Disable RQ system
export RQ_ENABLED=false

# 2. Enable database fallback
export DATABASE_POLLING_ENABLED=true

# 3. Restart application
pkill -f "python web_app.py"
python web_app.py & sleep 10

# 4. Start legacy workers
python caption_worker.py &
python simple_caption_worker.py &

# 5. Migrate RQ tasks back to database
python scripts/migration/migrate_rq_to_database.py
```

### Data Recovery

```bash
# Recover lost tasks from Redis backup
python scripts/recovery/recover_tasks_from_redis_backup.py

# Recover tasks from database audit trail
python scripts/recovery/recover_tasks_from_audit.py

# Rebuild task queue from database
python scripts/recovery/rebuild_queue_from_database.py
```

## Getting Help

### Log Collection for Support

```bash
# Collect comprehensive logs for support
mkdir -p /tmp/rq_debug_$(date +%Y%m%d_%H%M%S)
cd /tmp/rq_debug_$(date +%Y%m%d_%H%M%S)

# Application logs
cp /path/to/logs/webapp.log .
cp /path/to/logs/rq.log .

# System information
uname -a > system_info.txt
ps aux | grep -E "(rq|redis|python)" > processes.txt
netstat -tlnp | grep 6379 > network.txt

# Redis information
redis-cli info > redis_info.txt
redis-cli config get "*" > redis_config.txt

# RQ status
curl -s http://localhost:8000/admin/rq/health > rq_health.json
curl -s http://localhost:8000/admin/rq/stats > rq_stats.json

# Configuration
env | grep RQ > rq_env.txt

# Create archive
cd ..
tar -czf rq_debug_$(date +%Y%m%d_%H%M%S).tar.gz rq_debug_$(date +%Y%m%d_%H%M%S)/
```

### Support Contacts

- **System Administrator**: For Redis and infrastructure issues
- **Development Team**: For RQ system bugs and configuration
- **Database Administrator**: For MySQL performance and connectivity
- **DevOps Team**: For deployment and monitoring issues

### Useful Resources

- **RQ Documentation**: https://python-rq.org/
- **Redis Documentation**: https://redis.io/documentation
- **Vedfolnir RQ Design**: `docs/deployment/rq-system-design.md`
- **Configuration Guide**: `docs/deployment/rq-configuration-guide.md`
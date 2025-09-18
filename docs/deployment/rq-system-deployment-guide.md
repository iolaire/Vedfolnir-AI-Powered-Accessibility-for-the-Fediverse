# Redis Queue (RQ) System Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the Redis Queue (RQ) system in Vedfolnir. The RQ system replaces the database-polling task processing with efficient Redis-based queuing for improved performance and scalability.

## Prerequisites

### System Requirements
- **Redis Server**: Version 6.0+ (already configured for session management)
- **Python**: Version 3.8+ with RQ library
- **MySQL/MariaDB**: Existing database setup
- **Gunicorn**: For production web server deployment

### Dependencies
Ensure these packages are installed:
```bash
pip install rq redis msgpack
```

### Redis Configuration Verification
Verify Redis is properly configured and accessible:
```bash
# Test Redis connectivity
redis-cli ping
# Should return: PONG

# Check Redis memory configuration
redis-cli info memory

# Verify Redis persistence settings
redis-cli config get save
```

## Environment Configuration

### Required Environment Variables
Add these variables to your `.env` file:

```bash
# RQ Configuration
RQ_ENABLED=true
RQ_REDIS_URL=redis://localhost:6379/0
RQ_DEFAULT_TIMEOUT=3600
RQ_RESULT_TTL=86400

# Worker Configuration
RQ_WORKER_MODE=integrated  # Options: integrated, external, hybrid
RQ_WORKER_COUNT=2
RQ_WORKER_TIMEOUT=30
RQ_MAX_RETRIES=3

# Queue Configuration
RQ_QUEUE_URGENT_WORKERS=1
RQ_QUEUE_HIGH_WORKERS=2
RQ_QUEUE_NORMAL_WORKERS=2
RQ_QUEUE_LOW_WORKERS=1

# Monitoring Configuration
RQ_MONITORING_ENABLED=true
RQ_HEALTH_CHECK_INTERVAL=30
RQ_CLEANUP_INTERVAL=3600

# Fallback Configuration
RQ_FALLBACK_ENABLED=true
RQ_FALLBACK_TIMEOUT=30
RQ_REDIS_HEALTH_CHECK_INTERVAL=30
```

### Redis Memory Configuration
Configure Redis for optimal RQ performance:

```bash
# Add to redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

## Deployment Scenarios

### Scenario 1: Development Environment

**Configuration**: Single integrated worker
```bash
# Environment settings
RQ_WORKER_MODE=integrated
RQ_WORKER_COUNT=1
RQ_ENABLED=true

# Start application
python web_app.py & sleep 10
```

**Verification**:
```bash
# Check RQ workers are running
ps aux | grep rq
curl http://localhost:5000/admin/rq/stats
```

### Scenario 2: Production Environment (Recommended)

**Configuration**: Integrated workers with Gunicorn
```bash
# Environment settings
RQ_WORKER_MODE=integrated
RQ_WORKER_COUNT=4
RQ_ENABLED=true

# Start with Gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 web_app:app
```

**Verification**:
```bash
# Check Gunicorn processes
ps aux | grep gunicorn

# Verify RQ integration
curl http://localhost:8000/admin/rq/stats

# Check Redis queue status
redis-cli llen rq:queue:normal
```

### Scenario 3: High-Load Environment

**Configuration**: Hybrid mode with external workers
```bash
# Environment settings
RQ_WORKER_MODE=hybrid
RQ_WORKER_COUNT=2

# Start Gunicorn with integrated workers
gunicorn -w 4 -b 0.0.0.0:8000 web_app:app &

# Start additional external workers
rq worker urgent high --url redis://localhost:6379/0 &
rq worker normal low --url redis://localhost:6379/0 &
```

## Step-by-Step Deployment Process

### Step 1: Pre-Deployment Verification
```bash
# 1. Verify Redis connectivity
redis-cli ping

# 2. Check database connectivity
python -c "from config import Config; from app.core.database.core.database_manager import DatabaseManager; db = DatabaseManager(Config()); print('DB OK')"

# 3. Verify existing task processing is stopped
ps aux | grep caption_worker
# Kill any running workers: pkill -f caption_worker

# 4. Backup current database
mysqldump vedfolnir > backup_pre_rq_$(date +%Y%m%d_%H%M%S).sql
```

### Step 2: Configuration Update
```bash
# 1. Update environment variables
cp .env .env.backup
echo "RQ_ENABLED=true" >> .env
echo "RQ_WORKER_MODE=integrated" >> .env
echo "RQ_WORKER_COUNT=2" >> .env

# 2. Verify configuration
python -c "from config import Config; c = Config(); print(f'RQ Enabled: {c.RQ_ENABLED}')"
```

### Step 3: Application Deployment
```bash
# 1. Install RQ dependencies
pip install -r requirements.txt

# 2. Test RQ system initialization
python -c "
from app.services.task.core.task_queue_manager import RQQueueManager
from config import Config
config = Config()
print('RQ system test: OK')
"

# 3. Start application with RQ
# For development:
python web_app.py & sleep 10

# For production:
gunicorn -w 4 -b 0.0.0.0:8000 web_app:app
```

### Step 4: Migration Execution
```bash
# 1. Migrate existing queued tasks
python scripts/migration/migrate_database_tasks_to_rq.py

# 2. Verify migration
python scripts/migration/verify_rq_migration.py

# 3. Monitor initial processing
tail -f logs/webapp.log | grep RQ
```

### Step 5: Post-Deployment Verification
```bash
# 1. Test task submission
curl -X POST http://localhost:8000/api/test-rq-task

# 2. Verify queue statistics
curl http://localhost:8000/admin/rq/stats

# 3. Check worker health
redis-cli keys "rq:workers:*"

# 4. Monitor processing
redis-cli monitor | grep rq:queue
```

## Configuration Management

### Environment-Specific Configurations

#### Development (`config/rq/development.env`)
```bash
RQ_WORKER_MODE=integrated
RQ_WORKER_COUNT=1
RQ_MONITORING_ENABLED=true
RQ_DEBUG_LOGGING=true
```

#### Staging (`config/rq/staging.env`)
```bash
RQ_WORKER_MODE=integrated
RQ_WORKER_COUNT=2
RQ_MONITORING_ENABLED=true
RQ_PERFORMANCE_TRACKING=true
```

#### Production (`config/rq/production.env`)
```bash
RQ_WORKER_MODE=integrated
RQ_WORKER_COUNT=4
RQ_MONITORING_ENABLED=true
RQ_PERFORMANCE_TRACKING=true
RQ_ALERTING_ENABLED=true
```

### Dynamic Configuration Updates
```bash
# Update worker count without restart
redis-cli set rq:config:worker_count 4

# Update queue priorities
redis-cli hset rq:config:queues urgent 1 high 2 normal 3 low 4

# Reload configuration
curl -X POST http://localhost:8000/admin/rq/reload-config
```

## Monitoring and Health Checks

### Built-in Health Checks
```bash
# RQ system health
curl http://localhost:8000/admin/rq/health

# Queue statistics
curl http://localhost:8000/admin/rq/stats

# Worker status
curl http://localhost:8000/admin/rq/workers
```

### Redis Monitoring
```bash
# Queue lengths
redis-cli llen rq:queue:urgent
redis-cli llen rq:queue:high
redis-cli llen rq:queue:normal
redis-cli llen rq:queue:low

# Failed jobs
redis-cli llen rq:queue:failed

# Worker status
redis-cli keys "rq:workers:*"
```

### Log Monitoring
```bash
# RQ-specific logs
tail -f logs/webapp.log | grep "RQ\|Queue\|Worker"

# Error monitoring
tail -f logs/webapp.log | grep "ERROR\|CRITICAL"

# Performance monitoring
tail -f logs/webapp.log | grep "Performance\|Timing"
```

## Performance Optimization

### Redis Optimization
```bash
# Memory optimization
redis-cli config set maxmemory-policy allkeys-lru

# Persistence optimization for RQ
redis-cli config set save "900 1 300 10 60 10000"

# Connection optimization
redis-cli config set tcp-keepalive 60
```

### Worker Optimization
```bash
# Adjust worker count based on load
# Monitor CPU and memory usage
htop

# Adjust based on queue lengths
redis-cli llen rq:queue:normal

# Scale workers dynamically
curl -X POST http://localhost:8000/admin/rq/scale-workers -d '{"queue": "normal", "count": 4}'
```

### Database Connection Optimization
```bash
# Monitor database connections
mysql -e "SHOW PROCESSLIST;"

# Optimize connection pool
# Update in .env:
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
```

## Security Considerations

### Redis Security
```bash
# Enable Redis AUTH (recommended)
redis-cli config set requirepass "your-secure-password"

# Update connection string
RQ_REDIS_URL=redis://:your-secure-password@localhost:6379/0

# Bind Redis to localhost only
redis-cli config set bind "127.0.0.1"
```

### Network Security
```bash
# Firewall configuration (if Redis on separate server)
ufw allow from trusted-ip to any port 6379

# SSL/TLS for Redis (production)
# Configure Redis with SSL certificates
```

### Data Security
```bash
# Enable task data encryption
RQ_ENCRYPT_TASK_DATA=true
RQ_ENCRYPTION_KEY=your-fernet-key

# Secure error logging
RQ_SANITIZE_ERRORS=true
```

## Backup and Recovery

### Redis Backup
```bash
# Manual backup
redis-cli bgsave

# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
redis-cli bgsave
cp /var/lib/redis/dump.rdb /backup/redis_backup_$DATE.rdb
```

### Task Data Backup
```bash
# Export current queue state
python scripts/backup/export_rq_queues.py

# Backup task history
mysqldump vedfolnir images posts > task_backup_$(date +%Y%m%d_%H%M%S).sql
```

### Recovery Procedures
```bash
# Restore Redis from backup
systemctl stop redis
cp /backup/redis_backup_YYYYMMDD_HHMMSS.rdb /var/lib/redis/dump.rdb
systemctl start redis

# Restore task data
mysql vedfolnir < task_backup_YYYYMMDD_HHMMSS.sql
```

## Troubleshooting

See the separate troubleshooting guide: `docs/deployment/rq-troubleshooting-guide.md`

## Support and Maintenance

### Regular Maintenance Tasks
```bash
# Weekly cleanup of completed jobs
python scripts/maintenance/cleanup_rq_jobs.py

# Monthly performance review
python scripts/monitoring/generate_rq_performance_report.py

# Quarterly capacity planning review
python scripts/monitoring/analyze_rq_capacity_needs.py
```

### Monitoring Alerts
Configure alerts for:
- Queue backlog > 100 tasks
- Worker failure rate > 5%
- Redis memory usage > 80%
- Task processing time > 5 minutes

### Support Contacts
- **System Administrator**: For deployment and configuration issues
- **Development Team**: For RQ system bugs and enhancements
- **Database Administrator**: For MySQL performance and optimization
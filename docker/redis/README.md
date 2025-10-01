# Redis Container Configuration for Vedfolnir

## Overview

This directory contains the Redis container configuration for Vedfolnir's Docker Compose deployment. Redis serves as the primary session storage and RQ (Redis Queue) backend, optimized for high-performance session management and job queue processing.

## Architecture

### Container Configuration
- **Image**: `redis:7-alpine`
- **Container Name**: `vedfolnir_redis`
- **Network**: `vedfolnir_internal` (isolated internal network)
- **Restart Policy**: `unless-stopped`

### Volume Mounts
- **Data Persistence**: `redis_data:/data` - Redis database files (RDB, AOF)
- **Configuration**: `./config/redis/redis.conf:/usr/local/etc/redis/redis.conf:ro`
- **Backups**: `./storage/backups/redis:/backups`
- **Logs**: `./logs/redis:/var/log/redis`

### Resource Limits
- **CPU**: 1.0 cores (limit), 0.5 cores (reservation)
- **Memory**: 1GB (limit), 512MB (reservation)
- **Max Memory Policy**: `volatile-lru` (optimized for session storage)

## Security Configuration

### Authentication
- Password-based authentication using Docker secrets
- Password file: `./secrets/redis_password.txt`
- Protected mode enabled for security

### Access Controls
- Dangerous commands disabled (`FLUSHDB`, `FLUSHALL`, `DEBUG`, `EVAL`)
- `CONFIG` and `SHUTDOWN` commands renamed for security
- Default user disabled, application uses authenticated access
- Maximum client connections: 10,000

### Network Security
- Internal network only (no host port exposure by default)
- Container-to-container communication via service names
- Optional development port exposure: `127.0.0.1:6379:6379`

## Performance Optimization

### Memory Management
```
Max Memory: 1GB
Memory Policy: volatile-lru (prefer evicting keys with TTL)
Memory Samples: 10 (better LRU approximation)
Fragmentation Monitoring: Enabled
Active Defragmentation: Enabled
```

### Session Storage Optimization
```
Hash Max Ziplist Entries: 1024
Hash Max Ziplist Value: 256
List Max Ziplist Size: -1 (memory-optimized)
Set Max Intset Entries: 1024
```

### Persistence Configuration
```
RDB Snapshots:
- 900 seconds: 1+ key changes
- 300 seconds: 10+ key changes  
- 60 seconds: 10,000+ key changes
- 30 seconds: 100,000+ key changes

AOF (Append Only File):
- Enabled: yes
- Fsync: everysec (balance of performance/durability)
- Rewrite: 100% growth, 64MB minimum
```

## Session Management

### Session Storage Pattern
```
Key Pattern: vedfolnir:session:<session_id>
TTL: 7200 seconds (2 hours)
Data Format: JSON serialized session data
Cleanup: Automatic via TTL expiration
```

### Session Data Structure
```json
{
    "user_id": 1,
    "username": "admin",
    "role": "admin",
    "platform_connection_id": 123,
    "platform_name": "My Platform",
    "csrf_token": "abc123...",
    "created_at": "2025-01-01T12:00:00Z",
    "last_activity": "2025-01-01T12:30:00Z"
}
```

### Keyspace Notifications
- Enabled for session expiration tracking: `Ex`
- Allows application to monitor session lifecycle
- Supports real-time session cleanup

## RQ Queue Management

### Queue Configuration
```
Queue Pattern: rq:queue:<queue_name>
Job Pattern: rq:job:<job_id>
Result TTL: 86400 seconds (24 hours)
Job TTL: 7200 seconds (2 hours)
```

### Queue Optimization
- List data structure optimized for queue operations
- Memory-efficient ziplist encoding for small queues
- Background job processing via integrated RQ workers
- Job result persistence for debugging and monitoring

## Health Monitoring

### Health Check Configuration
```
Test Command: redis-cli ping + info replication
Interval: 30 seconds
Timeout: 10 seconds
Retries: 5
Start Period: 10 seconds
```

### Performance Monitoring
- Memory usage tracking
- Client connection monitoring
- Slow query logging (>10ms)
- Latency monitoring (>100μs threshold)
- Keyspace hit/miss ratio tracking

### Monitoring Scripts
- `redis-health-check.sh` - Container health validation
- `redis-performance-monitor.sh` - Real-time performance monitoring
- `redis-management.sh` - Backup, restore, and maintenance operations
- `validate-redis-setup.sh` - Configuration validation

## Backup and Recovery

### Automated Backups
```
RDB Snapshots: Automatic based on change thresholds
AOF Persistence: Continuous append-only logging
Manual Backups: BGSAVE command for point-in-time snapshots
Backup Storage: ./storage/backups/redis/
```

### Backup Management
```bash
# Create backup
./docker/scripts/redis-management.sh backup

# Restore from backup
./docker/scripts/redis-management.sh restore <backup_file>

# Cleanup old backups
./docker/scripts/redis-management.sh cleanup 30
```

### Disaster Recovery
- Point-in-time recovery via RDB snapshots
- Continuous recovery via AOF replay
- Cross-environment data migration support
- Backup verification and integrity checking

## Maintenance Operations

### Common Commands
```bash
# Check Redis health
./docker/scripts/redis-management.sh health

# Monitor performance
./docker/scripts/redis-performance-monitor.sh monitor

# Analyze session data
./docker/scripts/redis-management.sh sessions

# Validate configuration
./docker/scripts/validate-redis-setup.sh
```

### Container Management
```bash
# View Redis logs
docker-compose logs redis

# Execute Redis CLI
docker-compose exec redis redis-cli -a <password>

# Restart Redis service
docker-compose restart redis

# Scale Redis (single instance only)
docker-compose up -d --scale redis=1
```

## Configuration Files

### Primary Configuration
- `config/redis/redis.conf` - Main Redis configuration
- `config/redis/redis.env` - Environment variables
- `secrets/redis_password.txt` - Authentication password

### Management Scripts
- `docker/redis/init-redis.sh` - Container initialization
- `docker/scripts/redis-management.sh` - Operations management
- `docker/scripts/redis-health-check.sh` - Health validation
- `docker/scripts/redis-performance-monitor.sh` - Performance monitoring
- `docker/scripts/validate-redis-setup.sh` - Setup validation

## Troubleshooting

### Common Issues

#### Connection Refused
```bash
# Check container status
docker-compose ps redis

# Check container logs
docker-compose logs redis

# Verify network connectivity
docker-compose exec vedfolnir ping redis
```

#### Authentication Failures
```bash
# Verify password file
cat ./secrets/redis_password.txt

# Test authentication
docker-compose exec redis redis-cli -a <password> ping
```

#### Memory Issues
```bash
# Check memory usage
./docker/scripts/redis-performance-monitor.sh snapshot

# Monitor memory in real-time
./docker/scripts/redis-performance-monitor.sh monitor
```

#### Performance Problems
```bash
# Check slow queries
docker-compose exec redis redis-cli -a <password> slowlog get 10

# Monitor latency
docker-compose exec redis redis-cli -a <password> latency latest

# Analyze memory fragmentation
docker-compose exec redis redis-cli -a <password> memory doctor
```

### Log Analysis
```bash
# View Redis container logs
docker-compose logs -f redis

# Check performance monitor logs
tail -f ./logs/redis/performance_monitor.log

# Analyze slow queries
grep "slow" ./logs/redis/*.log
```

## Development and Testing

### Development Configuration
```yaml
# Uncomment in docker-compose.yml for development
ports:
  - "127.0.0.1:6379:6379"
```

### Testing Commands
```bash
# Test session functionality
./docker/scripts/validate-redis-setup.sh

# Load testing (external tool required)
redis-benchmark -h 127.0.0.1 -p 6379 -a <password> -n 10000

# Memory analysis
docker-compose exec redis redis-cli -a <password> --bigkeys
```

## Security Best Practices

### Production Deployment
1. Use strong, randomly generated passwords
2. Keep Redis on internal network only
3. Regularly rotate authentication credentials
4. Monitor for suspicious access patterns
5. Enable audit logging for security events

### Access Control
1. Disable dangerous commands in production
2. Use ACL (Access Control Lists) for fine-grained permissions
3. Implement connection limits and timeouts
4. Regular security audits and updates

### Data Protection
1. Enable encryption at rest (if supported by storage)
2. Use encrypted communication channels
3. Implement proper backup encryption
4. Follow data retention policies

## Performance Tuning

### Memory Optimization
- Adjust `maxmemory` based on available system memory
- Monitor memory fragmentation ratio
- Use appropriate eviction policies for workload
- Enable active defragmentation for long-running instances

### Network Optimization
- Tune TCP keepalive settings
- Adjust client timeout values
- Monitor connection pool usage
- Optimize for container networking latency

### Persistence Optimization
- Balance RDB and AOF based on durability requirements
- Tune save thresholds for workload patterns
- Monitor disk I/O for persistence operations
- Consider SSD storage for better performance

## Compliance and Audit

### GDPR Compliance
- Session data anonymization procedures
- Right to be forgotten implementation
- Data export capabilities for user requests
- Audit trail for data access and modifications

### Audit Logging
- All administrative operations logged
- Session lifecycle events tracked
- Performance metrics retained for analysis
- Security events monitored and alerted

This Redis configuration provides a robust, secure, and high-performance foundation for Vedfolnir's session management and job queue processing needs in a containerized environment.
# MySQL Optimization and Tuning Guide

This guide provides comprehensive MySQL optimization strategies specifically tailored for Vedfolnir's workload patterns and performance requirements.

## 📋 Table of Contents

1. [Performance Monitoring](#performance-monitoring)
2. [Connection Pool Optimization](#connection-pool-optimization)
3. [Query Optimization](#query-optimization)
4. [Index Strategy](#index-strategy)
5. [InnoDB Optimization](#innodb-optimization)
6. [Memory Configuration](#memory-configuration)
7. [Monitoring and Alerting](#monitoring-and-alerting)
8. [Production Tuning](#production-tuning)

## Performance Monitoring

### Built-in Performance Testing

Vedfolnir includes comprehensive MySQL performance testing tools:

```bash
# Run MySQL performance tests
python tests/integration/test_mysql_performance_integration.py

# Run comprehensive performance suite
python -c "
from tests.mysql_test_base import MySQLIntegrationTestBase
from tests.mysql_performance_testing import MySQLPerformanceTester

# Create performance tester
# ... performance testing code
"

# Generate performance report
python scripts/mysql_migration/generate_performance_report.py
```

### Key Performance Metrics

Monitor these critical MySQL metrics for Vedfolnir:

#### Connection Metrics
- **Active Connections**: Current active database connections
- **Connection Pool Utilization**: Percentage of pool connections in use
- **Connection Wait Time**: Time to acquire connection from pool
- **Connection Errors**: Failed connection attempts

#### Query Performance
- **Average Query Time**: Mean execution time for database queries
- **Slow Query Count**: Number of queries exceeding threshold
- **Query Throughput**: Queries processed per second
- **Index Usage**: Percentage of queries using indexes

#### Resource Utilization
- **InnoDB Buffer Pool Hit Ratio**: Should be >99%
- **Memory Usage**: Total MySQL memory consumption
- **Disk I/O**: Read/write operations per second
- **CPU Usage**: MySQL process CPU utilization

### Performance Monitoring Queries

```sql
-- Connection status
SHOW STATUS LIKE 'Connections';
SHOW STATUS LIKE 'Threads_connected';
SHOW STATUS LIKE 'Max_used_connections';

-- Query performance
SHOW STATUS LIKE 'Queries';
SHOW STATUS LIKE 'Slow_queries';
SHOW STATUS LIKE 'Questions';

-- InnoDB metrics
SHOW STATUS LIKE 'Innodb_buffer_pool_read_requests';
SHOW STATUS LIKE 'Innodb_buffer_pool_reads';
SHOW STATUS LIKE 'Innodb_buffer_pool_pages%';

-- Calculate buffer pool hit ratio
SELECT 
  ROUND(
    (1 - (
      (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_STATUS WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads') /
      (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_STATUS WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests')
    )) * 100, 2
  ) AS buffer_pool_hit_ratio_percent;
```

## Connection Pool Optimization

### Vedfolnir Connection Pool Settings

Optimize connection pool settings based on your workload:

```bash
# Development Environment
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=10
DB_POOL_RECYCLE=300

# Production Environment
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=50
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# High-Load Environment
DB_POOL_SIZE=50
DB_MAX_OVERFLOW=100
DB_POOL_TIMEOUT=60
DB_POOL_RECYCLE=7200
```

### MySQL Server Connection Settings

```ini
[mysqld]
# Connection limits
max_connections = 200
max_connect_errors = 1000
max_user_connections = 180

# Connection timeouts
connect_timeout = 60
wait_timeout = 28800
interactive_timeout = 28800
net_read_timeout = 30
net_write_timeout = 60

# Connection validation
validate_password = OFF  # For development only
```

### Connection Pool Monitoring

```python
# Monitor connection pool health
from sqlalchemy import create_engine

engine = create_engine(DATABASE_URL)
pool = engine.pool

print(f"Pool size: {pool.size()}")
print(f"Checked out connections: {pool.checkedout()}")
print(f"Overflow connections: {pool.overflow()}")
print(f"Invalid connections: {pool.invalidated()}")
```

## Query Optimization

### Vedfolnir-Specific Query Patterns

#### 1. Platform-Aware Queries

```sql
-- Optimize platform filtering
CREATE INDEX idx_posts_platform_connection ON posts(platform_connection_id);
CREATE INDEX idx_images_platform_connection ON images(platform_connection_id);

-- Example optimized query
SELECT p.*, i.image_url 
FROM posts p 
JOIN images i ON p.id = i.post_id 
WHERE p.platform_connection_id = ? 
  AND i.status = 'PENDING'
ORDER BY p.created_at DESC 
LIMIT 50;
```

#### 2. User Session Queries

```sql
-- Optimize session lookups
CREATE INDEX idx_user_sessions_user_platform ON user_sessions(user_id, platform_connection_id);
CREATE INDEX idx_user_sessions_active ON user_sessions(is_active, last_activity);

-- Example optimized session query
SELECT * FROM user_sessions 
WHERE user_id = ? 
  AND platform_connection_id = ? 
  AND is_active = 1 
  AND last_activity > DATE_SUB(NOW(), INTERVAL 2 HOUR);
```

#### 3. Caption Processing Queries

```sql
-- Optimize processing status queries
CREATE INDEX idx_images_status_created ON images(status, created_at);
CREATE INDEX idx_images_platform_status ON images(platform_connection_id, status);

-- Example optimized processing query
SELECT * FROM images 
WHERE platform_connection_id = ? 
  AND status IN ('PENDING', 'PROCESSING') 
ORDER BY created_at ASC 
LIMIT 100;
```

### Query Performance Analysis

```sql
-- Enable query profiling
SET profiling = 1;

-- Run your query
SELECT * FROM posts WHERE platform_connection_id = 1;

-- Show query profile
SHOW PROFILES;
SHOW PROFILE FOR QUERY 1;

-- Disable profiling
SET profiling = 0;
```

## Index Strategy

### Primary Indexes (Already Created)

```sql
-- Verify primary indexes exist
SHOW INDEX FROM users;
SHOW INDEX FROM platform_connections;
SHOW INDEX FROM posts;
SHOW INDEX FROM images;
```

### Recommended Additional Indexes

```sql
-- Performance-critical indexes for Vedfolnir
CREATE INDEX idx_users_username_active ON users(username, is_active);
CREATE INDEX idx_users_email_verified ON users(email, email_verified);

CREATE INDEX idx_platform_connections_user_active ON platform_connections(user_id, is_active);
CREATE INDEX idx_platform_connections_type_active ON platform_connections(platform_type, is_active);

CREATE INDEX idx_posts_user_created ON posts(user_id, created_at);
CREATE INDEX idx_posts_platform_created ON posts(platform_connection_id, created_at);

CREATE INDEX idx_images_post_status ON images(post_id, status);
CREATE INDEX idx_images_status_created ON images(status, created_at);
CREATE INDEX idx_images_platform_status ON images(platform_connection_id, status);

-- Composite indexes for common query patterns
CREATE INDEX idx_posts_platform_user_created ON posts(platform_connection_id, user_id, created_at);
CREATE INDEX idx_images_platform_status_created ON images(platform_connection_id, status, created_at);
```

### Index Maintenance

```sql
-- Check index usage statistics
SELECT 
  TABLE_SCHEMA,
  TABLE_NAME,
  INDEX_NAME,
  CARDINALITY,
  NULLABLE
FROM information_schema.STATISTICS 
WHERE TABLE_SCHEMA = 'vedfolnir'
ORDER BY CARDINALITY DESC;

-- Find unused indexes
SELECT 
  s.TABLE_SCHEMA,
  s.TABLE_NAME,
  s.INDEX_NAME
FROM information_schema.STATISTICS s
LEFT JOIN information_schema.INDEX_STATISTICS i 
  ON s.TABLE_SCHEMA = i.TABLE_SCHEMA 
  AND s.TABLE_NAME = i.TABLE_NAME 
  AND s.INDEX_NAME = i.INDEX_NAME
WHERE s.TABLE_SCHEMA = 'vedfolnir' 
  AND i.INDEX_NAME IS NULL
  AND s.INDEX_NAME != 'PRIMARY';

-- Rebuild indexes periodically
OPTIMIZE TABLE users, platform_connections, posts, images;
```

## InnoDB Optimization

### Buffer Pool Configuration

```ini
[mysqld]
# Buffer pool size (75% of available RAM)
innodb_buffer_pool_size = 2G

# Buffer pool instances (1 per GB, max 64)
innodb_buffer_pool_instances = 2

# Buffer pool chunk size
innodb_buffer_pool_chunk_size = 128M

# Preload buffer pool on startup
innodb_buffer_pool_load_at_startup = 1
innodb_buffer_pool_dump_at_shutdown = 1
```

### Log Configuration

```ini
[mysqld]
# Redo log configuration
innodb_log_file_size = 256M
innodb_log_files_in_group = 2
innodb_log_buffer_size = 16M

# Flush configuration
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT

# Doublewrite buffer
innodb_doublewrite = 1
```

### I/O Configuration

```ini
[mysqld]
# I/O capacity (adjust based on storage type)
innodb_io_capacity = 200        # HDD
# innodb_io_capacity = 2000     # SSD
# innodb_io_capacity = 6000     # NVMe SSD

innodb_io_capacity_max = 400    # 2x io_capacity

# Read-ahead
innodb_read_ahead_threshold = 56
innodb_random_read_ahead = OFF
```

## Memory Configuration

### MySQL Memory Allocation

```ini
[mysqld]
# Global buffers
innodb_buffer_pool_size = 2G    # 75% of RAM
key_buffer_size = 256M          # For MyISAM (if used)
query_cache_size = 0            # Disabled in MySQL 8.0+

# Per-connection buffers
sort_buffer_size = 2M
read_buffer_size = 128K
read_rnd_buffer_size = 256K
join_buffer_size = 128K

# Temporary tables
tmp_table_size = 64M
max_heap_table_size = 64M

# Thread cache
thread_cache_size = 50
```

### Memory Usage Monitoring

```sql
-- Check memory usage
SELECT 
  ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) AS 'DB Size in MB'
FROM information_schema.tables 
WHERE table_schema = 'vedfolnir';

-- Check buffer pool usage
SELECT 
  VARIABLE_NAME,
  VARIABLE_VALUE
FROM information_schema.GLOBAL_STATUS
WHERE VARIABLE_NAME IN (
  'Innodb_buffer_pool_pages_total',
  'Innodb_buffer_pool_pages_free',
  'Innodb_buffer_pool_pages_data'
);
```

## Monitoring and Alerting

### Performance Monitoring Setup

```bash
# Install monitoring tools
pip install mysql-connector-python prometheus-client

# Set up performance monitoring
python scripts/monitoring/setup_mysql_monitoring.py

# Configure alerts
python scripts/monitoring/configure_mysql_alerts.py
```

### Key Metrics to Monitor

#### Critical Alerts (Immediate Action Required)
- **Connection Pool Exhaustion**: >90% pool utilization
- **Slow Query Spike**: >10% of queries taking >2 seconds
- **Buffer Pool Hit Ratio**: <95%
- **Disk Space**: <10% free space
- **Connection Errors**: >5% error rate

#### Warning Alerts (Investigation Needed)
- **High Connection Count**: >80% of max_connections
- **Long-Running Queries**: Queries running >30 seconds
- **Lock Waits**: >100ms average lock wait time
- **Replication Lag**: >5 seconds (if using replication)

### Monitoring Queries

```sql
-- Real-time performance dashboard
SELECT 
  'Connections' as metric,
  VARIABLE_VALUE as current_value,
  (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_VARIABLES WHERE VARIABLE_NAME = 'max_connections') as max_value
FROM information_schema.GLOBAL_STATUS 
WHERE VARIABLE_NAME = 'Threads_connected'

UNION ALL

SELECT 
  'Buffer Pool Hit Ratio' as metric,
  ROUND((1 - (
    (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_STATUS WHERE VARIABLE_NAME = 'Innodb_buffer_pool_reads') /
    (SELECT VARIABLE_VALUE FROM information_schema.GLOBAL_STATUS WHERE VARIABLE_NAME = 'Innodb_buffer_pool_read_requests')
  )) * 100, 2) as current_value,
  '99.00' as max_value

UNION ALL

SELECT 
  'Slow Queries' as metric,
  VARIABLE_VALUE as current_value,
  'Monitor' as max_value
FROM information_schema.GLOBAL_STATUS 
WHERE VARIABLE_NAME = 'Slow_queries';
```

## Production Tuning

### High-Performance Configuration

```ini
[mysqld]
# High-performance settings for production
innodb_buffer_pool_size = 8G
innodb_buffer_pool_instances = 8
innodb_log_file_size = 512M
innodb_log_buffer_size = 64M
innodb_flush_log_at_trx_commit = 2
innodb_flush_method = O_DIRECT
innodb_io_capacity = 2000
innodb_io_capacity_max = 4000

# Connection optimization
max_connections = 500
thread_cache_size = 100
table_open_cache = 4000
table_definition_cache = 2000

# Query optimization
query_cache_type = 0  # Disabled in MySQL 8.0+
tmp_table_size = 256M
max_heap_table_size = 256M

# Binary logging
log-bin = mysql-bin
binlog_format = ROW
sync_binlog = 1
expire_logs_days = 7
```

### Load Testing Configuration

```bash
# Environment variables for load testing
export DB_POOL_SIZE=50
export DB_MAX_OVERFLOW=100
export DB_POOL_TIMEOUT=60
export DB_POOL_RECYCLE=3600

# Run load tests
python tests/performance/test_mysql_load.py

# Monitor during load test
watch -n 1 'mysql -u vedfolnir_user -p -e "SHOW PROCESSLIST; SHOW STATUS LIKE \"Threads_connected\";"'
```

### Scaling Recommendations

#### Small Deployment (1-10 users)
```ini
innodb_buffer_pool_size = 512M
max_connections = 50
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10
```

#### Medium Deployment (10-100 users)
```ini
innodb_buffer_pool_size = 2G
max_connections = 200
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 50
```

#### Large Deployment (100+ users)
```ini
innodb_buffer_pool_size = 8G
max_connections = 500
DB_POOL_SIZE = 50
DB_MAX_OVERFLOW = 100
```

## Backup and Maintenance

### Automated Backup Strategy

```bash
# Daily backup script
#!/bin/bash
BACKUP_DIR="/var/backups/vedfolnir"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Full database backup
mysqldump -u vedfolnir_backup -p \
  --single-transaction \
  --routines \
  --triggers \
  --events \
  --hex-blob \
  vedfolnir > $BACKUP_DIR/vedfolnir_full_$DATE.sql

# Compress backup
gzip $BACKUP_DIR/vedfolnir_full_$DATE.sql

# Remove backups older than 30 days
find $BACKUP_DIR -name "vedfolnir_full_*.sql.gz" -mtime +30 -delete

echo "Backup completed: vedfolnir_full_$DATE.sql.gz"
```

### Maintenance Tasks

```sql
-- Weekly maintenance tasks
ANALYZE TABLE users, platform_connections, posts, images;
OPTIMIZE TABLE users, platform_connections, posts, images;

-- Check table integrity
CHECK TABLE users, platform_connections, posts, images;

-- Update table statistics
ANALYZE TABLE users, platform_connections, posts, images;
```

## Security Optimization

### Connection Security

```sql
-- Secure user configuration
CREATE USER 'vedfolnir_app'@'localhost' IDENTIFIED BY 'strong_password';
GRANT SELECT, INSERT, UPDATE, DELETE ON vedfolnir.* TO 'vedfolnir_app'@'localhost';

-- Read-only user for monitoring
CREATE USER 'vedfolnir_monitor'@'localhost' IDENTIFIED BY 'monitor_password';
GRANT SELECT, PROCESS, REPLICATION CLIENT ON *.* TO 'vedfolnir_monitor'@'localhost';

FLUSH PRIVILEGES;
```

### SSL Configuration

```bash
# Enable SSL in connection string
DATABASE_URL=mysql+pymysql://vedfolnir_user:password@localhost/vedfolnir?charset=utf8mb4&ssl_disabled=false&ssl_ca=/path/to/ca.pem
```

## Troubleshooting Performance Issues

### Common Performance Problems

#### 1. Slow Queries

```sql
-- Find slow queries
SELECT 
  query_time,
  lock_time,
  rows_sent,
  rows_examined,
  sql_text
FROM mysql.slow_log
WHERE query_time > 1
ORDER BY query_time DESC
LIMIT 10;

-- Analyze query execution plan
EXPLAIN FORMAT=JSON SELECT * FROM posts WHERE platform_connection_id = 1;
```

#### 2. Connection Pool Exhaustion

```python
# Monitor connection pool
import logging
from sqlalchemy import event

@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    logging.info("New database connection established")

@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    logging.info("Connection checked out from pool")
```

#### 3. Memory Issues

```sql
-- Check memory usage
SELECT 
  ROUND(SUM(data_length + index_length) / 1024 / 1024, 1) AS 'Total Size MB',
  ROUND(SUM(data_length) / 1024 / 1024, 1) AS 'Data Size MB',
  ROUND(SUM(index_length) / 1024 / 1024, 1) AS 'Index Size MB'
FROM information_schema.TABLES 
WHERE TABLE_SCHEMA = 'vedfolnir';
```

### Performance Tuning Checklist

- [ ] **Buffer Pool**: Set to 75% of available RAM
- [ ] **Connection Pool**: Sized for concurrent user load
- [ ] **Indexes**: Created for all common query patterns
- [ ] **Query Cache**: Disabled (MySQL 8.0+) or properly sized
- [ ] **Slow Query Log**: Enabled with appropriate threshold
- [ ] **Binary Logging**: Configured for backup/replication needs
- [ ] **SSL**: Enabled for security
- [ ] **Monitoring**: Performance metrics collection active
- [ ] **Backup**: Automated backup strategy implemented
- [ ] **Maintenance**: Regular optimization tasks scheduled

## Performance Testing

### Automated Performance Tests

```bash
# Run comprehensive performance test suite
python tests/performance/test_mysql_comprehensive.py

# Run load tests
python tests/performance/test_mysql_load.py

# Generate performance report
python scripts/mysql_migration/generate_performance_report.py --output reports/mysql_performance.html
```

### Benchmarking

```bash
# Benchmark database operations
python scripts/benchmarking/mysql_benchmark.py

# Compare with baseline
python scripts/benchmarking/compare_performance.py --baseline baseline.json --current current.json
```

---

**🚀 MySQL Optimization Complete!** Your Vedfolnir MySQL installation is now optimized for performance, scalability, and reliability.
